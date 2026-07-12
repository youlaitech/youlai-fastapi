"""代码生成 Schemas。"""

from pydantic import BaseModel, Field


class TableQuery(BaseModel):
    pageNum: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=100)
    keywords: str | None = None


class TableVO(BaseModel):
    name: str = ""
    comment: str | None = None
    engine: str | None = None
    createTime: str | None = None


class FieldVO(BaseModel):
    columnName: str = ""
    dataType: str = ""
    columnComment: str | None = None
    isNullable: str = "YES"


class GenConfigForm(BaseModel):
    tableName: str = ""
    packageName: str = "com.youlai.boot"
    moduleName: str = ""
    className: str = ""
    classComment: str = ""
    author: str = ""


class PreviewVO(BaseModel):
    fileName: str = ""
    content: str = ""
