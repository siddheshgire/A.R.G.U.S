"""
A.R.G.U.S. — Alerts API Routes
Provides review queue management, triage assignment, and investigation resolution.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.schemas.alert import AlertResponse, AlertUpdateRequest
from backend.dependencies.database import get_db
from backend.dependencies.auth import get_current_user
from backend.security.rbac import require_role, UserRole
from backend.services.alert_service import AlertService
from database.models.user import User

router = APIRouter(prefix="/alerts", tags=["Fraud Investigation Queue & Alerts"])


@router.get(
    "",
    response_model=List[AlertResponse],
    status_code=status.HTTP_200_OK,
    summary="List Investigation Alerts",
    description=(
        "Queries persisted fraud review alerts with optional status and severity filtering. "
        "Restricted to ANALYST and ADMIN roles."
    ),
)
def list_alerts_endpoint(
    status: Optional[str] = Query(default=None, description="Filter by status (PENDING, IN_REVIEW, RESOLVED, DISMISSED)"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AlertResponse]:
    require_role(
        UserRole.ANALYST.value,
        UserRole.ADMIN.value,
        UserRole.AUDITOR.value,
    )(current_user)

    service = AlertService(db=db)
    return service.list_alerts(status=status, severity=severity, limit=limit, offset=offset)


@router.patch(
    "/{alert_id}",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Alert Triage Status",
    description=(
        "Updates alert triage status, analyst assignment, and resolution notes. "
        "Emits an immutable ALERT_TRIAGE_UPDATED event in the audit trail. "
        "Restricted to ANALYST and ADMIN roles."
    ),
)
def update_alert_endpoint(
    alert_id: uuid.UUID,
    payload: AlertUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertResponse:
    require_role(
        UserRole.ANALYST.value,
        UserRole.ADMIN.value,
    )(current_user)

    service = AlertService(db=db)
    try:
        return service.update_alert(alert_id=alert_id, update_data=payload, current_user=current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
