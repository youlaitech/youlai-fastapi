"""部门域 ORM 模型。"""

from sqlalchemy import BigInteger, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class SysDept(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sys_dept"

    name: Mapped[str] = mapped_column(String(100), comment="部门名称")
    code: Mapped[str] = mapped_column(String(100), unique=True, comment="部门编号")
    parent_id: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0", comment="父节点id")
    tree_path: Mapped[str] = mapped_column(String(255), comment="父节点id路径")
    sort: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", comment="显示顺序")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1", comment="状态 1-正常 0-禁用")
    create_by: Mapped[int | None] = mapped_column(BigInteger, comment="创建人ID")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="修改人ID")
