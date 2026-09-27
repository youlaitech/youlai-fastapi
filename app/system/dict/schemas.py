"""字典管理 Schemas。"""

from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field, field_validator

from app.serializers import BigId


def _orm_alias(camel: str, snake: str) -> AliasChoices:
    """兼容两种来源：读取 ORM 时用下划线字段，接收前端 JSON 时驼峰/下划线都认。"""
    return AliasChoices(snake, camel)


class DictQuery(BaseModel):
    pageNum: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=100)
    keywords: str | None = None


class DictItemQuery(BaseModel):
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
    dictCode: str = Field(..., min_length=1, max_length=50,
                          validation_alias=_orm_alias("dictCode", "dict_code"))
    name: str = Field(..., min_length=1, max_length=50)
    status: int = Field(default=1)
    remark: str | None = None


class DictForm(DictUpdate):
    pass


class DictItemCreate(BaseModel):
    dictCode: str | None = Field(default=None, description="关联字典编码",
                                 validation_alias=_orm_alias("dictCode", "dict_code"))
    value: str = Field(..., max_length=50)
    label: str = Field(..., max_length=100)
    tagType: str | None = Field(default=None, max_length=50,
                                validation_alias=_orm_alias("tagType", "tag_type"))
    status: int = Field(default=1)
    sort: int = Field(default=0)
    remark: str | None = None


class DictItemUpdate(BaseModel):
    id: BigId
    # 字典编码由路径参数注入（与参考实现一致），请求体可不带
    dictCode: str | None = Field(default=None, validation_alias=_orm_alias("dictCode", "dict_code"))
    value: str
    label: str
    tagType: str | None = Field(default=None, validation_alias=_orm_alias("tagType", "tag_type"))
    status: int = Field(default=1)
    sort: int = Field(default=0)
    remark: str | None = None


class DictItemForm(DictItemUpdate):
    pass


def _format_time(value):
    """ORM datetime 转成与其它后端一致的字符串格式。"""
    return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else value


class DictVO(BaseModel):
    id: BigId | None = None
    dictCode: str = Field(default="", validation_alias=_orm_alias("dictCode", "dict_code"))
    name: str = ""
    status: int = 1
    remark: str | None = None
    createTime: str | None = Field(default=None, validation_alias=_orm_alias("createTime", "create_time"))
    updateTime: str | None = Field(default=None, validation_alias=_orm_alias("updateTime", "update_time"))
    model_config = {"from_attributes": True}

    @field_validator("createTime", "updateTime", mode="before")
    @classmethod
    def _fmt_time(cls, value):
        return _format_time(value)


class DictItemVO(BaseModel):
    id: BigId | None = None
    dictCode: str = Field(default="", validation_alias=_orm_alias("dictCode", "dict_code"))
    value: str = ""
    label: str = ""
    tagType: str | None = Field(default=None, validation_alias=_orm_alias("tagType", "tag_type"))
    status: int = 1
    sort: int = 0
    remark: str | None = None
    model_config = {"from_attributes": True}


class DictItemOptionVO(BaseModel):
    value: str
    label: str
    tagType: str | None = Field(default=None, validation_alias=_orm_alias("tagType", "tag_type"))
    sort: int | None = None
    model_config = {"from_attributes": True}
