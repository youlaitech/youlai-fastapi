"""通知公告域 ORM 模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class SysNotice(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sys_notice"

    title: Mapped[str] = mapped_column(String(50), comment="通知标题")
    content: Mapped[str] = mapped_column(Text, comment="通知内容")
    type: Mapped[int] = mapped_column(SmallInteger, comment="通知类型 关联字典编码notice_type")
    level: Mapped[str] = mapped_column(String(5), comment="通知等级 L-低 M-中 H-高")
    target_type: Mapped[int] = mapped_column(SmallInteger, comment="目标类型 1-全体 2-指定")
    target_user_ids: Mapped[str | None] = mapped_column(String(255), comment="目标用户ID 逗号分隔")
    publisher_id: Mapped[int | None] = mapped_column(BigInteger, comment="发布人ID")
    publish_status: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", comment="发布状态 0-未发布 1-已发布 -1-已撤回")
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, comment="发布时间")
    revoke_time: Mapped[datetime | None] = mapped_column(DateTime, comment="撤回时间")
    create_by: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="创建人ID")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="修改人ID")


class SysUserNotice(Base):
    __tablename__ = "sys_user_notice"
    __table_args__ = (UniqueConstraint("notice_id", "user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    notice_id: Mapped[int] = mapped_column(BigInteger, comment="通知ID")
    user_id: Mapped[int] = mapped_column(BigInteger, comment="用户ID")
    is_read: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", comment="读取状态 0-未读 1-已读")
    read_time: Mapped[datetime | None] = mapped_column(DateTime, comment="阅读时间")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime | None] = mapped_column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())
    is_deleted: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", comment="逻辑删除 0-未删除 1-已删除")
