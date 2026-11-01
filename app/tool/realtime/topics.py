"""实时推送主题与消息类型常量。"""

# 订阅主题，连接必须包含 notice
TOPIC_NOTICE = "notice"
TOPIC_DICT = "dict"
TOPIC_PRESENCE = "presence"

# 当前支持的全部主题
SUPPORTED_TOPICS = frozenset({TOPIC_NOTICE, TOPIC_DICT, TOPIC_PRESENCE})

# 连接就绪，data 为 {"heartbeatTimeoutMs": int}
CONNECTION_READY = "connection.ready"

# 心跳应答超时时间（毫秒），与前端协议保持一致
HEARTBEAT_TIMEOUT_MS = 60000

# 公告变更，data 为 {"noticeId": str, "action": "published"|"revoked"}
NOTICE_CHANGED = "notice.changed"

# 字典变更，data 为 {"dictCode": str}
DICT_CHANGED = "dict.changed"

# 在线状态快照，data 为 {"onlineUsers": int, "onlineConnections": int, "nodeId": str, "observedAt": str}
PRESENCE_SNAPSHOT = "presence.snapshot"

# 心跳消息类型
HEARTBEAT_PING = "heartbeat.ping"
HEARTBEAT_PONG = "heartbeat.pong"
