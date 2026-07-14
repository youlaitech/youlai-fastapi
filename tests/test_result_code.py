"""ResultCode 业务错误码 + HTTP 状态码映射测试。"""

import pytest

from app.response import ResultCode
from app.exceptions import BusinessException


@pytest.mark.parametrize(
    "code, expected_http",
    [
        (ResultCode.SUCCESS, 200),
        (ResultCode.TOKEN_INVALID, 401),
        (ResultCode.TOKEN_REFRESH_FAIL, 401),
        (ResultCode.ACCESS_DENIED, 403),
        (ResultCode.USER_DISABLED, 403),
        (ResultCode.PARAM_VALID_FAIL, 422),
        (ResultCode.USERNAME_NOT_FOUND, 404),
        (ResultCode.BAD_CREDENTIALS, 401),
        (ResultCode.CAPTCHA_ERROR, 400),
        (ResultCode.SYSTEM_ERROR, 500),
        (ResultCode.DUPLICATE_KEY, 409),
        (ResultCode.DATA_NOT_FOUND, 404),
        (ResultCode.OPERATE_DENIED, 403),
    ],
)
def test_result_code_http_status(code, expected_http):
    """每个错误码应映射到正确的 HTTP 状态码。"""
    assert code.http_status == expected_http
    assert isinstance(code.value, str)
    # str Enum 可直接当字符串使用
    assert str(code) == code.value


@pytest.mark.parametrize(
    "code, msg",
    [
        (ResultCode.TOKEN_INVALID, "令牌失效"),
        (ResultCode.DATA_NOT_FOUND, "用户不存在"),
        (ResultCode.DUPLICATE_KEY, "用户名已存在"),
    ],
)
def test_business_exception_http_status(code, msg):
    """BusinessException 应携带正确的 HTTP 状态码。"""
    exc = BusinessException(code=code, msg=msg)
    assert exc.code == code.value
    assert exc.http_status == code.http_status
    assert exc.msg == msg


def test_business_exception_string_code():
    """也支持直接传入字符串错误码（兼容旧代码）。"""
    exc = BusinessException(code="A0230", msg="test")
    assert exc.code == "A0230"
    assert exc.http_status == 401


def test_result_code_is_enum():
    """ResultCode 应为 Enum 类型。"""
    assert isinstance(ResultCode.SUCCESS, ResultCode)
    # str Enum 特性
    assert ResultCode.SUCCESS == "00000"
    assert "00000" == ResultCode.SUCCESS
