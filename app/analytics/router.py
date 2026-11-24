"""访问统计接口。"""

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_perm
from app.exceptions import BusinessException
from app.response import Result, ResultCode
from app.system.log.models import SysLog
from app.system.user.service import UserService

router = APIRouter(prefix="/api/v1/analytics", tags=["统计接口"])

MAX_RANGE_DAYS = 366


class VisitSummaryVO(BaseModel):
    todayUv: int = 0
    yesterdayUv: int = 0
    totalUv: int = 0
    todayPv: int = 0
    yesterdayPv: int = 0
    totalPv: int = 0
    uvGrowthRate: float | None = None
    pvGrowthRate: float | None = None


class VisitTrendPointVO(BaseModel):
    date: str
    pv: int
    uv: int


class VisitTrendVO(BaseModel):
    startDate: str
    endDate: str
    points: list[VisitTrendPointVO]


class UserSummaryVO(BaseModel):
    total: int


def _parse_range(start_date: str, end_date: str) -> tuple[date, date]:
    """解析闭区间日期并校验跨度。"""
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="日期格式不正确，请使用 YYYY-MM-DD") from None

    span = (end - start).days
    if span < 0:
        raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="开始日期不能晚于结束日期")
    if span >= MAX_RANGE_DAYS:
        raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="查询跨度不能超过 366 天")
    return start, end


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _count(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        distinct_ip: bool = False,
    ) -> int:
        """统计日志条数或去重 IP 数，时间区间左闭右开。"""
        column = func.count(func.distinct(SysLog.ip)) if distinct_ip else func.count()
        stmt = select(column)
        if start is not None:
            stmt = stmt.where(SysLog.create_time >= start)
        if end is not None:
            stmt = stmt.where(SysLog.create_time < end)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_visit_summary(self) -> VisitSummaryVO:
        """按自然日统计今日、昨日、累计 PV/UV 及增长率。"""
        today = date.today()
        today_start = datetime.combine(today, time.min)
        tomorrow_start = today_start + timedelta(days=1)
        yesterday_start = today_start - timedelta(days=1)

        today_uv = await self._count(today_start, tomorrow_start, distinct_ip=True)
        yesterday_uv = await self._count(yesterday_start, today_start, distinct_ip=True)
        total_uv = await self._count(distinct_ip=True)
        today_pv = await self._count(today_start, tomorrow_start)
        yesterday_pv = await self._count(yesterday_start, today_start)
        total_pv = await self._count()

        uv_rate = round((today_uv - yesterday_uv) / yesterday_uv, 4) if yesterday_uv else None
        pv_rate = round((today_pv - yesterday_pv) / yesterday_pv, 4) if yesterday_pv else None

        return VisitSummaryVO(
            todayUv=today_uv,
            yesterdayUv=yesterday_uv,
            totalUv=total_uv,
            todayPv=today_pv,
            yesterdayPv=yesterday_pv,
            totalPv=total_pv,
            uvGrowthRate=uv_rate,
            pvGrowthRate=pv_rate,
        )

    async def get_visit_trend(self, start_date: str, end_date: str) -> VisitTrendVO:
        """按自然日返回闭区间内逐日 PV、UV。"""
        start, end = _parse_range(start_date, end_date)
        dates = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]

        range_start = datetime.combine(start, time.min)
        range_end = datetime.combine(end + timedelta(days=1), time.min)

        pv_rows = await self.db.execute(
            select(func.date(SysLog.create_time), func.count())
            .where(SysLog.create_time >= range_start, SysLog.create_time < range_end)
            .group_by(func.date(SysLog.create_time))
        )
        pv_map = {str(d): c for d, c in pv_rows}

        uv_rows = await self.db.execute(
            select(func.date(SysLog.create_time), func.count(func.distinct(SysLog.ip)))
            .where(SysLog.create_time >= range_start, SysLog.create_time < range_end)
            .group_by(func.date(SysLog.create_time))
        )
        uv_map = {str(d): c for d, c in uv_rows}

        return VisitTrendVO(
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            points=[VisitTrendPointVO(date=d, pv=pv_map.get(d, 0), uv=uv_map.get(d, 0)) for d in dates],
        )


@router.get("/visits/summary", summary="访问汇总", dependencies=[Depends(require_perm())])
async def get_visit_summary(db: AsyncSession = Depends(get_db)):
    return Result(data=await AnalyticsService(db).get_visit_summary())


@router.get("/visits/trend", summary="访问趋势", dependencies=[Depends(require_perm())])
async def get_visit_trend(
    startDate: str = Query(..., description="开始日期 YYYY-MM-DD"),
    endDate: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await AnalyticsService(db).get_visit_trend(startDate, endDate))


@router.get("/users/summary", summary="用户汇总", dependencies=[Depends(require_perm())])
async def get_user_summary(db: AsyncSession = Depends(get_db)):
    return Result(data=UserSummaryVO(total=await UserService(db).count()))
