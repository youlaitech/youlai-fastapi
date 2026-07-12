"""SSE 事件名常量。"""

# 在线用户数，data 为裸 int
ONLINE_COUNT = "online-count"

# 字典变更，data 为 {"dictCode": str, "timestamp": int}
DICT = "dict"

# 系统消息，data 为 {"sender": str, "content": str, "timestamp": int}
SYSTEM = "system"

# 通知发布，data 为 {"id": int, "title": str, "type": int, "publishTime": str|null}
NOTICE = "notice"

# 通知撤回，data 为 {"id": int}
NOTICE_REVOKE = "notice-revoke"
