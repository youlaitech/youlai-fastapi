"""日志域常量。"""

from enum import IntEnum


class ActionTypeEnum(IntEnum):
    LOGIN = 1
    LOGOUT = 2
    INSERT = 3
    UPDATE = 4
    DELETE = 5
    GRANT = 6
    EXPORT = 7
    IMPORT = 8
    UPLOAD = 9
    DOWNLOAD = 10
    CHANGE_PASSWORD = 11
    RESET_PASSWORD = 12
    ENABLE = 13
    DISABLE = 14
    LIST = 15
    OTHER = 99


class LogModuleEnum(IntEnum):
    LOGIN = 1
    USER = 2
    ROLE = 3
    DEPT = 4
    MENU = 5
    DICT = 6
    CONFIG = 7
    FILE = 8
    NOTICE = 9
    LOG = 10
    CODEGEN = 11
    OTHER = 99
