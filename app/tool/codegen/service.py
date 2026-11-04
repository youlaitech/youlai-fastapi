"""代码生成服务 — 元数据查询 + Jinja2 渲染 + 配置持久化 + zip 打包。"""

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateError
from sqlalchemy import text, select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import chat_json, load_prompt
from app.exceptions import BusinessException
from app.response import ResultCode
from app.system.menu.service import MenuService
from app.tool.codegen.models import GenTable, GenTableColumn
from app.tool.codegen.schemas import (
    FieldConfigVO,
    GenConfigForm,
    GenConfigVO,
    PreviewVO,
    TableQuery,
    TableVO,
)
from app.utils import kebab_case, pluralize_kebab

_TEMPLATE_DIR = Path(__file__).parent / "templates"

# 默认模块名（前端目录与菜单 component 命名用）与表前缀；权限前缀另经 _PERMISSION_NAMESPACES 映射
_DEFAULT_MODULE_NAME = "system"
_DEFAULT_REMOVE_TABLE_PREFIX = "sys_"

# 模块名 → 权限前缀，未配置时用模块名
_PERMISSION_NAMESPACES = {"system": "sys"}

# BaseIdMixin / TimestampMixin / SoftDeleteMixin 已提供的列，生成模型不再重复声明
_MIXIN_COLUMNS = ("id", "create_time", "update_time", "is_deleted")

# sqlalchemy 允许的列类型导入白名单，未知类型统一回落 String
_SA_TYPES = (
    "String", "Integer", "SmallInteger", "BigInteger", "Text", "Boolean",
    "DateTime", "Date", "Float", "Numeric", "JSON", "Uuid",
)

# 可绑定到 HTTP 查询参数的标量类型（dict/list 不能作为 Query 参数）
_QUERYABLE_PY_TYPES = ("str", "int", "float", "Decimal", "bool", "date", "datetime", "time")


def build_ai_user_prompt(config: GenConfigVO, requirement: str | None) -> str:
    """构造用户提示词，附带表结构与字段清单。"""
    columns = [
        {
            "columnName": field.column_name,
            "columnType": field.column_type,
            "fieldComment": field.column_comment,
            "isRequired": field.is_required,
        }
        for field in config.field_configs
    ]
    return "\n".join(
        [
            f"表名：{config.table_name or ''}",
            f"当前业务名：{config.business_name or ''}",
            f"补充说明：{(requirement or '').strip() or '无'}",
            "字段列表：",
            json.dumps(columns, ensure_ascii=False),
        ]
    )


def apply_ai_field_configs(fields: list[FieldConfigVO], ai_fields) -> None:
    """按列名匹配回填字段配置。"""
    if not fields or not isinstance(ai_fields, list):
        return

    ai_field_map = {}
    for ai_field in ai_fields:
        if not isinstance(ai_field, dict):
            continue
        column_name = str(ai_field.get("columnName") or "").strip()
        if column_name:
            ai_field_map[column_name] = ai_field

    int_fields = (
        ("isRequired", "is_required"),
        ("isShowInList", "is_show_in_list"),
        ("isShowInForm", "is_show_in_form"),
        ("isShowInQuery", "is_show_in_query"),
    )

    for field in fields:
        ai_field = ai_field_map.get(field.column_name)
        if not ai_field:
            continue

        field_comment = str(ai_field.get("fieldComment") or "").strip()
        if field_comment:
            field.column_comment = field_comment
        dict_type = str(ai_field.get("dictType") or "").strip()
        if dict_type:
            field.dict_type = dict_type

        form_type = form_type_value(str(ai_field.get("formType") or ""))
        if form_type is not None:
            field.form_type = form_type
        query_type = query_type_value(str(ai_field.get("queryType") or ""))
        if query_type is not None:
            field.query_type = query_type

        for ai_key, field_key in int_fields:
            value = ai_field.get(ai_key)
            if isinstance(value, int):
                setattr(field, field_key, value)


def form_type_value(name: str) -> int | None:
    """表单类型枚举名转存储值。"""
    values = {
        "INPUT": 1,
        "SELECT": 2,
        "RADIO": 3,
        "CHECK_BOX": 4,
        "INPUT_NUMBER": 5,
        "SWITCH": 6,
        "TEXT_AREA": 7,
        "DATE": 8,
        "DATE_TIME": 9,
        "HIDDEN": 10,
    }
    return values.get(name.strip().upper())


def query_type_value(name: str) -> int | None:
    """查询类型枚举名转存储值。"""
    values = {
        "EQ": 1,
        "LIKE": 2,
        "IN": 3,
        "BETWEEN": 4,
        "GT": 5,
        "GE": 6,
        "LT": 7,
        "LE": 8,
        "NE": 9,
        "LIKE_LEFT": 10,
    }
    return values.get(name.strip().upper())

# PostgreSQL → Python 类型 / SQLAlchemy 类型 / TypeScript 类型

_PY_TYPE: dict[str, str] = {
    "int2": "int", "smallint": "int",
    "int4": "int", "integer": "int",
    "int8": "int", "bigint": "int",
    "float4": "float", "real": "float",
    "float8": "float", "double precision": "float",
    "numeric": "Decimal", "decimal": "Decimal",
    "bool": "bool", "boolean": "bool",
    "varchar": "str", "char": "str", "bpchar": "str",
    "text": "str", "name": "str", "citext": "str",
    "uuid": "str",
    "json": "dict", "jsonb": "dict",
    "timestamp": "datetime", "timestamptz": "datetime",
    "date": "date", "time": "time",
}

_SA_COLUMN: dict[str, str] = {
    "int2": "SmallInteger", "smallint": "SmallInteger",
    "int4": "Integer", "integer": "Integer",
    "int8": "BigInteger", "bigint": "BigInteger",
    "float4": "Float", "real": "Float",
    "float8": "Float", "double precision": "Float",
    "numeric": "Numeric(18,2)", "decimal": "Numeric(18,2)",
    "bool": "Boolean", "boolean": "Boolean",
    "varchar": "String(255)", "char": "String(1)", "bpchar": "String",
    "text": "Text", "name": "String(64)", "citext": "String(255)",
    "uuid": "Uuid",
    "json": "JSON", "jsonb": "JSON",
    "timestamp": "DateTime", "timestamptz": "DateTime",
    "date": "Date", "time": "Time",
}

_TS_TYPE: dict[str, str] = {
    "int": "number", "float": "number",
    "Decimal": "number",
    "bool": "boolean",
    "str": "string", "dict": "any",
    "datetime": "string", "date": "string", "time": "string",
}

_FORM_TYPE = {"INPUT": 1, "SELECT": 2, "RADIO": 3, "CHECK_BOX": 4, "INPUT_NUMBER": 5,
              "SWITCH": 6, "TEXT_AREA": 7, "DATE": 8, "DATE_TIME": 9, "HIDDEN": 10}
_FORM_TYPE_REV = {v: k for k, v in _FORM_TYPE.items()}

_QUERY_TYPE = {"EQ": 1, "LIKE": 2, "IN": 3, "BETWEEN": 4, "GT": 5, "GE": 6, "LT": 7, "LE": 8,
               "NE": 9, "LIKE_LEFT": 10, "LIKE_RIGHT": 11}
_QUERY_TYPE_REV = {v: k for k, v in _QUERY_TYPE.items()}


def pg_to_python(udt: str) -> str:
    return _PY_TYPE.get(udt, "str")


def pg_to_sa(udt: str) -> str:
    return _SA_COLUMN.get(udt, "String(255)")


def py_to_ts(py_type: str) -> str:
    return _TS_TYPE.get(py_type, "any")


def form_type_name(i: int | None) -> str:
    return _FORM_TYPE_REV.get(i or 0, "INPUT")


def query_type_name(i: int | None) -> str:
    return _QUERY_TYPE_REV.get(i or 0, "EQ")


def pascal_case(s: str) -> str:
    return "".join(w.capitalize() for w in s.split("_"))


def lower_first(s: str) -> str:
    return s[:1].lower() + s[1:] if s else ""


def constant_case(s: str) -> str:
    """PascalCase / snake_case → SCREAMING_SNAKE_CASE，用于接口地址常量命名。"""
    return kebab_case(s).replace("-", "_")


def trim_table_prefix(table_name: str, remove_prefix: str) -> str:
    """去掉表前缀，避免 sys_article 推导出 SysArticle 这类把模块名重复进实体名的结果。"""
    if remove_prefix and table_name.startswith(remove_prefix):
        return table_name[len(remove_prefix):]
    return table_name


def resolve_perm_prefix(module_name: str, entity_name: str) -> str:
    """权限标识前缀（如 sys:article）：后端守卫、前端 v-hasPerm、菜单按钮权限共用同一个值。"""
    namespace = _PERMISSION_NAMESPACES.get(module_name, module_name)
    return f"{namespace}:{kebab_case(entity_name)}"


def type_import_lines(py_types: set[str]) -> list[str]:
    """按用到的 Python 类型生成标准库导入行，避免生成无用 import。"""
    datetime_types = [t for t in ("date", "datetime", "time") if t in py_types]
    lines = []
    if "Decimal" in py_types:
        lines.append("from decimal import Decimal")
    if datetime_types:
        lines.append(f"from datetime import {', '.join(datetime_types)}")
    return lines


# Jinja2 环境

def _jinja_env() -> Environment:
    """前端模板使用 [[ ]] 分隔符避免 Vue {{ }} 冲突。"""
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        variable_start_string="[[",
        variable_end_string="]]",
        block_start_string="{%",
        block_end_string="%}",
    )
    return env


# 服务

class CodegenService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # 表列表

    async def get_table_page(self, query: TableQuery) -> dict:
        where = ["t.table_schema = current_schema()", "t.table_type = 'BASE TABLE'",
                 "t.table_name NOT IN ('gen_table', 'gen_table_column', 'flyway_schema_history')"]
        params: dict = {"limit": query.page_size, "offset": (query.page_num - 1) * query.page_size}

        if query.keywords:
            where.append("t.table_name ILIKE :kw")
            params["kw"] = f"%{query.keywords}%"

        w = " AND ".join(where)

        total_sql = f"SELECT COUNT(*) FROM information_schema.tables t WHERE {w}"
        total = (await self.db.execute(text(total_sql), params)).scalar() or 0

        list_sql = f"""
            SELECT t.table_name,
                   obj_description(('"' || t.table_name || '"')::regclass) AS table_comment
            FROM information_schema.tables t WHERE {w}
            ORDER BY t.table_name LIMIT :limit OFFSET :offset
        """
        rows = await self.db.execute(text(list_sql), params)
        records = [
            TableVO(
                tableName=r.table_name,
                tableComment=r.table_comment or "",
                engine="InnoDB",
                createTime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ).model_dump(by_alias=True)
            for r in rows
        ]
        return {"list": records, "total": total}

    # 列元数据

    async def _get_columns(self, table_name: str) -> list[dict]:
        sql = """
            SELECT c.column_name, c.udt_name, c.data_type, c.is_nullable,
                   pg_catalog.col_description(
                       ('"' || c.table_schema || '"."' || c.table_name || '"')::regclass::oid,
                       c.ordinal_position
                   ) AS column_comment,
                   CASE WHEN pk.column_name IS NOT NULL THEN 'PRI' ELSE '' END AS column_key
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                 AND tc.table_name = kcu.table_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_name = :tn AND tc.table_schema = current_schema()
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_name = :tn AND c.table_schema = current_schema()
            ORDER BY c.ordinal_position
        """
        rows = await self.db.execute(text(sql), {"tn": table_name})
        cols = []
        for r in rows:
            cols.append({
                "name": r.column_name,
                "udt": r.udt_name,
                "data_type": r.data_type,
                "is_nullable": (r.is_nullable or "").upper() == "YES",
                "comment": r.column_comment or "",
                "is_pk": r.column_key == "PRI",
            })
        if not cols:
            raise BusinessException(code=ResultCode.USER_REQUEST_PARAMETER_ERROR, msg=f"表 {table_name} 不存在或无字段")
        return cols

    # 模板上下文构造

    def _build_field_meta(self, col: dict, saved_col: GenTableColumn | None = None) -> dict:
        py_type = pg_to_python(col["udt"])
        ts_type = py_to_ts(py_type)
        sa = pg_to_sa(col["udt"])

        is_non_sys = col["name"] not in _MIXIN_COLUMNS
        field_name = saved_col.field_name if saved_col else col["name"]
        field_type = (saved_col.field_type or py_type) if saved_col else py_type

        # 默认表单/查询类型推断
        if "status" in field_name:
            default_form = "SWITCH"
        elif any(k in field_name for k in ("time", "date")):
            default_form = "DATE_TIME"
        elif any(k in field_name for k in ("remark", "desc", "content")):
            default_form = "TEXT_AREA"
        elif py_type in ("float", "int", "Decimal"):
            default_form = "INPUT_NUMBER"
        elif py_type == "bool":
            default_form = "SWITCH"
        else:
            default_form = "INPUT"

        default_query = "LIKE" if py_type == "str" else "EQ"

        # JSON 等非标量列不能作为查询参数绑定，不默认参与查询
        is_queryable = is_non_sys and py_type in _QUERYABLE_PY_TYPES
        is_show_list = saved_col.is_show_in_list != 0 if saved_col else (not col["is_pk"] and is_non_sys)
        is_show_form = saved_col.is_show_in_form != 0 if saved_col else (not col["is_pk"] and is_non_sys)
        is_show_query = (saved_col.is_show_in_query != 0 if saved_col else not col["is_pk"]) and is_queryable
        is_required = saved_col.is_required == 1 if saved_col else (not col["is_nullable"] and not col["is_pk"])
        ft_name = form_type_name(saved_col.form_type) if saved_col else default_form
        qt_name = query_type_name(saved_col.query_type) if saved_col else default_query
        # BETWEEN / IN 由前端传重复参数，接收类型是列表
        query_py_type = f"list[{py_type}]" if qt_name in ("BETWEEN", "IN") else py_type

        return {
            "column_name": col["name"],
            "inherited_by_mixin": col["name"] in _MIXIN_COLUMNS,
            "field_name": field_name,
            "field_type": field_type,
            "field_comment": (saved_col.field_comment or col["comment"]) if saved_col else col["comment"],
            "ts_type": ts_type if not saved_col else py_to_ts(field_type),
            "py_type": py_type,
            "sa_column": sa,
            "is_pk": col["is_pk"],
            "is_nullable": col["is_nullable"],
            "is_required": is_required,
            "is_show_in_list": is_show_list,
            "is_show_in_form": is_show_form,
            "is_show_in_query": is_show_query,
            "form_type_name": ft_name,
            "query_type_name": qt_name,
            "query_py_type": query_py_type,
            "ts_query_type": "[string, string]" if qt_name == "BETWEEN" else ts_type,
            "dict_type": (saved_col.dict_type or "") if saved_col else "",
            "max_length": saved_col.max_length if saved_col else None,
        }

    async def _build_template_context(self, table_name: str) -> dict:
        raw_cols = await self._get_columns(table_name)
        pk = next((c["name"] for c in raw_cols if c["is_pk"]), None)
        if pk != "id":
            raise BusinessException(
                code=ResultCode.OPERATE_DENIED,
                msg=f"表 {table_name} 的主键为 {pk or '无'}，代码生成要求主键命名为 id",
            )
        entity_name = pascal_case(trim_table_prefix(table_name, _DEFAULT_REMOVE_TABLE_PREFIX))
        entity_lower = lower_first(entity_name)
        module_name = _DEFAULT_MODULE_NAME
        entity_kebab = kebab_case(entity_name)
        entity_upper_snake = constant_case(entity_name)

        ctx = {
            "table_name": table_name,
            "entity_name": entity_name,
            "entity_lower": entity_lower,
            "module_name": module_name,
            "entity_kebab": entity_kebab,
            "entity_kebab_plural": pluralize_kebab(entity_name),
            "entity_upper_snake": entity_upper_snake,
            "permission_prefix": resolve_perm_prefix(module_name, entity_name),
            "business_name": entity_name,
            "sa_imports": set(),
            "columns": [],
        }

        # 尝试从 DB 读取已保存的字段配置
        gt = (await self.db.execute(select(GenTable).where(GenTable.table_name == table_name))).scalar_one_or_none()
        saved_cols: dict[str, GenTableColumn] = {}
        if gt:
            ctx["entity_name"] = gt.entity_name
            ctx["module_name"] = gt.module_name or ctx["module_name"]
            ctx["business_name"] = gt.business_name
            ctx["entity_lower"] = lower_first(gt.entity_name)
            ctx["entity_kebab"] = kebab_case(gt.entity_name)
            ctx["entity_kebab_plural"] = pluralize_kebab(gt.entity_name)
            ctx["entity_upper_snake"] = constant_case(gt.entity_name)
            ctx["permission_prefix"] = resolve_perm_prefix(ctx["module_name"], ctx["entity_name"])
            rows = (await self.db.execute(
                select(GenTableColumn).where(GenTableColumn.table_id == gt.id).order_by(GenTableColumn.field_sort)
            )).scalars().all()
            saved_cols = {sc.column_name: sc for sc in rows if sc.column_name}

        for col in raw_cols:
            meta = self._build_field_meta(col, saved_cols.get(col["name"]))
            ctx["columns"].append(meta)
            if not meta["is_pk"] and not meta["inherited_by_mixin"]:
                sa_name = meta["sa_column"].split("(")[0]
                ctx["sa_imports"].add(sa_name if sa_name in _SA_TYPES else "String")

        ctx["sa_imports"] = sorted(ctx["sa_imports"])
        ctx["model_import_lines"] = type_import_lines({
            m["py_type"] for m in ctx["columns"] if not m["is_pk"] and not m["inherited_by_mixin"]
        })
        ctx["schema_import_lines"] = type_import_lines({
            m["py_type"] for m in ctx["columns"] if not m["is_pk"] or m["is_show_in_query"]
        })
        ctx["router_import_lines"] = type_import_lines({
            m["py_type"] for m in ctx["columns"] if m["is_show_in_query"]
        })
        return ctx

    # 配置 CRUD

    async def get_gen_config(self, table_name: str) -> GenConfigVO:
        gt = (await self.db.execute(select(GenTable).where(GenTable.table_name == table_name))).scalar_one_or_none()
        raw_cols = await self._get_columns(table_name)

        saved_cols: dict[str, GenTableColumn] = {}
        if gt:
            rows = (await self.db.execute(
                select(GenTableColumn).where(GenTableColumn.table_id == gt.id).order_by(GenTableColumn.field_sort)
            )).scalars().all()
            saved_cols = {sc.column_name: sc for sc in rows if sc.column_name}

        field_configs = []
        for col in raw_cols:
            sc = saved_cols.get(col["name"])
            meta = self._build_field_meta(col, sc)
            field_configs.append(FieldConfigVO(
                columnName=meta["column_name"],
                columnType=col["udt"],
                columnComment=meta["field_comment"],
                isNullable="YES" if col["is_nullable"] else "NO",
                is_pk=meta["is_pk"],
                column_key="PRI" if meta["is_pk"] else "",
                fieldName=meta["field_name"],
                fieldType=meta["field_type"],
                tsType=meta["ts_type"],
                isShowInList=1 if meta["is_show_in_list"] else 0,
                isShowInForm=1 if meta["is_show_in_form"] else 0,
                isShowInQuery=1 if meta["is_show_in_query"] else 0,
                isRequired=1 if meta["is_required"] else 0,
                formType=_FORM_TYPE.get(meta["form_type_name"], 0),
                queryType=_QUERY_TYPE.get(meta["query_type_name"], 0),
                dictType=meta["dict_type"] or None,
                maxLength=meta["max_length"],
                fieldSort=sc.field_sort if sc else None,
            ))

        default_entity = pascal_case(trim_table_prefix(table_name, _DEFAULT_REMOVE_TABLE_PREFIX))
        return GenConfigVO(
            id=gt.id if gt else None,
            tableName=table_name,
            businessName=gt.business_name if gt else default_entity,
            moduleName=gt.module_name if gt else _DEFAULT_MODULE_NAME,
            packageName=gt.package_name if gt else "com.youlai.fastapi",
            entityName=gt.entity_name if gt else default_entity,
            author=gt.author if gt else "youlai-fastapi",
            parentMenuId=gt.parent_menu_id if gt else None,
            pageType=gt.page_type if gt else "classic",
            removeTablePrefix=gt.remove_table_prefix if gt else _DEFAULT_REMOVE_TABLE_PREFIX,
            fieldConfigs=field_configs,
        )

    async def ai_fill_config(self, table_name: str, requirement: str | None = None) -> GenConfigVO:
        """用 AI 推断代码生成配置，未推断出的字段沿用原有默认值。"""
        config = await self.get_gen_config(table_name)
        content = await chat_json(load_prompt("codegen/system.md"), build_ai_user_prompt(config, requirement))

        business_name = str(content.get("businessName") or "").strip()
        if business_name:
            config.business_name = business_name
        apply_ai_field_configs(config.field_configs, content.get("fieldConfigs"))

        return config

    async def save_gen_config(self, table_name: str, form: GenConfigForm) -> None:
        gt = (await self.db.execute(select(GenTable).where(GenTable.table_name == table_name))).scalar_one_or_none()
        # 实体名兜底统一去表前缀，避免 SysArticle 这类把模块名重复进实体名、权限串变成 sys:sys-article
        default_entity = pascal_case(
            trim_table_prefix(table_name, form.remove_table_prefix or _DEFAULT_REMOVE_TABLE_PREFIX)
        )
        default_module = form.module_name or _DEFAULT_MODULE_NAME

        if gt:
            gt.module_name = default_module
            gt.package_name = form.package_name or "com.youlai.fastapi"
            gt.business_name = form.business_name or table_name
            gt.entity_name = form.entity_name or default_entity
            gt.author = form.author or "youlai-fastapi"
            gt.parent_menu_id = form.parent_menu_id
            gt.remove_table_prefix = form.remove_table_prefix
            gt.page_type = form.page_type
            gt.update_time = datetime.now()
            await self.db.flush()
        else:
            gt = GenTable(
                table_name=table_name,
                module_name=default_module,
                package_name=form.package_name or "com.youlai.fastapi",
                business_name=form.business_name or table_name,
                entity_name=form.entity_name or default_entity,
                author=form.author or "youlai-fastapi",
                parent_menu_id=form.parent_menu_id,
                remove_table_prefix=form.remove_table_prefix,
                page_type=form.page_type,
            )
            self.db.add(gt)
            await self.db.flush()

        await self.db.execute(sa_delete(GenTableColumn).where(GenTableColumn.table_id == gt.id))

        # 插入新字段配置
        if form.field_configs:
            for idx, fc in enumerate(form.field_configs):
                col = GenTableColumn(
                    table_id=gt.id,
                    column_name=fc.column_name,
                    column_type=fc.column_type,
                    field_name=fc.field_name or "",
                    field_type=fc.field_type,
                    field_sort=fc.field_sort or idx,
                    field_comment=fc.field_comment,
                    is_show_in_list=fc.is_show_in_list or 0,
                    is_show_in_form=fc.is_show_in_form or 0,
                    is_show_in_query=fc.is_show_in_query or 0,
                    is_required=fc.is_required,
                    max_length=fc.max_length,
                    form_type=fc.form_type,
                    query_type=fc.query_type,
                    dict_type=fc.dict_type,
                )
                self.db.add(col)
                await self.db.flush()

        # 选了上级菜单就同步生成页面菜单与按钮权限，权限前缀与模板守卫同源；失败随事务回滚，不留「有配置无权限」的半成品
        if form.parent_menu_id and form.parent_menu_id > 0:
            await MenuService(self.db).add_menu_for_codegen(
                form.parent_menu_id,
                gt.module_name,
                gt.business_name,
                gt.entity_name,
                resolve_perm_prefix(gt.module_name, gt.entity_name),
            )

    async def delete_gen_config(self, table_name: str) -> None:
        gt = (await self.db.execute(select(GenTable).where(GenTable.table_name == table_name))).scalar_one_or_none()
        if gt:
            await self.db.execute(sa_delete(GenTableColumn).where(GenTableColumn.table_id == gt.id))
            await self.db.delete(gt)
            await self.db.flush()

    # 预览 / 下载

    async def preview_code(self, table_name: str, page_type: str, frontend_type: str) -> list[PreviewVO]:
        ctx = await self._build_template_context(table_name)
        files = self._render_files(ctx, page_type, frontend_type)
        return [
            PreviewVO(
                path=f["path"],
                fileName=f["file_name"],
                content=f["content"],
                scope=f["scope"],
                language=f["language"],
            ) for f in files
        ]

    async def download_code(self, table_name: str, page_type: str, frontend_type: str) -> bytes:
        ctx = await self._build_template_context(table_name)
        files = self._render_files(ctx, page_type, frontend_type)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                entry = f"{f['path']}/{f['file_name']}"
                zf.writestr(entry, f["content"])
        buf.seek(0)
        return buf.read()

    def _render_files(self, ctx: dict, page_type: str, frontend_type: str) -> list[dict]:
        env = _jinja_env()
        fe = "vue3-element-admin"
        api_path = f"{fe}/src/api/{ctx['module_name']}/{ctx['entity_kebab']}"
        view_path = f"{fe}/src/views/{ctx['module_name']}/{ctx['entity_kebab']}"
        base_path = f"app/{ctx['module_name']}/{ctx['entity_lower']}"

        is_js = frontend_type == "js"
        is_crud = str(page_type or "").strip().lower() == "crud"
        suffix = "js" if is_js else "ts"
        view_tpl = "index.crud.vue.j2" if is_crud else "index.vue.j2"

        plan = [
            ("backend/router.py.j2", "router.py", base_path, "backend"),
            ("backend/service.py.j2", "service.py", base_path, "backend"),
            ("backend/schemas.py.j2", "schemas.py", base_path, "backend"),
            ("backend/models.py.j2", "models.py", base_path, "backend"),
            (f"frontend/{suffix}/api.{suffix}.j2", f"index.{suffix}", api_path, "frontend"),
            (f"frontend/{suffix}/{view_tpl}", "index.vue", view_path, "frontend"),
        ]
        if not is_js:
            plan.insert(-1, ("frontend/ts/types.ts.j2", "types.ts", api_path, "frontend"))

        return [
            {
                "path": path,
                "file_name": fname,
                "content": self._render_template(env, tpl, ctx),
                "scope": scope,
                "language": fname.rsplit(".", 1)[-1],
            }
            for tpl, fname, path, scope in plan
        ]

    @staticmethod
    def _render_template(env: Environment, tpl: str, ctx: dict) -> str:
        """模板缺失或语法错误都立即失败，不返回半套生成代码。"""
        try:
            return env.get_template(tpl).render(**ctx)
        except TemplateError as e:
            raise BusinessException(
                code=ResultCode.SYSTEM_ERROR, msg=f"模板 {tpl} 渲染失败: {e}"
            ) from e
