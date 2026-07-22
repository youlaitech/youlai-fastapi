"""角色管理路由。"""

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import SysUserDetails
from app.database import get_db
from app.dependencies import get_current_user, require_perm
from app.response import Result
from app.system.log.constants import ActionTypeEnum, LogModuleEnum
from app.system.log.operation_log import operation_log
from app.system.role.schemas import (
    RoleCreate, RoleQuery, RoleUpdate,
)
from app.system.role.service import RoleService

router = APIRouter(prefix="/api/v1/roles", tags=["角色管理"])


@router.get("", summary="角色分页列表", dependencies=[Depends(require_perm("sys:role:list"))])
async def get_role_page(
    pageNum: int = Query(default=1, ge=1), pageSize: int = Query(default=10, ge=1, le=100),
    keywords: str | None = None, status: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = RoleQuery(pageNum=pageNum, pageSize=pageSize, keywords=keywords, status=status)
    result = await RoleService(db).get_page(query)
    return Result(data=result)


@router.get("/options", summary="角色下拉选项")
async def get_role_options(db: AsyncSession = Depends(get_db)):
    result = await RoleService(db).get_options()
    return Result(data=result)


@router.get("/{role_id}/form", summary="角色表单数据", dependencies=[Depends(require_perm("sys:role:update"))])
async def get_role_form(role_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await RoleService(db).get_role_form(role_id))


@router.post("", summary="创建角色", dependencies=[Depends(require_perm("sys:role:create"))])
@operation_log(module=LogModuleEnum.ROLE, action_type=ActionTypeEnum.INSERT, title="新增角色")
async def create_role(
    request: Request,
    form: RoleCreate,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vo = await RoleService(db).create(form)
    return Result(data=vo)


@router.put("/{role_id}", summary="更新角色", dependencies=[Depends(require_perm("sys:role:update"))])
@operation_log(module=LogModuleEnum.ROLE, action_type=ActionTypeEnum.UPDATE, title="修改角色")
async def update_role(
    request: Request,
    role_id: int,
    form: RoleUpdate,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    form.id = role_id
    vo = await RoleService(db).update(form)
    return Result(data=vo)


@router.delete("/{ids}", summary="删除角色", dependencies=[Depends(require_perm("sys:role:delete"))])
async def delete_roles(ids: str, db: AsyncSession = Depends(get_db)):
    count = await RoleService(db).delete(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")


@router.put("/{role_id}/status", summary="修改角色状态", dependencies=[Depends(require_perm("sys:role:update"))])
async def update_role_status(role_id: int, status: int, db: AsyncSession = Depends(get_db)):
    await RoleService(db).update_status(role_id, status)
    return Result(data=None)


@router.get("/{role_id}/menu-ids", summary="获取角色菜单ID列表")
async def get_role_menu_ids(role_id: int, db: AsyncSession = Depends(get_db)):
    ids = await RoleService(db).get_role_menu_ids(role_id)
    return Result(data=ids)


@router.put("/{role_id}/menus", summary="分配菜单权限", dependencies=[Depends(require_perm("sys:role:assign"))])
@operation_log(module=LogModuleEnum.ROLE, action_type=ActionTypeEnum.GRANT, title="分配菜单权限")
async def assign_role_menus(
    request: Request,
    role_id: int,
    menuIds: list[int] = Body(...),
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await RoleService(db).assign_menus(role_id, menuIds)
    return Result(data=None)


@router.get("/{role_id}/dept-ids", summary="获取角色部门ID集合", dependencies=[Depends(require_perm("sys:role:update"))])
async def get_role_dept_ids(role_id: int, db: AsyncSession = Depends(get_db)):
    ids = await RoleService(db).get_role_dept_ids(role_id)
    return Result(data=ids)
