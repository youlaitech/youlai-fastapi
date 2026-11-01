"""微信小程序认证服务 — 占位实现。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.token import get_token_manager
from app.exceptions import BusinessException
from app.response import ResultCode
from app.system.user.models import SysUser, SysUserIdentity


class WxMaAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def silent_login(self, code: str) -> dict:
        """静默登录：根据 code 换取 openid，已绑定则返回 token。"""
        # TODO: 接入微信服务端 API 换取 openid
        openid = f"openid_{code}"
        result = await self.db.execute(
            select(SysUser).join(SysUserIdentity, SysUserIdentity.user_id == SysUser.id)
            .where(SysUserIdentity.provider_account_id == openid, SysUserIdentity.provider == "wechat-mini-main")
        )
        user = result.scalar_one_or_none()
        if user is None:
            return {"openid": openid, "isBound": False}
        token_manager = await get_token_manager()
        from app.auth.service import AuthService
        token = await AuthService(self.db)._build_token(user)
        return {"isBound": True, **token}

    async def phone_login(self, form) -> dict:
        """手机号快捷登录。"""
        # TODO: 接入微信手机号授权
        result = await self.db.execute(
            select(SysUser).where(SysUser.mobile == "13800138000", SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.USERNAME_NOT_FOUND, msg="用户不存在")
        from app.auth.service import AuthService
        return await AuthService(self.db)._build_token(user)

    async def bind_mobile(self, form) -> dict:
        """绑定手机号后完成登录。"""
        # TODO: 接入真实短信验证码校验
        user = SysUser(username=form.mobile, nickname=form.mobile, mobile=form.mobile, status=1)
        self.db.add(user)
        await self.db.flush()
        identity = SysUserIdentity(
            user_id=user.id,
            provider="wechat-mini-main",
            provider_account_id=form.openid,
            last_login_time=func.now(),
        )
        self.db.add(identity)
        await self.db.flush()
        from app.auth.service import AuthService
        return await AuthService(self.db)._build_token(user)
