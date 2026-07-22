"""管理后台操作日志装饰器。

贴在路由函数上，自动把本次请求的模块、操作类型、操作人、请求方式、耗时等
写入 sys_log 表，用于审计谁在何时对哪类资源做了什么操作。
"""

import functools
import time
from typing import Callable

from fastapi import Request
from loguru import logger

from app.database import AsyncSessionLocal
from app.system.log.constants import ActionTypeEnum, LogModuleEnum
from app.system.log.models import SysLog


async def write_operation_log(
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
    """写入一条操作日志到 sys_log 表。

    使用新建的独立数据库会话，不继承调用方的事务，因此即便业务操作回滚，
    本次审计记录依然保留。
    """
    async with AsyncSessionLocal() as session:
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
                error_msg=error_msg[:255] if error_msg else error_msg,
                operator_id=operator_id,
                operator_name=operator_name,
                ip=ip,
            )
            session.add(log_entry)
            await session.commit()
        except Exception:
            logger.exception("write_operation_log failed")


def operation_log(
    module: int = LogModuleEnum.OTHER,
    action_type: int = ActionTypeEnum.OTHER,
    title: str = "",
):
    """标记一个路由需要记录操作日志。

    被装饰的路由函数签名里要带上 request: Request 和经依赖注入的当前用户 user，
    装饰器从这两个参数里取 IP 来源与操作人信息；其余字段由调用处传入的
    module / action_type / title 决定。
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            error_msg = ""
            resp_status = 1

            request: Request | None = kwargs.get("request")
            user = kwargs.get("user")

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as exc:
                resp_status = 0
                error_msg = str(exc)
                raise
            finally:
                exec_time = int((time.time() - start) * 1000)
                operator_id = getattr(user, "userId", None) if user else None
                operator_name = getattr(user, "username", "") if user else ""
                ip = getattr(request, "client", {}).host if request else ""
                await write_operation_log(
                    module=module,
                    action_type=action_type,
                    title=title,
                    request_method=getattr(request, "method", ""),
                    request_uri=str(getattr(request, "url", ""))[:255] if request else "",
                    status=resp_status,
                    execution_time=exec_time,
                    error_msg=error_msg,
                    operator_id=operator_id,
                    operator_name=operator_name,
                    ip=ip,
                )

        return wrapper

    return decorator
