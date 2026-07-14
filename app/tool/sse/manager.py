"""SSE 实时推送管理 — Redis Pub/Sub，支持多 worker 部署。

每个连接订阅 sse:broadcast（全局）与 sse:user:{username}（定向）两个频道。
在线用户集合存 Redis Set sse:online，跨 worker 共享。

sse_starlette 的 data 字段须为字符串，因此事件 data 统一先 json.dumps 成字符串，
再整体包一层 JSON 写入 Redis，监听端取出后原样 yield 给 EventSourceResponse。
"""

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import Request
from loguru import logger
from sse_starlette.sse import EventSourceResponse

from app.redis import get_redis
from app.tool.sse.topics import ONLINE_COUNT

_BROADCAST_CHANNEL = "sse:broadcast"
_ONLINE_SET = "sse:online"
_HEARTBEAT_TIMEOUT = 30  # 秒，无消息时发心跳的等待间隔


def _user_channel(username: str) -> str:
    """用户定向推送频道名。"""
    return f"sse:user:{username}"


def _encode(event: str, data) -> str:
    """将事件编码为 Redis 消息体：内层 data 先序列化为 JSON 字符串，再整体包一层 JSON。"""
    return json.dumps(
        {"event": event, "data": json.dumps(data, default=str, ensure_ascii=False)},
        ensure_ascii=False,
    )


async def sse_connect(request: Request, username: str) -> EventSourceResponse:
    """建立 SSE 长连接。

    订阅广播频道与用户专属频道，断开时从在线集合移除并广播人数变化。
    """

    async def event_generator() -> AsyncIterator[dict]:
        redis = await get_redis()
        queue: asyncio.Queue = asyncio.Queue()
        pubsub = redis.pubsub()
        user_channel = _user_channel(username)

        # 上线：加入在线集合
        await redis.sadd(_ONLINE_SET, username)
        await pubsub.subscribe(_BROADCAST_CHANNEL, user_channel)

        # 连接建立即推送当前在线人数，并通知所有人人数变化
        online = await redis.scard(_ONLINE_SET)
        await broadcast(ONLINE_COUNT, online)
        yield {"event": ONLINE_COUNT, "data": json.dumps(online, ensure_ascii=False)}

        # 后台任务：把 Redis pubsub 消息搬到本地队列
        async def listen() -> None:
            try:
                async for msg in pubsub.listen():
                    if msg["type"] == "message":
                        try:
                            await queue.put(json.loads(msg["data"]))
                        except Exception:
                            logger.exception("SSE message decode error")
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("SSE Redis listener error")

        listen_task = asyncio.create_task(listen())
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_TIMEOUT)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "keepalive"}
        finally:
            listen_task.cancel()
            try:
                await listen_task
            except asyncio.CancelledError:
                pass
            await pubsub.unsubscribe(_BROADCAST_CHANNEL, user_channel)
            await pubsub.close()
            await redis.srem(_ONLINE_SET, username)
            remaining = await redis.scard(_ONLINE_SET)
            await broadcast(ONLINE_COUNT, remaining)
            logger.info("SSE disconnected: user={}", username)

    return EventSourceResponse(event_generator())


async def broadcast(event: str, data) -> None:
    """向 sse:broadcast 广播事件，data 须为 JSON 可序列化类型。"""
    redis = await get_redis()
    await redis.publish(_BROADCAST_CHANNEL, _encode(event, data))


async def send_to_user(username: str, event: str, data) -> None:
    """定向推送给指定用户的所有在线连接（多设备）。"""
    redis = await get_redis()
    await redis.publish(_user_channel(username), _encode(event, data))


async def get_online_count() -> int:
    """当前在线用户数。"""
    redis = await get_redis()
    return await redis.scard(_ONLINE_SET)


async def get_online_users() -> list[str]:
    """返回在线用户名列表。"""
    redis = await get_redis()
    return list(await redis.smembers(_ONLINE_SET))
