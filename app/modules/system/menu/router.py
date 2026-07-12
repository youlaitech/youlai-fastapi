"""菜单管理路由。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.framework.security.deps import get_current_user, require_perm
from app.framework.security.schemas import SysUserDetails
from app.framework.web.response import Result
from app.modules.system.menu.schemas import MenuCreate, MenuUpdate, MenuVisibleForm
from app.modules.system.menu.service import MenuService

router = APIRouter(prefix="/api/v1/menus", tags=["菜单管理"])


@router.get("", summary="菜单树", dependencies=[Depends(require_perm("sys:menu:list"))])
async def get_menu_tree(
    keywords: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    tree = await MenuService(db).get_tree(keywords)
    return Result(data=tree)


@router.get("/options", summary="菜单下拉选项", dependencies=[Depends(require_perm())])
async def get_menu_options(
    onlyParent: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    options = await MenuService(db).get_options(onlyParent)
    return Result(data=options)


@router.get("/routes", summary="前端动态路由", dependencies=[Depends(require_perm())])
async def get_routes(
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    routes = await MenuService(db).get_routes(user.roles, user.isRoot)
    return Result(data=routes)


@router.get("/{menu_id}/form", summary="菜单表单数据", dependencies=[Depends(require_perm("sys:menu:update"))])
async def get_menu_form(menu_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await MenuService(db).get_menu_form(menu_id))


@router.post("", summary="创建菜单", dependencies=[Depends(require_perm("sys:menu:create"))])
async def create_menu(form: MenuCreate, db: AsyncSession = Depends(get_db)):
    vo = await MenuService(db).create(form)
    return Result(data=vo)


@router.put("/{menu_id}", summary="更新菜单", dependencies=[Depends(require_perm("sys:menu:update"))])
async def update_menu(menu_id: int, form: MenuUpdate, db: AsyncSession = Depends(get_db)):
    form.id = menu_id
    vo = await MenuService(db).update(form)
    return Result(data=vo)


@router.delete("/{menu_id}", summary="删除菜单", dependencies=[Depends(require_perm("sys:menu:delete"))])
async def delete_menu(menu_id: int, db: AsyncSession = Depends(get_db)):
    await MenuService(db).delete(menu_id)
    return Result(data=None)


@router.patch("/{menu_id}", summary="修改菜单显示状态", dependencies=[Depends(require_perm("sys:menu:update"))])
async def update_menu_visible(menu_id: int, visible: int, db: AsyncSession = Depends(get_db)):
    await MenuService(db).update_visible(menu_id, visible)
    return Result(data=None)
