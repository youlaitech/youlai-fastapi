"""扫码登录。

generate/status/login 公开（不注入 get_current_user）；scan/confirm/cancel 需要 APP 登录态
（注入 get_current_user 取当前用户 ID），未带令牌时依赖直接抛 A0230。
"""

import json
import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import LoginResult, SysUserDetails
from app.auth.service import AuthService
from app.constants import QR_CODE_PREFIX, QR_CODE_TTL
from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import BusinessException
from app.redis import get_redis
from app.response import Result, ResultCode

router = APIRouter(prefix="/api/v1/auth/qr-code", tags=["扫码登录"])

# 扫码登录状态
STATUS_WAITING = "WAITING"
STATUS_SCANNED = "SCANNED"
STATUS_CONFIRMED = "CONFIRMED"
STATUS_LOGGED_IN = "LOGGED_IN"
STATUS_CANCELED = "CANCELED"
STATUS_EXPIRED = "EXPIRED"

# 状态流转时若 Redis 剩余 TTL 小于该值，补足到此值（秒）
MIN_REMAIN = 30


class QrTicketForm(BaseModel):
    """扫码登录票据表单，用于 scan/confirm/cancel/login 接口。"""

    ticket: str


def _qr_key(ticket: str) -> str:
    return f"{QR_CODE_PREFIX}{ticket}"


def _client_ip(request: Request) -> str:
    """从请求头提取客户端 IP，兼容反向代理：X-Forwarded-For → X-Real-IP → remote addr。"""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    xrip = request.headers.get("x-real-ip", "")
    if xrip:
        return xrip.strip()
    return request.client.host if request.client else "unknown"


def _mask_nickname(nickname: str) -> str:
    """昵称脱敏：保留首尾字符，中间以 * 填充。"""
    if not nickname:
        return ""
    chars = list(nickname)
    n = len(chars)
    if n <= 1:
        return nickname
    if n == 2:
        return chars[0] + "*"
    return chars[0] + "*" * (n - 2) + chars[-1]


async def _load(redis, ticket: str):
    """读取票据上下文；票据为空、不存在或已过期都视为 QR_CODE_NOT_FOUND。"""
    if not ticket:
        return None
    raw = await redis.get(_qr_key(ticket))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


async def _save(redis, ctx: dict, ttl: int) -> None:
    await redis.setex(_qr_key(ctx["ticket"]), ttl, json.dumps(ctx, ensure_ascii=False))


async def _remain(redis, ticket: str) -> int:
    ttl = await redis.ttl(_qr_key(ticket))
    return ttl if isinstance(ttl, int) and ttl > 0 else 0


async def _refresh_ttl(redis, ticket: str) -> int:
    remain = await _remain(redis, ticket)
    return MIN_REMAIN if remain < MIN_REMAIN else remain


def _to_status_vo(ctx: dict, expire_seconds: int) -> dict:
    vo = {
        "ticket": ctx["ticket"],
        "status": ctx["status"],
        "nickname": None,
        "avatar": None,
        "expireSeconds": expire_seconds,
    }
    # WAITING 阶段谁都能查状态，此时不能泄露用户信息；扫码/确认后才回传脱敏昵称与头像
    if ctx["status"] in (STATUS_SCANNED, STATUS_CONFIRMED):
        vo["nickname"] = _mask_nickname(ctx.get("nickname") or "")
        vo["avatar"] = ctx.get("avatar")
    return vo


@router.post("/generate", summary="生成扫码登录票据")
async def generate(request: Request):
    redis = await get_redis()
    ticket = uuid.uuid4().hex
    ctx = {
        "ticket": ticket,
        "status": STATUS_WAITING,
        "userId": None,
        "nickname": None,
        "avatar": None,
        "createdAt": None,
        "scannedAt": None,
        "confirmedAt": None,
        "ip": _client_ip(request),
    }
    await _save(redis, ctx, QR_CODE_TTL)
    return Result(data={"ticket": ticket, "expireSeconds": QR_CODE_TTL})


@router.get("/status", summary="查询扫码状态")
async def status(ticket: str = Query(...)):
    redis = await get_redis()
    ctx = await _load(redis, ticket)
    if ctx is None:
        raise BusinessException(code=ResultCode.QR_CODE_NOT_FOUND, msg="扫码登录票据不存在或已过期")
    return Result(data=_to_status_vo(ctx, await _remain(redis, ticket)))


@router.post("/scan", summary="APP 标记已扫码")
async def scan(
    form: QrTicketForm,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    ctx = await _load(redis, form.ticket)
    if ctx is None:
        raise BusinessException(code=ResultCode.QR_CODE_NOT_FOUND, msg="扫码登录票据不存在或已过期")
    if ctx["status"] != STATUS_WAITING:
        raise BusinessException(code=ResultCode.QR_CODE_STATUS_ILLEGAL, msg="扫码登录状态非法")
    info = await AuthService(db).get_auth_info_by_user_id(user.userId)
    ctx["userId"] = user.userId
    ctx["nickname"] = info.get("nickname")
    ctx["avatar"] = info.get("avatar")
    ctx["status"] = STATUS_SCANNED
    await _save(redis, ctx, await _refresh_ttl(redis, form.ticket))
    return Result(data=_to_status_vo(ctx, await _remain(redis, form.ticket)))


@router.post("/confirm", summary="APP 确认登录")
async def confirm(
    form: QrTicketForm,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    ctx = await _load(redis, form.ticket)
    if ctx is None:
        raise BusinessException(code=ResultCode.QR_CODE_NOT_FOUND, msg="扫码登录票据不存在或已过期")
    if ctx["status"] != STATUS_SCANNED:
        raise BusinessException(code=ResultCode.QR_CODE_STATUS_ILLEGAL, msg="扫码登录状态非法")
    if ctx.get("userId") != user.userId:
        raise BusinessException(code=ResultCode.QR_CODE_USER_MISMATCH, msg="扫码用户与确认用户不一致")
    ctx["status"] = STATUS_CONFIRMED
    await _save(redis, ctx, await _refresh_ttl(redis, form.ticket))
    return Result(data=_to_status_vo(ctx, await _remain(redis, form.ticket)))


@router.post("/cancel", summary="APP 取消登录")
async def cancel(
    form: QrTicketForm,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    ctx = await _load(redis, form.ticket)
    if ctx is None:
        raise BusinessException(code=ResultCode.QR_CODE_NOT_FOUND, msg="扫码登录票据不存在或已过期")
    if ctx["status"] not in (STATUS_WAITING, STATUS_SCANNED, STATUS_CONFIRMED):
        raise BusinessException(code=ResultCode.QR_CODE_STATUS_ILLEGAL, msg="扫码登录状态非法")
    if ctx["status"] != STATUS_WAITING and ctx.get("userId") is not None:
        if ctx.get("userId") != user.userId:
            raise BusinessException(code=ResultCode.QR_CODE_USER_MISMATCH, msg="扫码用户与取消用户不一致")
    ctx["status"] = STATUS_CANCELED
    await _save(redis, ctx, await _refresh_ttl(redis, form.ticket))
    return Result(data=_to_status_vo(ctx, await _remain(redis, form.ticket)))


@router.post("/login", summary="PC 端换取会话令牌")
async def login(form: QrTicketForm, db: AsyncSession = Depends(get_db)):
    redis = await get_redis()
    ctx = await _load(redis, form.ticket)
    if ctx is None:
        raise BusinessException(code=ResultCode.QR_CODE_NOT_FOUND, msg="扫码登录票据不存在或已过期")
    if ctx["status"] != STATUS_CONFIRMED:
        raise BusinessException(code=ResultCode.QR_CODE_STATUS_ILLEGAL, msg="扫码登录状态非法")
    token = await AuthService(db).login_by_qr(ctx["userId"])
    # 换取令牌成功后立即把票据置为已使用（一次性），再次 login 会在状态校验处被拒，杜绝重放
    ctx["status"] = STATUS_LOGGED_IN
    remain = await _remain(redis, form.ticket)
    await _save(redis, ctx, remain if remain > MIN_REMAIN else MIN_REMAIN)
    return Result(data=LoginResult(**token))
