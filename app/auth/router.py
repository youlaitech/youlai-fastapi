"""认证路由。"""

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.captcha.service import CaptchaService
from app.dependencies import get_current_user, oauth2_scheme
from app.auth.schemas import CaptchaResult, SysUserDetails
from app.response import Result, ResultCode
from app.auth.schemas import LoginForm, LoginResult, RefreshTokenForm
from app.auth.service import AuthService
from app.rate_limit import check_rate_limit

router = APIRouter(prefix="/api/v1/auth", tags=["认证管理"])


@router.post("/login", summary="账号密码登录")
async def login(form: LoginForm, db: AsyncSession = Depends(get_db)):
    """用户名 + 密码 + 验证码登录。"""
    if form.captchaId and form.captchaCode:
        if not await CaptchaService().verify(form.captchaId, form.captchaCode):
            return Result(code=ResultCode.CAPTCHA_ERROR, msg="验证码错误", data=None)

    result = await AuthService(db).login(form.username, form.password)
    return Result(data=LoginResult(**result))


@router.post("/login/sms", summary="短信验证码登录")
async def login_by_sms(
    mobile: str = Query(...),
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await AuthService(db).login_by_sms(mobile, code)
    return Result(data=LoginResult(**result))


@router.post("/sms/code", summary="发送登录短信验证码")
async def send_sms_code(mobile: str, db: AsyncSession = Depends(get_db)):
    # 同一手机号 60 秒内仅允许发送一次验证码
    await check_rate_limit(f"rate_limit:api:sms:{mobile}", 1, 60)
    await AuthService(db).send_sms_code(mobile)
    return Result(data=None)


@router.delete("/logout", summary="登出")
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if credentials is None:
        return Result(code=ResultCode.TOKEN_INVALID, msg="未提供认证令牌", data=None)
    await AuthService(db).logout(credentials.credentials)
    return Result(data=None)


@router.post("/refresh-token", summary="刷新令牌")
async def refresh_token(form: RefreshTokenForm, db: AsyncSession = Depends(get_db)):
    result = await AuthService(db).refresh_token(form.refreshToken)
    return Result(data=LoginResult(**result))


@router.get("/captcha", summary="获取验证码")
async def get_captcha():
    result = await CaptchaService().generate()
    return Result(data=CaptchaResult(captchaId=result.captchaId, captchaBase64=result.captchaBase64))
