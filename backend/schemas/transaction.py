"""
A.R.G.U.S. — Transaction Ingress Schemas
Validates simulated incoming transactions with strict anti-leakage guards.
"""

import uuid
from typing import Optional, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


VALID_PAYSIM_TYPES = {"TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN", "DEBIT"}
SUPPORTED_FRAUD_TYPES = {"TRANSFER", "CASH_OUT"}


class TransactionCreateRequest(BaseModel):
    """
    Ingress payload representing a live incoming transaction prior to fraud assessment.
    Strictly forbids target labels (isFraud) or simulation rule artifacts (isFlaggedFraud).
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    step: int = Field(
        ...,
        ge=1,
        description="Temporal simulation hour step (1 step = 1 hour)",
        examples=[646],
    )
    type: str = Field(
        ...,
        description="Transaction category ('TRANSFER', 'CASH_OUT', 'PAYMENT', 'CASH_IN', 'DEBIT')",
        examples=["TRANSFER"],
    )
    amount: float = Field(
        ...,
        ge=0.0,
        description="Transaction monetary magnitude",
        examples=[399045.08],
    )
    name_orig: str = Field(
        ...,
        alias="nameOrig",
        min_length=1,
        max_length=64,
        description="Origin customer account identifier",
        examples=["C1234567890"],
    )
    name_dest: str = Field(
        ...,
        alias="nameDest",
        min_length=1,
        max_length=64,
        description="Destination recipient identifier",
        examples=["M9876543210"],
    )
    oldbalance_org: float = Field(
        ...,
        alias="oldbalanceOrg",
        ge=0.0,
        description="Origin initial balance prior to transaction",
        examples=[10399045.08],
    )
    newbalance_orig: float = Field(
        ...,
        alias="newbalanceOrig",
        ge=0.0,
        description="Origin post-transaction ledger balance",
        examples=[10399045.08],
    )
    oldbalance_dest: float = Field(
        ...,
        alias="oldbalanceDest",
        ge=0.0,
        description="Destination initial balance prior to transaction",
        examples=[0.0],
    )
    newbalance_dest: float = Field(
        ...,
        alias="newbalanceDest",
        ge=0.0,
        description="Destination post-transaction ledger balance",
        examples=[0.0],
    )
    merchant_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional foreign key link to registered merchant entity",
    )
    device_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional foreign key link to registered POS / IoT edge terminal",
    )
    client_tx_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional client-side terminal sequence / idempotency identifier",
    )
    actor_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional identifier of the actor or simulated channel",
    )

    @field_validator("type")
    @classmethod
    def validate_transaction_type(cls, v: str) -> str:
        upper_v = v.strip().upper()
        if upper_v not in VALID_PAYSIM_TYPES:
            raise ValueError(
                f"Invalid transaction type '{v}'. Allowed types are: {sorted(list(VALID_PAYSIM_TYPES))}"
            )
        return upper_v

    @model_validator(mode="before")
    @classmethod
    def check_no_target_leakage(cls, data: Any) -> Any:
        """
        Anti-leakage guard: Prohibits the client from passing isFraud or isFlaggedFraud.
        This endpoint assesses unknown operational transactions.
        """
        if isinstance(data, dict):
            for forbidden_field in ["isFraud", "isfraud", "is_fraud", "isFlaggedFraud", "isflaggedfraud", "is_flagged_fraud"]:
                if forbidden_field in data:
                    raise ValueError(
                        f"Field '{forbidden_field}' is strictly forbidden in operational transaction assessment. "
                        "Target labels cannot be supplied to the live inference gateway."
                    )
        return data


class TransactionResponse(BaseModel):
    """Transaction query response model."""
    model_config = ConfigDict(from_attributes=True)

    tx_id: uuid.UUID
    step: int
    type: str
    amount: float
    name_orig: str
    name_dest: str
    oldbalance_org: float
    newbalance_orig: float
    oldbalance_dest: float
    newbalance_dest: float
    merchant_id: Optional[uuid.UUID] = None
    device_id: Optional[uuid.UUID] = None
    created_at: Any


class EngineeredFeaturesResponse(BaseModel):
    """
    Safely exposed 18 engineered features.
    Derived exclusively from backend computation. Strictly excludes target labels.
    """
    model_config = ConfigDict(from_attributes=True)

    amount: float
    oldbalance_org: float
    newbalance_orig: float
    oldbalance_dest: float
    newbalance_dest: float
    log_amount: float
    is_transfer: int
    is_cash_out: int
    hour_of_day: float
    hour_sin: float
    hour_cos: float
    is_night_transaction: int
    orig_balance_error: float
    orig_drain_ratio: float
    is_full_liquidation: int
    dest_balance_error: float
    dest_drain_ratio: float
    dest_zero_balance_anomaly: int


class RiskAssessmentSummaryResponse(BaseModel):
    """Concise risk assessment representation for transaction details."""
    model_config = ConfigDict(from_attributes=True)

    assessment_id: uuid.UUID
    final_risk_score: float
    xgboost_signal: float
    logistic_signal: float
    isolation_signal: float
    autoencoder_signal: float
    engine_version: str
    evaluated_by: str
    evaluated_at: Any


class DecisionSummaryResponse(BaseModel):
    """Concise decision representation for transaction details."""
    model_config = ConfigDict(from_attributes=True)

    decision_id: uuid.UUID
    policy_decision: str
    reasons: List[str]
    created_at: Any


class TransactionListItemResponse(BaseModel):
    """Item representation for paginated transaction history list."""
    model_config = ConfigDict(from_attributes=True)

    tx_id: uuid.UUID
    step: int
    type: str
    amount: float
    name_orig: str
    name_dest: str
    risk_score: Optional[float] = None
    decision: Optional[str] = None
    created_at: Any


class TransactionListResponse(BaseModel):
    """Paginated transaction query response."""
    items: List[TransactionListItemResponse]
    total: int
    limit: int
    offset: int


class TransactionDetailResponse(BaseModel):
    """
    Comprehensive transaction forensic detail representation.
    Enriched with risk assessment, policy decision, decomposed signals,
    and 18 engineered features.
    """
    model_config = ConfigDict(from_attributes=True)

    tx_id: uuid.UUID
    step: int
    type: str
    amount: float
    name_orig: str
    name_dest: str
    oldbalance_org: float
    newbalance_orig: float
    oldbalance_dest: float
    newbalance_dest: float
    merchant_id: Optional[uuid.UUID] = None
    merchant_name: Optional[str] = None
    device_id: Optional[uuid.UUID] = None
    device_code: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    client_tx_id: Optional[str] = None
    created_at: Any
    risk_assessment: Optional[RiskAssessmentSummaryResponse] = None
    decision: Optional[DecisionSummaryResponse] = None
    features: Optional[EngineeredFeaturesResponse] = None
