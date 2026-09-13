"""
A.R.G.U.S. — Alert Relational Model
Represents high-risk transaction alerts routed to the fraud analyst review queue.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class Alert(Base):
    """
    Alert record generated for transactions requiring human review or immediate triage.
    Supports analyst assignment, status lifecycle tracking, and resolution notes.
    """
    __tablename__ = "alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("risk_assessments.assessment_id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(16), default="HIGH", nullable=False, index=True
    )  # LOW, MEDIUM, HIGH, CRITICAL
    status: Mapped[str] = mapped_column(
        String(16), default="PENDING", nullable=False, index=True
    )  # PENDING, IN_REVIEW, RESOLVED, DISMISSED
    assigned_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.user_id"), nullable=True, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    risk_assessment: Mapped["RiskAssessmentRecord"] = relationship(
        "RiskAssessmentRecord", back_populates="alerts"
    )
    assigned_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="assigned_alerts"
    )

    def __repr__(self) -> str:
        return f"<Alert(alert_id={self.alert_id}, severity='{self.severity}', status='{self.status}')>"
