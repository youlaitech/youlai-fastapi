"""操作日志管理。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.serializers import BigId

from app.database import get_db
from app.pagination import PageResult
from app.dependencies import require_perm
from app.response import Result
from app.system.log.models import SysLog

router = APIRouter(prefix="/api/v1/logs", tags=["日志管理"])


class LogQuery(BaseModel):
    pageNum: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=100)
    module: int | None = None
    actionType: int | None = None
    keywords: str | None = None
    status: int | None = None


class LogVO(BaseModel):
    id: BigId | None = None
    module: int | None = None
    actionType: int | None = None
    title: str | None = None
    content: str | None = None
    requestMethod: str | None = None
    requestUri: str | None = None
    ip: str | None = None
    province: str | None = None
    city: str | None = None
    device: str | None = None
    os: str | None = None
    browser: str | None = None
    status: int | None = None
    errorMsg: str | None = None
    executionTime: int | None = None
    operatorId: BigId | None = None
    operatorName: str | None = None
    createTime: str | None = None
    model_config = {"from_attributes": True}


class LogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_page(self, query: LogQuery) -> PageResult:
        conditions = []
        if query.module is not None:
            conditions.append(SysLog.module == query.module)
        if query.actionType is not None:
            conditions.append(SysLog.action_type == query.actionType)
        if query.status is not None:
            conditions.append(SysLog.status == query.status)
        if query.keywords:
            kw = f"%{query.keywords}%"
            conditions.append(
                SysLog.title.ilike(kw)
                | SysLog.operator_name.ilike(kw)
                | cast(SysLog.ip, String).ilike(kw)
            )

        stmt = select(SysLog)
        if conditions:
            stmt = stmt.where(*conditions)
        base = stmt
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(
            stmt.order_by(SysLog.create_time.desc()).offset(offset).limit(query.pageSize)
        )
        vo_list = [LogVO.model_validate(r, from_attributes=True) for r in rows.scalars().all()]
        return PageResult(records=vo_list, total=total, pageNum=query.pageNum, pageSize=query.pageSize)



@router.get("", summary="日志分页", dependencies=[Depends(require_perm("sys:log:list"))])
async def get_logs(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    module: int | None = None,
    actionType: int | None = None,
    status: int | None = None,
    keywords: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = LogQuery(pageNum=pageNum, pageSize=pageSize, module=module, actionType=actionType, status=status, keywords=keywords)
    return Result(data=await LogService(db).get_page(q))
