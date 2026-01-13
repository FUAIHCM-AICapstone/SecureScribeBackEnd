from typing import Generic, List, Optional, TypeVar

from fastapi.params import Query
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses"""

    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ApiResponse(BaseModel, Generic[T]):
    """Generic API response wrapper"""

    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[str]] = None
    meta: Optional[dict] = None


class PaginatedResponse(ApiResponse[List[T]], Generic[T]):
    """Paginated API response with metadata"""

    pagination: Optional[PaginationMeta] = None


def create_pagination_meta(page: int, limit: int, total: int) -> PaginationMeta:
    """Create pagination metadata"""
    total_pages = (total + limit - 1) // limit  # Ceiling division
    return PaginationMeta(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


class PaginationSortSearchSchema(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=10, ge=1, le=100)
    sort_key: Optional[str] = Field(default=None)
    sort_dir: Optional[str] = Field(default=None)
    search: Optional[str] = Field(default=None)

    model_config = ConfigDict(from_attributes=True)


def pagination_params_dep(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    sort_key: Optional[str] = Query(None, description="Field to sort by"),
    sort_dir: Optional[str] = Query(None, description="Sort direction: asc or desc"),
    search: Optional[str] = Query(None, description="Search term to filter results"),
) -> PaginationSortSearchSchema:
    return PaginationSortSearchSchema(skip=skip, limit=limit, sort_key=sort_key, sort_dir=sort_dir, search=search)
