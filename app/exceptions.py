"""异常处理 — HTTP 状态码与 body 业务码双轨。"""

import traceback

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from app.response import ResultCode


class BusinessException(Exception):
    """业务异常 — 携带业务错误码、HTTP 状态码和提示信息。"""

    def __init__(
        self,
        code: ResultCode | str = ResultCode.SYSTEM_ERROR,
        msg: str = "系统异常",
    ):
        rc = ResultCode(code) if isinstance(code, str) else code
        self.code = rc.value
        self.http_status = rc.http_status
        self.result_code = rc
        self.msg = msg
        super().__init__(msg)


async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    """业务异常 — 返回对应 HTTP 状态码与 body code。"""
    logger.warning(f"BusinessException | code={exc.code} http={exc.http_status} msg={exc.msg} path={request.url.path}")
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "msg": exc.msg, "data": None},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """请求参数校验异常 — HTTP 422 + body code A0400。"""
    errors = exc.errors()
    msg = "; ".join(f"{e['loc'][-1] if e['loc'] else '?'}: {e['msg']}" for e in errors)
    logger.warning(f"ValidationError | path={request.url.path} errors={msg}")
    return JSONResponse(
        status_code=422,
        content={"code": ResultCode.PARAM_VALID_FAIL.value, "msg": msg, "data": None},
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底异常 — HTTP 500，body code B0001。"""
    logger.error(f"UnhandledException | path={request.url.path}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"code": ResultCode.SYSTEM_ERROR.value, "msg": "系统执行异常", "data": None},
    )
