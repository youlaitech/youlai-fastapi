"""全局常量。

集中安全前缀、Redis Key 前缀、系统级全局常量。
域专属常量放在各自域目录的 constants.py（如 DEFAULT_PASSWORD 在 app/user/constants.py）。
"""

# ── 安全 ──
ROLE_PREFIX = "ROLE_"
ROOT_ROLE_CODE = "ADMIN"
TOKEN_HEADER = "Authorization"
TOKEN_PREFIX = "Bearer "

# ── Redis Key 前缀 ──
REDIS_TOKEN_BLACKLIST = "token:blacklist:"
REDIS_CAPTCHA_PREFIX = "captcha:image:"
REDIS_ONLINE_USER = "online:user:"
REDIS_DICT_CACHE = "dict:cache:"
REDIS_CONFIG_CACHE = "config:cache:"
REDIS_USER_CACHE = "user:cache:"
REDIS_RATE_LIMIT_PREFIX = "rate_limit:"

# 扫码登录票据 Key 前缀（完整 Key 为 auth:qr_code:{ticket}）与有效期（秒）
QR_CODE_PREFIX = "auth:qr_code:"
QR_CODE_TTL = 300

# ── 系统级全局 ──
SUPER_ADMIN_ID = 1   # 内置超管账号 id
ROOT_DEPT_ID = 1     # 根部门 id
