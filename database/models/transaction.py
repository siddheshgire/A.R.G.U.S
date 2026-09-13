"""
A.R.G.U.S. — Transaction Relational Model
Operational ingress transaction record representing financial movements.
Strictly isolates operational transaction inputs from evaluation labels (isFraud).
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class Transaction(Base):
    """
    Financial transaction entity.
    Stores raw operational attributes from mobile money, web, or edge POS ingress.
    Ground-truth labels (isFraud) are explicitly excluded to prevent leakage.
    """
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("device_id", "client_tx_id", name="uq_device_client_tx"),
    )

    tx_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    client_tx_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    step: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # TRANSFER, CASH_OUT, PAYMENT, CASH_IN, DEBIT
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    name_orig: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name_dest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    oldbalance_org: Mapped[float] = mapped_column(Float, nullable=False)
    newbalance_orig: Mapped[float] = mapped_column(Float, nullable=False)
    oldbalance_dest: Mapped[float] = mapped_column(Float, nullable=False)
    newbalance_dest: Mapped[float] = mapped_column(Float, nullable=False)

    merchant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("merchants.merchant_id"), nullable=True, index=True
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("devices.device_id"), nullable=True, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.user_id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User")
    merchant: Mapped[Optional["Merchant"]] = relationship("Merchant", back_populates="transactions")
    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="transactions")
    features: Mapped[Optional["TransactionFeatures"]] = relationship(
        "TransactionFeatures", back_populates="transaction", uselist=False, cascade="all, delete-orphan"
    )
    model_results: Mapped[List["ModelResult"]] = relationship(
        "ModelResult", back_populates="transaction", cascade="all, delete-orphan"
    )
    risk_assessment: Mapped[Optional["RiskAssessmentRecord"]] = relationship(
        "RiskAssessmentRecord", back_populates="transaction", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Transaction(tx_id={self.tx_id}, type='{self.type}', amount={self.amount})>"
