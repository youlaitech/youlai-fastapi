"""部门管理服务 — 树形结构。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.exceptions import BusinessException
from app.response import ResultCode
from app.system.dept.models import SysDept
from app.system.dept.schemas import DeptCreate, DeptUpdate, DeptVO


class DeptService:
    """部门管理：树形结构维护、级联关联与删除保护。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tree(self, keywords: str | None = None, status: int | None = None) -> list[DeptVO]:
        """查询部门列表并组装为树形结构，支持关键字与状态筛选。"""
        conditions = [SysDept.is_deleted == 0]
        if keywords:
            conditions.append(SysDept.name.ilike(f"%{keywords}%"))
        if status is not None:
            conditions.append(SysDept.status == status)

        rows = await self.db.execute(
            select(SysDept).where(*conditions).order_by(SysDept.sort.asc())
        )
        depts = rows.scalars().all()
        vo_list = [self._to_vo(d) for d in depts]
        return self._build_tree(vo_list)

    async def get_by_id(self, dept_id: int) -> DeptVO:
        """根据 id 获取部门详情。"""
        result = await self.db.execute(
            select(SysDept).where(SysDept.id == dept_id, SysDept.is_deleted == 0)
        )
        dept = result.scalar_one_or_none()
        if dept is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="部门不存在")
        return self._to_vo(dept)

    async def get_options(self) -> list[dict]:
        """返回部门下拉选项树（递归嵌套 children），仅含启用部门。"""
        rows = await self.db.execute(
            select(SysDept.id, SysDept.parent_id, SysDept.name)
            .where(SysDept.is_deleted == 0, SysDept.status == 1)
            .order_by(SysDept.sort.asc())
        )
        depts = [{"id": r.id, "parentId": r.parent_id, "name": r.name} for r in rows]
        if not depts:
            return []

        dept_ids = {d["id"] for d in depts}
        parent_ids = {d["parentId"] for d in depts}
        root_ids = parent_ids - dept_ids  # parentId 不在当前集合中的为根节点

        def _build(parent_id: int) -> list[dict]:
            tree = []
            for d in depts:
                if d["parentId"] == parent_id:
                    node = {"value": d["id"], "label": d["name"]}
                    children = _build(d["id"])
                    if children:
                        node["children"] = children
                    tree.append(node)
            return tree

        result = []
        for root_id in sorted(root_ids):
            result.extend(_build(root_id))
        return result

    async def get_dept_form(self, dept_id: int) -> DeptUpdate:
        """获取部门编辑表单数据。"""
        result = await self.db.execute(select(SysDept).where(SysDept.id == dept_id, SysDept.is_deleted == 0))
        dept = result.scalar_one_or_none()
        if dept is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="部门不存在")
        return DeptUpdate.model_validate(dept, from_attributes=True)

    async def create(self, form: DeptCreate) -> DeptVO:
        exist = await self.db.execute(
            select(SysDept.id).where(SysDept.code == form.code, SysDept.is_deleted == 0)
        )
        if exist.scalar() is not None:
            raise BusinessException(code=ResultCode.DUPLICATE_KEY, msg="部门编号已存在")

        dept = SysDept(
            name=form.name, code=form.code, parent_id=form.parentId, sort=form.sort, status=form.status,
            tree_path="0", create_time=datetime.now(),
        )
        self.db.add(dept)
        await self.db.flush()

        if dept.parent_id > 0:
            parent = await self.db.get(SysDept, dept.parent_id)
            dept.tree_path = f"{parent.tree_path},{dept.id}" if parent else str(dept.id)
        else:
            dept.tree_path = "0"
        await self.db.flush()

        logger.info(f"Dept created: {form.name}")
        return self._to_vo(dept)

    async def update(self, form: DeptUpdate) -> DeptVO:
        """更新部门（编号重复返回 B0002）；parent_id 变动时重算 tree_path 并级联子节点。"""
        result = await self.db.execute(
            select(SysDept).where(SysDept.id == form.id, SysDept.is_deleted == 0)
        )
        dept = result.scalar_one_or_none()
        if dept is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="部门不存在")

        exist = await self.db.execute(
            select(SysDept.id).where(SysDept.code == form.code, SysDept.is_deleted == 0, SysDept.id != form.id)
        )
        if exist.scalar() is not None:
            raise BusinessException(code=ResultCode.DUPLICATE_KEY, msg="部门编号已存在")

        old_parent_id = dept.parent_id
        dept.name = form.name
        dept.code = form.code
        dept.parent_id = form.parentId
        dept.sort = form.sort
        dept.status = form.status
        dept.update_time = datetime.now()

        if old_parent_id != dept.parent_id:
            if dept.parent_id > 0:
                parent = await self.db.get(SysDept, dept.parent_id)
                dept.tree_path = f"{parent.tree_path},{dept.id}" if parent and parent.tree_path else str(dept.id)
            else:
                dept.tree_path = "0"
            await self.db.flush()
            # 级联更新子部门的 tree_path
            await self._update_child_tree_paths(dept)

        await self.db.flush()
        logger.info(f"Dept updated: {form.name}")
        return self._to_vo(dept)

    async def _update_child_tree_paths(self, parent: SysDept) -> None:
        """递归更新子部门的 tree_path。"""
        children = await self.db.execute(
            select(SysDept).where(SysDept.parent_id == parent.id, SysDept.is_deleted == 0)
        )
        for child in children.scalars().all():
            child.tree_path = f"{parent.tree_path},{child.id}" if parent.tree_path else str(child.id)
            await self.db.flush()
            await self._update_child_tree_paths(child)

    async def delete(self, ids: str) -> int:
        """批量逻辑删除部门；存在子部门的部门拒绝删除（返回 B0004）。"""
        id_list = [int(x) for x in ids.split(",") if x.strip()]
        if not id_list:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="请选择要删除的部门")
        for did in id_list:
            children = await self.db.execute(
                select(SysDept.id).where(SysDept.parent_id == did, SysDept.is_deleted == 0).limit(1)
            )
            if children.scalar() is not None:
                raise BusinessException(code=ResultCode.OPERATE_DENIED, msg=f"部门ID {did} 存在子部门，无法删除")
        for did in id_list:
            dept = await self.db.get(SysDept, did)
            if dept:
                dept.is_deleted = 1
        await self.db.flush()
        return len(id_list)

    @staticmethod
    def _to_vo(d: SysDept) -> DeptVO:
        """ORM 对象转视图对象（DeptVO）。"""
        return DeptVO(
            id=d.id, name=d.name, code=d.code, parentId=d.parent_id,
            treePath=d.tree_path, sort=d.sort, status=d.status,
            createTime=str(d.create_time) if d.create_time else None,
        )

    @staticmethod
    def _build_tree(vo_list: list[DeptVO]) -> list[DeptVO]:
        """将扁平部门列表按 parent_id 组装为树形结构。"""
        node_map = {vo.id: vo for vo in vo_list}
        tree = []
        for vo in vo_list:
            parent = node_map.get(vo.parentId)
            if parent:
                parent.children.append(vo)
            else:
                tree.append(vo)
        return tree
