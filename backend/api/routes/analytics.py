"""
A.R.G.U.S. — Analytics API Routes
Provides aggregated fraud statistics, decision metrics, and live feeds for the monitoring dashboard.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.schemas.analytics import DashboardAnalyticsResponse
from backend.dependencies.database import get_db
from backend.dependencies.auth import get_current_user
from backend.security.rbac import require_role, UserRole
from backend.services.analytics_service import AnalyticsService
from database.models.user import User

router = APIRouter(prefix="/analytics", tags=["Fraud Analytics & Dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Analyst Dashboard Metrics",
    description=(
        "Returns live aggregated operational fraud statistics computed directly from PostgreSQL. "
        "Includes total evaluated volume, approved/review/blocked counts, average risk score, "
        "active IoT terminal counts, pending alert counts, and the 5 latest high-risk transactions. "
        "Restricted to ANALYST, ADMIN, and AUDITOR roles."
    ),
)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardAnalyticsResponse:
    # RBAC: Privileged access required
    require_role(
        UserRole.ANALYST.value,
        UserRole.ADMIN.value,
        UserRole.AUDITOR.value,
    )(current_user)

    analytics_service = AnalyticsService(db=db)
    return analytics_service.get_dashboard_analytics()
