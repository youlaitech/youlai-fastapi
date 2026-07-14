"""分页工具，集成 fastapi-pagination。"""

from typing import TypeVar

from fastapi import Query
from fastapi_pagination import Page as FastAPIPage
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from pydantic import BaseModel, Field
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

T = TypeVar("T")


class PageQuery(BaseModel):
    """分页查询参数。"""

    pageNum: int = Field(default=1, ge=1, description="当前页码")
    pageSize: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="每页条数",
    )


class PageResult(BaseModel):
    """分页查询响应结构。"""

    records: list = Field(default_factory=list, serialization_alias="list", description="数据列表")
    total: int = Field(default=0, description="总条数")
    pageNum: int = Field(default=1, description="当前页码")
    pageSize: int = Field(default=10, description="每页条数")

    @classmethod
    def from_fastapi_page(cls, page: FastAPIPage, query: PageQuery) -> "PageResult":
        return cls(
            records=list(page.items),
            total=page.total,
            pageNum=query.pageNum,
            pageSize=query.pageSize,
        )


async def paginate_query(
    db: AsyncSession,
    stmt: Select,
    query: PageQuery,
) -> PageResult:
    """使用 fastapi-pagination 执行分页查询，返回项目 PageResult。

    用法:
        result = await paginate_query(db, select(SysUser).where(...), query)
    """
    page: FastAPIPage = await sqlalchemy_paginate(db, stmt, page=query.pageNum, size=query.pageSize)
    return PageResult.from_fastapi_page(page, query)
