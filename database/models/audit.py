"""
A.R.G.U.S. — Audit Log Relational Model
Provides structured, append-only persistence of system, transaction,
and administrative security events.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, BigInteger, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from ..base import Base


class AuditLog(Base):
    """
    Append-only security and operational audit trail.
    Records system events, risk decisions, user actions, and device communications.
    """
    __tablename__ = "audit_logs"

    log_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    actor_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(
        String(32), default="SYSTEM", nullable=False, index=True
    )  # USER, DEVICE, SYSTEM, API
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # TRANSACTION_ASSESSED, DECISION_RENDERED, ALERT_GENERATED, CONFIG_CHANGED
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog(log_id={self.log_id}, event='{self.event_type}', action='{self.action}')>"
