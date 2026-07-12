"""SSE 路由。"""

from fastapi import APIRouter, Depends, Request

from app.framework.security.deps import get_current_user
from app.framework.security.schemas import SysUserDetails
from app.framework.sse.manager import get_online_count, sse_connect
from app.framework.web.response import Result

router = APIRouter(prefix="/api/v1/sse", tags=["SSE推送"])


@router.get("/connect", summary="SSE 长连接")
async def connect(request: Request, user: SysUserDetails = Depends(get_current_user)):
    return await sse_connect(request, user.username or "")


@router.get("/online-count", summary="在线用户数")
async def online_count():
    return Result(data=await get_online_count())
