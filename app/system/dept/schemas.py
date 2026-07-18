"""部门管理 Schemas。"""

from pydantic import BaseModel, Field

from app.serializers import BigId


class DeptQuery(BaseModel):
    keywords: str | None = None
    status: int | None = None


class DeptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="部门名称")
    code: str = Field(..., min_length=1, max_length=100, description="部门编号")
    parentId: BigId = Field(default=0, description="父节点ID")
    sort: int = Field(default=0, description="排序")
    status: int = Field(default=1, description="状态 1-正常 0-禁用")


class DeptUpdate(BaseModel):
    id: BigId
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=100)
    parentId: BigId = Field(default=0)
    sort: int = Field(default=0)
    status: int = Field(default=1)


class DeptVO(BaseModel):
    id: BigId | None = None
    name: str = ""
    code: str = ""
    parentId: BigId = 0
    treePath: str = ""
    sort: int = 0
    status: int = 1
    children: list["DeptVO"] = Field(default_factory=list)
    createTime: str | None = None
    model_config = {"from_attributes": True}


# 解析 forward reference（DeptVO.children 中的字符串引用）
DeptVO.model_rebuild()
