"""角色域常量。"""

from enum import IntEnum


class DataScopeEnum(IntEnum):
    """数据权限范围枚举。"""
    ALL = 1
    DEPT_AND_CHILD = 2
    DEPT = 3
    OWN = 4
    CUSTOM_DEPT = 5

    @property
    def label(self) -> str:
        return _DATA_SCOPE_LABELS.get(self.value, "")

    @classmethod
    def get_label(cls, value: int | None) -> str:
        if value is None:
            return ""
        return _DATA_SCOPE_LABELS.get(value, "")


_DATA_SCOPE_LABELS: dict[int, str] = {
    1: "所有数据",
    2: "部门及子部门数据",
    3: "本部门数据",
    4: "本人数据",
    5: "自定义部门数据",
}
