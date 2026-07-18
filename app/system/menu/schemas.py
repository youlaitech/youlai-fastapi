"""菜单管理 Schemas。"""

from pydantic import BaseModel, Field

from app.serializers import BigId


class MenuQuery(BaseModel):
    keywords: str | None = None


class MenuCreate(BaseModel):
    parentId: BigId = Field(default=0, description="父菜单ID")
    name: str = Field(..., min_length=1, max_length=64, description="菜单名称")
    type: str = Field(..., description="菜单类型 C-目录 M-菜单 E-外链 B-按钮")
    routeName: str | None = Field(default=None)
    routePath: str | None = Field(default=None)
    component: str | None = None
    externalUrl: str | None = Field(default=None)
    perm: str | None = None
    alwaysShow: int = Field(default=0)
    keepAlive: int = Field(default=0)
    visible: int = Field(default=1)
    sort: int = Field(default=0)
    icon: str | None = None
    redirect: str | None = None
    params: dict | None = None


class MenuUpdate(MenuCreate):
    id: BigId = Field(..., description="菜单ID")


class MenuForm(MenuUpdate):
    pass


class MenuVisibleForm(BaseModel):
    menuId: BigId
    visible: int


class MenuVO(BaseModel):
    id: BigId | None = None
    parentId: BigId = 0
    name: str = ""
    type: str = "M"
    routeName: str | None = None
    routePath: str | None = None
    component: str | None = None
    externalUrl: str | None = None
    perm: str | None = None
    alwaysShow: int | None = 0
    keepAlive: int | None = 0
    visible: int | None = 1
    sort: int | None = 0
    icon: str | None = None
    redirect: str | None = None
    params: dict | None = None
    children: list["MenuVO"] = Field(default_factory=list)
    createTime: str | None = None
    model_config = {"from_attributes": True}


class RouteVO(BaseModel):
    """前端路由 VO。"""
    name: str = ""
    path: str = ""
    component: str | None = None
    redirect: str | None = None
    meta: dict = Field(default_factory=dict)
    children: list["RouteVO"] = Field(default_factory=list)


# 解析 forward references
MenuVO.model_rebuild()
RouteVO.model_rebuild()
