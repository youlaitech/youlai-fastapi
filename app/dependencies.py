"""安全依赖注入 — get_current_user / require_perm。"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.schemas import SysUserDetails
from app.auth.token import TokenManager, get_token_manager
from app.exceptions import BusinessException
from app.response import ResultCode
from app.constants import ROOT_ROLE_CODE

oauth2_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
    token_manager: TokenManager = Depends(get_token_manager),
) -> SysUserDetails:
    """从请求头 Authorization: Bearer <token> 解析当前用户。"""
    if credentials is None:
        raise BusinessException(code=ResultCode.TOKEN_INVALID, msg="未提供认证令牌")

    user = await token_manager.parse_token(credentials.credentials)
    if user is None:
        raise BusinessException(code=ResultCode.TOKEN_INVALID, msg="访问令牌无效或过期")
    return user


class PermissionChecker:
    """权限校验工厂。"""

    def __init__(self, required_perm: str | None = None):
        self.required_perm = required_perm

    async def __call__(
        self,
        user: SysUserDetails = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> SysUserDetails:
        # 超管放行
        if user.isRoot or ROOT_ROLE_CODE in user.roles:
            return user

        if self.required_perm is None:
            return user

        # 从 sys_role_menu 表查询当前用户是否拥有目标权限
        role_codes = user.roles
        if not role_codes:
            raise BusinessException(code=ResultCode.ACCESS_DENIED, msg="权限不足")

        result = await db.execute(
            text("""
                SELECT 1 FROM sys_role_menu rm
                INNER JOIN sys_menu m ON rm.menu_id = m.id
                INNER JOIN sys_role r ON rm.role_id = r.id
                WHERE r.code = ANY(:role_codes) AND m.perm = :perm
                  AND r.is_deleted = 0 AND r.status = 1
                LIMIT 1
            """),
            {"role_codes": list(role_codes), "perm": self.required_perm},
        )
        if result.scalar() is None:
            raise BusinessException(code=ResultCode.ACCESS_DENIED, msg="权限不足")
        return user


def require_perm(perm: str | None = None) -> PermissionChecker:
    """路由权限依赖注入 — 用法: Depends(require_perm('sys:user:create'))。"""
    return PermissionChecker(perm)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
    token_manager: TokenManager = Depends(get_token_manager),
) -> SysUserDetails | None:
    """可选用户 — 有 token 解析用户，无 token 返回 None。"""
    if credentials is None:
        return None
    return await token_manager.parse_token(credentials.credentials)
