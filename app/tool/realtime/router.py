"""实时推送路由。"""

from fastapi import APIRouter, Depends, Query, WebSocket
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.auth.schemas import SysUserDetails
from app.auth.token import TokenManager, get_token_manager
from app.dependencies import get_current_user, oauth2_scheme
from app.exceptions import BusinessException
from app.response import Result
from app.tool.realtime.connection import realtime_connect
from app.tool.realtime.manager import presence_snapshot
from app.tool.realtime.ticket import consume_ticket, create_ticket
from app.tool.realtime.topics import SUPPORTED_TOPICS, TOPIC_NOTICE

router = APIRouter(prefix="/api/v1/realtime", tags=["实时推送"])


class RealtimeTicketRequest(BaseModel):
    """申请握手票据的请求体。"""

    topics: list[str] = Field(..., description="订阅主题，须包含 notice")


@router.post("/tickets", summary="签发实时连接票据")
async def create_realtime_ticket(
    request: RealtimeTicketRequest,
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    user: SysUserDetails = Depends(get_current_user),
):
    """校验访问凭证与订阅主题后签发一次性票据。"""
    topics = request.topics
    if TOPIC_NOTICE not in topics:
        raise BusinessException(msg="订阅主题须包含 notice")

    unsupported = [t for t in topics if t not in SUPPORTED_TOPICS]
    if unsupported:
        raise BusinessException(msg=f"不支持的订阅主题：{', '.join(unsupported)}")

    ticket = await create_ticket(user.username or "", credentials.credentials, topics)
    return Result(data={"ticket": ticket})


@router.get("/presence", summary="在线状态")
async def presence():
    """返回当前节点的在线状态快照。"""
    return Result(data=await presence_snapshot())


@router.websocket("/ws")
async def realtime_ws(
    websocket: WebSocket,
    ticket: str = Query(..., description="一次性握手票据"),
    token_manager: TokenManager = Depends(get_token_manager),
):
    """实时连接握手，票据只能使用一次且 30 秒内有效。"""
    grant = await consume_ticket(ticket)
    if grant is None:
        await websocket.close(code=4001)
        return

    user = await token_manager.parse_token(grant.get("access_token", ""))
    if user is None:
        await websocket.close(code=4001)
        return

    await realtime_connect(websocket, grant)
