import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.task import (
    BulkTaskCreate,
    BulkTaskDelete,
    BulkTaskResponse,
    BulkTaskUpdate,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.task import (
    bulk_create_tasks,
    bulk_delete_tasks,
    bulk_update_tasks,
    create_task,
    delete_task,
    get_task,
    get_tasks,
    update_task,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Task"])


@router.get("/tasks", response_model=PaginatedResponse[TaskResponse])
def get_tasks_endpoint(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    title: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    creator_id: Optional[uuid.UUID] = Query(None),
    assignee_id: Optional[uuid.UUID] = Query(None),
    due_date_gte: Optional[str] = Query(None),
    due_date_lte: Optional[str] = Query(None),
    created_at_gte: Optional[str] = Query(None),
    created_at_lte: Optional[str] = Query(None),
):
    tasks, total = get_tasks(
        db=db,
        user_id=current_user["id"],
        title=title,
        status=status,
        creator_id=creator_id,
        assignee_id=assignee_id,
        due_date_gte=due_date_gte,
        due_date_lte=due_date_lte,
        created_at_gte=created_at_gte,
        created_at_lte=created_at_lte,
        page=page,
        limit=limit,
    )

    pagination_meta = create_pagination_meta(page, limit, total)

    return PaginatedResponse(
        success=True,
        message="Tasks retrieved successfully",
        data=tasks,
        pagination=pagination_meta,
    )


@router.get("/tasks/{task_id}", response_model=ApiResponse[TaskResponse])
def get_task_endpoint(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    task = get_task(db, task_id, current_user["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return ApiResponse(
        success=True,
        message="Task retrieved successfully",
        data=task,
    )


@router.post("/tasks", response_model=ApiResponse[TaskResponse])
def create_task_endpoint(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    created_task = create_task(db, task, current_user["id"])
    return ApiResponse(
        success=True,
        message="Task created successfully",
        data=created_task,
    )


@router.put("/tasks/{task_id}", response_model=ApiResponse[TaskResponse])
def update_task_endpoint(
    task_id: uuid.UUID,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    updated_task = update_task(db, task_id, task_update, current_user["id"])
    return ApiResponse(
        success=True,
        message="Task updated successfully",
        data=updated_task,
    )


@router.delete("/tasks/{task_id}", response_model=ApiResponse[dict])
def delete_task_endpoint(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    delete_task(db, task_id, current_user["id"])
    return ApiResponse(
        success=True,
        message="Task deleted successfully",
        data={"id": task_id},
    )


@router.post("/tasks/bulk", response_model=BulkTaskResponse)
def bulk_create_tasks_endpoint(
    bulk_request: BulkTaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    results = bulk_create_tasks(db, bulk_request.tasks, current_user["id"])

    total_processed = len(results)
    total_success = sum(1 for r in results if r["success"])
    total_failed = total_processed - total_success

    return BulkTaskResponse(
        success=total_failed == 0,
        message=f"Bulk task creation completed. {total_success} successful, {total_failed} failed.",
        data=results,
        total_processed=total_processed,
        total_success=total_success,
        total_failed=total_failed,
    )


@router.put("/tasks/bulk", response_model=BulkTaskResponse)
def bulk_update_tasks_endpoint(
    bulk_request: BulkTaskUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    updates = [{"id": item.id, "updates": item.updates} for item in bulk_request.tasks]
    results = bulk_update_tasks(db, updates, current_user["id"])

    total_processed = len(results)
    total_success = sum(1 for r in results if r["success"])
    total_failed = total_processed - total_success

    return BulkTaskResponse(
        success=total_failed == 0,
        message=f"Bulk task update completed. {total_success} successful, {total_failed} failed.",
        data=results,
        total_processed=total_processed,
        total_success=total_success,
        total_failed=total_failed,
    )


@router.delete("/tasks/bulk", response_model=BulkTaskResponse)
def bulk_delete_tasks_endpoint(
    task_ids: str = BulkTaskDelete,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    results = bulk_delete_tasks(db, task_ids, current_user["id"])

    total_processed = len(results)
    total_success = sum(1 for r in results if r["success"])
    total_failed = total_processed - total_success

    return BulkTaskResponse(
        success=total_failed == 0,
        message=f"Bulk task deletion completed. {total_success} successful, {total_failed} failed.",
        data=results,
        total_processed=total_processed,
        total_success=total_success,
        total_failed=total_failed,
    )
