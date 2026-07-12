"""公共常量。"""


class SecurityConstants:
    """安全相关常量。"""
    ROLE_PREFIX = "ROLE_"
    ROOT_ROLE_CODE = "ADMIN"
    TOKEN_HEADER = "Authorization"
    TOKEN_PREFIX = "Bearer "


class RedisConstants:
    """Redis Key 前缀常量。"""
    TOKEN_BLACKLIST = "token:blacklist:"
    CAPTCHA_PREFIX = "captcha:image:"
    ONLINE_USER = "online:user:"
    DICT_CACHE = "dict:cache:"
    CONFIG_CACHE = "config:cache:"
    USER_CACHE = "user:cache:"
    RATE_LIMIT_PREFIX = "rate_limit:"


class SystemConstants:
    """系统级常量。"""
    DEFAULT_PASSWORD = "123456"   # 种子用户的初始密码
    CAPTCHA_TTL = 300  # 秒，验证码在 Redis 中的存活时间
    MAX_PAGE_SIZE = 100           # 单页条数上限，防止一次拉取过多
    DEFAULT_PAGE_SIZE = 10
    SUPER_ADMIN_ID = 1            # 内置超管账号 id
    ROOT_DEPT_ID = 1              # 根部门 id
