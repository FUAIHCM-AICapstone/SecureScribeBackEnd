from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.constants.messages import MessageConstants
from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.statistics import (
    DashboardPeriod,
    DashboardResponse,
    DashboardScope,
)
from app.services.statistics import StatisticsService
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR)


@router.get("/statistics/dashboard", response_model=ApiResponse[DashboardResponse])
def get_dashboard_statistics(
    period: DashboardPeriod = Query(default=DashboardPeriod.SEVEN_DAYS, description="Time period for statistics"),
    scope: DashboardScope = Query(default=DashboardScope.HYBRID, description="Data scope (personal, project, or hybrid)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[DashboardResponse]:
    """
    Get comprehensive dashboard statistics for the current user.

    - **period**: Time range for charts and trend analysis (7d, 30d, 90d, all)
    - **scope**: Context of data to include
        - `personal`: Only items directly owned/assigned to user
        - `project`: Items from all projects the user is a member of
        - `hybrid`: Mix (Personal Tasks/Files, Project Meetings)
    """
    service = StatisticsService(db, current_user.id)
    stats = service.get_dashboard_stats(period, scope)
    return ApiResponse(success=True, message=MessageConstants.STATISTICS_RETRIEVED_SUCCESS, data=stats)
