"""
A.R.G.U.S. — IoT & Edge Terminal API Router
Provides authenticated ingress endpoints for microcontrollers (ESP32) and smart terminals:
- POST /api/v1/iot/transactions: Transaction evaluation through the full 18-feature + 4-model pipeline.
- POST /api/v1/iot/heartbeat: Terminal status, telemetry, and liveness synchronization.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database.models.device import Device
from backend.dependencies.database import get_db
from backend.dependencies.models import get_model_manager
from backend.dependencies.iot import get_authenticated_device
from backend.schemas.iot import (
    IoTTransactionRequest,
    IoTRiskResponse,
    IoTHeartbeatRequest,
    IoTHeartbeatResponse,
)
from backend.services.model_service import ModelManager
from backend.services.transaction_service import TransactionService
from backend.services.audit_service import AuditService
from backend.services.device_service import DeviceService
from backend.services.iot_transaction_service import IoTTransactionService

iot_router = APIRouter(prefix="/iot", tags=["IoT & Edge Terminals"])


@iot_router.post(
    "/transactions",
    response_model=IoTRiskResponse,
    status_code=status.HTTP_200_OK,
    summary="Assess Edge Transaction from Authenticated Terminal",
    description=(
        "Authenticates the edge device via X-Device-Code and X-Device-API-Key headers, "
        "validates merchant association, enforces concurrency-safe duplicate prevention, "
        "and routes the transaction through the existing 18-feature pipeline, 4 ML/DL models, "
        "and Risk Engine. Returns a concise risk verdict for display on microcontrollers."
    ),
)
def assess_iot_transaction(
    payload: IoTTransactionRequest,
    device: Device = Depends(get_authenticated_device),
    db: Session = Depends(get_db),
    model_manager: ModelManager = Depends(get_model_manager),
) -> IoTRiskResponse:
    """Evaluates an edge transaction sent by an authenticated ESP32 terminal."""
    tx_service = TransactionService(model_manager=model_manager)
    audit_service = AuditService(db=db)
    iot_tx_service = IoTTransactionService(
        transaction_service=tx_service,
        audit_service=audit_service,
    )
    return iot_tx_service.process_terminal_transaction(
        request=payload,
        device=device,
        db=db,
    )


@iot_router.post(
    "/heartbeat",
    response_model=IoTHeartbeatResponse,
    status_code=status.HTTP_200_OK,
    summary="Edge Device Telemetry & Heartbeat",
    description=(
        "Receives periodic telemetry from authenticated terminals (uptime, temperature, tamper status), "
        "updates the device's last_seen_at timestamp, and records an immutable audit log entry."
    ),
)
def device_heartbeat(
    payload: IoTHeartbeatRequest,
    device: Device = Depends(get_authenticated_device),
    db: Session = Depends(get_db),
) -> IoTHeartbeatResponse:
    """Processes heartbeat report from edge terminal."""
    device_service = DeviceService(db=db)
    audit_service = AuditService(db=db)

    # Update device telemetry & last seen timestamp
    device_service.process_heartbeat(
        device=device,
        firmware_version=payload.firmware_version,
        tamper_flag=payload.tamper_flag,
    )

    # Log device heartbeat event
    audit_service.log_event(
        event_type="DEVICE_HEARTBEAT",
        action="PROCESS_HEARTBEAT",
        resource_type="device",
        actor_id=device.device_code,
        actor_type="DEVICE",
        resource_id=str(device.device_id),
        details={
            "device_status": payload.device_status,
            "network_status": payload.network_status,
            "temperature": payload.temperature,
            "tamper_flag": payload.tamper_flag,
            "uptime_seconds": payload.uptime_seconds,
            "firmware_version": payload.firmware_version,
        },
    )
    db.commit()

    return IoTHeartbeatResponse(
        status="ok",
        device_code=device.device_code,
        acknowledged_at=datetime.now(timezone.utc),
        server_command="CONTINUE",
    )
