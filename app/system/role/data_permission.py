"""数据权限：根据用户角色 data_scope 拼接 SQL WHERE 条件。

data_scope 取值（sys_role.data_scope）：
    1 ALL           全部数据，不过滤
    2 DEPT_AND_CHILD 本部门及子部门
    3 DEPT           本部门
    4 OWN            本人
    5 CUSTOM_DEPT    自定义部门

多角色取并集（OR），任一 ALL 则全量放行。
无 dataScopes / 无生效条件时不过滤（不拒绝）。

用法:
    from app.system.role.data_permission import apply_data_scope

    stmt = apply_data_scope(
        select(SysUser).where(SysUser.is_deleted == 0),
        user, SysUser.dept_id, SysUser.create_by,
    )
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, false, or_, select, text

from app.constants import ROOT_ROLE_CODE
from app.system.role.constants import DataScopeEnum
from app.auth.schemas import SysUserDetails
from app.system.dept.models import SysDept


# ── 跳过判断 ──

def _should_skip(user: SysUserDetails | None) -> bool:
    """超管 / 未登录 / 角色含 ALL → 不附加过滤。"""
    if user is None or user.userId is None:
        return True
    if user.isRoot or ROOT_ROLE_CODE in (user.roles or set()):
        return True
    if _has_all_data_scope(user):
        return True
    return False


def _has_all_data_scope(user: SysUserDetails) -> bool:
    """任一角色 dataScope == 1。"""
    return any(
        scope.get("dataScope") == DataScopeEnum.ALL
        for scope in (user.dataScopes or [])
    )


# ── 单个角色条件 ──

def _build_role_expression(
    dept_col: ColumnElement | None,
    user_col: ColumnElement | None,
    user: SysUserDetails,
    scope: dict,
) -> ColumnElement | None:
    """按 data_scope 构建该角色的 WHERE 条件，无则返回 None。"""
    ds = scope.get("dataScope")

    if ds == DataScopeEnum.ALL:
        return None

    if ds == DataScopeEnum.DEPT_AND_CHILD:
        if dept_col is None or user.deptId is None:
            return None
        dept_id = user.deptId
        # tree_path 以逗号包裹存储祖先部门 id（如 ",1,3,"），
        # 用 "%,{dept_id},%" 可同时命中本部门及其全部子孙部门
        subquery = select(SysDept.id).where(
            or_(
                SysDept.id == dept_id,
                text(
                    "(',' || COALESCE(tree_path, '') || ',') LIKE :dp_pattern"
                ).bindparams(dp_pattern=f"%,{dept_id},%"),
            )
        )
        return dept_col.in_(subquery)

    if ds == DataScopeEnum.DEPT:
        if dept_col is None or user.deptId is None:
            return None
        return dept_col == user.deptId

    if ds == DataScopeEnum.OWN:
        # 本人：只看自己创建的数据，create_by 在创建时记录操作人
        if user_col is None or user.userId is None:
            return None
        return user_col == user.userId

    if ds == DataScopeEnum.CUSTOM_DEPT:
        if dept_col is None:
            return None
        custom_ids: list[int] = scope.get("customDeptIds") or []
        if not custom_ids:
            return false()
        return dept_col.in_(custom_ids)

    return None


# ── 多角色并集 ──

def _build_union_expression(
    dept_col: ColumnElement | None,
    user_col: ColumnElement | None,
    user: SysUserDetails,
) -> ColumnElement | None:
    """各角色条件 OR 连接；并集为空返回 None（不过滤）。"""
    scopes = user.dataScopes or []
    if not scopes:
        return None

    union: ColumnElement | None = None
    for scope in scopes:
        expr = _build_role_expression(dept_col, user_col, user, scope)
        if expr is not None:
            union = expr if union is None else or_(union, expr)
    return union


# ── 公共 API ──

def build_data_scope_filters(
    user: SysUserDetails | None,
    dept_col: ColumnElement | None = None,
    user_col: ColumnElement | None = None,
) -> list[ColumnElement]:
    """返回数据权限 WHERE 条件列表，可直接 `stmt.where(*filters)`。

    dept_col 为 None 时跳过部门过滤（DEPT / DEPT_AND_CHILD / CUSTOM_DEPT）。
    user_col 为 None 时跳过本人过滤（OWN）。
    """
    if _should_skip(user):
        return []
    expr = _build_union_expression(dept_col, user_col, user)
    if expr is None:
        return []
    return [expr]


def apply_data_scope(
    stmt,
    user: SysUserDetails | None,
    dept_col: ColumnElement | None = None,
    user_col: ColumnElement | None = None,
):
    """给 SELECT 语句附加数据权限 WHERE 条件。超管或 ALL 数据范围时不附加过滤。"""
    filters = build_data_scope_filters(user, dept_col, user_col)
    if filters:
        stmt = stmt.where(*filters)
    return stmt
