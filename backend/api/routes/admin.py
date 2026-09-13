"""
A.R.G.U.S. — Administrative & Security Governance Endpoints
Provides audit trail inspection and identity management restricted to ADMIN and AUDITOR roles.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from datetime import datetime

from backend.dependencies.auth import get_current_user, get_audit_service, get_user_service
from backend.security.rbac import require_role, UserRole
from backend.services.audit_service import AuditService
from backend.services.user_service import UserService
from backend.schemas.auth import UserResponse
from database.models.user import User

router = APIRouter(prefix="/admin", tags=["Administrative & Security Governance"])


class AuditLogResponse(BaseModel):
    """Safe audit trail representation for compliance review."""
    log_id: int
    actor_id: Optional[str]
    actor_type: str
    event_type: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    created_at: datetime


@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Query Security Audit Trail",
    description="Inspects structured security and transaction events. Restricted to ADMIN and AUDITOR roles.",
)
def get_audit_logs_endpoint(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    event_type: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service),
) -> List[AuditLogResponse]:
    # Enforce RBAC: ADMIN or AUDITOR required
    require_role(UserRole.ADMIN.value, UserRole.AUDITOR.value)(current_user)

    logs = audit_service.get_logs(limit=limit, offset=offset, event_type=event_type)
    return [
        AuditLogResponse(
            log_id=log.log_id,
            actor_id=log.actor_id,
            actor_type=log.actor_type,
            event_type=log.event_type,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get(
    "/users",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List System Users",
    description="Retrieves the registered user accounts and their assigned operational roles. Restricted to ADMIN.",
)
def get_users_endpoint(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> List[UserResponse]:
    # Enforce RBAC: ADMIN required
    require_role(UserRole.ADMIN.value)(current_user)

    users = user_service.list_users(limit=limit, offset=offset)
    return [
        UserResponse(
            user_id=u.user_id,
            username=u.username,
            email=u.email,
            role=u.role.name if u.role else "USER",
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]
