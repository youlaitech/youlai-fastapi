"""微信小程序认证服务 — 通道未接入，接口暂不开放。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessException
from app.response import ResultCode

_NOT_OPEN = "微信小程序登录暂未开放"


class WxMaAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def silent_login(self, code: str) -> dict:
        """静默登录。"""
        raise BusinessException(code=ResultCode.OPERATE_DENIED, msg=_NOT_OPEN)

    async def phone_login(self, form) -> dict:
        """手机号快捷登录。"""
        raise BusinessException(code=ResultCode.OPERATE_DENIED, msg=_NOT_OPEN)

    async def bind_mobile(self, form) -> dict:
        """绑定手机号。"""
        raise BusinessException(code=ResultCode.OPERATE_DENIED, msg=_NOT_OPEN)
