"""
A.R.G.U.S. — IoT Transaction Service (OOP Application Layer)
Orchestrates edge transaction ingestion, merchant validation, concurrency-safe duplicate protection,
delegation to the core TransactionService, and edge-friendly response formatting.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database.models.device import Device
from database.models.merchant import Merchant
from database.repository import check_duplicate_device_tx
from backend.schemas.iot import IoTTransactionRequest, IoTRiskResponse
from backend.schemas.transaction import TransactionCreateRequest
from backend.services.transaction_service import TransactionService
from backend.services.audit_service import AuditService


class IoTTransactionService:
    """
    Application service handling transaction requests originating from IoT terminals.
    Coordinates edge validation and delegates ML evaluation to TransactionService.
    """

    def __init__(
        self,
        transaction_service: TransactionService,
        audit_service: AuditService,
    ):
        self.transaction_service = transaction_service
        self.audit_service = audit_service

    def process_terminal_transaction(
        self,
        request: IoTTransactionRequest,
        device: Device,
        db: Session,
    ) -> IoTRiskResponse:
        """
        Processes a transaction originating from an authenticated edge terminal:
        1. Validates device-merchant association.
        2. Enforces concurrency-safe duplicate / replay protection.
        3. Transforms IoT request into standard transaction request.
        4. Delegates to TransactionService (running 18-feature pipeline, 4 models, Risk Engine).
        5. Logs structured device transaction audit event.
        6. Returns concise IoTRiskResponse tailored for microcontrollers.
        """
        # 1. Device-Merchant Association Validation
        effective_merchant_id = request.merchant_id or device.merchant_id
        if request.merchant_id and device.merchant_id and request.merchant_id != device.merchant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Terminal '{device.device_code}' is not associated with merchant '{request.merchant_id}' "
                    f"(registered to merchant '{device.merchant_id}')."
                ),
            )

        if request.merchant_code and device.merchant:
            if device.merchant.merchant_code != request.merchant_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Terminal '{device.device_code}' is not associated with merchant code '{request.merchant_code}' "
                        f"(registered to merchant code '{device.merchant.merchant_code}')."
                    ),
                )

        # 2. Duplicate / Replay Protection (Application Pre-Check)
        if request.client_tx_id:
            if check_duplicate_device_tx(session=db, device_id=device.device_id, client_tx_id=request.client_tx_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Duplicate transaction: Transaction with client sequence '{request.client_tx_id}' "
                        f"from device '{device.device_code}' has already been processed and recorded."
                    ),
                )

        # 3. Transform IoT request into canonical TransactionCreateRequest
        tx_req = TransactionCreateRequest(
            step=request.step,
            type=request.type,
            amount=request.amount,
            name_orig=request.name_orig,
            name_dest=request.name_dest,
            oldbalance_org=request.oldbalance_org,
            newbalance_orig=request.newbalance_orig,
            oldbalance_dest=request.oldbalance_dest,
            newbalance_dest=request.newbalance_dest,
            merchant_id=effective_merchant_id,
            device_id=device.device_id,
            client_tx_id=request.client_tx_id,
            actor_id=f"IOT_TERMINAL_{device.device_code}",
        )

        # 4. Delegate to existing TransactionService (Atomically evaluated & persisted)
        # Database-level uniqueness constraint catches concurrent race conditions
        try:
            assess_res = self.transaction_service.assess_and_persist(
                request=tx_req,
                db=db,
                current_user=None,  # Terminal machine identity, not human user
            )
        except IntegrityError as exc:
            db.rollback()
            # If the database unique constraint uq_device_client_tx was violated
            if "uq_device_client_tx" in str(exc) or "client_tx_id" in str(exc):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Duplicate transaction: Transaction with client sequence '{request.client_tx_id}' "
                        f"from device '{device.device_code}' has already been processed and recorded."
                    ),
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database integrity error during transaction persistence.",
            )

        # 5. Audit Logging for Device Ingress
        self.audit_service.log_event(
            event_type="DEVICE_TRANSACTION_RECEIVED",
            action="ASSESS_EDGE_TRANSACTION",
            resource_type="transaction",
            actor_id=device.device_code,
            actor_type="DEVICE",
            resource_id=str(assess_res.transaction_id),
            details={
                "client_tx_id": request.client_tx_id,
                "type": request.type,
                "amount": request.amount,
                "decision": assess_res.decision,
                "risk_score": assess_res.risk_score,
                "device_status": request.device_status,
                "network_status": request.network_status,
            },
        )
        db.commit()

        # 6. Terminal Display Message Formulation
        if assess_res.decision == "APPROVE":
            terminal_msg = "TRANSACTION APPROVED"
        elif assess_res.decision == "REVIEW":
            terminal_msg = "FLAGGED FOR OPERATIONAL REVIEW"
        else:
            terminal_msg = "TRANSACTION BLOCKED - HIGH RISK"

        return IoTRiskResponse(
            transaction_id=assess_res.transaction_id,
            client_tx_id=request.client_tx_id,
            device_code=device.device_code,
            decision=assess_res.decision,
            risk_score=assess_res.risk_score,
            terminal_message=terminal_msg,
            evaluated_at=assess_res.created_at or datetime.now(timezone.utc),
        )
