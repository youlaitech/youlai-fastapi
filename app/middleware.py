"""全局中间件。"""

import time

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://.*" if settings.DEBUG else settings.ALLOWED_ORIGINS or "http://localhost",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        expose_headers=["Content-Disposition"],
        max_age=600,
    )


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)")
        return response


limiter = Limiter(
    # 按客户端 IP 区分限流主体
    key_func=get_remote_address,
    # 总开关：默认关。关闭时 SlowAPIMiddleware 直接透传，不计数也不回写头。
    enabled=settings.RATE_LIMIT_ENABLED,
    # 全局兜底限流：单 IP 每分钟最多 1000 请求。
    # 阈值宽松，正常调用不会误触 429；仅在恶意刷接口时生效。
    default_limits=["1000/minute"],
    storage_uri=settings.REDIS_URL,
    # 滑动窗口：在滚动时间窗内计数，比固定窗口更平滑，不会在窗口边界出现双倍放行
    strategy="moving-window",
    # 在响应头回写 X-RateLimit-Limit / X-RateLimit-Remaining / X-RateLimit-Reset
    headers_enabled=True,
)
