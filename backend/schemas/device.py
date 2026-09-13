"""
A.R.G.U.S. — Device Fleet Schemas
Provides response models for IoT and Smart POS terminal inventory queries.
"""

import uuid
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class DeviceListItemResponse(BaseModel):
    """
    Representation of an edge POS terminal or payment device.
    Exposes operational telemetry and tamper indicators without secrets.
    """
    model_config = ConfigDict(from_attributes=True)

    device_id: uuid.UUID
    device_code: str
    merchant_id: Optional[uuid.UUID] = None
    merchant_name: Optional[str] = None
    device_type: str
    firmware_version: Optional[str] = None
    status: str
    tamper_flag: bool
    last_seen_at: Optional[Any] = None
    created_at: Any
