"""动态表单业务：规则校验、发布快照、渲染缓存、访问菜单生成、AI 生成。"""
import json
import logging
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import BusinessException
from app.redis import get_redis
from app.response import ResultCode
from app.system.form.models import FormData, FormDefinition, FormSnapshot
from app.system.form.schemas import (
    FormDataDetailVO, FormDataPageVO, FormDefinitionCreate, FormDefinitionForm,
    FormDefinitionPageVO, FormMenuSave, FormMenuVO, FormRenderVO,
)
from app.system.menu.models import SysMenu

logger = logging.getLogger(__name__)

STATUS_DRAFT = 0
STATUS_PUBLISHED = 1
STATUS_DISABLED = -1
DEFAULT_CATALOG_NAME = "表单中心"
FORM_ADMIN_CATALOG_NAME = "动态表单"
PUBLIC_SUBMIT_LIMIT = 10
RENDER_CACHE_TTL = 1800
SYSTEM_PROMPT_PATH = "form/system.md"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class FormService:
    """动态表单服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 规则校验 ──────────────────────────────────────────────

    @staticmethod
    def _check_nodes(nodes: list) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="表单规则格式非法：节点必须为对象")
            if not isinstance(node.get("type"), str):
                raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="表单规则格式非法：节点缺少 type")
            children = node.get("children") or []
            if children:
                FormService._check_nodes(children)
            elif not isinstance(node.get("field"), str):
                raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="表单规则格式非法：字段节点缺少 field")

    @staticmethod
    def validate_rule(form_json) -> list:
        """校验表单规则结构，返回规则数组。"""
        rules = json.loads(form_json) if isinstance(form_json, str) else form_json
        if not isinstance(rules, list) or not rules:
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="表单规则格式非法：应为非空数组")
        FormService._check_nodes(rules)
        return rules

    @staticmethod
    def _check_type(kind: str, value) -> bool:
        if kind in ("number", "integer", "float"):
            if isinstance(value, bool):
                return False
            if isinstance(value, (int, float)):
                return True
            return isinstance(value, str) and value.strip().replace(".", "", 1).isdigit()
        if kind == "array":
            return isinstance(value, list)
        return True

    @classmethod
    def _walk(cls, nodes: list, data: dict, filtered: dict, errors: list) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            field = node.get("field")
            if isinstance(field, str) and field:
                # 字段白名单：规则未声明的 field 直接丢弃
                if field in data:
                    filtered[field] = data[field]
                cls._validate_field(node, field, data, errors)
            children = node.get("children") or []
            if children:
                cls._walk(children, data, filtered, errors)

    @classmethod
    def _validate_field(cls, rule: dict, field: str, data: dict, errors: list) -> None:
        validates = rule.get("validate") or []
        title = rule.get("title") or field
        value = data.get(field)
        empty = value is None or (isinstance(value, str) and not value.strip()) or (
            isinstance(value, list) and not value
        )
        for item in validates:
            if not isinstance(item, dict):
                continue
            if item.get("required") is True and empty:
                errors.append(item.get("message") or f"「{title}」不能为空")
            if not empty and item.get("type") and not cls._check_type(item["type"], value):
                errors.append(f"「{title}」数据类型非法")

    @classmethod
    def validate_and_filter(cls, form_json, data) -> dict:
        """按规则白名单过滤提交数据并逐字段校验必填与类型。"""
        rules = form_json if isinstance(form_json, list) else json.loads(form_json or "[]")
        if not isinstance(rules, list):
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="表单规则格式非法")

        filtered: dict = {}
        errors: list = []
        cls._walk(rules, data if isinstance(data, dict) else {}, filtered, errors)
        if errors:
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="；".join(errors))
        return filtered

    # ── 表单定义 ──────────────────────────────────────────────

    async def _find(self, form_id: int) -> FormDefinition:
        rows = await self.db.execute(
            select(FormDefinition).where(
                FormDefinition.id == form_id, FormDefinition.is_deleted == 0
            )
        )
        obj = rows.scalars().first()
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="表单不存在")
        return obj

    async def _find_by_key(self, form_key: str) -> FormDefinition:
        rows = await self.db.execute(
            select(FormDefinition).where(
                FormDefinition.form_key == form_key, FormDefinition.is_deleted == 0
            )
        )
        obj = rows.scalars().first()
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="表单不存在")
        return obj

    async def get_page(self, page_num: int, page_size: int, keywords: str | None = None,
                       status: int | None = None, category: str | None = None) -> dict:
        conditions = [FormDefinition.is_deleted == 0]
        if keywords:
            conditions.append(
                FormDefinition.form_name.ilike(f"%{keywords}%")
                | FormDefinition.form_key.ilike(f"%{keywords}%")
            )
        if status is not None:
            conditions.append(FormDefinition.status == status)
        if category:
            conditions.append(FormDefinition.category == category)

        total = await self.db.scalar(
            select(func.count()).select_from(FormDefinition).where(*conditions)
        )
        rows = await self.db.execute(
            select(FormDefinition)
            .where(*conditions)
            .order_by(FormDefinition.id.desc())
            .offset((page_num - 1) * page_size)
            .limit(page_size)
        )
        items = []
        for obj in rows.scalars().all():
            items.append(FormDefinitionPageVO(
                id=obj.id,
                formKey=obj.form_key,
                formName=obj.form_name,
                description=obj.description,
                status=obj.status,
                isPublic=obj.is_public,
                category=obj.category or "normal",
                version=obj.version,
                createTime=obj.create_time.strftime("%Y-%m-%d %H:%M:%S") if obj.create_time else None,
            ).model_dump())
        return {"list": items, "total": total or 0}

    async def get_form(self, form_id: int) -> FormDefinitionForm:
        obj = await self._find(form_id)
        return FormDefinitionForm(
            id=obj.id, formKey=obj.form_key, formName=obj.form_name, description=obj.description,
            formJson=obj.form_json, optionsJson=obj.options_json,
            isPublic=obj.is_public, category=obj.category or "normal",
        )

    async def create(self, form: FormDefinitionCreate, user_id: int | None) -> int:
        form_key = form.formKey.strip()
        exists = await self.db.execute(
            select(FormDefinition.id).where(
                FormDefinition.form_key == form_key, FormDefinition.is_deleted == 0
            )
        )
        if exists.first() is not None:
            raise BusinessException(code=ResultCode.DUPLICATE_KEY, msg="表单标识已存在")

        obj = FormDefinition(
            form_key=form_key,
            form_name=form.formName.strip(),
            description=form.description,
            form_json=form.formJson or [],
            options_json=form.optionsJson,
            is_public=form.isPublic or 0,
            category=form.category or "normal",
            status=STATUS_DRAFT,
            version=1,
            create_by=user_id,
            update_by=user_id,
        )
        self.db.add(obj)
        await self.db.flush()
        return obj.id

    async def update(self, form_id: int, form: FormDefinitionCreate, user_id: int | None) -> None:
        obj = await self._find(form_id)
        form_key = (form.formKey or "").strip()
        if form_key and form_key != obj.form_key:
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="表单标识创建后不可修改")

        obj.form_name = (form.formName or obj.form_name).strip()
        obj.description = form.description
        if form.formJson is not None:
            obj.form_json = form.formJson
        if form.optionsJson is not None:
            obj.options_json = form.optionsJson
        if form.isPublic is not None:
            obj.is_public = form.isPublic
        if obj.status == STATUS_DRAFT and form.category:
            obj.category = form.category
        obj.update_by = user_id
        obj.update_time = datetime.now()
        await self.db.flush()

        # 已发布表单规则变更后清渲染缓存，保证渲染端即时生效
        if obj.status == STATUS_PUBLISHED:
            await self._evict_render_cache(obj.form_key)

    async def delete(self, ids: str) -> None:
        id_list = self._parse_ids(ids)
        if not id_list:
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="删除的表单数据为空")

        rows = await self.db.execute(
            select(FormDefinition).where(
                FormDefinition.id.in_(id_list), FormDefinition.is_deleted == 0
            )
        )
        forms = rows.scalars().all()
        for form in forms:
            if form.menu_id:
                await self.db.execute(text("DELETE FROM sys_role_menu WHERE menu_id = :mid"), {"mid": form.menu_id})
                await self.db.execute(text("DELETE FROM sys_menu WHERE id = :mid"), {"mid": form.menu_id})
                await self._evict_render_cache(form.form_key)

        await self._soft_delete(FormDefinition, id_list)
        await self._soft_delete(FormData, id_list, column=FormData.form_id)
        await self._soft_delete(FormSnapshot, id_list, column=FormSnapshot.form_id)

    async def _soft_delete(self, model, id_list: list[int], column=None) -> None:
        target = column if column is not None else model.id
        rows = await self.db.execute(
            select(model).where(target.in_(id_list), model.is_deleted == 0)
        )
        for obj in rows.scalars().all():
            obj.is_deleted = 1
        await self.db.flush()

    async def publish(self, form_id: int) -> None:
        obj = await self._find(form_id)
        obj.status = STATUS_PUBLISHED
        obj.version = (obj.version or 1) + 1
        obj.update_time = datetime.now()
        await self.db.flush()

        # 固化版本快照：数据回显按提交时版本加载，防止规则变更导致历史数据漂移
        self.db.add(FormSnapshot(
            form_id=obj.id, version=obj.version,
            form_json=obj.form_json, options_json=obj.options_json,
        ))
        await self.db.flush()
        await self._evict_render_cache(obj.form_key)

    async def disable(self, form_id: int) -> None:
        obj = await self._find(form_id)
        obj.status = STATUS_DISABLED
        obj.update_time = datetime.now()
        await self.db.flush()

    # ── 渲染 ──────────────────────────────────────────────────

    @staticmethod
    def _render_cache_key(form_key: str) -> str:
        return f"form:render:{form_key}"

    async def _evict_render_cache(self, form_key: str) -> None:
        try:
            redis = await get_redis()
            await redis.delete(self._render_cache_key(form_key))
        except Exception as exc:  # noqa: BLE001 缓存异常不影响主流程
            logger.warning("清理表单渲染缓存失败 formKey=%s: %s", form_key, exc)

    @staticmethod
    def _render_payload(obj: FormDefinition) -> dict:
        return FormRenderVO(
            formKey=obj.form_key, formName=obj.form_name, version=obj.version,
            formJson=obj.form_json, optionsJson=obj.options_json,
        ).model_dump()

    async def render(self, form_key: str) -> dict:
        """已发布表单渲染规则（Redis 缓存兜底 30 分钟）。"""
        key = self._render_cache_key(form_key)
        try:
            redis = await get_redis()
            cached = await redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as exc:  # noqa: BLE001
            logger.warning("读取表单渲染缓存失败 formKey=%s: %s", form_key, exc)
            redis = None

        rows = await self.db.execute(
            select(FormDefinition).where(
                FormDefinition.form_key == form_key,
                FormDefinition.status == STATUS_PUBLISHED,
                FormDefinition.is_deleted == 0,
            )
        )
        obj = rows.scalars().first()
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="表单不存在或未发布")

        data = self._render_payload(obj)
        try:
            redis = redis or await get_redis()
            await redis.set(key, json.dumps(data, ensure_ascii=False), ex=RENDER_CACHE_TTL)
        except Exception as exc:  # noqa: BLE001
            logger.warning("写入表单渲染缓存失败 formKey=%s: %s", form_key, exc)
        return data

    async def public_render(self, form_key: str) -> dict:
        """公开表单渲染规则：直查库不走缓存，避免命中缓存绕过 is_public 校验。"""
        rows = await self.db.execute(
            select(FormDefinition).where(
                FormDefinition.form_key == form_key,
                FormDefinition.status == STATUS_PUBLISHED,
                FormDefinition.is_public == 1,
                FormDefinition.is_deleted == 0,
            )
        )
        obj = rows.scalars().first()
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="表单不存在或未开放公开访问")
        return self._render_payload(obj)

    async def get_workflow_options(self) -> list[dict]:
        rows = await self.db.execute(
            select(FormDefinition).where(
                FormDefinition.category == "workflow",
                FormDefinition.status == STATUS_PUBLISHED,
                FormDefinition.is_deleted == 0,
            ).order_by(FormDefinition.id.asc())
        )
        return [
            {"value": obj.form_key, "label": obj.form_name}
            for obj in rows.scalars().all()
        ]

    # ── 访问菜单 ──────────────────────────────────────────────

    @staticmethod
    def _catalog_tree_path(parent: SysMenu) -> str:
        return f"{parent.tree_path},{parent.id}" if parent.tree_path else str(parent.id)

    @staticmethod
    def _to_upper_camel(value: str) -> str:
        return "".join(part[:1].upper() + part[1:] for part in value.split("_") if part)

    async def get_menu(self, form_id: int) -> FormMenuVO | None:
        form = await self._find(form_id)
        if not form.menu_id:
            return None

        rows = await self.db.execute(select(SysMenu).where(SysMenu.id == form.menu_id))
        menu = rows.scalars().first()
        if menu is None:
            return None

        role_rows = await self.db.execute(
            text("SELECT role_id FROM sys_role_menu WHERE menu_id = :mid"), {"mid": menu.id}
        )
        return FormMenuVO(
            menuId=menu.id, menuName=menu.name, parentId=menu.parent_id,
            roleIds=[r.role_id for r in role_rows],
        )

    async def _ensure_default_catalog(self) -> SysMenu:
        """确保默认挂载目录"表单中心"存在，不存在则创建。"""
        rows = await self.db.execute(
            select(SysMenu).where(SysMenu.name == DEFAULT_CATALOG_NAME, SysMenu.type == "C")
        )
        catalog = rows.scalars().first()
        if catalog:
            return catalog

        rows = await self.db.execute(
            select(SysMenu).where(
                SysMenu.parent_id == 0, SysMenu.name == FORM_ADMIN_CATALOG_NAME, SysMenu.type == "C"
            )
        )
        admin_catalog = rows.scalars().first()
        if admin_catalog:
            parent_id, tree_path = admin_catalog.id, self._catalog_tree_path(admin_catalog)
            route_path = "center"
        else:
            parent_id, tree_path, route_path = 0, "0", "/form-center"

        catalog = SysMenu(
            parent_id=parent_id, tree_path=tree_path, name=DEFAULT_CATALOG_NAME, type="C",
            route_path=route_path, component="Layout", visible=1, sort=5, icon="el-icon-EditPen",
            create_time=datetime.now(),
        )
        self.db.add(catalog)
        await self.db.flush()
        return catalog

    async def save_menu(self, form_id: int, form: FormMenuSave) -> None:
        obj = await self._find(form_id)
        if form.parentId:
            parent = await self.db.get(SysMenu, form.parentId)
            if parent is None:
                raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="上级菜单不存在")
            if parent.type != "C":
                raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="上级菜单必须为目录类型")
        else:
            parent = await self._ensure_default_catalog()

        route_name = "FormRender" + self._to_upper_camel(obj.form_key)
        tree_path = self._catalog_tree_path(parent)

        # 已生成过时走更新语义（幂等）
        existing = None
        if obj.menu_id:
            existing = await self.db.get(SysMenu, obj.menu_id)

        if existing is not None:
            menu = existing
            menu.parent_id = parent.id
            menu.name = form.menuName.strip()
            menu.route_name = route_name
            menu.route_path = obj.form_key
            menu.component = "dynamic-form/render"
            menu.params = {"formKey": obj.form_key}
            menu.tree_path = tree_path
            menu.update_time = datetime.now()
        else:
            menu = SysMenu(
                parent_id=parent.id, tree_path=tree_path, name=form.menuName.strip(), type="M",
                route_name=route_name, route_path=obj.form_key, component="dynamic-form/render",
                params={"formKey": obj.form_key}, visible=1, sort=1, keep_alive=0,
                create_time=datetime.now(),
            )
            self.db.add(menu)

        # 回写 menu_id：下次发布走更新语义，防重复生成菜单
        await self.db.flush()
        obj.menu_id = menu.id
        obj.update_time = datetime.now()
        if form.roleIds:
            await self._assign_menu_to_roles(menu, form.roleIds)
        await self.db.flush()

    async def _assign_menu_to_roles(self, menu: SysMenu, role_ids: list[int]) -> None:
        # 授权集合 = 菜单本身 + tree_path 祖先目录（根节点 0 排除）
        menu_ids = {menu.id}
        for part in (menu.tree_path or "").split(","):
            part = part.strip()
            if part and part != "0":
                menu_ids.add(int(part))

        rows = await self.db.execute(
            text("SELECT role_id, menu_id FROM sys_role_menu WHERE menu_id = ANY(:ids)"),
            {"ids": list(menu_ids)},
        )
        existing = {(r.role_id, r.menu_id) for r in rows}
        for role_id in role_ids:
            for grant_id in menu_ids:
                if (role_id, grant_id) not in existing:
                    await self.db.execute(
                        text("INSERT INTO sys_role_menu (role_id, menu_id) VALUES (:r, :m)"),
                        {"r": role_id, "m": grant_id},
                    )

    # ── 表单数据 ──────────────────────────────────────────────

    async def submit(self, form_key: str, data: dict, user_id: int | None) -> None:
        form = await self._find_by_key(form_key)
        if form.status != STATUS_PUBLISHED:
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="表单未发布或已停用")
        await self._persist(form, data, user_id)

    async def submit_public(self, form_key: str, data: dict, ip: str) -> None:
        form = await self._find_by_key(form_key)
        if form.status != STATUS_PUBLISHED or form.is_public != 1:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="表单不存在或未开放公开访问")
        if not await self._check_public_limit(form_key, ip):
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="提交过于频繁，请稍后再试")

        logger.info("公开表单匿名提交 formKey=%s ip=%s", form_key, ip)
        await self._persist(form, data, None)

    async def _persist(self, form: FormDefinition, data: dict, user_id: int | None) -> None:
        filtered = self.validate_and_filter(form.form_json, data)
        self.db.add(FormData(
            form_id=form.id, form_version=form.version, data_json=filtered, create_by=user_id,
        ))
        await self.db.flush()

    async def _check_public_limit(self, form_key: str, ip: str) -> bool:
        """公开表单按 formKey + IP 限流（固定窗口计数，Redis 异常时放行）。"""
        key = f"form:public:submit:{form_key}:{ip}"
        try:
            redis = await get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 60)
            return count <= PUBLIC_SUBMIT_LIMIT
        except Exception as exc:  # noqa: BLE001
            logger.warning("公开表单限流 Redis 异常，放行 formKey=%s: %s", form_key, exc)
            return True

    async def get_data_page(self, form_key: str, page_num: int, page_size: int) -> dict:
        form = await self._find_by_key(form_key)
        conditions = [FormData.form_id == form.id, FormData.is_deleted == 0]
        total = await self.db.scalar(select(func.count()).select_from(FormData).where(*conditions))
        rows = await self.db.execute(
            select(FormData).where(*conditions).order_by(FormData.id.desc())
            .offset((page_num - 1) * page_size).limit(page_size)
        )
        records = rows.scalars().all()

        # 提交人昵称按批查询补全，避免逐行查库
        user_ids = [r.create_by for r in records if r.create_by]
        nickname_map: dict[int, str] = {}
        if user_ids:
            from app.system.user.models import SysUser

            user_rows = await self.db.execute(
                select(SysUser.id, SysUser.nickname).where(SysUser.id.in_(user_ids))
            )
            nickname_map = {r.id: r.nickname for r in user_rows}

        items = [
            FormDataPageVO(
                id=r.id, formVersion=r.form_version, dataJson=r.data_json,
                createBy=r.create_by, createByName=nickname_map.get(r.create_by),
                createTime=r.create_time.strftime("%Y-%m-%d %H:%M:%S") if r.create_time else None,
            ).model_dump()
            for r in records
        ]
        return {"list": items, "total": total or 0}

    async def get_data_detail(self, data_id: int) -> FormDataDetailVO:
        rows = await self.db.execute(
            select(FormData).where(FormData.id == data_id, FormData.is_deleted == 0)
        )
        row = rows.scalars().first()
        if row is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="表单数据不存在")

        # 命中版本快照用快照规则，否则回退当前定义（兼容快照表启用前提交的历史数据）
        snap_rows = await self.db.execute(
            select(FormSnapshot).where(
                FormSnapshot.form_id == row.form_id,
                FormSnapshot.version == row.form_version,
                FormSnapshot.is_deleted == 0,
            )
        )
        snapshot = snap_rows.scalars().first()
        if snapshot:
            form_json, options_json = snapshot.form_json, snapshot.options_json
        else:
            form = await self.db.get(FormDefinition, row.form_id)
            form_json = form.form_json if form else None
            options_json = form.options_json if form else None

        return FormDataDetailVO(
            id=row.id, formVersion=row.form_version, dataJson=row.data_json,
            createBy=row.create_by,
            createTime=row.create_time.strftime("%Y-%m-%d %H:%M:%S") if row.create_time else None,
            formJson=form_json, optionsJson=options_json,
        )

    async def delete_data(self, ids: str) -> None:
        id_list = self._parse_ids(ids)
        if not id_list:
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="删除的表单数据为空")
        await self._soft_delete(FormData, id_list)

    @staticmethod
    def _parse_ids(ids: str) -> list[int]:
        return [int(part.strip()) for part in str(ids or "").split(",") if part.strip().isdigit()]

    # ── AI ────────────────────────────────────────────────────

    async def ai_generate_rule(self, description: str) -> list:
        """用 AI 把需求描述转成 form-create 规则，产出经结构校验后才返回。"""
        content = await self._chat(self._load_prompt(SYSTEM_PROMPT_PATH), f"需求描述：\n{description}")
        return self.validate_rule(content)

    @staticmethod
    def _load_prompt(name: str) -> str:
        path = PROMPTS_DIR / name
        if not path.exists():
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg=f"提示词不存在：{name}")
        return path.read_text(encoding="utf-8").strip()

    @staticmethod
    async def _chat(system_prompt: str, user_prompt: str) -> str:
        if not settings.AI_ENABLED:
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="AI 功能未开启，请配置 AI_ENABLED 与 AI_API_KEY")

        url = f"{settings.AI_BASE_URL.rstrip('/')}/chat/completions"
        payload = {
            "model": settings.AI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url, json=payload, headers={"Authorization": f"Bearer {settings.AI_API_KEY}"}
            )
        if response.status_code != 200:
            logger.error("AI 调用失败 %s: %s", response.status_code, response.text)
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg=f"AI 调用失败：{response.status_code}")

        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return FormService._strip_code_fence(content)

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        """去掉模型输出里可能包裹的 json 代码围栏。"""
        text = (content or "").strip()
        if not text.startswith("```"):
            return text
        start, end = text.find("\n"), text.rfind("```")
        return text[start + 1:end].strip() if start != -1 and end > start else text
