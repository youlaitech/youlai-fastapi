"""角色域常量。"""

from enum import IntEnum


class DataScopeEnum(IntEnum):
    """数据权限范围。值即为 sys_role.data_scope。"""
    ALL = 1
    DEPT_AND_CHILD = 2
    DEPT = 3
    OWN = 4
    CUSTOM_DEPT = 5
