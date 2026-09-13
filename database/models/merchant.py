"""
A.R.G.U.S. — Merchant Relational Model
Defines commercial merchant entities receiving financial transactions.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class Merchant(Base):
    """
    Commercial merchant entity capable of operating physical POS devices
    and receiving e-commerce transfers.
    """
    __tablename__ = "merchants"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    merchant_code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    risk_tier: Mapped[str] = mapped_column(String(16), default="STANDARD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    devices: Mapped[List["Device"]] = relationship("Device", back_populates="merchant")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="merchant")

    def __repr__(self) -> str:
        return f"<Merchant(merchant_id={self.merchant_id}, code='{self.merchant_code}', tier='{self.risk_tier}')>"
