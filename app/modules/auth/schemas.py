"""认证模块 Schema。"""

from pydantic import BaseModel, Field


class LoginForm(BaseModel):
    """账号密码登录表单。"""
    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    password: str = Field(..., min_length=1, max_length=100, description="密码")
    captchaId: str | None = Field(default=None, description="验证码ID")
    captchaCode: str | None = Field(default=None, description="验证码")


class SmsLoginForm(BaseModel):
    """短信验证码登录表单。"""
    mobile: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")
    smsCode: str = Field(..., min_length=4, max_length=6, description="短信验证码")


class RefreshTokenForm(BaseModel):
    """刷新令牌表单。"""
    refreshToken: str = Field(..., description="刷新令牌")


class LoginResult(BaseModel):
    """登录返回。"""
    accessToken: str = ""
    refreshToken: str = ""
    tokenType: str = "Bearer"
    expiresIn: int = 0


class UserInfoVO(BaseModel):
    """当前用户信息 VO — 前端 /api/v1/users/me 返回。"""
    userId: int | None = None
    username: str = ""
    nickname: str = ""
    avatar: str | None = None
    roles: list[str] = Field(default_factory=list)
    perms: list[str] = Field(default_factory=list)
    deptId: int | None = None
