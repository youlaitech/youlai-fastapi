"""用户管理 Schemas。"""

from pydantic import BaseModel, Field

from app.serializers import BigId


class UserQuery(BaseModel):
    """用户分页查询参数。"""
    pageNum: int = Field(default=1, ge=1, description="当前页码")
    pageSize: int = Field(default=10, ge=1, le=100, description="每页条数")
    keywords: str | None = Field(default=None, description="搜索关键词（用户名/昵称/手机号）")
    deptId: BigId | None = Field(default=None, description="部门ID")
    status: int | None = Field(default=None, description="状态")


class UserCreate(BaseModel):
    """创建用户表单。"""
    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    nickname: str = Field(..., min_length=1, max_length=64, description="昵称")
    password: str = Field(default="123456", max_length=100, description="密码")
    gender: int | None = Field(default=None, description="性别")
    deptId: BigId | None = Field(default=None, description="部门ID")
    mobile: str | None = Field(default=None, pattern=r"^1[3-9]\d{9}$", description="手机号")
    email: str | None = Field(default=None, max_length=100, description="邮箱")
    status: int = Field(default=1, description="状态 1-启用 0-禁用")
    roleIds: list[BigId] = Field(default_factory=list, description="角色ID列表")


class UserUpdate(BaseModel):
    """更新用户表单。"""
    id: BigId = Field(..., description="用户ID")
    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    nickname: str = Field(..., min_length=1, max_length=64, description="昵称")
    gender: int | None = Field(default=None, description="性别")
    deptId: BigId | None = Field(default=None, description="部门ID")
    mobile: str | None = Field(default=None, pattern=r"^1[3-9]\d{9}$", description="手机号")
    email: str | None = Field(default=None, max_length=100, description="邮箱")
    status: int = Field(default=1, description="状态 1-启用 0-禁用")
    roleIds: list[BigId] = Field(default_factory=list, description="角色ID列表")


class UserForm(UserUpdate):
    pass


class UserVO(BaseModel):
    """用户 VO — 列表/详情返回。"""
    id: BigId | None = None
    username: str = ""
    nickname: str = ""
    gender: int | None = None
    deptId: BigId | None = None
    deptName: str | None = None
    mobile: str | None = None
    email: str | None = None
    avatar: str | None = None
    status: int = 1
    roleIds: list[BigId] = Field(default_factory=list)
    roleNames: list[str] = Field(default_factory=list)
    createTime: str | None = None
    updateTime: str | None = None
    model_config = {"from_attributes": True}


class UserStatusForm(BaseModel):
    """修改用户状态。"""
    userId: BigId = Field(..., description="用户ID")
    status: int = Field(..., description="状态 1-启用 0-禁用")


class UserPasswordForm(BaseModel):
    """重置密码。"""
    userId: BigId = Field(..., description="用户ID")
    password: str = Field(..., min_length=6, max_length=100, description="新密码")


class UserProfileForm(BaseModel):
    """个人中心修改表单。"""
    nickname: str | None = None
    avatar: str | None = None
    gender: int | None = None
    mobile: str | None = Field(default=None, pattern=r"^1[3-9]\d{9}$")
    email: str | None = Field(default=None, max_length=100)


class PasswordUpdateForm(BaseModel):
    """当前用户修改密码。"""
    oldPassword: str = Field(..., min_length=6, max_length=100)
    newPassword: str = Field(..., min_length=6, max_length=100)


class PasswordVerifyForm(BaseModel):
    """密码验证表单。"""
    password: str = Field(..., min_length=6, max_length=100)


class MobileUpdateForm(BaseModel):
    """绑定/更换手机号。"""
    mobile: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    smsCode: str = Field(..., min_length=4, max_length=6)


class EmailUpdateForm(BaseModel):
    """绑定/更换邮箱。"""
    email: str = Field(..., max_length=100)
    smsCode: str = Field(..., min_length=4, max_length=6)


class UserProfileVO(UserVO):
    """个人中心用户信息。"""
    pass


class CurrentUserVO(UserVO):
    """当前登录用户信息。"""
    pass


class ExcelResultVO(BaseModel):
    """Excel 导入结果。"""
    code: str = "00000"
    validCount: int = 0
    invalidCount: int = 0
    messageList: list[str] = Field(default_factory=list)
