"""文件管理 — S3（RustFS）上传下载。"""

import asyncio
import io
import uuid
from datetime import datetime

import boto3
from botocore.client import Config
from fastapi import APIRouter, Depends, UploadFile, File
from loguru import logger
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


def _get_s3_client():
    """构造 S3 客户端（指向 RustFS 等 S3 兼容服务，路径风格寻址）。"""
    endpoint = ("https://" if settings.S3_SECURE else "http://") + settings.S3_ENDPOINT
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
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


async def _ensure_bucket(client, bucket: str) -> None:
    """检查并创建 S3 bucket（同步调用放进线程池，避免阻塞事件循环）。"""
    loop = asyncio.get_running_loop()

    def _sync():
        try:
            client.head_bucket(Bucket=bucket)
        except client.exceptions.ClientError:
            client.create_bucket(Bucket=bucket)
            policy = (
                '{"Version":"2012-10-17","Statement":['
                '{"Effect":"Allow","Principal":{"AWS":["*"]},'
                '"Action":["s3:GetObject"],"Resource":["arn:aws:s3:::%s/*"]}]}'
                % bucket
            )
            client.put_bucket_policy(Bucket=bucket, Policy=policy)

    await loop.run_in_executor(None, _sync)


@router.post("", summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    user: SysUserDetails = Depends(get_current_user),
):
    """上传文件到 S3（RustFS）。"""
    ext = _validate_file(file)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise BusinessException(
            code=ResultCode.PARAM_VALID_FAIL,
            msg=f"文件大小超过限制: {len(content) / 1024 / 1024:.1f}MB > {settings.FILE_MAX_SIZE_MB}MB",
        )

    client = _get_s3_client()
    bucket = settings.S3_BUCKET
    await _ensure_bucket(client, bucket)

    object_name = f"{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4().hex}.{ext}"
    loop = asyncio.get_running_loop()

    def _sync_upload():
        client.put_object(
            Bucket=bucket,
            Key=object_name,
            Body=io.BytesIO(content),
            ContentLength=len(content),
            ContentType=file.content_type or "application/octet-stream",
        )

    await loop.run_in_executor(None, _sync_upload)

    url = f"{'https' if settings.S3_SECURE else 'http'}://{settings.S3_ENDPOINT}/{bucket}/{object_name}"
    logger.info(f"File uploaded: {object_name} by user={user.userId}")
    return Result(data={"name": file.filename, "url": url, "size": len(content)})


@router.delete("", summary="删除文件")
async def delete_file(filePath: str, user: SysUserDetails = Depends(get_current_user)):
    """从 S3（RustFS）删除文件。"""
    client = _get_s3_client()
    bucket = settings.S3_BUCKET

    # 从 URL 提取 object_name
    object_name = filePath.split(f"/{bucket}/")[-1]
    loop = asyncio.get_running_loop()

    def _sync_delete():
        client.delete_object(Bucket=bucket, Key=object_name)

    await loop.run_in_executor(None, _sync_delete)
    logger.info(f"File deleted: {object_name} by user={user.userId}")
    return Result(data=None)
