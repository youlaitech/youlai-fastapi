"""动态表单路由（表单定义 12 个 + 数据 4 个 + 公开 2 个）。"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import SysUserDetails
from app.database import get_db
from app.dependencies import get_current_user, require_perm
from app.response import Result
from app.system.form.schemas import (
    FormAiGenerateForm, FormDataSubmit, FormDefinitionCreate, FormMenuSave,
)
from app.system.form.service import FormService
from app.system.log.constants import ActionTypeEnum, LogModuleEnum
from app.system.log.operation_log import operation_log

router = APIRouter(prefix="/api/v1/forms", tags=["动态表单"])


# ── 表单定义 ──────────────────────────────────────────────────

@router.get("", summary="表单分页列表", dependencies=[Depends(require_perm("form:definition:list"))])
async def get_form_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    keywords: str | None = None,
    status: int | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    data = await FormService(db).get_page(pageNum, pageSize, keywords, status, category)
    return Result(data=data)


@router.post("", summary="新增表单", dependencies=[Depends(require_perm("form:definition:create"))])
@operation_log(module=LogModuleEnum.FORM, action_type=ActionTypeEnum.INSERT, title="新增表单")
async def create_form(
    request: Request,
    form: FormDefinitionCreate,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    form_id = await FormService(db).create(form, user.userId)
    return Result(data=form_id)


@router.get("/options", summary="审批表单下拉选项")
async def get_form_options(db: AsyncSession = Depends(get_db)):
    return Result(data=await FormService(db).get_workflow_options())


@router.post("/ai-generate", summary="AI 生成表单规则",
             dependencies=[Depends(require_perm("form:definition:create"))])
async def ai_generate_form(form: FormAiGenerateForm, db: AsyncSession = Depends(get_db)):
    return Result(data=await FormService(db).ai_generate_rule(form.description))


# ── 公开表单（匿名，不加鉴权依赖）──────────────────────────────

@router.get("/public/{form_key}/render", summary="公开表单渲染规则")
async def public_render(form_key: str, db: AsyncSession = Depends(get_db)):
    return Result(data=await FormService(db).public_render(form_key))


@router.post("/public/{form_key}/data", summary="公开表单提交")
async def public_submit(
    form_key: str,
    form: FormDataSubmit,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    await FormService(db).submit_public(form_key, form.model_dump(), ip)
    return Result(data=None)


# ── 表单定义（id 段）───────────────────────────────────────────

@router.get("/{form_id}/form", summary="表单设计数据",
            dependencies=[Depends(require_perm("form:definition:list"))])
async def get_form_detail(form_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await FormService(db).get_form(form_id))


@router.put("/{form_id}", summary="修改表单", dependencies=[Depends(require_perm("form:definition:update"))])
@operation_log(module=LogModuleEnum.FORM, action_type=ActionTypeEnum.UPDATE, title="修改表单")
async def update_form(
    form_id: int,
    request: Request,
    form: FormDefinitionCreate,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FormService(db).update(form_id, form, user.userId)
    return Result(data=None)


@router.delete("/{ids}", summary="删除表单", dependencies=[Depends(require_perm("form:definition:delete"))])
@operation_log(module=LogModuleEnum.FORM, action_type=ActionTypeEnum.DELETE, title="删除表单")
async def delete_form(
    ids: str,
    request: Request,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FormService(db).delete(ids)
    return Result(data=None)


@router.put("/{form_id}/publish", summary="发布表单",
            dependencies=[Depends(require_perm("form:definition:update"))])
@operation_log(module=LogModuleEnum.FORM, action_type=ActionTypeEnum.UPDATE, title="发布表单")
async def publish_form(
    form_id: int,
    request: Request,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FormService(db).publish(form_id)
    return Result(data=None)


@router.put("/{form_id}/disable", summary="停用表单",
            dependencies=[Depends(require_perm("form:definition:update"))])
@operation_log(module=LogModuleEnum.FORM, action_type=ActionTypeEnum.UPDATE, title="停用表单")
async def disable_form(
    form_id: int,
    request: Request,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FormService(db).disable(form_id)
    return Result(data=None)


@router.get("/{form_id}/menu", summary="表单访问菜单回显",
            dependencies=[Depends(require_perm("form:definition:list"))])
async def get_form_menu(form_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await FormService(db).get_menu(form_id))


@router.post("/{form_id}/menu", summary="生成表单访问菜单",
             dependencies=[Depends(require_perm("form:definition:update"))])
@operation_log(module=LogModuleEnum.FORM, action_type=ActionTypeEnum.INSERT, title="生成表单菜单")
async def save_form_menu(
    form_id: int,
    request: Request,
    form: FormMenuSave,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FormService(db).save_menu(form_id, form)
    return Result(data=None)


# ── 渲染与表单数据 ────────────────────────────────────────────

@router.get("/{form_key}/render", summary="表单渲染规则",
            dependencies=[Depends(require_perm("form:definition:list"))])
async def render_form(form_key: str, db: AsyncSession = Depends(get_db)):
    return Result(data=await FormService(db).render(form_key))


@router.get("/{form_key}/data", summary="表单数据分页",
            dependencies=[Depends(require_perm("form:data:list"))])
async def get_form_data_page(
    form_key: str,
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await FormService(db).get_data_page(form_key, pageNum, pageSize))


@router.post("/{form_key}/data", summary="提交表单数据")
@operation_log(module=LogModuleEnum.FORM, action_type=ActionTypeEnum.INSERT, title="提交表单数据")
async def submit_form_data(
    form_key: str,
    request: Request,
    form: FormDataSubmit,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FormService(db).submit(form_key, form.model_dump(), user.userId)
    return Result(data=None)


@router.get("/{form_key}/data/{data_id}", summary="表单数据详情",
            dependencies=[Depends(require_perm("form:data:list"))])
async def get_form_data_detail(form_key: str, data_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await FormService(db).get_data_detail(data_id))


@router.delete("/{form_key}/data/{ids}", summary="删除表单数据",
               dependencies=[Depends(require_perm("form:data:delete"))])
@operation_log(module=LogModuleEnum.FORM, action_type=ActionTypeEnum.DELETE, title="删除表单数据")
async def delete_form_data(
    form_key: str,
    ids: str,
    request: Request,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FormService(db).delete_data(ids)
    return Result(data=None)
