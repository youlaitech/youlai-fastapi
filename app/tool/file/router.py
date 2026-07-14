"""文件管理 — MinIO 上传下载。"""

import asyncio
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, File
from loguru import logger
from minio import Minio
from pydantic import BaseModel

from app.config import settings
from app.dependencies import get_current_user
from app.auth.schemas import SysUserDetails
from app.exceptions import BusinessException
from app.response import Result, ResultCode

router = APIRouter(prefix="/api/v1/files", tags=["文件管理"])

# 文件大小限制
MAX_FILE_SIZE = settings.FILE_MAX_SIZE_MB * 1024 * 1024  # bytes
ALLOWED_EXTENSIONS = {ext.strip().lower() for ext in settings.FILE_ALLOWED_TYPES.split(",") if ext.strip()}


class FileVO(BaseModel):
    name: str = ""
    url: str = ""
    size: int = 0
    model_config = {"from_attributes": True}


def _get_minio_client() -> Minio:
    """构造 MinIO 客户端（基于配置中的端点与密钥）。"""
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def _validate_file(file: UploadFile) -> str:
    """校验文件大小和类型，返回扩展名。"""
    # 扩展名校验
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ALLOWED_EXTENSIONS and ext not in ALLOWED_EXTENSIONS:
        raise BusinessException(
            code=ResultCode.PARAM_VALID_FAIL,
            msg=f"不支持的文件类型: .{ext}，允许: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext or "bin"


async def _ensure_bucket(client: Minio, bucket: str) -> None:
    """检查并创建 MinIO bucket（同步调用放进线程池，避免阻塞事件循环）。"""
    loop = asyncio.get_running_loop()

    def _sync():
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            return True
        return False

    created = await loop.run_in_executor(None, _sync)
    if created:
        logger.info(f"MinIO bucket created: {bucket}")


@router.post("", summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    user: SysUserDetails = Depends(get_current_user),
):
    """上传文件到 MinIO。"""
    ext = _validate_file(file)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise BusinessException(
            code=ResultCode.PARAM_VALID_FAIL,
            msg=f"文件大小超过限制: {len(content) / 1024 / 1024:.1f}MB > {settings.FILE_MAX_SIZE_MB}MB",
        )

    client = _get_minio_client()
    bucket = settings.MINIO_BUCKET
    await _ensure_bucket(client, bucket)

    object_name = f"{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4().hex}.{ext}"
    loop = asyncio.get_running_loop()

    def _sync_upload():
        client.put_object(
            bucket,
            object_name,
            io.BytesIO(content),
            length=len(content),
            content_type=file.content_type or "application/octet-stream",
        )

    await loop.run_in_executor(None, _sync_upload)

    url = f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}/{bucket}/{object_name}"
    logger.info(f"File uploaded: {object_name} by user={user.userId}")
    return Result(data={"name": file.filename, "url": url, "size": len(content)})


@router.delete("", summary="删除文件")
async def delete_file(filePath: str, user: SysUserDetails = Depends(get_current_user)):
    """从 MinIO 删除文件。"""
    client = _get_minio_client()
    bucket = settings.MINIO_BUCKET

    # 从 URL 提取 object_name
    object_name = filePath.split(f"/{bucket}/")[-1]
    loop = asyncio.get_running_loop()

    def _sync_delete():
        client.remove_object(bucket, object_name)

    await loop.run_in_executor(None, _sync_delete)
    logger.info(f"File deleted: {object_name} by user={user.userId}")
    return Result(data=None)
