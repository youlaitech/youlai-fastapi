"""用户管理模块：增删改查、导入导出、数据权限过滤。"""

from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.pagination import PageResult
from app.system.user.constants import DEFAULT_PASSWORD
from app.auth.utils import hash_password, verify_password
from app.system.role.data_permission import apply_data_scope
from app.auth.schemas import SysUserDetails
from app.exceptions import BusinessException
from app.response import ResultCode
from app.system.dept.models import SysDept
from app.system.role.models import SysRole
from app.system.user.models import SysUser, SysUserRole
from app.system.user.schemas import UserCreate, UserQuery, UserUpdate, UserVO


class UserService:
    """用户增删改查、导入导出与数据权限过滤。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_page(self, query: UserQuery, user: SysUserDetails | None = None) -> PageResult:
        """分页查询用户列表。传入 user 则按角色 data_scope 过滤。"""
        conditions = [SysUser.is_deleted == 0]
        if query.keywords:
            keyword = f"%{query.keywords}%"
            conditions.append(
                (SysUser.username.ilike(keyword))
                | (SysUser.nickname.ilike(keyword))
                | (SysUser.mobile.ilike(keyword))
            )
        if query.deptId is not None:
            conditions.append(SysUser.dept_id == query.deptId)
        if query.status is not None:
            conditions.append(SysUser.status == query.status)

        # 数据权限：按 dept_id 与 create_by 过滤
        stmt = apply_data_scope(
            select(SysUser).where(*conditions),
            user, SysUser.dept_id, SysUser.create_by,
        )

        # 总数（基于上面的子查询计数）
        count_q = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        # 分页数据
        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(
            stmt.order_by(SysUser.update_time.desc()).offset(offset).limit(query.pageSize)
        )
        users = rows.scalars().all()

        # 批量预加载 dept + roles（消除 N+1）
        vo_list = await self._batch_to_vo(users)

        return PageResult(
            records=vo_list,
            total=total,
            pageNum=query.pageNum,
            pageSize=query.pageSize,
        )

    async def get_by_id(self, user_id: int) -> UserVO:
        """根据 ID 获取用户详情。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        return await self._to_vo(user)

    async def create(self, form: UserCreate, operator_id: int | None = None) -> UserVO:
        """新增用户，operator_id 写入 create_by / update_by。"""
        # 用户名唯一性检查
        exist = await self.db.execute(
            select(SysUser.id).where(SysUser.username == form.username, SysUser.is_deleted == 0)
        )
        if exist.scalar() is not None:
            raise BusinessException(code=ResultCode.DUPLICATE_KEY, msg="用户名已存在")

        user = SysUser(
            username=form.username,
            nickname=form.nickname,
            password=hash_password(form.password),
            gender=form.gender,
            dept_id=form.deptId,
            mobile=form.mobile,
            email=form.email,
            status=form.status,
            create_by=operator_id,
            update_by=operator_id,
        )
        self.db.add(user)
        await self.db.flush()

        # 分配角色
        if form.roleIds:
            for rid in form.roleIds:
                self.db.add(SysUserRole(user_id=user.id, role_id=rid))
            await self.db.flush()

        logger.info(f"User created: {form.username} id={user.id}")
        return await self._to_vo(user)

    async def update(self, form: UserUpdate, operator_id: int | None = None) -> UserVO:
        """更新用户，operator_id 写入 update_by。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == form.id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")

        exist = await self.db.execute(
            select(SysUser.id).where(
                SysUser.username == form.username,
                SysUser.is_deleted == 0,
                SysUser.id != form.id,
            )
        )
        if exist.scalar() is not None:
            raise BusinessException(code=ResultCode.DUPLICATE_KEY, msg="用户名已存在")

        user.username = form.username
        user.nickname = form.nickname
        user.gender = form.gender
        user.dept_id = form.deptId
        user.mobile = form.mobile
        user.email = form.email
        user.status = form.status
        user.update_by = operator_id
        user.update_time = datetime.now()
        await self.db.flush()

        await self.db.execute(
            text("DELETE FROM sys_user_role WHERE user_id = :uid"),
            {"uid": form.id},
        )
        if form.roleIds:
            for rid in form.roleIds:
                self.db.add(SysUserRole(user_id=form.id, role_id=rid))
            await self.db.flush()

        logger.info(f"User updated: {form.username} id={form.id}")
        return await self._to_vo(user)

    async def delete(self, user_ids: str) -> int:
        """批量删除用户（逻辑删除）。"""
        ids = [int(x) for x in user_ids.split(",") if x.strip()]
        if not ids:
            raise BusinessException(code=ResultCode.PARAM_VALID_FAIL, msg="请选择要删除的用户")
        result = await self.db.execute(
            text("UPDATE sys_user SET is_deleted = 1 WHERE id = ANY(:ids)"),
            {"ids": ids},
        )
        logger.info(f"Users deleted: {ids}")
        return len(ids)

    async def update_status(self, user_id: int, status: int) -> None:
        """修改用户状态。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        user.status = status
        await self.db.flush()

    async def reset_password(self, user_id: int, password: str) -> None:
        """重置用户密码。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        user.password = hash_password(password)
        await self.db.flush()
        logger.info(f"Password reset for user: {user_id}")

    async def get_user_form(self, user_id: int) -> UserUpdate:
        """获取用户表单数据。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        return await self._to_form(user)

    async def get_user_options(self) -> list[dict]:
        """用户下拉选项。"""
        rows = await self.db.execute(
            select(SysUser.id, SysUser.username, SysUser.nickname)
            .where(SysUser.is_deleted == 0, SysUser.status == 1)
        )
        return [{"value": r.id, "label": f"{r.nickname}({r.username})"} for r in rows]

    async def get_current_user_info(self, user_id: int) -> UserVO:
        """获取当前登录用户信息。"""
        return await self.get_by_id(user_id)

    async def get_user_profile(self, user_id: int) -> UserVO:
        """获取个人中心用户信息。"""
        return await self.get_by_id(user_id)

    async def update_user_profile(self, user_id: int, form) -> UserVO:
        """个人中心修改用户信息。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        data = form.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(user, k, v)
        await self.db.flush()
        return await self._to_vo(user)

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> None:
        """当前用户修改密码。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        if not verify_password(old_password, user.password):
            raise BusinessException(code=ResultCode.BAD_CREDENTIALS, msg="原密码错误")
        user.password = hash_password(new_password)
        await self.db.flush()

    async def bind_or_change_mobile(self, user_id: int, mobile: str, code: str) -> None:
        """绑定或更换手机号（验证码校验占位）。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        # TODO: 接入真实短信验证码校验
        user.mobile = mobile
        await self.db.flush()

    async def unbind_mobile(self, user_id: int, password: str) -> None:
        """解绑手机号。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        if not verify_password(password, user.password):
            raise BusinessException(code=ResultCode.BAD_CREDENTIALS, msg="密码错误")
        user.mobile = None
        await self.db.flush()

    async def bind_or_change_email(self, user_id: int, email: str, code: str) -> None:
        """绑定或更换邮箱（验证码校验占位）。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        user.email = email
        await self.db.flush()

    async def unbind_email(self, user_id: int, password: str) -> None:
        """解绑邮箱。"""
        result = await self.db.execute(
            select(SysUser).where(SysUser.id == user_id, SysUser.is_deleted == 0)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="用户不存在")
        if not verify_password(password, user.password):
            raise BusinessException(code=ResultCode.BAD_CREDENTIALS, msg="密码错误")
        user.email = None
        await self.db.flush()

    async def _to_form(self, user: SysUser) -> UserUpdate:
        """ORM 转 UserUpdate 表单。"""
        role_rows = await self.db.execute(
            text("SELECT role_id FROM sys_user_role WHERE user_id = :uid"),
            {"uid": user.id},
        )
        role_ids = [r for r, in role_rows]
        return UserUpdate(
            id=user.id, username=user.username, nickname=user.nickname, gender=user.gender,
            deptId=user.dept_id, mobile=user.mobile, email=user.email, status=user.status,
            roleIds=role_ids,
        )

    async def export_users(self, query: UserQuery, user: SysUserDetails | None = None) -> list[dict]:
        """导出用户列表。传入 user 则按角色 data_scope 过滤。"""
        conditions = [SysUser.is_deleted == 0]
        if query.keywords:
            keyword = f"%{query.keywords}%"
            conditions.append(
                (SysUser.username.ilike(keyword))
                | (SysUser.nickname.ilike(keyword))
                | (SysUser.mobile.ilike(keyword))
            )
        if query.deptId is not None:
            conditions.append(SysUser.dept_id == query.deptId)
        if query.status is not None:
            conditions.append(SysUser.status == query.status)

        rows = await self.db.execute(
            apply_data_scope(
                select(SysUser).where(*conditions).order_by(SysUser.id),
                user, SysUser.dept_id, SysUser.create_by,
            )
        )
        users = rows.scalars().all()
        return [
            {
                "用户名": u.username,
                "昵称": u.nickname,
                "手机号": u.mobile or "",
                "邮箱": u.email or "",
                "状态": "启用" if u.status == 1 else "禁用",
                "创建时间": str(u.create_time) if u.create_time else "",
            }
            for u in users
        ]

    async def import_users(self, data: list[dict]) -> dict:
        """批量导入用户。"""
        valid, invalid, errors = 0, 0, []
        for i, row in enumerate(data, start=2):
            try:
                username = row.get("用户名", "").strip()
                if not username:
                    invalid += 1
                    errors.append(f"第{i}行: 用户名为空")
                    continue
                exist = await self.db.execute(
                    select(SysUser.id).where(
                        SysUser.username == username, SysUser.is_deleted == 0
                    )
                )
                if exist.scalar() is not None:
                    invalid += 1
                    errors.append(f"第{i}行: 用户名 {username} 已存在")
                    continue
                self.db.add(SysUser(
                    username=username,
                    nickname=row.get("昵称", username),
                    password=hash_password(DEFAULT_PASSWORD),
                    mobile=row.get("手机号"),
                    email=row.get("邮箱"),
                    status=1 if row.get("状态") == "启用" else 0,
                ))
                valid += 1
            except Exception as e:
                invalid += 1
                errors.append(f"第{i}行: {str(e)}")
        await self.db.flush()
        return {"validCount": valid, "invalidCount": invalid, "messageList": errors}

    async def _batch_to_vo(self, users: list[SysUser]) -> list[UserVO]:
        """批量将 ORM 模型转为 VO（预加载部门名称和角色，消除 N+1）。"""
        if not users:
            return []

        user_ids = [u.id for u in users]
        dept_ids = list({u.dept_id for u in users if u.dept_id})

        # 1) 批量查询部门名称
        dept_map: dict[int, str] = {}
        if dept_ids:
            dept_rows = await self.db.execute(
                select(SysDept.id, SysDept.name).where(SysDept.id.in_(dept_ids))
            )
            dept_map = {row.id: row.name for row in dept_rows}

        # 2) 批量查询用户角色
        role_rows = await self.db.execute(
            text("""
                SELECT ur.user_id, r.id, r.name FROM sys_role r
                INNER JOIN sys_user_role ur ON r.id = ur.role_id
                WHERE ur.user_id = ANY(:user_ids) AND r.is_deleted = 0
            """),
            {"user_ids": user_ids},
        )
        role_map: dict[int, list[tuple[int, str]]] = {uid: [] for uid in user_ids}
        for row in role_rows:
            role_map[row.user_id].append((row.id, row.name))

        # 3) 组装 VO
        result = []
        for u in users:
            roles = role_map.get(u.id, [])
            result.append(UserVO(
                id=u.id,
                username=u.username,
                nickname=u.nickname,
                gender=u.gender,
                deptId=u.dept_id,
                deptName=dept_map.get(u.dept_id) if u.dept_id else None,
                mobile=u.mobile,
                email=u.email,
                avatar=u.avatar,
                status=u.status,
                roleIds=[r[0] for r in roles],
                roleNames=[r[1] for r in roles],
                createTime=str(u.create_time) if u.create_time else None,
                updateTime=str(u.update_time) if u.update_time else None,
            ))
        return result

    async def _to_vo(self, user: SysUser) -> UserVO:
        """单条 ORM 模型转 VO（适用于 create/update/get_by_id）。"""
        return (await self._batch_to_vo([user]))[0]
