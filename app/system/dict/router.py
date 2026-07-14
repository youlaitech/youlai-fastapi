"""字典管理路由。"""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_perm
from app.response import Result
from app.tool.sse.manager import broadcast
from app.tool.sse.topics import DICT
from app.system.dict.schemas import (
    DictCreate, DictItemCreate, DictItemUpdate, DictItemVO, DictUpdate,
)
from app.system.dict.service import DictService

router = APIRouter(prefix="/api/v1/dicts", tags=["字典管理"])


@router.get("", summary="字典分页列表", dependencies=[Depends(require_perm("sys:dict:list"))])
async def get_dict_page(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    keywords: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    from app.system.dict.schemas import DictQuery
    result = await DictService(db).get_type_page(DictQuery(pageNum=pageNum, pageSize=pageSize, keywords=keywords))
    return Result(data=result)


@router.get("/options", summary="字典列表")
async def get_dict_options(db: AsyncSession = Depends(get_db)):
    return Result(data=await DictService(db).get_dict_options())


@router.get("/{id}/form", summary="获取字典表单数据")
async def get_dict_form(id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await DictService(db).get_dict_form(id))


@router.post("", summary="新增字典", dependencies=[Depends(require_perm("sys:dict:create"))])
async def create_dict(form: DictCreate, db: AsyncSession = Depends(get_db)):
    result = await DictService(db).create_type(form)
    await broadcast(DICT, {"dictCode": form.dictCode, "timestamp": int(time.time() * 1000)})
    return Result(data=result)


@router.put("/{id}", summary="修改字典", dependencies=[Depends(require_perm("sys:dict:update"))])
async def update_dict(id: int, form: DictUpdate, db: AsyncSession = Depends(get_db)):
    form.id = id
    await DictService(db).update_type(form)
    if form.dictCode:
        await broadcast(DICT, {"dictCode": form.dictCode, "timestamp": int(time.time() * 1000)})
    return Result(data=None)


@router.delete("/{ids}", summary="删除字典", dependencies=[Depends(require_perm("sys:dict:delete"))])
async def delete_dict(ids: str, db: AsyncSession = Depends(get_db)):
    # 删除前取出 dictCode 列表
    codes = await DictService(db).get_dict_codes_by_ids(ids)
    await DictService(db).delete_type(ids)
    ts = int(time.time() * 1000)
    for code in codes:
        await broadcast(DICT, {"dictCode": code, "timestamp": ts})
    return Result(data=None)


@router.get("/{dict_code}/items", summary="字典项列表")
async def get_dict_items(dict_code: str, db: AsyncSession = Depends(get_db)):
    return Result(data=await DictService(db).get_items(dict_code))


@router.get("/{dict_code}/items/options", summary="字典项下拉列表")
async def get_dict_item_options(dict_code: str, db: AsyncSession = Depends(get_db)):
    return Result(data=await DictService(db).get_item_options(dict_code))


@router.get("/{dict_code}/items/{item_id}/form", summary="字典项表单数据")
async def get_dict_item_form(dict_code: str, item_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await DictService(db).get_item_form(item_id))


@router.post("/{dict_code}/items", summary="新增字典项", dependencies=[Depends(require_perm("sys:dict-item:create"))])
async def create_dict_item(dict_code: str, form: DictItemCreate, db: AsyncSession = Depends(get_db)):
    form.dictCode = dict_code
    result = await DictService(db).create_item(form)
    await broadcast(DICT, {"dictCode": dict_code, "timestamp": int(time.time() * 1000)})
    return Result(data=result)


@router.put("/{dict_code}/items/{item_id}", summary="更新字典项", dependencies=[Depends(require_perm("sys:dict-item:update"))])
async def update_dict_item(dict_code: str, item_id: int, form: DictItemUpdate, db: AsyncSession = Depends(get_db)):
    form.id = item_id
    form.dictCode = dict_code
    await DictService(db).update_item(form)
    await broadcast(DICT, {"dictCode": dict_code, "timestamp": int(time.time() * 1000)})
    return Result(data=None)


@router.delete("/{dict_code}/items/{item_ids}", summary="删除字典项", dependencies=[Depends(require_perm("sys:dict-item:delete"))])
async def delete_dict_items(dict_code: str, item_ids: str, db: AsyncSession = Depends(get_db)):
    await DictService(db).delete_items(item_ids)
    await broadcast(DICT, {"dictCode": dict_code, "timestamp": int(time.time() * 1000)})
    return Result(data=None)
