"""代码生成 Pydantic Schemas。"""

from pydantic import BaseModel, Field


# ── 查询参数 ──


class TableQuery(BaseModel):
    page_num: int = Field(default=1, ge=1, alias="pageNum")
    page_size: int = Field(default=10, ge=1, le=100, alias="pageSize")
    keywords: str | None = None

    model_config = {"populate_by_name": True}


class PreviewQuery(BaseModel):
    page_type: str = Field(default="classic", alias="pageType")
    frontend_type: str = Field(default="ts", alias="type")

    model_config = {"populate_by_name": True}


# ── VO ──


class TableVO(BaseModel):
    table_name: str = Field(default="", alias="tableName")
    table_comment: str = Field(default="", alias="tableComment")
    engine: str = Field(default="", alias="engine")
    create_time: str | None = Field(default=None, alias="createTime")

    model_config = {"populate_by_name": True}


class FieldConfigVO(BaseModel):
    column_name: str = Field(default="", alias="columnName")
    column_type: str = Field(default="", alias="columnType")
    column_comment: str = Field(default="", alias="columnComment")
    is_nullable: str = Field(default="YES", alias="isNullable")
    is_pk: bool = Field(default=False)
    column_key: str = Field(default="")
    field_name: str = Field(default="")
    field_type: str = Field(default="")
    ts_type: str = Field(default="")
    is_show_in_list: int = Field(default=0, alias="isShowInList")
    is_show_in_form: int = Field(default=0, alias="isShowInForm")
    is_show_in_query: int = Field(default=0, alias="isShowInQuery")
    is_required: int = Field(default=0, alias="isRequired")
    form_type: int | None = Field(default=None, alias="formType")
    query_type: int | None = Field(default=None, alias="queryType")
    dict_type: str | None = Field(default=None, alias="dictType")
    max_length: int | None = Field(default=None, alias="maxLength")
    field_sort: int | None = Field(default=None, alias="fieldSort")

    model_config = {"populate_by_name": True}


class GenConfigVO(BaseModel):
    id: int | None = None
    table_name: str = Field(default="", alias="tableName")
    business_name: str | None = Field(default=None, alias="businessName")
    module_name: str | None = Field(default=None, alias="moduleName")
    package_name: str | None = Field(default=None, alias="packageName")
    entity_name: str = Field(default="", alias="entityName")
    author: str | None = Field(default=None, alias="author")
    parent_menu_id: int | None = Field(default=None, alias="parentMenuId")
    page_type: str | None = Field(default=None, alias="pageType")
    remove_table_prefix: str | None = Field(default=None, alias="removeTablePrefix")
    field_configs: list[FieldConfigVO] = Field(default_factory=list, alias="fieldConfigs")

    model_config = {"populate_by_name": True}


class PreviewVO(BaseModel):
    path: str = ""
    file_name: str = Field(default="", alias="fileName")
    content: str = ""
    scope: str = ""
    language: str = ""

    model_config = {"populate_by_name": True}


# ── 请求体 ──


class FieldConfigForm(BaseModel):
    id: int | None = None
    column_name: str | None = Field(default=None, alias="columnName")
    column_type: str | None = Field(default=None, alias="columnType")
    field_name: str | None = Field(default=None, alias="fieldName")
    field_sort: int | None = Field(default=None, alias="fieldSort")
    field_type: str | None = Field(default=None, alias="fieldType")
    field_comment: str | None = Field(default=None, alias="fieldComment")
    is_show_in_list: int | None = Field(default=None, alias="isShowInList")
    is_show_in_form: int | None = Field(default=None, alias="isShowInForm")
    is_show_in_query: int | None = Field(default=None, alias="isShowInQuery")
    is_required: int | None = Field(default=None, alias="isRequired")
    max_length: int | None = Field(default=None, alias="maxLength")
    form_type: int | None = Field(default=None, alias="formType")
    query_type: int | None = Field(default=None, alias="queryType")
    dict_type: str | None = Field(default=None, alias="dictType")

    model_config = {"populate_by_name": True}


class GenConfigForm(BaseModel):
    id: int | None = None
    table_name: str = Field(default="", alias="tableName")
    business_name: str | None = Field(default=None, alias="businessName")
    module_name: str | None = Field(default=None, alias="moduleName")
    package_name: str | None = Field(default=None, alias="packageName")
    entity_name: str | None = Field(default=None, alias="entityName")
    author: str | None = Field(default=None, alias="author")
    parent_menu_id: int | None = Field(default=None, alias="parentMenuId")
    page_type: str | None = Field(default=None, alias="pageType")
    remove_table_prefix: str | None = Field(default=None, alias="removeTablePrefix")
    field_configs: list[FieldConfigForm] | None = Field(default=None, alias="fieldConfigs")

    model_config = {"populate_by_name": True}
