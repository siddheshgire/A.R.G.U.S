"""
A.R.G.U.S. — Audit Service (OOP Application Layer)
Encapsulates structured recording and retrieval of security and operational events.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from database.models.audit import AuditLog
from database.repository import log_audit_event, get_audit_logs


class AuditService:
    """
    Application service managing immutable audit logging for security governance.
    Demonstrates OOP encapsulation of persistence mechanics behind high-level business methods.
    """

    def __init__(self, db: Session):
        self.db = db

    def log_event(
        self,
        event_type: str,
        action: str,
        resource_type: str,
        actor_id: Optional[str] = None,
        actor_type: str = "SYSTEM",
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Records an arbitrary security or operational event."""
        return log_audit_event(
            session=self.db,
            event_type=event_type,
            action=action,
            resource_type=resource_type,
            actor_id=actor_id,
            actor_type=actor_type,
            resource_id=resource_id,
            details=details,
        )

    def log_login_success(self, username: str, user_id: str, client_ip: str) -> AuditLog:
        """Records successful authentication event."""
        return self.log_event(
            event_type="AUTH_LOGIN_SUCCESS",
            action="AUTHENTICATE_USER",
            resource_type="user",
            actor_id=username,
            actor_type="USER",
            resource_id=user_id,
            details={"client_ip": client_ip, "status": "SUCCESS"},
        )

    def log_login_failure(self, username: str, client_ip: str, reason: str) -> AuditLog:
        """Records failed authentication attempt."""
        return self.log_event(
            event_type="AUTH_LOGIN_FAILURE",
            action="AUTHENTICATE_USER",
            resource_type="user",
            actor_id=username,
            actor_type="USER",
            details={"client_ip": client_ip, "status": "FAILED", "reason": reason},
        )

    def log_access_denied(
        self,
        actor_id: str,
        resource_type: str,
        resource_id: Optional[str],
        reason: str,
    ) -> AuditLog:
        """Records unauthorized access or privilege escalation attempt."""
        return self.log_event(
            event_type="SECURITY_ACCESS_DENIED",
            action="AUTHORIZE_ACCESS",
            resource_type=resource_type,
            actor_id=actor_id,
            actor_type="USER",
            resource_id=resource_id,
            details={"status": "FORBIDDEN", "reason": reason},
        )

    def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
    ) -> List[AuditLog]:
        """Retrieves paginated audit log entries for review by authorized administrators."""
        return get_audit_logs(
            session=self.db,
            limit=limit,
            offset=offset,
            event_type=event_type,
        )
