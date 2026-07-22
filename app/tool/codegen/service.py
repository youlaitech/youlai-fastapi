"""代码生成服务 — 元数据查询 + Jinja2 渲染 + 配置持久化 + zip 打包。"""

import io
import zipfile
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import text, select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessException
from app.response import ResultCode
from app.tool.codegen.models import GenTable, GenTableColumn
from app.tool.codegen.schemas import (
    FieldConfigVO,
    GenConfigForm,
    GenConfigVO,
    PreviewVO,
    TableQuery,
    TableVO,
)

_TEMPLATE_DIR = Path(__file__).parent / "templates"

# ═══════════════════════════════════════════════════════════
# PostgreSQL → Python 类型 / SQLAlchemy 类型 / TypeScript 类型
# ═══════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════
# Jinja2 环境
# ═══════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════

class CodegenService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 表列表 ──

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

    # ── 列元数据 ──

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

    # ── 模板上下文构造 ──

    def _build_field_meta(self, col: dict, saved_col: GenTableColumn | None = None) -> dict:
        py_type = pg_to_python(col["udt"])
        ts_type = py_to_ts(py_type)
        sa = pg_to_sa(col["udt"])

        is_non_sys = col["name"] not in ("id", "create_time", "update_time", "is_deleted")
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

        is_show_list = saved_col.is_show_in_list != 0 if saved_col else (not col["is_pk"] and is_non_sys)
        is_show_form = saved_col.is_show_in_form != 0 if saved_col else (not col["is_pk"])
        is_show_query = saved_col.is_show_in_query != 0 if saved_col else (not col["is_pk"] and is_non_sys)
        is_required = saved_col.is_required == 1 if saved_col else (not col["is_nullable"] and not col["is_pk"])
        ft_name = form_type_name(saved_col.form_type) if saved_col else default_form
        qt_name = query_type_name(saved_col.query_type) if saved_col else default_query

        return {
            "column_name": col["name"],
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
            "dict_type": (saved_col.dict_type or "") if saved_col else "",
            "max_length": saved_col.max_length if saved_col else None,
        }

    async def _build_template_context(self, table_name: str) -> dict:
        raw_cols = await self._get_columns(table_name)
        entity_name = pascal_case(table_name)
        entity_lower = lower_first(entity_name)
        module_name = table_name.split("_")[0] if "_" in table_name else "app"
        entity_kebab = table_name.replace("_", "-")
        entity_upper_snake = table_name.upper()
        pk = next((c["name"] for c in raw_cols if c["is_pk"]), "id")

        ctx = {
            "table_name": table_name,
            "entity_name": entity_name,
            "entity_lower": entity_lower,
            "module_name": module_name,
            "entity_kebab": entity_kebab,
            "entity_upper_snake": entity_upper_snake,
            "pk_name": pk,
            "business_name": entity_name,
            "entity_comment": entity_name,
            "package_name": "com.youlai.fastapi",
            "author": "youlai-fastapi",
            "has_datetime": False,
            "has_date": False,
            "has_time": False,
            "has_json": False,
            "has_decimal": False,
            "sa_imports": set(),
            "columns": [],
        }

        # 尝试从 DB 读取已保存的字段配置
        gt = (await self.db.execute(select(GenTable).where(GenTable.table_name == table_name))).scalar_one_or_none()
        saved_cols: dict[str, GenTableColumn] = {}
        if gt:
            ctx["entity_name"] = gt.entity_name
            ctx["module_name"] = gt.module_name or ctx["module_name"]
            ctx["package_name"] = gt.package_name
            ctx["author"] = gt.author
            ctx["business_name"] = gt.business_name
            ctx["entity_comment"] = gt.business_name
            ctx["entity_lower"] = lower_first(gt.entity_name)
            ctx["entity_kebab"] = gt.entity_name.lower()
            rows = (await self.db.execute(
                select(GenTableColumn).where(GenTableColumn.table_id == gt.id).order_by(GenTableColumn.field_sort)
            )).scalars().all()
            saved_cols = {sc.column_name: sc for sc in rows if sc.column_name}

        for col in raw_cols:
            sc = saved_cols.get(col["name"])
            meta = self._build_field_meta(col, sc)
            ctx["columns"].append(meta)
            py = meta["py_type"]
            sa = meta["sa_column"]
            if py == "datetime":
                ctx["has_datetime"] = True
            if py == "date":
                ctx["has_date"] = True
            if py == "time":
                ctx["has_time"] = True
            if py == "Decimal":
                ctx["has_decimal"] = True
            if "json" in col["udt"]:
                ctx["has_json"] = True
            sa_name = sa.split("(")[0]
            if sa_name not in ("String", "Integer", "SmallInteger", "BigInteger", "Text", "Boolean", "DateTime", "Date", "Float", "Numeric", "JSON", "Uuid"):
                sa_name = "String"
            ctx["sa_imports"].add(sa_name)

        ctx["sa_imports"] = sorted(ctx["sa_imports"])
        return ctx

    # ── 配置 CRUD ──

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
            py_type = pg_to_python(col["udt"])
            ts = py_to_ts(py_type)
            field_name = sc.field_name if sc else col["name"]
            field_type = (sc.field_type or py_type) if sc else py_type
            if sc:
                ts = py_to_ts(field_type)

            field_configs.append(FieldConfigVO(
                columnName=col["name"],
                columnType=f"{col['udt']}",
                columnComment=(sc.field_comment or col["comment"]) if sc else col["comment"],
                isNullable="YES" if col["is_nullable"] else "NO",
                is_pk=col["is_pk"],
                column_key="PRI" if col["is_pk"] else "",
                fieldName=field_name,
                fieldType=field_type,
                tsType=ts,
                isShowInList=sc.is_show_in_list if sc else (1 if not col["is_pk"] and col["name"] not in ("id", "create_time", "update_time", "is_deleted") else 0),
                isShowInForm=sc.is_show_in_form if sc else (1 if not col["is_pk"] else 0),
                isShowInQuery=sc.is_show_in_query if sc else (1 if not col["is_pk"] and col["name"] not in ("id", "create_time", "update_time", "is_deleted") else 0),
                isRequired=(sc.is_required or 0) if sc else (1 if not col["is_nullable"] and not col["is_pk"] else 0),
                formType=sc.form_type if sc else _FORM_TYPE.get(
                    "SWITCH" if "status" in field_name else "DATE_TIME" if any(k in field_name for k in ("time", "date"))
                    else "INPUT_NUMBER" if py_type in ("float", "int", "Decimal") else "SWITCH" if py_type == "bool" else "INPUT", 0),
                queryType=sc.query_type if sc else _QUERY_TYPE.get("LIKE" if py_type == "str" else "EQ", 0),
                dictType=sc.dict_type if sc else None,
                maxLength=sc.max_length if sc else None,
                fieldSort=sc.field_sort if sc else None,
            ))

        return GenConfigVO(
            id=gt.id if gt else None,
            tableName=table_name,
            businessName=gt.business_name if gt else pascal_case(table_name),
            moduleName=gt.module_name if gt else table_name.split("_")[0] if "_" in table_name else "app",
            packageName=gt.package_name if gt else "com.youlai.fastapi",
            entityName=gt.entity_name if gt else pascal_case(table_name),
            author=gt.author if gt else "youlai-fastapi",
            parentMenuId=gt.parent_menu_id if gt else None,
            pageType=gt.page_type if gt else "classic",
            removeTablePrefix=gt.remove_table_prefix if gt else None,
            fieldConfigs=field_configs,
        )

    async def save_gen_config(self, table_name: str, form: GenConfigForm) -> None:
        gt = (await self.db.execute(select(GenTable).where(GenTable.table_name == table_name))).scalar_one_or_none()

        if gt:
            gt.module_name = form.module_name
            gt.package_name = form.package_name or "com.youlai.fastapi"
            gt.business_name = form.business_name or table_name
            gt.entity_name = form.entity_name or pascal_case(table_name)
            gt.author = form.author or "youlai-fastapi"
            gt.parent_menu_id = form.parent_menu_id
            gt.remove_table_prefix = form.remove_table_prefix
            gt.page_type = form.page_type
            gt.update_time = datetime.now()
            await self.db.flush()
        else:
            gt = GenTable(
                table_name=table_name,
                module_name=form.module_name,
                package_name=form.package_name or "com.youlai.fastapi",
                business_name=form.business_name or table_name,
                entity_name=form.entity_name or pascal_case(table_name),
                author=form.author or "youlai-fastapi",
                parent_menu_id=form.parent_menu_id,
                remove_table_prefix=form.remove_table_prefix,
                page_type=form.page_type,
            )
            self.db.add(gt)
            await self.db.flush()

        # 删除旧字段配置
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

    async def delete_gen_config(self, table_name: str) -> None:
        gt = (await self.db.execute(select(GenTable).where(GenTable.table_name == table_name))).scalar_one_or_none()
        if gt:
            await self.db.execute(sa_delete(GenTableColumn).where(GenTableColumn.table_id == gt.id))
            await self.db.delete(gt)
            await self.db.flush()

    # ── 预览 / 下载 ──

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
        out: list[dict] = []
        fe = "vue3-element-admin"
        api_path = f"{fe}/src/api/{ctx['module_name']}/{ctx['entity_kebab']}"
        view_path = f"{fe}/src/views/{ctx['module_name']}/{ctx['entity_kebab']}"
        base_path = f"src/modules/{ctx['module_name']}/{ctx['entity_lower']}"
        is_js = frontend_type == "js"

        # 后端模板
        for tpl, fname in [
            ("backend/router.py.j2", "router.py"),
            ("backend/service.py.j2", "service.py"),
            ("backend/schemas.py.j2", "schemas.py"),
            ("backend/models.py.j2", "models.py"),
        ]:
            try:
                tmpl = env.get_template(tpl)
                content = tmpl.render(**ctx)
                ext = fname.rsplit(".", 1)[-1]
                out.append({"path": base_path, "file_name": fname, "content": content,
                             "scope": "backend", "language": ext})
            except Exception:
                pass  # 模板缺失时跳过

        # 前端模板
        if is_js:
            for tpl, fname in [
                ("frontend/js/api.js.j2", "index.js"),
                ("frontend/js/index.vue.j2", "index.vue"),
            ]:
                try:
                    tmpl = env.get_template(tpl)
                    content = tmpl.render(**ctx)
                    ext = fname.rsplit(".", 1)[-1]
                    p = api_path if fname.endswith(".js") else view_path
                    out.append({"path": p, "file_name": fname, "content": content,
                                 "scope": "frontend", "language": ext})
                except Exception:
                    pass
        else:
            for tpl, fname in [
                ("frontend/ts/api.ts.j2", "index.ts"),
                ("frontend/ts/types.ts.j2", "types.ts"),
                ("frontend/ts/index.vue.j2", "index.vue"),
            ]:
                try:
                    tmpl = env.get_template(tpl)
                    content = tmpl.render(**ctx)
                    ext = fname.rsplit(".", 1)[-1]
                    p = view_path if fname.endswith(".vue") else api_path
                    out.append({"path": p, "file_name": fname, "content": content,
                                 "scope": "frontend", "language": ext})
                except Exception:
                    pass

        return out
