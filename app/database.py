"""异步数据库引擎、Session 工厂与 ORM 声明基类。"""

from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


# ── ORM 声明基类 ──

class Base(DeclarativeBase):
    """ORM 声明式基类。"""
    pass


class TimestampMixin:
    """维护 create_time / update_time。

    用 Python 层 default=func.now() 在插入时由应用显式写入时间戳，
    不依赖库表列的默认值（共享库部分表 create_time 为 NOT NULL 且无默认）。
    """
    create_time: Mapped[datetime | None] = mapped_column(
        DateTime, default=func.now(), server_default=func.now(), comment="创建时间"
    )
    update_time: Mapped[datetime | None] = mapped_column(
        DateTime, default=func.now(), server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class SoftDeleteMixin:
    is_deleted: Mapped[int] = mapped_column(
        SmallInteger, default=0, server_default="0", comment="逻辑删除 0-未删除 1-已删除"
    )


class BaseIdMixin:
    """自增主键 ID。"""
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )


engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：每次请求创建独立的数据库会话。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
