"""应用配置，从 .env 与环境变量读取（pydantic-settings）。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """配置项均可用 .env 或环境变量覆盖。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # ── 数据库 ──
    DATABASE_URL: str = "postgresql+asyncpg://youlai:Youlai%402026@www.youlai.tech:15432/youlai_admin"

    # ── Redis ──
    REDIS_URL: str = "redis://:123456@www.youlai.tech:6379/0"

    # ── 认证 ──
    SESSION_TYPE: str = "jwt"
    JWT_SECRET_KEY: str = "SecretKey012345678901234567890123456789012345678901234567890123456789"
    ACCESS_TOKEN_TTL: int = 7200
    REFRESH_TOKEN_TTL: int = 604800
    ALLOW_MULTI_LOGIN: bool = True

    # ── S3（RustFS） ──
    S3_ENDPOINT: str = "111.229.83.153:9000"
    S3_ACCESS_KEY: str = "rustfs-admin"
    S3_SECRET_KEY: str = "rustfs-admin"
    S3_BUCKET: str = "public"
    S3_SECURE: bool = False

    # ── 邮件 ──
    MAIL_USERNAME: str = "your-email@example.com"
    MAIL_PASSWORD: str = "123456"
    MAIL_FROM: str = "youlaitech@163.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.youlai.tech"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # ── 限流 ──
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_IP_LIMIT: int = 1000     # IP 窗口内最大请求数
    RATE_LIMIT_IP_WINDOW: int = 60      # IP 滑动窗口大小（秒）

    # ── CORS ──
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── 文件上传 ──
    FILE_MAX_SIZE_MB: int = 50
    FILE_ALLOWED_TYPES: str = "jpg,jpeg,png,gif"

    # ── 调试 ──
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"


settings = Settings()
