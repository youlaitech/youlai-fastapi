"""系统管理 ORM 模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, JSON, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseIdMixin, SoftDeleteMixin, TimestampMixin


# =====================================================================
# 字典
# =====================================================================

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


# =====================================================================
# 部门
# =====================================================================

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


# =====================================================================
# 菜单
# =====================================================================

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


# =====================================================================
# 角色
# =====================================================================

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


# =====================================================================
# 用户
# =====================================================================

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


# =====================================================================
# 系统配置
# =====================================================================

class SysConfig(Base, BaseIdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sys_config"

    config_name: Mapped[str] = mapped_column(String(50), comment="配置名称")
    config_key: Mapped[str] = mapped_column(String(50), unique=True, comment="配置键")
    config_value: Mapped[str] = mapped_column(String(100), comment="配置值")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
    create_by: Mapped[int | None] = mapped_column(BigInteger, comment="创建人ID")
    update_by: Mapped[int | None] = mapped_column(BigInteger, comment="修改人ID")


# =====================================================================
# 通知公告
# =====================================================================

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


# =====================================================================
# 操作日志
# =====================================================================

class SysLog(Base, BaseIdMixin):
    __tablename__ = "sys_log"

    module: Mapped[int] = mapped_column(SmallInteger, comment="模块 数字枚举")
    action_type: Mapped[int] = mapped_column(SmallInteger, comment="操作类型 数字枚举")
    title: Mapped[str] = mapped_column(String(100), comment="显示标题")
    content: Mapped[str | None] = mapped_column(Text, comment="日志内容")
    operator_id: Mapped[int | None] = mapped_column(BigInteger, comment="操作人ID")
    operator_name: Mapped[str | None] = mapped_column(String(50), comment="操作人名称")
    request_uri: Mapped[str | None] = mapped_column(String(255), comment="请求路径")
    request_method: Mapped[str | None] = mapped_column(String(10), comment="请求方法")
    ip: Mapped[str | None] = mapped_column(String(45), comment="IP地址")
    province: Mapped[str | None] = mapped_column(String(100), comment="省份")
    city: Mapped[str | None] = mapped_column(String(100), comment="城市")
    device: Mapped[str | None] = mapped_column(String(100), comment="设备")
    os: Mapped[str | None] = mapped_column(String(100), comment="操作系统")
    browser: Mapped[str | None] = mapped_column(String(100), comment="浏览器")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1", comment="0-失败 1-成功")
    error_msg: Mapped[str | None] = mapped_column(String(255), comment="错误信息")
    execution_time: Mapped[int | None] = mapped_column(Integer, comment="执行时间 ms")
    create_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), comment="操作时间")
