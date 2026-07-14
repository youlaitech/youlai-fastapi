"""角色域 ORM 模型。"""

from sqlalchemy import BigInteger, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class SysRole(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sys_role"

    name: Mapped[str] = mapped_column(String(64), unique=True, comment="角色名称")
    code: Mapped[str] = mapped_column(String(32), unique=True, comment="角色编码")
    sort: Mapped[int | None] = mapped_column(Integer, comment="显示顺序")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1", comment="角色状态 1-正常 0-停用")
    data_scope: Mapped[int | None] = mapped_column(SmallInteger, comment="数据权限 1-所有 2-部门及子部门 3-本部门 4-本人 5-自定义部门")
    create_by: Mapped[int | None] = mapped_column(BigInteger, comment="创建人ID")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="更新人ID")

    menus: Mapped[list["SysRoleMenu"]] = relationship(back_populates="role", lazy="selectin")
    depts: Mapped[list["SysRoleDept"]] = relationship(back_populates="role", lazy="selectin")


class SysRoleMenu(Base):
    __tablename__ = "sys_role_menu"
    __table_args__ = (UniqueConstraint("role_id", "menu_id"),)

    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_role.id"), primary_key=True, comment="角色ID")
    menu_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="菜单ID")
    role: Mapped["SysRole"] = relationship(back_populates="menus")


class SysRoleDept(Base):
    __tablename__ = "sys_role_dept"
    __table_args__ = (UniqueConstraint("role_id", "dept_id"),)

    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_role.id"), primary_key=True, comment="角色ID")
    dept_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="部门ID")
    role: Mapped["SysRole"] = relationship(back_populates="depts")
