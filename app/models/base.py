"""SQLAlchemy ORM 基类和 Mixin — 2.0 风格声明式映射。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """ORM 声明式基类。"""
    pass


class TimestampMixin:
    """维护 create_time / update_time。

    用 Python 层 default=func.now() 在插入时由应用显式写入时间戳，
    不依赖库表列的默认值（共享库部分表 create_time 为 NOT NULL 且无默认）。
    """
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime, default=func.now(), server_default=func.now(), comment="创建时间"
    )
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime, default=func.now(), server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class SoftDeleteMixin:
    is_deleted: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0", comment="逻辑删除 0-未删除 1-已删除"
    )


class BaseIdMixin:
    """自增主键 ID。"""
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )
