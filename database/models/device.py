"""
A.R.G.U.S. — Device / Terminal Relational Model
Defines edge POS and IoT hardware terminals (e.g. ESP32) originating transactions.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class Device(Base):
    """
    Physical edge point-of-sale terminal or payment gateway device.
    Supports hardware tamper status tracking for IoT terminals.
    """
    __tablename__ = "devices"

    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    device_code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    merchant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("merchants.merchant_id"), nullable=True, index=True
    )
    device_type: Mapped[str] = mapped_column(
        String(32), default="POS_TERMINAL", nullable=False
    )
    firmware_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="ACTIVE", nullable=False
    )  # ACTIVE, OFFLINE, TAMPERED, DECOMMISSIONED
    tamper_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    merchant: Mapped[Optional["Merchant"]] = relationship("Merchant", back_populates="devices")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="device")

    def __repr__(self) -> str:
        return f"<Device(device_id={self.device_id}, code='{self.device_code}', status='{self.status}')>"
