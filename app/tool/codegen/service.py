"""代码生成服务 — 简化实现。"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessException
from app.response import ResultCode
from app.tool.codegen.schemas import GenConfigForm, PreviewVO, TableVO, TableQuery


# 代码生成配置进程内缓存（按表名存）；多 worker 部署不共享，正式场景可换 Redis。
_CONFIG_CACHE: dict[str, GenConfigForm] = {}


class CodegenService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_table_page(self, query: TableQuery) -> dict:
        """分页查询 information_schema 中的表清单（仅 public 模式）。"""
        params: dict = {
            "limit": query.pageSize,
            "offset": (query.pageNum - 1) * query.pageSize,
        }
        where_clauses = ["table_schema='public'"]
        if query.keywords:
            # keywords 用绑定参数传入，避免直接拼接到 information_schema 查询造成注入
            where_clauses.append("table_name ILIKE :kw")
            params["kw"] = f"%{query.keywords}%"
        where_sql = "WHERE " + " AND ".join(where_clauses)

        count_sql = f"SELECT COUNT(*) FROM information_schema.tables {where_sql}"
        total = (await self.db.execute(text(count_sql), params)).scalar() or 0

        sql = f"""
            SELECT table_name, '' as table_comment, '' as engine, NOW() as create_time
            FROM information_schema.tables
            {where_sql}
            ORDER BY table_name
            LIMIT :limit OFFSET :offset
        """
        rows = await self.db.execute(text(sql), params)
        list_data = [TableVO(name=r.table_name, comment=r.table_comment, engine=r.engine, createTime=str(r.create_time)).model_dump() for r in rows]
        return {"list": list_data, "total": total}

    async def get_gen_config(self, table_name: str) -> GenConfigForm:
        """读取表的代码生成配置；未保存过则返回基于表名推导的默认值。"""
        if table_name in _CONFIG_CACHE:
            return _CONFIG_CACHE[table_name]
        return GenConfigForm(
            tableName=table_name,
            packageName="com.youlai.boot",
            moduleName=table_name.replace("sys_", ""),
            className=self._to_class_name(table_name),
            classComment=table_name,
            author="youlai",
        )

    async def save_gen_config(self, table_name: str, form: GenConfigForm) -> None:
        """将代码生成配置存入进程内缓存。"""
        _CONFIG_CACHE[table_name] = form

    async def delete_gen_config(self, table_name: str) -> None:
        """删除进程内缓存的代码生成配置。"""
        _CONFIG_CACHE.pop(table_name, None)

    async def preview_code(self, table_name: str, page_type: str, type: str) -> list[PreviewVO]:
        """返回各层代码预览（当前为简化占位实现）。"""
        config = await self.get_gen_config(table_name)
        return [
            PreviewVO(fileName=f"{config.className}Controller.java", content=f"// {config.className} controller preview"),
            PreviewVO(fileName=f"{config.className}Service.java", content=f"// {config.className} service preview"),
            PreviewVO(fileName=f"{config.className}Mapper.java", content=f"// {config.className} mapper preview"),
            PreviewVO(fileName=f"{config.className}.vue", content=f"// {config.className} vue preview"),
        ]

    async def download_code(self, table_name: str, page_type: str, type: str) -> bytes:
        """将各层预览代码打包为 zip 返回字节流。"""
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for preview in await self.preview_code(table_name, page_type, type):
                zf.writestr(preview.fileName, preview.content)
        buf.seek(0)
        return buf.read()

    @staticmethod
    def _to_class_name(table_name: str) -> str:
        """sys_user -> SysUser。"""
        return "".join(word.capitalize() for word in table_name.replace("sys_", "").split("_"))
