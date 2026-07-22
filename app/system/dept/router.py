"""部门管理路由。"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import SysUserDetails
from app.database import get_db
from app.dependencies import get_current_user, require_perm
from app.response import Result
from app.system.dept.schemas import DeptCreate, DeptUpdate
from app.system.dept.service import DeptService
from app.system.log.operation_log import operation_log
from app.system.log.constants import ActionTypeEnum, LogModuleEnum

router = APIRouter(prefix="/api/v1/depts", tags=["部门管理"])


@router.get("", summary="部门树", dependencies=[Depends(require_perm("sys:dept:list"))])
async def get_dept_tree(
    keywords: str | None = None, status: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    tree = await DeptService(db).get_tree(keywords, status)
    return Result(data=tree)


@router.get("/options", summary="部门下拉选项", dependencies=[Depends(require_perm())])
async def get_dept_options(db: AsyncSession = Depends(get_db)):
    options = await DeptService(db).get_options()
    return Result(data=options)


@router.get("/{dept_id}", summary="部门详情", dependencies=[Depends(require_perm("sys:dept:detail"))])
async def get_dept(dept_id: int, db: AsyncSession = Depends(get_db)):
    vo = await DeptService(db).get_by_id(dept_id)
    return Result(data=vo)


@router.get("/{dept_id}/form", summary="部门表单数据", dependencies=[Depends(require_perm("sys:dept:update"))])
async def get_dept_form(dept_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await DeptService(db).get_dept_form(dept_id))


@router.post("", summary="创建部门", dependencies=[Depends(require_perm("sys:dept:create"))])
@operation_log(module=LogModuleEnum.DEPT, action_type=ActionTypeEnum.INSERT, title="新增部门")
async def create_dept(
    request: Request,
    form: DeptCreate,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vo = await DeptService(db).create(form)
    return Result(data=vo)


@router.put("/{dept_id}", summary="更新部门", dependencies=[Depends(require_perm("sys:dept:update"))])
@operation_log(module=LogModuleEnum.DEPT, action_type=ActionTypeEnum.UPDATE, title="修改部门")
async def update_dept(
    request: Request,
    dept_id: int,
    form: DeptUpdate,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    form.id = dept_id
    vo = await DeptService(db).update(form)
    return Result(data=vo)


@router.delete("/{ids}", summary="删除部门", dependencies=[Depends(require_perm("sys:dept:delete"))])
@operation_log(module=LogModuleEnum.DEPT, action_type=ActionTypeEnum.DELETE, title="删除部门")
async def delete_depts(
    request: Request,
    ids: str,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await DeptService(db).delete(ids)
    return Result(data=count, msg=f"成功删除 {count} 条记录")
