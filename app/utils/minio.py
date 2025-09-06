import logging
from typing import Optional

import minio
from minio import Minio
from minio.error import S3Error
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

minio_client = None


def get_minio_client() -> Minio:
    global minio_client
    if minio_client is None:
        minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return minio_client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    retry=retry_if_exception_type(S3Error),
)
def upload_file_to_minio(
    file_data: bytes,
    bucket_name: str,
    object_name: str,
    content_type: Optional[str] = None,
) -> bool:
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
        client.put_object(
            bucket_name,
            object_name,
            file_data,
            len(file_data),
            content_type=content_type,
        )
        return True
    except S3Error as e:
        logger.exception(f"MinIO upload error: {e}")
        return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    retry=retry_if_exception_type(S3Error),
)
def download_file_from_minio(bucket_name: str, object_name: str) -> Optional[bytes]:
    try:
        client = get_minio_client()
        response = client.get_object(bucket_name, object_name)
        return response.read()
    except S3Error as e:
        logger.exception(f"MinIO download error: {e}")
        return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    retry=retry_if_exception_type(S3Error),
)
def delete_file_from_minio(bucket_name: str, object_name: str) -> bool:
    try:
        client = get_minio_client()
        client.remove_object(bucket_name, object_name)
        return True
    except S3Error as e:
        logger.exception(f"MinIO delete error: {e}")
        return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    retry=retry_if_exception_type(S3Error),
)
def generate_presigned_url(
    bucket_name: str, object_name: str, expires: int = 3600
) -> Optional[str]:
    try:
        client = get_minio_client()
        return client.presigned_get_object(bucket_name, object_name, expires)
    except S3Error as e:
        logger.exception(f"MinIO presigned URL error: {e}")
        return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    retry=retry_if_exception_type(S3Error),
)
def file_exists_in_minio(bucket_name: str, object_name: str) -> bool:
    try:
        client = get_minio_client()
        client.stat_object(bucket_name, object_name)
        return True
    except S3Error:
        return False
