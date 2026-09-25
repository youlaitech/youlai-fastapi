"""动态表单域 ORM 模型：表单定义、表单数据、版本快照。"""
from sqlalchemy import BigInteger, Integer, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


class FormDefinition(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """表单定义表 form_definition。"""
    __tablename__ = "form_definition"

    form_key: Mapped[str] = mapped_column(String(64), comment="表单唯一标识")
    form_name: Mapped[str] = mapped_column(String(100), comment="表单名称")
    description: Mapped[str | None] = mapped_column(String(255), comment="表单描述")
    form_json: Mapped[list | None] = mapped_column(JSONB, comment="表单规则（form-create rule 数组）")
    options_json: Mapped[dict | None] = mapped_column(JSONB, comment="表单全局配置")
    status: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", comment="0草稿 1已发布 -1已停用")
    is_public: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", comment="是否允许匿名公开访问")
    category: Mapped[str | None] = mapped_column(String(16), default="normal", server_default="normal", comment="normal通用 workflow审批表单")
    menu_id: Mapped[int | None] = mapped_column(BigInteger, comment="生成的访问菜单ID，NULL未生成")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", comment="版本号")
    create_by: Mapped[int | None] = mapped_column(BigInteger, comment="创建人ID")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="修改人ID")


class FormData(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """表单数据表 form_data。"""
    __tablename__ = "form_data"

    form_id: Mapped[int] = mapped_column(BigInteger, comment="表单定义ID")
    form_version: Mapped[int] = mapped_column(Integer, comment="表单版本（提交时快照）")
    data_json: Mapped[dict | None] = mapped_column(JSONB, comment="表单数据 field -> value")
    create_by: Mapped[int | None] = mapped_column(BigInteger, comment="提交人ID，匿名为空")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="修改人ID")


class FormSnapshot(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    """表单版本快照表 form_snapshot，发布时固化规则，只增不改。"""
    __tablename__ = "form_snapshot"

    form_id: Mapped[int] = mapped_column(BigInteger, comment="表单定义ID")
    version: Mapped[int] = mapped_column(Integer, comment="版本号")
    form_json: Mapped[list | None] = mapped_column(JSONB, comment="表单规则快照")
    options_json: Mapped[dict | None] = mapped_column(JSONB, comment="表单全局配置快照")
