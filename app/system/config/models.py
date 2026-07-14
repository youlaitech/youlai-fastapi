"""系统配置域 ORM 模型。"""

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class SysConfig(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sys_config"

    config_name: Mapped[str] = mapped_column(String(50), comment="配置名称")
    config_key: Mapped[str] = mapped_column(String(50), unique=True, comment="配置键")
    config_value: Mapped[str] = mapped_column(String(100), comment="配置值")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
    create_by: Mapped[int | None] = mapped_column(BigInteger, comment="创建人ID")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="修改人ID")
