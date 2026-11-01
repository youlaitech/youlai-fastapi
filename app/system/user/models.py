"""用户域 ORM 模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class SysUser(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sys_user"

    username: Mapped[str] = mapped_column(String(64), unique=True, comment="用户名")
    nickname: Mapped[str] = mapped_column(String(64), comment="昵称")
    gender: Mapped[int | None] = mapped_column(SmallInteger, default=1, comment="性别 1-男 2-女 0-保密")
    password: Mapped[str] = mapped_column(String(100), comment="密码")
    dept_id: Mapped[int | None] = mapped_column(BigInteger, comment="部门ID")
    mobile: Mapped[str | None] = mapped_column(String(20), comment="手机号")
    email: Mapped[str | None] = mapped_column(String(128), comment="邮箱")
    avatar: Mapped[str | None] = mapped_column(String(255), comment="头像URL")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1", comment="状态 1-启用 0-禁用")
    create_by: Mapped[int | None] = mapped_column(BigInteger, comment="创建人ID")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="修改人ID")

    roles: Mapped[list["SysRole"]] = relationship(
        secondary="sys_user_role",
        primaryjoin="SysUser.id == SysUserRole.user_id",
        secondaryjoin="SysRole.id == SysUserRole.role_id",
        lazy="selectin",
        viewonly=True,
    )


class SysUserRole(Base):
    __tablename__ = "sys_user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), primary_key=True, comment="用户ID")
    role_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="角色ID")


class SysUserIdentity(Base):
    """本地用户与外部账号的关联"""

    __tablename__ = "sys_user_identity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, comment="本地用户ID")
    provider: Mapped[str] = mapped_column(String(64), comment="具体认证源标识，如 wechat-mini-main")
    provider_account_id: Mapped[str] = mapped_column(String(255), comment="来源方账号ID")
    display_name: Mapped[str | None] = mapped_column(String(128), comment="外部账号展示名")
    avatar_url: Mapped[str | None] = mapped_column(String(512), comment="外部账号头像")
    last_login_time: Mapped[datetime | None] = mapped_column(DateTime, comment="最近一次登录时间")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), comment="关联创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "provider_account_id", name="uk_provider_account"),
        UniqueConstraint("user_id", "provider", name="uk_user_provider"),
    )
