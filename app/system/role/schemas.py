"""角色管理 Schemas。"""

from pydantic import BaseModel, Field

from app.serializers import BigId


class RoleQuery(BaseModel):
    pageNum: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=100)
    keywords: str | None = Field(default=None, description="角色名称/编码搜索")
    status: int | None = Field(default=None)


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="角色名称")
    code: str = Field(..., min_length=1, max_length=32, description="角色编码")
    sort: int = Field(default=0, description="排序")
    status: int = Field(default=1, description="状态 1-正常 0-停用")
    dataScope: int | None = Field(default=None, description="数据权限范围")
    menuIds: list[BigId] = Field(default_factory=list, description="菜单权限ID列表")
    deptIds: list[BigId] = Field(default_factory=list, description="数据权限部门ID列表")


class RoleUpdate(BaseModel):
    id: BigId = Field(..., description="角色ID")
    name: str = Field(..., min_length=1, max_length=64)
    code: str = Field(..., min_length=1, max_length=32)
    sort: int = Field(default=0)
    status: int = Field(default=1)
    dataScope: int | None = None
    menuIds: list[BigId] = Field(default_factory=list)
    deptIds: list[BigId] = Field(default_factory=list)


class RoleStatusForm(BaseModel):
    roleId: BigId
    status: int


class RoleMenuForm(BaseModel):
    roleId: BigId
    menuIds: list[BigId] = Field(default_factory=list)


class RoleVO(BaseModel):
    id: BigId | None = None
    name: str = ""
    code: str = ""
    sort: int = 0
    status: int = 1
    dataScope: int | None = None
    menuIds: list[BigId] = Field(default_factory=list)
    deptIds: list[BigId] = Field(default_factory=list)
    createTime: str | None = None
    updateTime: str | None = None
    model_config = {"from_attributes": True}


class RoleForm(RoleUpdate):
    pass


class RoleOptionVO(BaseModel):
    """角色下拉选项。"""
    value: BigId = Field(..., alias="id")
    label: str = Field(..., alias="name")
    model_config = {"from_attributes": True}
