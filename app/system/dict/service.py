"""字典管理服务。"""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.pagination import PageResult
from app.exceptions import BusinessException
from app.response import ResultCode
from app.system.dict.models import SysDict, SysDictItem
from app.system.dict.schemas import (
    DictCreate, DictItemCreate, DictItemUpdate, DictItemVO,
    DictQuery, DictUpdate, DictVO, DictItemOptionVO,
)


class DictService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_type_page(self, query: DictQuery) -> PageResult:
        """分页查询字典类型，支持按名称/编码关键字筛选。"""
        conditions = [SysDict.is_deleted == 0]
        if query.keywords:
            kw = f"%{query.keywords}%"
            conditions.append(SysDict.name.ilike(kw) | SysDict.dict_code.ilike(kw))
        base = select(SysDict).where(*conditions)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(select(SysDict).where(*conditions).offset(offset).limit(query.pageSize))
        vo_list = [DictVO.model_validate(d, from_attributes=True) for d in rows.scalars().all()]
        return PageResult(records=vo_list, total=total, pageNum=query.pageNum, pageSize=query.pageSize)

    async def get_type_by_id(self, dict_id: int) -> DictVO:
        """根据 id 获取字典类型详情。"""
        obj = await self.db.get(SysDict, dict_id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="字典类型不存在")
        return DictVO.model_validate(obj, from_attributes=True)

    async def get_dict_form(self, dict_id: int) -> DictUpdate:
        """获取字典类型编辑表单数据。"""
        obj = await self.db.get(SysDict, dict_id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="字典类型不存在")
        return DictUpdate.model_validate(obj, from_attributes=True)

    async def get_dict_options(self) -> list[dict]:
        """返回字典类型下拉选项（dict_code + 名称）。"""
        rows = await self.db.execute(
            select(SysDict.dict_code, SysDict.name).where(SysDict.is_deleted == 0, SysDict.status == 1)
        )
        return [{"value": r.dict_code, "label": r.name} for r in rows]

    async def create_type(self, form: DictCreate) -> DictVO:
        """创建字典类型；dict_code 重复时返回 B0002。"""
        exist = await self.db.execute(select(SysDict.id).where(SysDict.dict_code == form.dictCode, SysDict.is_deleted == 0))
        if exist.scalar() is not None:
            raise BusinessException(code=ResultCode.DUPLICATE_KEY, msg="字典编码已存在")
        obj = SysDict(dict_code=form.dictCode, name=form.name, status=form.status, remark=form.remark)
        self.db.add(obj); await self.db.flush()
        return DictVO.model_validate(obj, from_attributes=True)

    async def update_type(self, form: DictUpdate) -> DictVO:
        """更新字典类型。"""
        obj = await self.db.get(SysDict, form.id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="字典类型不存在")
        obj.dict_code = form.dictCode
        obj.name = form.name
        obj.status = form.status
        obj.remark = form.remark
        await self.db.flush()
        return DictVO.model_validate(obj, from_attributes=True)

    async def get_dict_codes_by_ids(self, ids: str) -> list[str]:
        """删除前查出 dict_code 列表，供 SSE 广播通知。"""
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        if not id_list:
            return []
        rows = await self.db.execute(
            select(SysDict.dict_code).where(SysDict.id.in_(id_list), SysDict.is_deleted == 0)
        )
        return [r.dict_code for r in rows if r.dict_code]

    async def delete_type(self, ids: str) -> int:
        """批量逻辑删除字典类型，并级联删除其下所有字典项。"""
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        for did in id_list:
            obj = await self.db.get(SysDict, did)
            if obj:
                await self.db.execute(
                    delete(SysDictItem).where(SysDictItem.dict_code == obj.dict_code)
                )
                obj.is_deleted = 1
        await self.db.flush()
        return len(id_list)

    async def get_items(self, dict_code: str) -> list[DictItemVO]:
        """获取指定字典类型下的全部字典项（按 sort 排序）。"""
        rows = await self.db.execute(
            select(SysDictItem).where(SysDictItem.dict_code == dict_code).order_by(SysDictItem.sort.asc())
        )
        return [DictItemVO.model_validate(r, from_attributes=True) for r in rows.scalars().all()]

    async def get_item_options(self, dict_code: str) -> list[DictItemOptionVO]:
        """返回字典项下拉选项（仅启用项）。"""
        rows = await self.db.execute(
            select(SysDictItem).where(
                SysDictItem.dict_code == dict_code, SysDictItem.status == 1
            ).order_by(SysDictItem.sort.asc())
        )
        return [DictItemOptionVO.model_validate(r, from_attributes=True) for r in rows.scalars().all()]

    async def get_item_form(self, item_id: int) -> DictItemUpdate:
        """获取字典项编辑表单数据。"""
        obj = await self.db.get(SysDictItem, item_id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="字典项不存在")
        return DictItemUpdate.model_validate(obj, from_attributes=True)

    async def get_item_by_id(self, item_id: int) -> DictItemVO:
        """根据 id 获取字典项详情。"""
        obj = await self.db.get(SysDictItem, item_id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="字典项不存在")
        return DictItemVO.model_validate(obj, from_attributes=True)

    async def create_item(self, form: DictItemCreate) -> DictItemVO:
        obj = SysDictItem(
            dict_code=form.dictCode, value=form.value, label=form.label,
            tag_type=form.tagType, status=form.status, sort=form.sort, remark=form.remark,
        )
        self.db.add(obj); await self.db.flush()
        return DictItemVO.model_validate(obj, from_attributes=True)

    async def update_item(self, form: DictItemUpdate) -> DictItemVO:
        """更新字典项。"""
        obj = await self.db.get(SysDictItem, form.id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="字典项不存在")
        obj.dict_code = form.dictCode
        obj.value = form.value
        obj.label = form.label
        obj.tag_type = form.tagType
        obj.status = form.status
        obj.sort = form.sort
        obj.remark = form.remark
        await self.db.flush()
        return DictItemVO.model_validate(obj, from_attributes=True)

    async def delete_items(self, ids: str) -> int:
        """批量删除字典项（物理删除）。"""
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        for iid in id_list:
            obj = await self.db.get(SysDictItem, iid)
            if obj: await self.db.delete(obj)
        await self.db.flush()
        return len(id_list)
