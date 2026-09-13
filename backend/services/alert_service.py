"""
A.R.G.U.S. — Alert Service (OOP Application Layer)
Encapsulates fraud review queue management, triage lifecycle, and resolution auditing.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from database.models.alert import Alert
from database.models.risk_assessment import RiskAssessmentRecord
from database.models.transaction import Transaction
from database.models.user import User
from backend.schemas.alert import AlertResponse, AlertUpdateRequest
from backend.services.audit_service import AuditService


class AlertService:
    """Application service managing fraud review alerts and triage operations."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db=db)

    def list_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AlertResponse]:
        """
        Retrieves fraud review alerts with optional status and severity filtering.
        Enriches records with risk score, decision, and assigned username.
        """
        stmt = select(Alert).order_by(Alert.created_at.desc())
        if status:
            stmt = stmt.where(Alert.status == status.upper())
        if severity:
            stmt = stmt.where(Alert.severity == severity.upper())

        stmt = stmt.offset(offset).limit(limit)
        alerts = list(self.db.scalars(stmt).all())

        responses = []
        for a in alerts:
            tx_id = None
            risk_score = None
            decision_val = None
            if a.risk_assessment:
                risk_score = a.risk_assessment.final_risk_score
                if a.risk_assessment.transaction:
                    tx_id = a.risk_assessment.transaction.tx_id
                if a.risk_assessment.decision:
                    decision_val = a.risk_assessment.decision.policy_decision

            assigned_username = a.assigned_user.username if a.assigned_user else None

            responses.append(
                AlertResponse(
                    alert_id=a.alert_id,
                    assessment_id=a.assessment_id,
                    transaction_id=tx_id,
                    severity=a.severity,
                    status=a.status,
                    assigned_user_id=a.assigned_user_id,
                    assigned_username=assigned_username,
                    notes=a.notes,
                    risk_score=risk_score,
                    decision=decision_val,
                    created_at=a.created_at,
                    resolved_at=a.resolved_at,
                )
            )
        return responses

    def update_alert(
        self,
        alert_id: uuid.UUID,
        update_data: AlertUpdateRequest,
        current_user: User,
    ) -> AlertResponse:
        """
        Updates alert triage status, assignment, and resolution notes.
        Records an immutable audit log event upon status transition.
        """
        alert = self.db.get(Alert, alert_id)
        if not alert:
            raise ValueError(f"Alert with ID '{alert_id}' not found.")

        old_status = alert.status

        if update_data.status:
            new_status = update_data.status.upper()
            alert.status = new_status
            if new_status in ("RESOLVED", "DISMISSED"):
                alert.resolved_at = datetime.now(timezone.utc)
            elif new_status in ("PENDING", "IN_REVIEW"):
                alert.resolved_at = None

        if update_data.notes is not None:
            alert.notes = update_data.notes

        if update_data.assigned_user_id is not None:
            alert.assigned_user_id = update_data.assigned_user_id
        elif alert.assigned_user_id is None and current_user:
            # Auto-assign to current triaging analyst if unassigned
            alert.assigned_user_id = current_user.user_id

        # Log security event
        self.audit_service.log_event(
            event_type="ALERT_TRIAGE_UPDATED",
            action="UPDATE_ALERT_STATUS",
            resource_type="alert",
            actor_id=current_user.username if current_user else "SYSTEM",
            actor_type="USER",
            resource_id=str(alert.alert_id),
            details={
                "previous_status": old_status,
                "new_status": alert.status,
                "notes": alert.notes,
                "assigned_user_id": str(alert.assigned_user_id) if alert.assigned_user_id else None,
            },
        )

        self.db.commit()
        self.db.refresh(alert)

        # Build response
        tx_id = None
        risk_score = None
        decision_val = None
        if alert.risk_assessment:
            risk_score = alert.risk_assessment.final_risk_score
            if alert.risk_assessment.transaction:
                tx_id = alert.risk_assessment.transaction.tx_id
            if alert.risk_assessment.decision:
                decision_val = alert.risk_assessment.decision.policy_decision

        assigned_username = alert.assigned_user.username if alert.assigned_user else None

        return AlertResponse(
            alert_id=alert.alert_id,
            assessment_id=alert.assessment_id,
            transaction_id=tx_id,
            severity=alert.severity,
            status=alert.status,
            assigned_user_id=alert.assigned_user_id,
            assigned_username=assigned_username,
            notes=alert.notes,
            risk_score=risk_score,
            decision=decision_val,
            created_at=alert.created_at,
            resolved_at=alert.resolved_at,
        )
