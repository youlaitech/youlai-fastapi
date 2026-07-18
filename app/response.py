"""统一响应 Result[T] + 业务错误码 ResultCode。"""

from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    """统一响应体。

    code: 业务状态码，'00000' 表示成功
    msg:  提示信息
    data: 响应数据
    """
    code: str = Field(default="00000", description="业务状态码")
    msg: str = Field(default="成功", description="提示信息")
    data: T | None = Field(default=None, description="响应数据")


# 业务错误码 → HTTP 状态码映射
_HTTP_STATUS_MAP: dict[str, int] = {
    "00000": 200,
    # Auth
    "A0230": 401, "A0231": 401, "A0250": 401,
    "A0251": 400, "A0252": 400, "A0253": 400,
    "A0301": 403,
    "A0400": 422,
    "A0401": 404, "A0402": 401, "A0403": 403, "A0404": 400,
    "B0001": 500, "B0002": 409, "B0003": 404, "B0004": 403,
    "A0502": 429,
}


class ResultCode(str, Enum):
    """业务错误码。首位 0=成功, A=用户端(4xx), B=系统端(5xx), C=第三方(5xx)。"""

    SUCCESS = "00000"  # → HTTP 200

    # ── Token / 认证 ──
    TOKEN_INVALID = "A0230"       # → HTTP 401 访问令牌无效或过期
    TOKEN_REFRESH_FAIL = "A0231"  # → HTTP 401 刷新令牌无效或过期
    QR_CODE_NOT_FOUND = "A0250"    # → HTTP 401 扫码登录票据不存在或已过期
    QR_CODE_STATUS_ILLEGAL = "A0251"  # → HTTP 400 扫码登录状态非法
    QR_CODE_USER_MISMATCH = "A0252"   # → HTTP 400 扫码用户与确认用户不一致
    QR_CODE_ALREADY_USED = "A0253"    # → HTTP 400 扫码登录票据已使用
    ACCESS_DENIED = "A0301"       # → HTTP 403 权限不足
    USER_DISABLED = "A0403"       # → HTTP 403 用户被禁用

    # ── 参数/校验 ──
    PARAM_VALID_FAIL = "A0400"    # → HTTP 422 参数校验失败
    USERNAME_NOT_FOUND = "A0401"  # → HTTP 404 用户名不存在
    BAD_CREDENTIALS = "A0402"     # → HTTP 401 密码错误
    CAPTCHA_ERROR = "A0404"       # → HTTP 400 验证码错误

    # ── 业务异常 ──
    SYSTEM_ERROR = "B0001"        # → HTTP 500 系统执行异常
    DUPLICATE_KEY = "B0002"       # → HTTP 409 数据重复
    DATA_NOT_FOUND = "B0003"      # → HTTP 404 数据不存在
    OPERATE_DENIED = "B0004"      # → HTTP 403 操作不允许
    RATE_LIMIT_EXCEEDED = "A0502" # → HTTP 429 请求过于频繁（限流）

    @property
    def http_status(self) -> int:
        """业务错误码 → 对应的 HTTP 状态码。"""
        return _HTTP_STATUS_MAP.get(self.value, 500)
