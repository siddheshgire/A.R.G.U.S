"""
A.R.G.U.S. — Risk Assessment Relational Model
Persists the evaluated multi-signal aggregation, individual component signals,
and final Risk Score (0–100) produced by the Risk Engine.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class RiskAssessmentRecord(Base):
    """
    Ensemble Risk Engine assessment record.
    Captures normalized signals across all four models, final continuous risk score,
    and engine version.
    """
    __tablename__ = "risk_assessments"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    tx_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.tx_id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # Component normalized signals (0.0 to 1.0)
    xgboost_signal: Mapped[float] = mapped_column(Float, nullable=False)
    logistic_signal: Mapped[float] = mapped_column(Float, nullable=False)
    isolation_signal: Mapped[float] = mapped_column(Float, nullable=False)
    autoencoder_signal: Mapped[float] = mapped_column(Float, nullable=False)

    # Final Risk Score (0.00 to 100.00)
    final_risk_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    # Engine metadata
    engine_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    evaluated_by: Mapped[str] = mapped_column(
        String(32), default="ml_ensemble", nullable=False
    )  # ml_ensemble or business_rule_fast_path
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="risk_assessment")
    decision: Mapped[Optional["DecisionRecord"]] = relationship(
        "DecisionRecord", back_populates="risk_assessment", uselist=False, cascade="all, delete-orphan"
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="risk_assessment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RiskAssessmentRecord(assessment_id={self.assessment_id}, score={self.final_risk_score:.2f})>"
