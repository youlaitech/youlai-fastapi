"""认证模块 Schema。"""

from pydantic import BaseModel, Field

from app.serializers import BigId


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
    userId: BigId | None = None
    username: str = ""
    nickname: str = ""
    avatar: str | None = None
    roles: list[str] = Field(default_factory=list)
    perms: list[str] = Field(default_factory=list)
    deptId: BigId | None = None


class SecurityUser(BaseModel):
    """登录时从 DB 查出的用户安全数据。"""
    userId: int | None = Field(default=None, description="用户ID")
    username: str | None = Field(default=None, description="用户名")
    password: str | None = Field(default=None, description="密码")
    nickname: str | None = Field(default=None, description="昵称")
    deptId: int | None = Field(default=None, description="部门ID")
    status: int = Field(default=1, description="状态 1-启用 0-禁用")
    roles: set[str] = Field(default_factory=set, description="角色编码集合")
    dataScopes: list[dict] = Field(default_factory=list, description="数据权限范围")
    mobile: str | None = Field(default=None, description="手机号")
    email: str | None = Field(default=None, description="邮箱")
    avatar: str | None = Field(default=None, description="头像URL")


class SysUserDetails(BaseModel):
    """认证后的用户详情，缓存到 JWT payload 中。"""
    userId: int | None = None
    username: str | None = None
    password: str | None = None
    enabled: bool = True
    deptId: int | None = None
    dataScopes: list[dict] = Field(default_factory=list)
    roles: set[str] = Field(default_factory=set)
    isRoot: bool = False

    @staticmethod
    def from_security_user(user: SecurityUser, is_root: bool = False) -> "SysUserDetails":
        """从 SecurityUser 构造。"""
        return SysUserDetails(
            userId=user.userId,
            username=user.username,
            password=None,  # 不存密码
            enabled=user.status == 1,
            deptId=user.deptId,
            dataScopes=user.dataScopes,
            roles=user.roles,
            isRoot=is_root,
        )


class AuthenticationToken(BaseModel):
    """认证令牌。"""
    accessToken: str = ""
    refreshToken: str = ""
    tokenType: str = "Bearer"
    expiresIn: int = 0


class CaptchaResult(BaseModel):
    """验证码返回。"""
    captchaId: str = Field(description="验证码ID")
    captchaBase64: str = Field(description="base64 编码的验证码图片")
