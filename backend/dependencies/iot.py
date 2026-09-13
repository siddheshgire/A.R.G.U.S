"""
A.R.G.U.S. — IoT Edge Device FastAPI Dependencies
Provides device authentication, validation, and injection into IoT route handlers.
"""

from datetime import datetime, timezone
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.models.device import Device
from database.repository import get_device_by_code
from backend.dependencies.database import get_db
from backend.security.device_auth import extract_device_credentials, verify_device_credentials
from backend.services.audit_service import AuditService


async def get_authenticated_device(
    request: Request,
    db: Session = Depends(get_db),
) -> Device:
    """
    FastAPI dependency enforcing strict device authentication for edge terminals.

    Validation Pipeline:
    1. Extracts X-Device-Code and X-Device-API-Key from headers (or payload fallback).
    2. Queries database for registered device entity.
    3. Verifies API key hash in constant time.
    4. Enforces active operational status (rejects INACTIVE or DECOMMISSIONED).
    5. Enforces hardware integrity (rejects TAMPERED devices).
    6. Logs audit trail (success/failure) via AuditService.
    7. Updates terminal last_seen_at timestamp.
    """
    audit_service = AuditService(db)
    client_ip = request.client.host if request.client else "UNKNOWN"

    device_code, raw_key = await extract_device_credentials(request)

    if not device_code or not raw_key:
        audit_service.log_event(
            event_type="DEVICE_AUTH_FAILURE",
            action="AUTHENTICATE_DEVICE",
            resource_type="device",
            actor_id=device_code or "UNKNOWN",
            actor_type="DEVICE",
            details={"client_ip": client_ip, "reason": "Missing device credentials"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required device credentials. Provide 'X-Device-Code' and 'X-Device-API-Key' headers.",
        )

    # 2. Query device by unique code
    device = get_device_by_code(session=db, device_code=device_code)
    if device is None:
        audit_service.log_event(
            event_type="DEVICE_AUTH_FAILURE",
            action="AUTHENTICATE_DEVICE",
            resource_type="device",
            actor_id=device_code,
            actor_type="DEVICE",
            details={"client_ip": client_ip, "reason": "Device not registered"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Device '{device_code}' is not registered in the system.",
        )

    # 3. Verify cryptographic API key hash
    if not verify_device_credentials(device, raw_key):
        audit_service.log_event(
            event_type="DEVICE_AUTH_FAILURE",
            action="AUTHENTICATE_DEVICE",
            resource_type="device",
            actor_id=device_code,
            actor_type="DEVICE",
            resource_id=str(device.device_id),
            details={"client_ip": client_ip, "reason": "Invalid credential"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid API key supplied for device '{device_code}'.",
        )

    # 4. Check active status
    if device.status.upper() != "ACTIVE":
        audit_service.log_event(
            event_type="DEVICE_ACCESS_DENIED",
            action="AUTHORIZE_DEVICE",
            resource_type="device",
            actor_id=device_code,
            actor_type="DEVICE",
            resource_id=str(device.device_id),
            details={"client_ip": client_ip, "status": device.status, "reason": "Device inactive"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Device '{device_code}' is currently {device.status}. Terminal access denied.",
        )

    # 5. Check hardware tamper flag
    if device.tamper_flag:
        audit_service.log_event(
            event_type="DEVICE_ACCESS_DENIED",
            action="AUTHORIZE_DEVICE",
            resource_type="device",
            actor_id=device_code,
            actor_type="DEVICE",
            resource_id=str(device.device_id),
            details={"client_ip": client_ip, "reason": "Hardware tamper flag set"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Hardware tamper flag detected on terminal '{device_code}'. Terminal locked.",
        )

    # 6. Record successful authentication & update last_seen_at
    audit_service.log_event(
        event_type="DEVICE_AUTH_SUCCESS",
        action="AUTHENTICATE_DEVICE",
        resource_type="device",
        actor_id=device_code,
        actor_type="DEVICE",
        resource_id=str(device.device_id),
        details={"client_ip": client_ip, "status": "AUTHENTICATED"},
    )
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()

    return device
