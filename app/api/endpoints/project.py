import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.project import (
    BulkUserProjectCreate,
    BulkUserProjectResponse,
    ProjectApiResponse,
    ProjectCreate,
    ProjectFilter,
    ProjectMembersApiResponse,
    ProjectResponse,
    ProjectsPaginatedResponse,
    ProjectUpdate,
    ProjectWithMembers,
    ProjectWithMembersApiResponse,
    UserProjectApiResponse,
    UserProjectCreate,
    UserProjectResponse,
    UserProjectUpdate,
)
from app.services.project import (
    add_user_to_project,
    archive_project,
    bulk_add_users_to_project,
    bulk_remove_users_from_project,
    create_project,
    delete_project,
    format_project_response,
    format_project_with_members_response,
    format_user_project_response,
    get_project,
    get_project_members,
    get_projects,
    get_user_projects,
    get_user_role_in_project,
    is_user_in_project,
    remove_user_from_project,
    update_project,
    update_user_role_in_project,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Project"])


# ===== PROJECT CRUD ENDPOINTS =====


@router.post("/projects", response_model=ProjectApiResponse)
def create_project_endpoint(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new project
    """
    try:
        new_project = create_project(db, project, current_user.id)
        response_data = format_project_response(new_project)

        return ApiResponse(
            success=True,
            message="Project created successfully",
            data=response_data,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects", response_model=ProjectsPaginatedResponse)
def get_projects_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    order_by: str = Query("created_at"),
    dir: str = Query("desc"),
    name: Optional[str] = Query(None),
    is_archived: Optional[bool] = Query(None),
    created_by: Optional[str] = Query(None),
    member_id: Optional[str] = Query(None),
    created_at_gte: Optional[str] = Query(None),
    created_at_lte: Optional[str] = Query(None),
):
    """
    Get projects with filtering and pagination
    """
    try:
        # Parse UUID fields
        created_by_uuid = None
        if created_by:
            try:
                created_by_uuid = uuid.UUID(created_by)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid created_by UUID format"
                )

        member_id_uuid = None
        if member_id:
            try:
                member_id_uuid = uuid.UUID(member_id)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid member_id UUID format"
                )

        # Create filter object
        filters = ProjectFilter(
            name=name,
            is_archived=is_archived,
            created_by=created_by_uuid,
            member_id=member_id_uuid,
            created_at_gte=created_at_gte,
            created_at_lte=created_at_lte,
        )

        projects, total = get_projects(
            db=db,
            filters=filters,
            page=page,
            limit=limit,
            order_by=order_by,
            dir=dir,
        )

        # Format response data
        projects_data = [format_project_response(project) for project in projects]

        pagination_meta = create_pagination_meta(page, limit, total)

        return PaginatedResponse(
            success=True,
            message="Projects retrieved successfully",
            data=projects_data,
            pagination=pagination_meta,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProjectWithMembersApiResponse)
def get_project_endpoint(
    project_id: uuid.UUID,
    include_members: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific project by ID
    """
    try:
        project = get_project(db, project_id, include_members=include_members)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check if user has access to this project
        if not is_user_in_project(db, project_id, current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        if include_members:
            response_data = format_project_with_members_response(project)
        else:
            response_data = format_project_response(project)

        return ApiResponse(
            success=True,
            message="Project retrieved successfully",
            data=response_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/projects/{project_id}", response_model=ProjectApiResponse)
def update_project_endpoint(
    project_id: uuid.UUID,
    updates: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a project
    """
    try:
        # Check if user has admin access to this project
        user_role = get_user_role_in_project(db, project_id, current_user.id)
        if not user_role or user_role not in ["admin", "owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        updated_project = update_project(db, project_id, updates)
        if not updated_project:
            raise HTTPException(status_code=404, detail="Project not found")

        response_data = format_project_response(updated_project)

        return ApiResponse(
            success=True,
            message="Project updated successfully",
            data=response_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/projects/{project_id}", response_model=ApiResponse[dict])
def delete_project_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a project
    """
    try:
        # Check if user has admin access to this project
        user_role = get_user_role_in_project(db, project_id, current_user.id)
        if not user_role or user_role not in ["admin", "owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        success = delete_project(db, project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")

        return ApiResponse(
            success=True,
            message="Project deleted successfully",
            data={},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/projects/{project_id}/archive", response_model=ProjectApiResponse)
def archive_project_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Archive a project (soft delete)
    """
    try:
        # Check if user has admin access to this project
        user_role = get_user_role_in_project(db, project_id, current_user.id)
        if not user_role or user_role not in ["admin", "owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        archived_project = archive_project(db, project_id)
        if not archived_project:
            raise HTTPException(status_code=404, detail="Project not found")

        response_data = format_project_response(archived_project)

        return ApiResponse(
            success=True,
            message="Project archived successfully",
            data=response_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== USER-PROJECT RELATIONSHIP ENDPOINTS =====


@router.post("/projects/{project_id}/members", response_model=UserProjectApiResponse)
def add_member_to_project_endpoint(
    project_id: uuid.UUID,
    member_data: UserProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a user to a project
    """
    try:
        # Check if current user has admin access to this project
        user_role = get_user_role_in_project(db, project_id, current_user.id)
        if not user_role or user_role not in ["admin", "owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        user_project = add_user_to_project(
            db, project_id, member_data.user_id, member_data.role
        )
        if not user_project:
            raise HTTPException(status_code=400, detail="Failed to add user to project")

        response_data = format_user_project_response(user_project)

        return ApiResponse(
            success=True,
            message="User added to project successfully",
            data=response_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/projects/{project_id}/members/{user_id}", response_model=ApiResponse[dict]
)
def remove_member_from_project_endpoint(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a user from a project
    """
    try:
        # Check if current user has admin access to this project
        user_role = get_user_role_in_project(db, project_id, current_user.id)
        if not user_role or user_role not in ["admin", "owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        # Prevent removing yourself if you're the only admin
        if user_id == current_user.id:
            members = get_project_members(db, project_id)
            admin_count = sum(1 for m in members if m.role in ["admin", "owner"])
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400, detail="Cannot remove the last admin from project"
                )

        success = remove_user_from_project(db, project_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found in project")

        return ApiResponse(
            success=True,
            message="User removed from project successfully",
            data={},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/projects/{project_id}/members/{user_id}", response_model=UserProjectApiResponse
)
def update_member_role_endpoint(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role_update: UserProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a user's role in a project
    """
    try:
        # Check if current user has admin access to this project
        user_role = get_user_role_in_project(db, project_id, current_user.id)
        if not user_role or user_role not in ["admin", "owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        # Prevent changing your own role if you're the only admin
        if user_id == current_user.id and role_update.role not in ["admin", "owner"]:
            members = get_project_members(db, project_id)
            admin_count = sum(1 for m in members if m.role in ["admin", "owner"])
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400, detail="Cannot change role of the last admin"
                )

        updated_user_project = update_user_role_in_project(
            db, project_id, user_id, role_update.role
        )
        if not updated_user_project:
            raise HTTPException(status_code=404, detail="User not found in project")

        response_data = format_user_project_response(updated_user_project)

        return ApiResponse(
            success=True,
            message="User role updated successfully",
            data=response_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}/members", response_model=ProjectMembersApiResponse)
def get_project_members_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all members of a project
    """
    try:
        # Check if user has access to this project
        if not is_user_in_project(db, project_id, current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        members = get_project_members(db, project_id)
        formatted_members = [format_user_project_response(member) for member in members]

        from app.schemas.project import ProjectMembersResponse

        response_data = ProjectMembersResponse(
            project_id=project_id,
            members=formatted_members,
            total_count=len(formatted_members),
        )

        return ApiResponse(
            success=True,
            message="Project members retrieved successfully",
            data=response_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== BULK OPERATIONS =====


@router.post(
    "/projects/{project_id}/members/bulk", response_model=BulkUserProjectResponse
)
def bulk_add_members_endpoint(
    project_id: uuid.UUID,
    bulk_data: BulkUserProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk add users to a project
    """
    try:
        # Check if current user has admin access to this project
        user_role = get_user_role_in_project(db, project_id, current_user.id)
        if not user_role or user_role not in ["admin", "owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        results = bulk_add_users_to_project(db, project_id, bulk_data.users)

        total_processed = len(results)
        total_success = sum(1 for r in results if r["success"])
        total_failed = total_processed - total_success

        return BulkUserProjectResponse(
            success=total_failed == 0,
            message=f"Bulk add members completed. {total_success} successful, {total_failed} failed.",
            data=results,
            total_processed=total_processed,
            total_success=total_success,
            total_failed=total_failed,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/projects/{project_id}/members/bulk", response_model=BulkUserProjectResponse
)
def bulk_remove_members_endpoint(
    project_id: uuid.UUID,
    user_ids: List[uuid.UUID] = Query(..., description="List of user IDs to remove"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk remove users from a project
    """
    try:
        # Check if current user has admin access to this project
        user_role = get_user_role_in_project(db, project_id, current_user.id)
        if not user_role or user_role not in ["admin", "owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        # Prevent removing yourself if you're the only admin
        if current_user.id in user_ids:
            members = get_project_members(db, project_id)
            admin_count = sum(
                1
                for m in members
                if m.role in ["admin", "owner"] and m.user_id not in user_ids
            )
            if admin_count == 0:
                raise HTTPException(
                    status_code=400, detail="Cannot remove all admins from project"
                )

        results = bulk_remove_users_from_project(db, project_id, user_ids)

        total_processed = len(results)
        total_success = sum(1 for r in results if r["success"])
        total_failed = total_processed - total_success

        return BulkUserProjectResponse(
            success=total_failed == 0,
            message=f"Bulk remove members completed. {total_success} successful, {total_failed} failed.",
            data=results,
            total_processed=total_processed,
            total_success=total_success,
            total_failed=total_failed,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== USER'S PROJECTS =====


@router.get("/users/me/projects", response_model=ApiResponse[List[ProjectResponse]])
def get_my_projects_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all projects the current user belongs to
    """
    try:
        user_projects = get_user_projects(db, current_user.id)
        projects_data = []

        for user_project in user_projects:
            if user_project.project:
                project_data = format_project_response(user_project.project)
                projects_data.append(project_data)

        return ApiResponse(
            success=True,
            message="User projects retrieved successfully",
            data=projects_data,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/projects/{project_id}/join", response_model=UserProjectApiResponse)
def join_project_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Join a project as a member (if project allows self-join)
    """
    try:
        # Check if project exists
        project = get_project(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check if already a member
        if is_user_in_project(db, project_id, current_user.id):
            raise HTTPException(
                status_code=400, detail="Already a member of this project"
            )

        # For now, allow anyone to join any project (this can be restricted later)
        user_project = add_user_to_project(db, project_id, current_user.id, "member")
        if not user_project:
            raise HTTPException(status_code=400, detail="Failed to join project")

        response_data = format_user_project_response(user_project)

        return ApiResponse(
            success=True,
            message="Successfully joined project",
            data=response_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/projects/{project_id}/leave", response_model=ApiResponse[dict])
def leave_project_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Leave a project
    """
    try:
        # Check if user is a member
        if not is_user_in_project(db, project_id, current_user.id):
            raise HTTPException(status_code=400, detail="Not a member of this project")

        # Prevent leaving if you're the only admin
        user_role = get_user_role_in_project(db, project_id, current_user.id)
        if user_role in ["admin", "owner"]:
            members = get_project_members(db, project_id)
            admin_count = sum(
                1
                for m in members
                if m.role in ["admin", "owner"] and m.user_id != current_user.id
            )
            if admin_count == 0:
                raise HTTPException(
                    status_code=400, detail="Cannot leave project as the last admin"
                )

        success = remove_user_from_project(db, project_id, current_user.id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to leave project")

        return ApiResponse(
            success=True,
            message="Successfully left project",
            data={},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
