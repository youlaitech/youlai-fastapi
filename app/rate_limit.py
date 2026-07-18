"""Redis 滑动窗口限流工具（ZSet Lua 原子计数）"""

import time
import uuid

from app.redis import get_redis
from app.exceptions import BusinessException
from app.response import ResultCode

LUA_SLIDING_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local member = ARGV[3]
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
redis.call('ZADD', key, now, member)
redis.call('PEXPIRE', key, window + 1000)
return redis.call('ZCARD', key)
"""


async def sliding_window_count(key: str, window_ms: int) -> int:
    """滑动窗口计数，返回当前窗口内请求数"""
    now_ms = int(time.time() * 1000)
    member = str(uuid.uuid4())
    r = await get_redis()
    result = await r.eval(
        LUA_SLIDING_WINDOW, 1, key, now_ms, window_ms, member
    )
    return int(result)


async def check_rate_limit(key: str, limit: int, window_sec: int) -> int:
    """滑动窗口限流检查，返回窗口内当前请求数。

    窗口内请求数超过 limit 时抛 BusinessException（HTTP 429）；
    Redis 异常时放行（返回 0）。
    """
    try:
        count = await sliding_window_count(key, window_sec * 1000)
    except BusinessException:
        raise
    except Exception:
        return 0
    if count > limit:
        raise BusinessException(ResultCode.RATE_LIMIT_EXCEEDED, "请求过于频繁，请稍后再试")
    return count
