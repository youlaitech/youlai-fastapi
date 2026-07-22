"""认证服务。"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.constants import ROOT_ROLE_CODE
from app.auth.utils import verify_password
from app.auth.schemas import SecurityUser, SysUserDetails
from app.auth.token import get_token_manager
from app.exceptions import BusinessException
from app.response import ResultCode
from app.system.user.models import SysUser


class AuthService:
    """认证业务服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, username: str, password: str) -> dict:
        """账号密码登录。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.username == username, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.USERNAME_NOT_FOUND, msg="用户名不存在")
        if user.status != 1:
            raise BusinessException(code=ResultCode.USER_DISABLED, msg="用户已被禁用")
        if not verify_password(password, user.password):
            raise BusinessException(code=ResultCode.BAD_CREDENTIALS, msg="密码错误")
        return await self._build_token(user)

    async def login_by_sms(self, mobile: str, code: str) -> dict:
        """短信验证码登录。"""
        # TODO: 接入真实短信验证码校验
        result = await self.db.execute(
            select(SysUser).where(SysUser.mobile == mobile, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.USERNAME_NOT_FOUND, msg="手机号未注册")
        if user.status != 1:
            raise BusinessException(code=ResultCode.USER_DISABLED, msg="用户已被禁用")
        return await self._build_token(user)

    async def send_sms_code(self, mobile: str) -> None:
        """发送短信验证码（占位）。"""
        # TODO: 接入真实短信服务
        logger.info(f"Send SMS code to {mobile}")

    async def logout(self, token: str) -> None:
        """用户登出。"""
        token_manager = await get_token_manager()
        await token_manager.invalidate_token(token)
        logger.info("User logged out")

    async def refresh_token(self, refresh_token: str) -> dict:
        """刷新访问令牌。"""
        token_manager = await get_token_manager()
        new_token = await token_manager.refresh_token(refresh_token)
        if new_token is None:
            raise BusinessException(code=ResultCode.TOKEN_REFRESH_FAIL, msg="刷新令牌无效或过期")
        return {
            "accessToken": new_token.accessToken,
            "refreshToken": new_token.refreshToken,
            "tokenType": new_token.tokenType,
            "expiresIn": new_token.expiresIn,
        }

    async def get_user_info(self, user_id: int) -> dict:
        """获取当前登录用户信息（角色+权限）。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        role_result = await self.db.execute(
            text("""
                SELECT r.code FROM sys_role r
                INNER JOIN sys_user_role ur ON r.id = ur.role_id
                WHERE ur.user_id = :user_id AND r.is_deleted = 0 AND r.status = 1
            """),
            {"user_id": user_id},
        )
        roles = [row.code for row in role_result]
        perms: list[str] = []
        if roles:
            perm_result = await self.db.execute(
                text("""
                    SELECT DISTINCT m.perm FROM sys_menu m
                    INNER JOIN sys_role_menu rm ON m.id = rm.menu_id
                    INNER JOIN sys_role r ON rm.role_id = r.id
                    WHERE r.code = ANY(:roles) AND m.perm IS NOT NULL
                    AND m.perm != ''
                """),
                {"roles": roles},
            )
            perms = [row.perm for row in perm_result if row.perm]
        return {
            "userId": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "roles": roles,
            "perms": perms,
            "deptId": user.dept_id,
        }

    async def get_auth_info_by_user_id(self, user_id: int) -> dict:
        """获取用户认证信息：username/nickname/avatar/roles/perms。"""
        return await self.get_user_info(user_id)

    async def login_by_qr(self, user_id: int) -> dict:
        """扫码登录后签发令牌。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.USERNAME_NOT_FOUND, msg="用户不存在")
        if user.status != 1:
            raise BusinessException(code=ResultCode.USER_DISABLED, msg="用户已被禁用")
        return await self._build_token(user)

    async def _build_token(self, user: SysUser) -> dict:
        """查用户角色及 data_scope，构造 token 并签发。"""
        role_result = await self.db.execute(
            text("""
                SELECT r.code, r.data_scope
                FROM sys_role r
                INNER JOIN sys_user_role ur ON r.id = ur.role_id
                WHERE ur.user_id = :user_id AND r.is_deleted = 0 AND r.status = 1
            """),
            {"user_id": user.id},
        )
        role_rows = role_result.fetchall()
        roles = set()
        is_root = False
        for row in role_rows:
            roles.add(row.code)
            if row.code == ROOT_ROLE_CODE:
                is_root = True
        data_scopes = await self._get_data_scopes(role_rows)
        security_user = SecurityUser(
            userId=user.id,
            username=user.username,
            nickname=user.nickname,
            password=user.password,
            deptId=user.dept_id,
            status=user.status,
            roles=roles,
            dataScopes=data_scopes,
            mobile=user.mobile,
            email=user.email,
            avatar=user.avatar,
        )
        user_details = SysUserDetails.from_security_user(security_user, is_root=is_root)
        token_manager = await get_token_manager()
        token = await token_manager.generate_token(user_details)
        logger.info(f"User login: {user.username} | roles={roles}")
        return {
            "accessToken": token.accessToken,
            "refreshToken": token.refreshToken,
            "tokenType": token.tokenType,
            "expiresIn": token.expiresIn,
        }

    async def _get_data_scopes(self, role_rows: list) -> list[dict]:
        """构建用户 dataScopes 列表。

        data_scope=5（自定义部门）时查 sys_role_dept 取部门 ID。
        返回 [{"roleCode": str, "dataScope": int, "customDeptIds": List[int]}]
        """
        scopes = []
        for row in role_rows:
            if row.data_scope == 5:
                dept_result = await self.db.execute(
                    text("""
                        SELECT d.id FROM sys_dept d
                        INNER JOIN sys_role_dept rd ON d.id = rd.dept_id
                        INNER JOIN sys_role r ON rd.role_id = r.id
                        WHERE r.code = :code AND d.is_deleted = 0
                    """),
                    {"code": row.code},
                )
                custom_dept_ids = [d.id for d in dept_result]
                scopes.append({
                    "roleCode": row.code,
                    "dataScope": row.data_scope,
                    "customDeptIds": custom_dept_ids,
                })
            else:
                scopes.append({
                    "roleCode": row.code,
                    "dataScope": row.data_scope,
                    "customDeptIds": [],
                })
        return scopes
