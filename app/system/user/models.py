"""用户域 ORM 模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String, UniqueConstraint, func
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


class SysUserSocial(Base):
    __tablename__ = "sys_user_social"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, comment="用户ID")
    platform: Mapped[str] = mapped_column(String(20), comment="平台类型 WECHAT_MINI/WECHAT_MP/ALIPAY/QQ/APPLE")
    openid: Mapped[str] = mapped_column(String(64), comment="平台openid")
    unionid: Mapped[str | None] = mapped_column(String(64), comment="微信unionid")
    nickname: Mapped[str | None] = mapped_column(String(64), comment="第三方昵称")
    avatar: Mapped[str | None] = mapped_column(String(255), comment="第三方头像URL")
    session_key: Mapped[str | None] = mapped_column(String(128), comment="微信session_key")
    verified: Mapped[int] = mapped_column(SmallInteger, default=1, comment="是否已验证 1-已验证 0-未验证")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), comment="绑定时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("platform", "openid", name="uk_platform_openid"),
        Index("idx_user_id", "user_id"),
        Index("idx_unionid", "unionid"),
    )
