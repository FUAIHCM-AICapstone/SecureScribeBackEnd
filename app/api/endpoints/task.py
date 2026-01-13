import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.constants.messages import MessageConstants
from app.core.config import settings
from app.db import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.task import (
    BulkTaskCreate,
    BulkTaskResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.task import (
    bulk_create_tasks,
    create_task,
    delete_task,
    get_task,
    get_tasks,
    serialize_task,
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
    meeting_id: Optional[uuid.UUID] = Query(None),
    created_at_gte: Optional[str] = Query(None),
    created_at_lte: Optional[str] = Query(None),
):
    tasks, total = get_tasks(
        db=db,
        user_id=current_user.id,
        title=title,
        status=status,
        creator_id=creator_id,
        assignee_id=assignee_id,
        due_date_gte=due_date_gte,
        due_date_lte=due_date_lte,
        created_at_gte=created_at_gte,
        created_at_lte=created_at_lte,
        meeting_id=meeting_id,
        page=page,
        limit=limit,
    )

    pagination_meta = create_pagination_meta(page, limit, total)

    return PaginatedResponse(
        success=True,
        message=MessageConstants.TASK_RETRIEVED_SUCCESS,
        data=[serialize_task(t) for t in tasks],
        pagination=pagination_meta,
    )


@router.get("/tasks/{task_id}", response_model=ApiResponse[TaskResponse])
def get_task_endpoint(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    task = get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.TASK_NOT_FOUND)

    return ApiResponse(
        success=True,
        message=MessageConstants.TASK_RETRIEVED_SUCCESS,
        data=serialize_task(task),
    )


@router.post("/tasks", response_model=ApiResponse[TaskResponse])
def create_task_endpoint(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    created_task = create_task(db, task, current_user.id)
    # Reload with relationships for consistent serialization
    loaded_task = get_task(db, created_task.id, current_user.id)
    return ApiResponse(
        success=True,
        message=MessageConstants.TASK_CREATED_SUCCESS,
        data=serialize_task(loaded_task or created_task),
    )


@router.post("/tasks/bulk", response_model=BulkTaskResponse)
def bulk_create_tasks_endpoint(
    bulk_request: BulkTaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    results = bulk_create_tasks(db, bulk_request.tasks, current_user.id)

    total_processed = len(results)
    total_success = sum(1 for r in results if r["success"])
    total_failed = total_processed - total_success

    return BulkTaskResponse(
        success=total_failed == 0,
        message=MessageConstants.TASK_CREATED_SUCCESS,
        data=results,
        total_processed=total_processed,
        total_success=total_success,
        total_failed=total_failed,
    )


@router.put("/tasks/{task_id}", response_model=ApiResponse[TaskResponse])
def update_task_endpoint(
    task_id: uuid.UUID,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    updated_task = update_task(db, task_id, task_update, current_user.id)
    # Reload with relationships for consistent serialization
    loaded_task = get_task(db, task_id, current_user.id)
    return ApiResponse(
        success=True,
        message=MessageConstants.TASK_UPDATED_SUCCESS,
        data=serialize_task(loaded_task or updated_task),
    )


@router.delete("/tasks/{task_id}", response_model=ApiResponse[dict])
def delete_task_endpoint(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    delete_task(db, task_id, current_user.id)
    return ApiResponse(
        success=True,
        message=MessageConstants.TASK_DELETED_SUCCESS,
        data={"id": task_id},
    )
