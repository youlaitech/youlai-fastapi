"""实时 WebSocket 连接处理。"""

import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.redis import get_redis
from app.tool.realtime.manager import (
    encode,
    mark_offline,
    mark_online,
    topic_channel,
    user_channel,
)
from app.tool.realtime.manager import mark_connection_closed, mark_connection_opened
from app.tool.realtime.topics import CONNECTION_READY, HEARTBEAT_PING, HEARTBEAT_PONG, HEARTBEAT_TIMEOUT_MS

# 心跳间隔与超时，与 youlai-boot 保持一致
_PING_INTERVAL = 25
_PONG_TIMEOUT = 60

# 单帧上限
_MAX_MESSAGE_BYTES = 16 * 1024


async def realtime_connect(websocket: WebSocket, grant: dict) -> None:
    """建立实时连接并收发消息。"""
    username = grant["username"]
    topics = set(grant.get("topics") or [])

    await websocket.accept()

    redis = await get_redis()
    queue: asyncio.Queue = asyncio.Queue()
    pubsub = redis.pubsub()
    channels = [topic_channel(topic) for topic in topics] + [user_channel(username)]

    await mark_online(username)
    await mark_connection_opened(id(websocket))
    await pubsub.subscribe(*channels)

    await websocket.send_text(encode(CONNECTION_READY, {"heartbeatTimeoutMs": HEARTBEAT_TIMEOUT_MS}))

    # 心跳状态由收发两侧共享，同一事件循环内无需加锁
    state: dict[str, Any] = {"last_pong": time.monotonic(), "pending_ping_id": None}

    async def listen() -> None:
        """把 Redis 订阅到的消息搬到本地队列。"""
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    await queue.put(msg["data"])
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Redis 监听异常")

    async def sender() -> None:
        """发送队列中的消息，无消息时按间隔发送心跳。"""
        while True:
            try:
                raw = await asyncio.wait_for(queue.get(), timeout=_PING_INTERVAL)
            except asyncio.TimeoutError:
                if time.monotonic() - state["last_pong"] >= _PONG_TIMEOUT:
                    logger.info(f"实时连接心跳超时: user={username}")
                    await websocket.close(code=4011)
                    return
                ping_id = uuid.uuid4().hex
                state["pending_ping_id"] = ping_id
                await websocket.send_text(
                    json.dumps(
                        {
                            "version": 1,
                            "id": ping_id,
                            "type": HEARTBEAT_PING,
                            "payload": {},
                        },
                        ensure_ascii=False,
                    )
                )
                continue
            await websocket.send_text(raw)

    async def receiver() -> None:
        """接收客户端心跳响应，其余消息忽略。"""
        while True:
            data = await websocket.receive_text()
            if len(data.encode("utf-8")) > _MAX_MESSAGE_BYTES:
                await websocket.close(code=4009)
                return
            try:
                payload = json.loads(data)
            except ValueError:
                continue
            if not isinstance(payload, dict) or payload.get("version") != 1:
                continue
            if payload.get("type") != HEARTBEAT_PONG:
                continue
            ping_id = (payload.get("payload") or {}).get("pingId")
            if ping_id and ping_id == state["pending_ping_id"]:
                state["pending_ping_id"] = None
                state["last_pong"] = time.monotonic()

    listen_task = asyncio.create_task(listen())
    try:
        await asyncio.gather(sender(), receiver())
    except WebSocketDisconnect:
        pass
    finally:
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass
        try:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
        except Exception:
            logger.exception("取消 Redis 订阅失败")
        await mark_offline(username)
        await mark_connection_closed(id(websocket))
        logger.info(f"实时连接断开: user={username}")
