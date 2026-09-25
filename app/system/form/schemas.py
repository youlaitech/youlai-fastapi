"""动态表单 Pydantic 模型。"""
from pydantic import BaseModel, Field


class FormDefinitionPageVO(BaseModel):
    """表单定义分页行。"""
    id: int | None = None
    formKey: str = ""
    formName: str = ""
    description: str | None = None
    status: int = 0
    isPublic: int = 0
    category: str = "normal"
    version: int = 1
    createTime: str | None = None


class FormDefinitionForm(BaseModel):
    """表单定义回显（设计器数据）。"""
    id: int | None = None
    formKey: str = ""
    formName: str = ""
    description: str | None = None
    formJson: list | None = None
    optionsJson: dict | None = None
    isPublic: int = 0
    category: str = "normal"


class FormDefinitionCreate(BaseModel):
    """表单定义入参。"""
    formKey: str = Field(min_length=1, max_length=64)
    formName: str = Field(min_length=1, max_length=100)
    description: str | None = None
    formJson: list | None = None
    optionsJson: dict | None = None
    isPublic: int | None = 0
    category: str | None = "normal"


class FormDefinitionUpdate(FormDefinitionCreate):
    """表单定义修改入参（formKey 创建后不可改，传了也被忽略）。"""


class FormMenuSave(BaseModel):
    """生成访问菜单入参。"""
    menuName: str = Field(min_length=1, max_length=50)
    parentId: int | None = None
    roleIds: list[int] | None = None


class FormMenuVO(BaseModel):
    """生成访问菜单回显。"""
    menuId: int | None = None
    menuName: str | None = None
    parentId: int | None = None
    roleIds: list[int] = Field(default_factory=list)


class FormRenderVO(BaseModel):
    """表单渲染规则。"""
    formKey: str = ""
    formName: str = ""
    version: int = 1
    formJson: list | None = None
    optionsJson: dict | None = None


class FormAiGenerateForm(BaseModel):
    """AI 生成表单规则入参。"""
    description: str = Field(min_length=1)


class FormDataPageVO(BaseModel):
    """表单数据分页行。"""
    id: int | None = None
    formVersion: int = 1
    dataJson: dict | None = None
    createBy: int | None = None
    createByName: str | None = None
    createTime: str | None = None


class FormDataDetailVO(FormDataPageVO):
    """表单数据详情（附提交时版本规则）。"""
    formJson: list | None = None
    optionsJson: dict | None = None


class FormDataSubmit(BaseModel):
    """表单数据提交（字段由规则白名单过滤，这里放开为任意字典）。"""
    model_config = {"extra": "allow"}
