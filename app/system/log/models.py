"""操作日志域 ORM 模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BaseIdMixin


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
