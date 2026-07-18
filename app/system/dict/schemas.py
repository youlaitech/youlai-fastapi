"""字典管理 Schemas。"""

from pydantic import BaseModel, Field

from app.serializers import BigId


class DictQuery(BaseModel):
    pageNum: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=100)
    keywords: str | None = None


class DictCreate(BaseModel):
    dictCode: str = Field(..., min_length=1, max_length=50, description="类型编码")
    name: str = Field(..., min_length=1, max_length=50, description="类型名称")
    status: int = Field(default=1)
    remark: str | None = None


class DictUpdate(BaseModel):
    id: BigId
    dictCode: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    status: int = Field(default=1)
    remark: str | None = None


class DictForm(DictUpdate):
    pass


class DictItemCreate(BaseModel):
    dictCode: str | None = Field(default=None, description="关联字典编码")
    value: str = Field(..., max_length=50)
    label: str = Field(..., max_length=100)
    tagType: str | None = Field(default=None, max_length=50)
    status: int = Field(default=1)
    sort: int = Field(default=0)
    remark: str | None = None


class DictItemUpdate(BaseModel):
    id: BigId
    dictCode: str
    value: str
    label: str
    tagType: str | None = None
    status: int = Field(default=1)
    sort: int = Field(default=0)
    remark: str | None = None


class DictItemForm(DictItemUpdate):
    pass


class DictVO(BaseModel):
    id: BigId | None = None
    dictCode: str = ""
    name: str = ""
    status: int = 1
    remark: str | None = None
    createTime: str | None = None
    updateTime: str | None = None
    model_config = {"from_attributes": True}


class DictItemVO(BaseModel):
    id: BigId | None = None
    dictCode: str = ""
    value: str = ""
    label: str = ""
    tagType: str | None = None
    status: int = 1
    sort: int = 0
    remark: str | None = None
    model_config = {"from_attributes": True}


class DictItemOptionVO(BaseModel):
    value: str
    label: str
    tagType: str | None = None
    sort: int | None = None
    model_config = {"from_attributes": True}
