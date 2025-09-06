import io
import logging
from typing import Optional

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
        try:
            minio_client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
        except Exception as e:
            logger.exception(f"MinIO client initialization error: {e}")
            raise
    return minio_client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    retry=retry_if_exception_type(S3Error),
)
def upload_bytes_to_minio(
    file_bytes: bytes,
    bucket_name: str,
    object_name: str,
    content_type: Optional[str] = None,
) -> bool:
    """Upload file bytes directly to MinIO

    Args:
        file_bytes: File content as bytes
        bucket_name: MinIO bucket name
        object_name: Object name in MinIO
        content_type: Content type (optional)

    Returns:
        bool: Success status
    """
    try:
        client = get_minio_client()

        # Ensure bucket exists
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)

        # Upload bytes directly
        file_size = len(file_bytes)
        file_data = io.BytesIO(file_bytes)
        client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=file_data,
            length=file_size,
            content_type=content_type,
        )

        return True
    except S3Error as e:
        logger.exception(f"MinIO upload error: {e}")
        return False
    except Exception as e:
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
