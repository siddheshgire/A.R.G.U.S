"""
A.R.G.U.S. — Device Service (OOP Application Layer)
Encapsulates edge terminal provisioning, query, status tracking, and telemetry updates.
"""

import uuid
from typing import Optional, List
from sqlalchemy.orm import Session

from database.models.device import Device
from database.repository import (
    get_device_by_code,
    get_device_by_id,
    create_device,
    update_device_heartbeat,
)
from backend.security.device_auth import hash_device_key


class DeviceService:
    """
    Application service managing IoT terminals and POS edge devices.
    Adheres to OOP encapsulation principles.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_code(self, device_code: str) -> Optional[Device]:
        """Queries terminal by its unique hardware identifier code."""
        return get_device_by_code(session=self.db, device_code=device_code)

    def get_by_id(self, device_id: uuid.UUID) -> Optional[Device]:
        """Queries terminal by primary key UUID."""
        return get_device_by_id(session=self.db, device_id=device_id)

    def register_device(
        self,
        device_code: str,
        raw_api_key: Optional[str] = None,
        merchant_id: Optional[uuid.UUID] = None,
        device_type: str = "POS_TERMINAL",
        firmware_version: Optional[str] = "v1.0.0",
        status: str = "ACTIVE",
        tamper_flag: bool = False,
    ) -> Device:
        """
        Registers a new terminal, hashing its API key before persistence.
        Ensures plaintext credentials are never stored in the database.
        """
        api_key_hash = hash_device_key(raw_api_key) if raw_api_key else None
        device = create_device(
            session=self.db,
            device_code=device_code,
            api_key_hash=api_key_hash,
            merchant_id=merchant_id,
            device_type=device_type,
            firmware_version=firmware_version,
            status=status,
            tamper_flag=tamper_flag,
        )
        self.db.commit()
        return device

    def process_heartbeat(
        self,
        device: Device,
        firmware_version: Optional[str] = None,
        tamper_flag: Optional[bool] = None,
    ) -> Device:
        """Updates device timestamp and telemetry flags."""
        updated = update_device_heartbeat(
            session=self.db,
            device=device,
            firmware_version=firmware_version,
            tamper_flag=tamper_flag,
        )
        self.db.commit()
        return updated

    def list_devices(self, limit: int = 50, offset: int = 0) -> List[Device]:
        """Lists registered IoT terminals with pagination."""
        from sqlalchemy import select
        stmt = select(Device).order_by(Device.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def reset_tamper(self, device_id: uuid.UUID) -> Device:
        """Clears hardware tamper flag and restores terminal to ACTIVE status."""
        device = self.get_by_id(device_id)
        if not device:
            raise ValueError(f"Device with ID '{device_id}' not found.")
        device.tamper_flag = False
        device.status = "ACTIVE"
        self.db.commit()
        self.db.refresh(device)
        return device
