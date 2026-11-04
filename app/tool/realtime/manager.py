"""实时推送管理 — Redis Pub/Sub 通道与在线状态。

主题广播走 realtime:topic:{topic}，定向推送走 realtime:user:{username}，
在线用户集合存 Redis Set realtime:online，跨 worker 共享。
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.redis import get_redis

_TOPIC_CHANNEL_PREFIX = "realtime:topic:"
_USER_CHANNEL_PREFIX = "realtime:user:"
_ONLINE_SET = "realtime:online"
_CONNECTIONS_SET = "realtime:online:connections"

# 节点标识，进程内固定，用于前端区分多节点部署
NODE_ID = uuid.uuid4().hex


def topic_channel(topic: str) -> str:
    """主题广播频道名。"""
    return f"{_TOPIC_CHANNEL_PREFIX}{topic}"


def user_channel(username: str) -> str:
    """用户定向推送频道名。"""
    return f"{_USER_CHANNEL_PREFIX}{username}"


def encode(type_: str, payload: Any) -> str:
    """按协议封装服务端消息。"""
    return json.dumps(
        {
            "version": 1,
            "id": uuid.uuid4().hex,
            "type": type_,
            "payload": payload,
        },
        default=str,
        ensure_ascii=False,
    )


async def broadcast(topic: str, type_: str, payload: Any) -> None:
    """向订阅该主题的全部连接广播消息。"""
    redis = await get_redis()
    await redis.publish(topic_channel(topic), encode(type_, payload))


async def send_to_user(username: str, type_: str, payload: Any) -> None:
    """定向推送给指定用户的所有在线连接。"""
    redis = await get_redis()
    await redis.publish(user_channel(username), encode(type_, payload))


async def mark_online(username: str) -> None:
    """登记在线用户"""
    redis = await get_redis()
    await redis.sadd(_ONLINE_SET, username)


async def mark_offline(username: str) -> None:
    """注销在线用户"""
    redis = await get_redis()
    await redis.srem(_ONLINE_SET, username)


async def mark_connection_opened(connection_id: int) -> None:
    """登记一条在线连接"""
    redis = await get_redis()
    await redis.sadd(_CONNECTIONS_SET, str(connection_id))


async def mark_connection_closed(connection_id: int) -> None:
    """注销一条在线连接"""
    redis = await get_redis()
    await redis.srem(_CONNECTIONS_SET, str(connection_id))


async def presence_snapshot() -> dict:
    """生成在线状态快照"""
    redis = await get_redis()
    now = datetime.now(timezone.utc)
    return {
        "onlineUsers": await redis.scard(_ONLINE_SET),
        "onlineConnections": await redis.scard(_CONNECTIONS_SET),
        "nodeId": NODE_ID,
        "observedAt": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
    }


async def get_online_users() -> list[str]:
    """在线用户名列表。"""
    redis = await get_redis()
    return list(await redis.smembers(_ONLINE_SET))
