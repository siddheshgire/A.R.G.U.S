"""
A.R.G.U.S. — Transaction Ingress & Assessment Routes
Provides REST endpoints for simulated transaction risk evaluation and historical query.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.schemas.transaction import (
    TransactionCreateRequest,
    TransactionResponse,
    TransactionListResponse,
    TransactionDetailResponse,
)
from backend.schemas.risk import TransactionAssessResponse
from backend.dependencies.database import get_db
from backend.dependencies.models import get_transaction_service
from backend.dependencies.auth import get_optional_current_user
from backend.services.transaction_service import TransactionService
from database.models.user import User

router = APIRouter(prefix="/transactions", tags=["Transaction Risk Assessment"])


@router.post(
    "/assess",
    response_model=TransactionAssessResponse,
    status_code=status.HTTP_200_OK,
    summary="Assess Simulated Transaction Risk",
    description=(
        "Ingests a simulated transaction payload, extracts 18 engineered features, "
        "computes model inference across all 4 ML/DL models (XGBoost, Logistic Regression, "
        "Isolation Forest, Deep Autoencoder), aggregates a continuous Risk Score (0-100), "
        "determines an operational policy action (APPROVE, REVIEW, BLOCK), and atomically "
        "persists the transaction, features, model signals, assessment, and alert into PostgreSQL.\n\n"
        "**Notice:** Strictly for simulated transactions. ML assessment is supported for TRANSFER and CASH_OUT types. "
        "Target labels (isFraud) are strictly forbidden."
    ),
)
def assess_transaction_endpoint(
    request: TransactionCreateRequest,
    db: Session = Depends(get_db),
    service: TransactionService = Depends(get_transaction_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> TransactionAssessResponse:
    return service.assess_and_persist(request=request, db=db, current_user=current_user)


@router.get(
    "",
    response_model=TransactionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Transactions with Filters & Scoped RBAC",
    description=(
        "Retrieves a paginated list of transactions with server-side filters. "
        "Enforces Scoped RBAC: USER accounts view only their own records; "
        "ANALYST, ADMIN, and AUDITOR accounts have system-wide visibility."
    ),
)
def list_transactions_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    type: Optional[str] = Query(default=None, description="Filter by type (TRANSFER, CASH_OUT)"),
    decision: Optional[str] = Query(default=None, description="Filter by decision (APPROVE, REVIEW, BLOCK)"),
    min_risk: Optional[float] = Query(default=None, ge=0.0, le=100.0, description="Minimum risk score"),
    max_risk: Optional[float] = Query(default=None, ge=0.0, le=100.0, description="Maximum risk score"),
    db: Session = Depends(get_db),
    service: TransactionService = Depends(get_transaction_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> TransactionListResponse:
    return service.list_transactions(
        db=db,
        current_user=current_user,
        limit=limit,
        offset=offset,
        tx_type=type,
        decision=decision,
        min_risk=min_risk,
        max_risk=max_risk,
    )


@router.get(
    "/{tx_id}",
    response_model=TransactionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Transaction Forensic Details",
    description=(
        "Retrieves full forensic details of a transaction including 18 engineered features, "
        "decomposed model signals, and operational policy decision. "
        "Enforces Object-Level Authorization (IDOR Defense)."
    ),
)
def get_transaction_endpoint(
    tx_id: uuid.UUID,
    db: Session = Depends(get_db),
    service: TransactionService = Depends(get_transaction_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> TransactionDetailResponse:
    return service.get_transaction_detail(tx_id=tx_id, db=db, current_user=current_user)
