"""字典域 ORM 模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class SysDict(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sys_dict"

    dict_code: Mapped[str | None] = mapped_column(String(50), comment="类型编码")
    name: Mapped[str | None] = mapped_column(String(50), comment="类型名称")
    status: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", comment="状态 0:正常 1:禁用")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
    create_by: Mapped[int | None] = mapped_column(BigInteger, comment="创建人ID")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="修改人ID")

    items: Mapped[list["SysDictItem"]] = relationship(
        back_populates="dict", lazy="selectin",
        primaryjoin="foreign(SysDictItem.dict_code) == SysDict.dict_code",
    )


class SysDictItem(Base, BaseIdMixin):
    __tablename__ = "sys_dict_item"

    dict_code: Mapped[str | None] = mapped_column(String(50), comment="关联字典编码")
    value: Mapped[str | None] = mapped_column(String(50), comment="字典项值")
    label: Mapped[str | None] = mapped_column(String(100), comment="字典项标签")
    tag_type: Mapped[str | None] = mapped_column(String(50), comment="标签类型")
    status: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", comment="状态 1-正常 0-禁用")
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0", comment="排序")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    create_by: Mapped[int | None] = mapped_column(BigInteger, comment="创建人ID")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="修改人ID")

    dict: Mapped["SysDict"] = relationship(
        back_populates="items", lazy="selectin",
        primaryjoin="foreign(SysDictItem.dict_code) == SysDict.dict_code",
    )
