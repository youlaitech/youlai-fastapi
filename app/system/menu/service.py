"""菜单管理服务 — 树形结构 CRUD + 路由生成。"""

from datetime import datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.ai import chat_json, load_prompt
from app.exceptions import BusinessException
from app.response import ResultCode
from app.system.menu.models import SysMenu
from app.system.role.models import SysRole, SysRoleMenu
from app.system.menu.schemas import MenuAiFillForm, MenuAiFillVO, MenuCreate, MenuUpdate, MenuVO, RouteVO

SYSTEM_PROMPT_PATH = "menu/system.md"
# 同级菜单取样条数，样本只用于让模型沿用既有命名风格
SIBLING_SAMPLE_LIMIT = 10
MENU_TYPE_LABELS = {"C": "目录", "M": "菜单", "E": "外链", "B": "按钮"}


def _menu_type_label(menu_type: str | None) -> str:
    """菜单类型取中文名称，无匹配时沿用原值。"""
    if not menu_type:
        return "未指定"
    return MENU_TYPE_LABELS.get(menu_type, menu_type)


def normalize_params(value):
    """菜单路由参数兼容共享库的两种形态：dict（本服务写入）与 boot 风格的 [{key,value}] 数组。"""
    if isinstance(value, list):
        pairs = {
            str(item.get("key")): item.get("value")
            for item in value
            if isinstance(item, dict) and item.get("key")
        }
        return pairs or None
    return value if isinstance(value, dict) else None


class MenuService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tree(self, keywords: str | None = None) -> list[MenuVO]:
        """查询菜单列表并组装为树形结构，支持按名称关键字筛选。"""
        conditions = []
        if keywords:
            conditions.append(SysMenu.name.ilike(f"%{keywords}%"))

        rows = await self.db.execute(
            select(SysMenu).where(*conditions).order_by(SysMenu.sort.asc(), SysMenu.id.asc())
        )
        menus = rows.scalars().all()
        vo_list = [self._to_vo(m) for m in menus]
        return self._build_tree(vo_list)

    async def get_by_id(self, menu_id: int) -> MenuVO:
        """根据 id 获取菜单详情。"""
        result = await self.db.execute(select(SysMenu).where(SysMenu.id == menu_id))
        menu = result.scalar_one_or_none()
        if menu is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="菜单不存在")
        return self._to_vo(menu)

    async def get_options(self, types: list[str] | None = None) -> list[dict]:
        """返回菜单下拉选项树（递归嵌套 children），可按菜单类型过滤。"""
        stmt = select(SysMenu.id, SysMenu.parent_id, SysMenu.name, SysMenu.type).order_by(SysMenu.sort.asc())
        if types:
            stmt = stmt.where(SysMenu.type.in_(types))
        rows = await self.db.execute(stmt)
        menus = [{"id": r.id, "parentId": r.parent_id, "name": r.name} for r in rows]
        if not menus:
            return []

        def _build(parent_id: int) -> list[dict]:
            tree = []
            for m in menus:
                if m["parentId"] == parent_id:
                    node = {"value": m["id"], "label": m["name"]}
                    children = _build(m["id"])
                    if children:
                        node["children"] = children
                    tree.append(node)
            return tree

        # 固定以顶级(0)为根递归：类型过滤后父级不在结果集内的节点不作为根节点，与参考实现一致
        return _build(0)

    async def get_menu_form(self, menu_id: int) -> MenuUpdate:
        """获取菜单编辑表单数据。"""
        result = await self.db.execute(select(SysMenu).where(SysMenu.id == menu_id))
        menu = result.scalar_one_or_none()
        if menu is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="菜单不存在")
        return MenuUpdate(
            id=menu.id,
            parentId=menu.parent_id,
            name=menu.name,
            type=menu.type,
            routeName=menu.route_name,
            routePath=menu.route_path,
            component=menu.component,
            externalUrl=menu.external_url,
            perm=menu.perm,
            keepAlive=menu.keep_alive,
            visible=menu.visible,
            sort=menu.sort,
            icon=menu.icon,
            redirect=menu.redirect,
            params=normalize_params(menu.params),
        )

    async def update_visible(self, menu_id: int, visible: int) -> None:
        """切换菜单显示/隐藏状态（visible=1 显示，0 隐藏）。"""
        result = await self.db.execute(select(SysMenu).where(SysMenu.id == menu_id))
        menu = result.scalar_one_or_none()
        if menu is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="菜单不存在")
        menu.visible = visible
        await self.db.flush()

    async def create(self, form: MenuCreate) -> MenuVO:
        """创建菜单并回填 tree_path 祖先路径；目录/外链的 component 取值规则见内联注释。"""
        # 父级层级校验：按钮只能挂在菜单下，其他类型只能挂在顶级或目录下
        await self._check_parent(form.type, form.parentId)

        # 新增菜单未指定排序时排到同级末尾；显式传 0 时保留 0
        if "sort" not in form.model_fields_set:
            form.sort = await self._next_sort(form.parentId)

        # 一级目录的 routePath 不以 / 开头时自动补前缀
        if form.type == "C" and form.parentId == 0 and form.routePath and not form.routePath.startswith("/"):
            form.routePath = "/" + form.routePath

        is_embedded = form.type == "E" and form.component == "iframe"
        needs_route_name = form.type == "M" or is_embedded

        # 路由名称唯一性校验（仅菜单和内嵌外链）
        if needs_route_name and form.routeName:
            exists = await self.db.execute(
                select(SysMenu.id).where(SysMenu.route_name == form.routeName)
            )
            if exists.scalar() is not None:
                raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="路由名称已存在")

        # C/E 类型清空路由名称（仅菜单和内嵌外链需要 routeName）
        route_name = form.routeName if needs_route_name else None

        # 目录类型(C)的 component 固定为 Layout；外链新标签页 component 置空
        if form.type == "C":
            component = "Layout"
        elif form.type == "E" and not is_embedded:
            component = None
        else:
            component = form.component
        menu = SysMenu(
            parent_id=form.parentId,
            tree_path="",
            name=form.name,
            type=form.type,
            route_name=route_name,
            route_path=form.routePath,
            component=component,
            external_url=form.externalUrl,
            perm=form.perm,
            keep_alive=form.keepAlive,
            visible=form.visible,
            sort=form.sort,
            icon=form.icon,
            redirect=form.redirect,
            params=form.params,
            create_time=datetime.now(),
        )
        self.db.add(menu)
        await self.db.flush()

        if menu.parent_id and menu.parent_id > 0:
            parent = await self.db.get(SysMenu, menu.parent_id)
            menu.tree_path = f"{parent.tree_path},{menu.id}" if parent else str(menu.id)
        else:
            menu.tree_path = "0"
        await self.db.flush()

        # 新增页面菜单时按需生成增删改查按钮
        if form.generateCrudButtons and form.buttonPermPrefix and form.buttonPermPrefix.strip():
            await self._create_crud_buttons(menu, form.buttonPermPrefix.strip())

        logger.info(f"Menu created: {menu.name}")
        return self._to_vo(menu)

    async def update(self, form: MenuUpdate) -> MenuVO:
        result = await self.db.execute(select(SysMenu).where(SysMenu.id == form.id))
        menu = result.scalar_one_or_none()
        if menu is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="菜单不存在")

        # 父级菜单不能指向自身
        if form.parentId == form.id:
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="父级菜单不能为当前菜单")

        # 父级层级校验：父级变更时才校验，未变更时放行历史遗留的非法层级
        if form.parentId != menu.parent_id:
            await self._check_parent(form.type, form.parentId)

        # 一级目录的 routePath 不以 / 开头时自动补前缀
        if form.type == "C" and form.parentId == 0 and form.routePath and not form.routePath.startswith("/"):
            form.routePath = "/" + form.routePath

        is_embedded = form.type == "E" and form.component == "iframe"
        needs_route_name = form.type == "M" or is_embedded

        # 路由名称唯一性校验（排除自身）
        if needs_route_name and form.routeName:
            exists = await self.db.execute(
                select(SysMenu.id).where(SysMenu.route_name == form.routeName, SysMenu.id != form.id)
            )
            if exists.scalar() is not None:
                raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="路由名称已存在")

        # C/E 类型清空路由名称
        route_name = form.routeName if needs_route_name else None

        menu.parent_id = form.parentId
        menu.name = form.name
        menu.type = form.type
        menu.route_name = route_name
        menu.route_path = form.routePath
        if form.type == "C":
            menu.component = "Layout"
        elif form.type == "E" and not is_embedded:
            menu.component = None
        else:
            menu.component = form.component
        menu.external_url = form.externalUrl
        menu.perm = form.perm
        menu.keep_alive = form.keepAlive
        menu.visible = form.visible
        menu.sort = form.sort
        menu.icon = form.icon
        menu.redirect = form.redirect
        menu.params = form.params
        menu.update_time = datetime.now()

        if menu.parent_id and menu.parent_id > 0:
            parent = await self.db.get(SysMenu, menu.parent_id)
            menu.tree_path = f"{parent.tree_path},{menu.id}" if parent else str(menu.id)
        else:
            menu.tree_path = "0"

        await self.db.flush()
        logger.info(f"Menu updated: {menu.name}")
        return self._to_vo(menu)

    async def delete(self, menu_id: int) -> None:
        """删除菜单并级联删除子菜单（按 tree_path 判定后代），同时解绑角色菜单。"""
        result = await self.db.execute(select(SysMenu).where(SysMenu.id == menu_id))
        menu = result.scalar_one_or_none()
        if menu is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="菜单不存在")

        # 级联范围：自身 + tree_path 祖先链里带上该菜单ID的后代
        rows = await self.db.execute(
            select(SysMenu.id).where(
                or_(
                    SysMenu.id == menu_id,
                    SysMenu.tree_path == str(menu_id),
                    SysMenu.tree_path.like(f"{menu_id},%"),
                    SysMenu.tree_path.like(f"%,{menu_id},%"),
                    SysMenu.tree_path.like(f"%,{menu_id}"),
                )
            )
        )
        menu_ids = rows.scalars().all()

        # 先解绑角色菜单，避免外键约束
        await self.db.execute(delete(SysRoleMenu).where(SysRoleMenu.menu_id.in_(menu_ids)))
        await self.db.execute(delete(SysMenu).where(SysMenu.id.in_(menu_ids)))
        await self.db.flush()
        logger.info(f"Menu deleted: {menu.name} (含子菜单 {len(menu_ids) - 1} 个)")

    async def get_routes(self, roles: set[str] = None, is_root: bool = False) -> list[RouteVO]:
        """生成前端动态路由树，按用户角色及状态过滤。"""
        # B=按钮类型不进入前端路由；仅返回菜单/目录/外链且可见的菜单
        stmt = select(SysMenu).where(SysMenu.type != "B", SysMenu.visible == 1)

        if not is_root:
            if not roles:
                return []
            menu_ids_subq = (
                select(SysRoleMenu.menu_id)
                .join(SysRole, SysRole.id == SysRoleMenu.role_id)
                .where(SysRole.code.in_(roles), SysRole.status == 1)
            ).subquery()
            stmt = stmt.where(SysMenu.id.in_(select(menu_ids_subq)))

        stmt = stmt.order_by(SysMenu.sort.asc())
        rows = await self.db.execute(stmt)
        menus = rows.scalars().all()
        node_list = [self._to_route_with_parent(m) for m in menus]
        return self._build_route_tree(node_list)

    async def _check_parent(self, menu_type: str | None, parent_id: int | None) -> None:
        """校验上级菜单层级：按钮只能挂在菜单下，其他类型只能挂在顶级或目录下。"""
        if not parent_id or parent_id == 0:
            if menu_type == "B":
                raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="按钮权限只能挂在菜单下")
            return

        parent = await self.db.get(SysMenu, parent_id)
        if parent is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="上级菜单不存在")

        parent_is_menu = parent.type == "M"
        if menu_type == "B" and not parent_is_menu:
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="按钮权限只能挂在菜单下")
        if menu_type != "B" and parent_is_menu:
            raise BusinessException(code=ResultCode.OPERATE_DENIED, msg="菜单下只能挂按钮权限")

    async def _next_sort(self, parent_id: int | None) -> int:
        """同级菜单的最大排序 + 1。"""
        rows = await self.db.execute(
            select(SysMenu.sort)
            .where(SysMenu.parent_id == (parent_id or 0))
            .order_by(SysMenu.sort.desc())
            .limit(1)
        )
        max_sort = rows.scalar()
        return (max_sort or 0) + 1

    async def _create_crud_buttons(self, menu: SysMenu, perm_prefix: str) -> None:
        """生成增删改查按钮权限。"""
        names = ["查询", "新增", "修改", "删除"]
        actions = ["list", "create", "update", "delete"]
        # 树路径记录祖先链，等于所属菜单的树路径加上所属菜单ID，删除菜单时据此级联
        button_tree_path = f"{menu.tree_path},{menu.id}" if menu.tree_path else str(menu.id)

        for index, (name, action) in enumerate(zip(names, actions)):
            self.db.add(SysMenu(
                parent_id=menu.id,
                tree_path=button_tree_path,
                name=name,
                type="B",
                perm=f"{perm_prefix}:{action}",
                visible=1,
                sort=index + 1,
                create_time=datetime.now(),
            ))
        await self.db.flush()

    async def ai_fill(self, form: MenuAiFillForm) -> MenuAiFillVO:
        """推断菜单配置，命名风格参照同级菜单。"""
        content = await chat_json(load_prompt(SYSTEM_PROMPT_PATH), await self._build_ai_prompt(form))
        icon_keywords = content.get("iconKeywords")
        return MenuAiFillVO(
            routePath=content.get("routePath") or None,
            perm=content.get("perm") or None,
            iconKeywords=[str(item) for item in icon_keywords] if isinstance(icon_keywords, list) else [],
        )

    async def _build_ai_prompt(self, form: MenuAiFillForm) -> str:
        """构造用户提示词，附带同级菜单样本供模型沿用既有命名风格。"""
        parent_id = form.parentId or 0
        parent = await self.db.get(SysMenu, parent_id) if parent_id else None

        rows = await self.db.execute(
            select(SysMenu)
            .where(SysMenu.parent_id == parent_id)
            .order_by(SysMenu.sort.asc())
            .limit(SIBLING_SAMPLE_LIMIT)
        )
        siblings = rows.scalars().all()

        text = [
            f"菜单名称：{form.name}",
            f"菜单类型：{_menu_type_label(form.type)}",
            f"上级菜单：{parent.name if parent else '顶级'}",
            "同级菜单示例：",
        ]
        if not siblings:
            text.append("（无）")
        else:
            for menu in siblings:
                text.append(
                    f"- {menu.name}（类型 {_menu_type_label(menu.type)}，"
                    f"路径片段 {menu.route_path or '无'}，权限 {menu.perm or '无'}）"
                )
        return "\n".join(text) + "\n"

    def _to_vo(self, m: SysMenu) -> MenuVO:
        """ORM 对象转菜单视图对象（MenuVO）。"""
        return MenuVO(
            id=m.id, parentId=m.parent_id, name=m.name, type=m.type,
            routeName=m.route_name, routePath=m.route_path, component=m.component,
            externalUrl=m.external_url, perm=m.perm,
            keepAlive=m.keep_alive, visible=m.visible,
            sort=m.sort, icon=m.icon, redirect=m.redirect,
            params=normalize_params(m.params),
        )

    def _to_route(self, m: SysMenu) -> RouteVO:
        is_external = m.type == "E"
        is_embedded = is_external and m.component == "iframe"
        # 外链（非内嵌 iframe）：路径用 external_url（http 开头，前端新标签打开）
        # 内嵌 iframe：路径用 route_path，component 固定 iframe
        if is_external and not is_embedded:
            path = m.external_url or m.route_path or ""
            comp = None
        elif is_embedded:
            path = m.route_path or ""
            comp = "iframe"
        else:
            path = m.route_path or ""
            comp = "Layout" if m.type == "C" else m.component

        meta = {
            "title": m.name,
            "icon": m.icon,
            "hidden": m.visible != 1,
            "keepAlive": m.keep_alive == 1 if m.keep_alive is not None else False,
        }
        if is_embedded and m.external_url:
            meta["externalUrl"] = m.external_url

        return RouteVO(
            name=m.route_name or "",
            path=path,
            component=comp,
            redirect=m.redirect,
            meta=meta,
        )

    def _to_route_with_parent(self, m: SysMenu) -> tuple[int, int, RouteVO]:
        """返回 (id, parentId, RouteVO)，供上层组装路由树。"""
        return (m.id, m.parent_id, self._to_route(m))

    @staticmethod
    def _build_tree(vo_list: list[MenuVO]) -> list[MenuVO]:
        """将扁平菜单列表按 parent_id 组装为树形结构。"""
        node_map = {vo.id: vo for vo in vo_list}
        tree = []
        for vo in vo_list:
            parent = node_map.get(vo.parentId)
            if parent:
                parent.children.append(vo)
            else:
                tree.append(vo)
        return tree

    @staticmethod
    def _build_route_tree(node_list: list[tuple[int, int, RouteVO]]) -> list[RouteVO]:
        """根据 (id, parentId, RouteVO) 构建路由树。"""
        id_map: dict[int, RouteVO] = {}
        parent_map: dict[int, int] = {}
        for nid, pid, route in node_list:
            id_map[nid] = route
            parent_map[nid] = pid

        tree: list[RouteVO] = []
        for nid, route in id_map.items():
            pid = parent_map[nid]
            parent = id_map.get(pid)
            if parent:
                parent.children.append(route)
            else:
                tree.append(route)
        return tree
