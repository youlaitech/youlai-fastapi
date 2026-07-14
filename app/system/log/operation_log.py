"""操作日志装饰器。"""

import functools
import time
from typing import Callable

from fastapi import Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.system.log.constants import ActionTypeEnum, LogModuleEnum
from app.system.log.models import SysLog


async def write_operation_log(
    db: AsyncSession,
    *,
    module: int = LogModuleEnum.OTHER,
    action_type: int = ActionTypeEnum.OTHER,
    title: str = "",
    content: str = "",
    request_method: str = "",
    request_uri: str = "",
    status: int = 1,
    execution_time: int = 0,
    error_msg: str = "",
    operator_id: int | None = None,
    operator_name: str = "",
    ip: str = "",
) -> None:
    try:
        log_entry = SysLog(
            module=module,
            action_type=action_type,
            title=title,
            content=content,
            request_method=request_method,
            request_uri=request_uri,
            status=status,
            execution_time=execution_time,
            error_msg=error_msg,
            operator_id=operator_id,
            operator_name=operator_name,
            ip=ip,
        )
        db.add(log_entry)
        await db.flush()
    except Exception:
        logger.exception("write_operation_log failed")


def operation_log(
    module: int = LogModuleEnum.OTHER,
    action_type: int = ActionTypeEnum.OTHER,
    title: str = "",
):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            error_msg = ""
            resp_status = 1

            request: Request | None = kwargs.get("request")
            db: AsyncSession | None = kwargs.get("db")
            user = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as exc:
                resp_status = 0
                error_msg = str(exc)
                raise
            finally:
                exec_time = int((time.time() - start) * 1000)
                if db is not None:
                    await write_operation_log(
                        db,
                        module=module,
                        action_type=action_type,
                        title=title,
                        request_method=getattr(request, "method", ""),
                        request_uri=str(getattr(request, "url", "")) if request else "",
                        status=resp_status,
                        execution_time=exec_time,
                        error_msg=error_msg,
                        operator_id=getattr(user, "userId", None) if user else None,
                        operator_name=getattr(user, "username", "") if user else "",
                        ip=getattr(request, "client", {}).host if request else "",
                    )

        return wrapper

    return decorator
