"""异步 Redis 客户端。"""

import asyncio

import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None
_redis_lock = asyncio.Lock()


async def get_redis() -> aioredis.Redis:
    """获取或懒初始化 Redis 连接（使用 Lock 防止并发重复创建）。"""
    global _redis
    if _redis is None:
        async with _redis_lock:
            if _redis is None:
                _redis = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,  # 响应解码为 str
                    max_connections=100,    # 连接池上限，超出排队等待而非无限新建
                )
    return _redis


async def close_redis() -> None:
    """关闭 Redis 连接池（应用 shutdown 时调用）。"""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
