"""菜单域 ORM 模型。"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BaseIdMixin


class SysMenu(Base, BaseIdMixin):
    __tablename__ = "sys_menu"

    parent_id: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0", comment="父菜单ID")
    tree_path: Mapped[str | None] = mapped_column(String(255), comment="父节点ID路径")
    name: Mapped[str] = mapped_column(String(64), comment="菜单名称")
    type: Mapped[str] = mapped_column(String(1), comment="菜单类型 C-目录 M-菜单 E-外链 B-按钮")
    route_name: Mapped[str | None] = mapped_column(String(255), comment="路由名称")
    route_path: Mapped[str | None] = mapped_column(String(128), comment="路由路径")
    component: Mapped[str | None] = mapped_column(String(128), comment="组件路径")
    external_url: Mapped[str | None] = mapped_column(String(512), comment="外链地址")
    perm: Mapped[str | None] = mapped_column(String(128), comment="权限标识")
    always_show: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", comment="目录-只有一个子路由是否始终显示")
    keep_alive: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", comment="菜单-是否开启页面缓存")
    visible: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1", comment="显示状态 1-显示 0-隐藏")
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0", comment="排序")
    icon: Mapped[str | None] = mapped_column(String(64), comment="菜单图标")
    redirect: Mapped[str | None] = mapped_column(String(128), comment="跳转路径")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    update_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    params: Mapped[dict | None] = mapped_column(JSON, comment="路由参数")
