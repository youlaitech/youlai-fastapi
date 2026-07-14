"""微信小程序认证路由。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.response import Result
from app.tool.wxma.service import WxMaAuthService

router = APIRouter(prefix="/api/v1/wxma/auth", tags=["微信小程序认证"])


class WxMaPhoneLoginForm(BaseModel):
    loginCode: str = Field(..., description="微信登录 code")
    phoneCode: str = Field(..., description="手机号授权 code")


class WxMaBindMobileForm(BaseModel):
    openid: str = Field(...)
    mobile: str = Field(...)
    smsCode: str = Field(...)


class WxMaLoginVO(BaseModel):
    openid: str | None = None
    isBound: bool = False


@router.post("/silent-login", summary="静默登录")
async def silent_login(code: str, db: AsyncSession = Depends(get_db)):
    return Result(data=await WxMaAuthService(db).silent_login(code))


@router.post("/phone-login", summary="手机号快捷登录")
async def phone_login(form: WxMaPhoneLoginForm, db: AsyncSession = Depends(get_db)):
    return Result(data=await WxMaAuthService(db).phone_login(form))


@router.post("/bind-mobile", summary="绑定手机号")
async def bind_mobile(form: WxMaBindMobileForm, db: AsyncSession = Depends(get_db)):
    return Result(data=await WxMaAuthService(db).bind_mobile(form))
