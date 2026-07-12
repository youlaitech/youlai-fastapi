"""限流中间件 (slowapi)。"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    # 按客户端 IP 区分限流主体
    key_func=get_remote_address,
    # 默认阈值，如 "5/second" 表示单 IP 每秒最多 5 个请求
    default_limits=[f"{settings.RATE_LIMIT_QPS}/second"],
    storage_uri=settings.REDIS_URL,
    # 滑动窗口：在滚动时间窗内计数，比固定窗口更平滑，不会在窗口边界出现双倍放行
    strategy="moving-window",
)
