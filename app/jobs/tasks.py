import asyncio
import time
import uuid
from typing import Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.jobs.celery_worker import celery_app
from app.models.file import File
from app.services.qdrant_service import qdrant_service
from app.utils.task_progress import (
    publish_task_progress_sync,
    update_task_progress,
)

# Database setup for tasks
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def _perform_async_indexing(file_id: str, filename: str) -> bool:
    """Async helper function to perform file indexing"""
    try:
        import os
        import tempfile

        from app.utils.minio import get_minio_client

        minio_client = get_minio_client()
        file_content = minio_client.get_object(settings.MINIO_BUCKET_NAME, file_id)

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
            temp_file.write(file_content.data)
            temp_file_path = temp_file.name

        try:
            # Use qdrant_service to process the file with file_id
            success = await qdrant_service.process_file(
                file_path=temp_file_path,
                collection_name="documents",
                file_id=str(file_id)  # Include file_id for proper search filtering
            )
            return success
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)

    except Exception as e:
        print(f"\033[91m❌ Async indexing error: {e}\033[0m")
        return False


@celery_app.task(bind=True, soft_time_limit=300, time_limit=600)
def index_file_task(self, file_id: str, user_id: str) -> Dict[str, Any]:
    """Background task to index a file for search"""
    task_id = self.request.id or f"index_file_{file_id}_{int(time.time())}"

    print(f"\033[94m🚀 Starting file indexing task for file {file_id}\033[0m")

    try:
        # Step 1: Started
        update_task_progress(task_id, user_id, 0, "started", task_type="file_indexing")
        publish_task_progress_sync(user_id, 0, "started", "60s", "file_indexing", task_id)
        print(f"\033[93m📋 Task {task_id}: Indexing started for file {file_id}\033[0m")

        # Create database session
        db = SessionLocal()

        # Step 2: Validating file
        update_task_progress(task_id, user_id, 10, "validating", task_type="file_indexing")
        publish_task_progress_sync(user_id, 10, "validating", "55s", "file_indexing", task_id)
        print(f"\033[95m🔍 Validating file {file_id}\033[0m")

        # Get file info
        file = db.query(File).filter(File.id == uuid.UUID(file_id)).first()
        if not file:
            raise Exception(f"File {file_id} not found")

        print(f"\033[92m✅ File validated: {file.filename} ({file.mime_type})\033[0m")

        # Step 3: Extracting text
        update_task_progress(task_id, user_id, 25, "extracting_text", task_type="file_indexing")
        publish_task_progress_sync(user_id, 25, "extracting_text", "45s", "file_indexing", task_id)
        print(f"\033[96m📄 Extracting text from {file.filename}\033[0m")

        # Step 4: Chunking text
        update_task_progress(task_id, user_id, 40, "chunking_text", task_type="file_indexing")
        publish_task_progress_sync(user_id, 40, "chunking_text", "35s", "file_indexing", task_id)
        print("\033[94m✂️ Preparing to chunk text\033[0m")

        # Step 5: Generating embeddings
        update_task_progress(task_id, user_id, 60, "generating_embeddings", task_type="file_indexing")
        publish_task_progress_sync(user_id, 60, "generating_embeddings", "25s", "file_indexing", task_id)
        print("\033[95m🧠 Generating embeddings\033[0m")

        # Step 6: Storing vectors
        update_task_progress(task_id, user_id, 80, "storing_vectors", task_type="file_indexing")
        publish_task_progress_sync(user_id, 80, "storing_vectors", "15s", "file_indexing", task_id)
        print("\033[93m💾 Storing vectors in Qdrant\033[0m")

        # Perform the actual indexing using new ai_service
        print(f"\033[94m🚀 Starting actual indexing process for file {file_id}\033[0m")

        try:
            # Use asyncio.run to handle the async indexing
            success = asyncio.run(_perform_async_indexing(file_id, file.filename))

        except Exception as e:
            print(f"\033[91m❌ Error during indexing: {e}\033[0m")
            success = False

        if not success:
            raise Exception("Indexing failed")

        # Step 7: Completed
        update_task_progress(task_id, user_id, 100, "completed", task_type="file_indexing")
        publish_task_progress_sync(user_id, 100, "completed", "0s", "file_indexing", task_id)

        # Get filename before closing session
        filename = file.filename

        db.close()

        print(f"\033[92m🎉 File indexing completed successfully for {file_id}\033[0m")

        return {
            "status": "success",
            "file_id": file_id,
            "filename": filename,
            "message": "File indexed successfully"
        }

    except Exception as exc:
        print(f"\033[91m💥 File indexing failed for {file_id}: {exc}\033[0m")

        # Publish failure state
        update_task_progress(task_id, user_id, 0, "failed", task_type="file_indexing")
        publish_task_progress_sync(user_id, 0, "failed", "0s", "file_indexing", task_id)

        try:
            db.close()
        except Exception:
            pass

        raise


@celery_app.task(bind=True, soft_time_limit=900, time_limit=1800)  # 15min soft, 30min hard
def reindex_all_files_task(self, user_id: str) -> Dict[str, Any]:
    """Background task to reindex all files for a user"""
    task_id = self.request.id or f"reindex_all_{user_id}_{int(time.time())}"

    print(f"\033[94m🔄 Starting bulk reindexing task for user {user_id}\033[0m")

    try:
        # Step 1: Started
        update_task_progress(task_id, user_id, 0, "started", task_type="bulk_indexing")
        publish_task_progress_sync(user_id, 0, "started", "300s", "bulk_indexing", task_id)
        print(f"\033[93m📋 Task {task_id}: Bulk reindexing started\033[0m")

        db = SessionLocal()

        # Get all files for the user
        files = db.query(File).filter(File.uploaded_by == uuid.UUID(user_id)).all()

        if not files:
            print(f"\033[93m⚠️ No files found for user {user_id}\033[0m")
            db.close()
            return {"status": "success", "files_processed": 0, "message": "No files to index"}

        total_files = len(files)
        processed = 0
        successful = 0

        print(f"\033[96m📁 Found {total_files} files to reindex\033[0m")

        for i, file in enumerate(files):
            try:
                progress = int(10 + (i / total_files) * 85)  # 10-95%
                update_task_progress(
                    task_id, user_id, progress, f"indexing_{file.filename[:20]}...",
                    task_type="bulk_indexing"
                )
                publish_task_progress_sync(
                    user_id, progress, f"indexing_{file.filename[:20]}...",
                    f"{total_files - i - 1} files remaining", "bulk_indexing", task_id
                )

                print(f"\033[95m🔄 Reindexing file {i+1}/{total_files}: {file.filename}\033[0m")

                # Index the file using new async approach
                success = asyncio.run(_perform_async_indexing(str(file.id), file.filename))
                if success:
                    successful += 1
                    print(f"\033[92m✅ Successfully reindexed {file.filename}\033[0m")
                else:
                    print(f"\033[91m❌ Failed to reindex {file.filename}\033[0m")

                processed += 1

            except Exception as e:
                print(f"\033[91m❌ Error reindexing {file.filename}: {e}\033[0m")
                processed += 1

        # Step 7: Completed
        update_task_progress(task_id, user_id, 100, "completed", task_type="bulk_indexing")
        publish_task_progress_sync(user_id, 100, "completed", "0s", "bulk_indexing", task_id)

        print(f"\033[92m🎉 Bulk reindexing completed: {successful}/{total_files} files successful\033[0m")

        db.close()

        return {
            "status": "success",
            "files_processed": processed,
            "files_successful": successful,
            "files_failed": processed - successful,
            "message": f"Bulk reindexing completed: {successful}/{total_files} files successful"
        }

    except Exception as exc:
        print(f"\033[91m💥 Bulk reindexing failed: {exc}\033[0m")

        # Publish failure state
        update_task_progress(task_id, user_id, 0, "failed", task_type="bulk_indexing")
        publish_task_progress_sync(user_id, 0, "failed", "0s", "bulk_indexing", task_id)

        try:
            db.close()
        except Exception:
            pass

        raise
