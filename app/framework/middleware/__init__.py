"""中间件模块。"""

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
from loguru import logger

from app.core.config import settings


# ── CORS 中间件 ──
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


# ── 请求日志中间件 ──
class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)")
        return response
