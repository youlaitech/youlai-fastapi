"""通知公告。"""

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.serializers import BigId

from app.pagination import PageResult
from app.database import get_db
from app.dependencies import get_current_user, require_perm
from app.exceptions import BusinessException
from app.response import Result, ResultCode
from datetime import datetime

from app.auth.schemas import SysUserDetails
from app.tool.sse.manager import broadcast, get_online_users, send_to_user
from app.tool.sse.topics import NOTICE, NOTICE_REVOKE
from app.system.notice.models import SysNotice, SysUserNotice
from app.system.user.models import SysUser
from app.system.log.operation_log import operation_log
from app.system.log.constants import ActionTypeEnum, LogModuleEnum

router = APIRouter(prefix="/api/v1/notices", tags=["通知公告"])


class NoticeQuery(BaseModel):
    pageNum: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=100)
    title: str | None = None
    publishStatus: int | None = None


class NoticeForm(BaseModel):
    title: str = Field(..., max_length=50)
    content: str = Field(...)
    type: int
    level: str = Field(max_length=5)
    targetType: int = Field(...)
    targetUserIds: list | str | None = Field(default=None)
    publishStatus: int = Field(default=0)
    status: int | None = Field(default=None)


class NoticeVO(BaseModel):
    id: BigId | None = None
    title: str = ""
    content: str = ""
    type: int = 1
    level: str | None = None
    targetType: int | None = Field(default=None, validation_alias="target_type")
    targetUserIds: str | None = Field(default=None, validation_alias="target_user_ids")
    publisherId: int | None = Field(default=None, validation_alias="publisher_id")
    publishStatus: int = Field(default=0, validation_alias="publish_status")
    publishTime: datetime | None = Field(default=None, validation_alias="publish_time")
    revokeTime: datetime | None = Field(default=None, validation_alias="revoke_time")
    createTime: datetime | None = Field(default=None, validation_alias="create_time")
    updateTime: datetime | None = Field(default=None, validation_alias="update_time")
    model_config = {"from_attributes": True}


class NoticeDetailVO(NoticeVO):
    pass


class UserNoticeVO(BaseModel):
    id: BigId | None = None
    title: str = ""
    content: str = ""
    type: int = 1
    level: str | None = None
    publishTime: str | None = None
    isRead: int = 0
    readTime: str | None = None
    createTime: str | None = None
    model_config = {"from_attributes": True}


class NoticeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_page(self, query: NoticeQuery) -> PageResult:
        conditions = [SysNotice.is_deleted == 0]
        if query.title:
            conditions.append(SysNotice.title.ilike(f"%{query.title}%"))
        if query.publishStatus is not None:
            conditions.append(SysNotice.publish_status == query.publishStatus)

        base = select(SysNotice).where(*conditions)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(
            select(SysNotice).where(*conditions).order_by(SysNotice.create_time.desc()).offset(offset).limit(query.pageSize)
        )
        vo_list = [NoticeVO.model_validate(r, from_attributes=True) for r in rows.scalars().all()]
        return PageResult(records=vo_list, total=total, pageNum=query.pageNum, pageSize=query.pageSize)

    async def get_by_id(self, notice_id: int, user_id: int | None = None) -> NoticeVO:
        """通知详情。登录用户查看时同步标记为已读。"""
        obj = await self.db.get(SysNotice, notice_id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="通知不存在")
        if user_id is not None:
            await self.db.execute(
                update(SysUserNotice)
                .where(
                    SysUserNotice.notice_id == notice_id,
                    SysUserNotice.user_id == user_id,
                    SysUserNotice.is_read == 0,
                )
                .values(is_read=1, read_time=datetime.now())
            )
        return NoticeVO.model_validate(obj, from_attributes=True)

    async def create(self, form: NoticeForm, create_by: int) -> NoticeVO:
        target_ids = form.targetUserIds
        if isinstance(target_ids, list):
            target_ids = ",".join(str(x) for x in target_ids)
        elif target_ids is not None:
            target_ids = str(target_ids)
        obj = SysNotice(
            title=form.title,
            content=form.content,
            type=form.type,
            level=form.level,
            target_type=form.targetType,
            target_user_ids=target_ids,
            publish_status=form.status if form.status is not None else form.publishStatus,
            create_by=create_by,
        )
        self.db.add(obj)
        await self.db.flush()
        return NoticeVO.model_validate(obj, from_attributes=True)

    async def update(self, notice_id: int, form: NoticeForm, update_by: int) -> NoticeVO:
        obj = await self.db.get(SysNotice, notice_id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="通知不存在")
        target_ids = form.targetUserIds
        if isinstance(target_ids, list):
            target_ids = ",".join(str(x) for x in target_ids)
        elif target_ids is not None:
            target_ids = str(target_ids)
        obj.title = form.title
        obj.content = form.content
        obj.type = form.type
        obj.level = form.level
        obj.target_type = form.targetType
        obj.target_user_ids = target_ids
        obj.publish_status = form.status if form.status is not None else form.publishStatus
        obj.update_by = update_by
        await self.db.flush()
        return NoticeVO.model_validate(obj, from_attributes=True)

    async def get_notice_form(self, notice_id: int) -> NoticeForm:
        obj = await self.db.get(SysNotice, notice_id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="通知不存在")
        return NoticeForm.model_validate(obj, from_attributes=True)

    async def publish(self, notice_id: int, publisher_id: int) -> tuple[dict, list[tuple[int, str]]]:
        """发布通知：写未读记录，返回推送用的通知体与目标用户(id,username)列表。"""
        obj = await self.db.get(SysNotice, notice_id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="通知不存在")
        if obj.publish_status == 1:
            raise BusinessException(code=ResultCode.SYSTEM_ERROR, msg="通知已发布")

        # 删除旧未读记录（支持重新发布）
        await self.db.execute(delete(SysUserNotice).where(SysUserNotice.notice_id == notice_id))

        # 按目标类型筛选用户
        if obj.target_type == 2:
            ids = [int(x) for x in (obj.target_user_ids or "").split(",") if x.strip()]
            rows = await self.db.execute(
                select(SysUser.id, SysUser.username).where(SysUser.id.in_(ids), SysUser.is_deleted == 0)
            )
        else:
            rows = await self.db.execute(
                select(SysUser.id, SysUser.username).where(SysUser.status == 1, SysUser.is_deleted == 0)
            )
        target_users: list[tuple[int, str]] = [(uid, uname) for uid, uname in rows.all()]

        # 批量写入未读记录
        if target_users:
            self.db.add_all([
                SysUserNotice(notice_id=notice_id, user_id=uid, is_read=0)
                for uid, _ in target_users
            ])

        obj.publish_status = 1
        obj.publish_time = datetime.now()
        obj.publisher_id = publisher_id
        await self.db.flush()

        notice_vo = {
            "id": obj.id,
            "title": obj.title,
            "type": obj.type,
            "publishTime": obj.publish_time.isoformat() if obj.publish_time else None,
        }
        return notice_vo, target_users

    async def revoke(self, notice_id: int) -> int:
        """撤回通知：置撤回状态、删除未读记录，返回通知 ID。"""
        obj = await self.db.get(SysNotice, notice_id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="通知不存在")
        if obj.publish_status != 1:
            raise BusinessException(code=ResultCode.SYSTEM_ERROR, msg="通知未发布或已撤回")
        obj.publish_status = -1
        obj.revoke_time = datetime.now()
        await self.db.execute(delete(SysUserNotice).where(SysUserNotice.notice_id == notice_id))
        await self.db.flush()
        return notice_id

    async def read_all(self, user_id: int) -> None:
        rows = await self.db.execute(
            select(SysUserNotice.id).where(SysUserNotice.user_id == user_id, SysUserNotice.is_read == 0)
        )
        for (nid,) in rows:
            obj = await self.db.get(SysUserNotice, nid)
            if obj:
                obj.is_read = 1
                obj.read_time = datetime.now()
        await self.db.flush()

    async def get_my_page(self, query: NoticeQuery, user_id: int) -> PageResult:
        # 已发布且未删除的通知
        base = (
            select(SysNotice, SysUserNotice.is_read, SysUserNotice.read_time)
            .join(SysUserNotice, SysUserNotice.notice_id == SysNotice.id, isouter=True)
            .where(SysNotice.is_deleted == 0, SysNotice.publish_status == 1)
        )
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
        offset = (query.pageNum - 1) * query.pageSize
        rows = await self.db.execute(
            base.order_by(SysNotice.create_time.desc()).offset(offset).limit(query.pageSize)
        )
        vo_list = []
        for notice, is_read, read_time in rows:
            vo_list.append(UserNoticeVO(
                id=notice.id,
                title=notice.title,
                content=notice.content,
                type=notice.type,
                level=notice.level,
                publishTime=str(notice.publish_time) if notice.publish_time else None,
                isRead=is_read or 0,
                readTime=str(read_time) if read_time else None,
                createTime=str(notice.create_time) if notice.create_time else None,
            ))
        return PageResult(records=vo_list, total=total, pageNum=query.pageNum, pageSize=query.pageSize)

    async def get_unread_count(self, user_id: int) -> int:
        cnt = (await self.db.execute(
            select(func.count()).select_from(SysUserNotice).where(
                SysUserNotice.user_id == user_id, SysUserNotice.is_read == 0
            )
        )).scalar() or 0
        return cnt

    async def delete(self, notice_id: int) -> None:
        obj = await self.db.get(SysNotice, notice_id)
        if obj is None:
            raise BusinessException(code=ResultCode.DATA_NOT_FOUND, msg="通知不存在")
        obj.is_deleted = 1
        await self.db.flush()


@router.get("", summary="通知分页", dependencies=[Depends(require_perm("sys:notice:list"))])
async def get_notices(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    title: str | None = None,
    publishStatus: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = NoticeQuery(pageNum=pageNum, pageSize=pageSize, title=title, publishStatus=publishStatus)
    return Result(data=await NoticeService(db).get_page(q))


@router.get("/my", summary="我的通知")
async def get_my_notices(
    pageNum: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = NoticeQuery(pageNum=pageNum, pageSize=pageSize)
    return Result(data=await NoticeService(db).get_my_page(q, user.userId))


@router.get("/unread-count", summary="未读通知数量")
async def get_unread_count(
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await NoticeService(db).get_unread_count(user.userId))


@router.get("/{notice_id}", summary="通知详情")
async def get_notice(
    notice_id: int,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await NoticeService(db).get_by_id(notice_id, user.userId))


@router.post("", summary="创建通知", dependencies=[Depends(require_perm("sys:notice:create"))])
@operation_log(module=LogModuleEnum.NOTICE, action_type=ActionTypeEnum.INSERT, title="新增通知")
async def create_notice(
    request: Request,
    form: NoticeForm,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await NoticeService(db).create(form, user.userId))


@router.put("/{notice_id}", summary="更新通知", dependencies=[Depends(require_perm("sys:notice:update"))])
@operation_log(module=LogModuleEnum.NOTICE, action_type=ActionTypeEnum.UPDATE, title="修改通知")
async def update_notice(
    request: Request,
    notice_id: int,
    form: NoticeForm,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return Result(data=await NoticeService(db).update(notice_id, form, user.userId))


@router.get("/{notice_id}/form", summary="通知表单数据", dependencies=[Depends(require_perm("sys:notice:update"))])
async def get_notice_form(notice_id: int, db: AsyncSession = Depends(get_db)):
    return Result(data=await NoticeService(db).get_notice_form(notice_id))


@router.put("/{notice_id}/publish", summary="发布通知", dependencies=[Depends(require_perm("sys:notice:publish"))])
@operation_log(module=LogModuleEnum.NOTICE, action_type=ActionTypeEnum.UPDATE, title="发布通知")
async def publish_notice(
    request: Request,
    notice_id: int,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notice_vo, targets = await NoticeService(db).publish(notice_id, user.userId)
    # 仅推送给在线的目标用户
    online = set(await get_online_users())
    for _uid, uname in targets:
        if uname in online:
            await send_to_user(uname, NOTICE, notice_vo)
    return Result(data=None)


@router.put("/{notice_id}/revoke", summary="撤回通知", dependencies=[Depends(require_perm("sys:notice:revoke"))])
@operation_log(module=LogModuleEnum.NOTICE, action_type=ActionTypeEnum.UPDATE, title="撤回通知")
async def revoke_notice(
    request: Request,
    notice_id: int,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    nid = await NoticeService(db).revoke(notice_id)
    await broadcast(NOTICE_REVOKE, {"id": nid})
    return Result(data=None)


@router.delete("/{notice_id}", summary="删除通知", dependencies=[Depends(require_perm("sys:notice:delete"))])
@operation_log(module=LogModuleEnum.NOTICE, action_type=ActionTypeEnum.DELETE, title="删除通知")
async def delete_notice(
    request: Request,
    notice_id: int,
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await NoticeService(db).delete(notice_id)
    return Result(data=None)


@router.put("/read-all", summary="全部已读")
async def read_all(
    user: SysUserDetails = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await NoticeService(db).read_all(user.userId)
    return Result(data=None)
