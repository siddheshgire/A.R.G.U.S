"""
A.R.G.U.S. — Device Management & Fleet Monitoring Routes
Provides authenticated endpoints for human users (ANALYST, ADMIN, AUDITOR) to inspect IoT terminals
and for administrators to clear hardware tamper locks.
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.schemas.device import DeviceListItemResponse
from backend.dependencies.database import get_db
from backend.dependencies.auth import get_current_user
from backend.security.rbac import require_role, UserRole
from backend.services.device_service import DeviceService
from database.models.user import User

router = APIRouter(prefix="/devices", tags=["IoT Fleet Monitoring & Device Governance"])


@router.get(
    "",
    response_model=List[DeviceListItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List Registered IoT Edge Terminals",
    description=(
        "Retrieves the registered edge POS terminal fleet with live telemetry, "
        "heartbeat timestamps, and hardware tamper status. Restricted to ANALYST, ADMIN, and AUDITOR."
    ),
)
def list_devices_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DeviceListItemResponse]:
    require_role(
        UserRole.ANALYST.value,
        UserRole.ADMIN.value,
        UserRole.AUDITOR.value,
    )(current_user)

    service = DeviceService(db=db)
    devices = service.list_devices(limit=limit, offset=offset)

    return [
        DeviceListItemResponse(
            device_id=d.device_id,
            device_code=d.device_code,
            merchant_id=d.merchant_id,
            merchant_name=d.merchant.name if d.merchant else None,
            device_type=d.device_type,
            firmware_version=d.firmware_version,
            status=d.status,
            tamper_flag=d.tamper_flag,
            last_seen_at=d.last_seen_at,
            created_at=d.created_at,
        )
        for d in devices
    ]


@router.post(
    "/{device_id}/reset-tamper",
    response_model=DeviceListItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Terminal Hardware Tamper Lock",
    description=(
        "Clears the hardware tamper flag and restores terminal to ACTIVE status "
        "following physical inspection. Restricted strictly to ADMIN role."
    ),
)
def reset_tamper_endpoint(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeviceListItemResponse:
    require_role(UserRole.ADMIN.value)(current_user)

    service = DeviceService(db=db)
    try:
        device = service.reset_tamper(device_id=device_id)
        return DeviceListItemResponse(
            device_id=device.device_id,
            device_code=device.device_code,
            merchant_id=device.merchant_id,
            merchant_name=device.merchant.name if device.merchant else None,
            device_type=device.device_type,
            firmware_version=device.firmware_version,
            status=device.status,
            tamper_flag=device.tamper_flag,
            last_seen_at=device.last_seen_at,
            created_at=device.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
