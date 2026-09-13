"""
A.R.G.U.S. — IoT Edge Terminal Schemas
Data contracts for ESP32 and edge POS terminal transaction ingress and telemetry.
Enforces anti-leakage guards and isolates operational data from training labels.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from backend.schemas.transaction import VALID_PAYSIM_TYPES, SUPPORTED_FRAUD_TYPES


class IoTTransactionRequest(BaseModel):
    """
    Edge POS / ESP32 terminal transaction payload.
    Combines transaction movement attributes with hardware telemetry and client tracking.
    """
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    # Edge Terminal & Routing Identity
    device_code: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Terminal hardware identifier (e.g. ESP32-POS-01). Can also be supplied via X-Device-Code header.",
    )
    api_key: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Terminal secret credential. Can also be supplied via X-Device-API-Key header.",
    )
    merchant_code: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional merchant code operating this terminal.",
    )
    merchant_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional merchant primary key UUID.",
    )
    client_tx_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Client-side sequence ID or terminal UUID for duplicate / replay defense.",
    )

    # Financial Transaction Attributes
    step: int = Field(
        ...,
        ge=1,
        description="Temporal simulation hour step.",
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
        description="Origin account / card identifier",
        examples=["C1234567890"],
    )
    name_dest: str = Field(
        ...,
        alias="nameDest",
        min_length=1,
        max_length=64,
        description="Destination recipient / merchant account",
        examples=["M9876543210"],
    )
    oldbalance_org: float = Field(
        ...,
        alias="oldbalanceOrg",
        ge=0.0,
        description="Origin initial ledger balance prior to transaction",
        examples=[10399045.08],
    )
    newbalance_orig: float = Field(
        ...,
        alias="newbalanceOrig",
        ge=0.0,
        description="Origin post-transaction balance",
        examples=[10399045.08],
    )
    oldbalance_dest: float = Field(
        ...,
        alias="oldbalanceDest",
        ge=0.0,
        description="Destination initial ledger balance",
        examples=[0.0],
    )
    newbalance_dest: float = Field(
        ...,
        alias="newbalanceDest",
        ge=0.0,
        description="Destination post-transaction balance",
        examples=[0.0],
    )

    # Lightweight Device Telemetry
    device_status: Optional[str] = Field(
        default="ONLINE",
        max_length=32,
        description="Operational terminal status (ONLINE, BATTERY_LOW, etc.)",
    )
    network_status: Optional[str] = Field(
        default="CONNECTED",
        max_length=32,
        description="Network link status (CONNECTED, WIFI_WEAK, etc.)",
    )
    firmware_version: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Current firmware build on edge microcontroller.",
    )
    temperature: Optional[float] = Field(
        default=None,
        description="Microcontroller SoC core temperature in Celsius.",
    )
    tamper_status: Optional[bool] = Field(
        default=False,
        description="Hardware chassis tamper switch state (True if breached).",
    )
    uptime_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Uptime in seconds since edge device boot.",
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
        Anti-leakage guard: Strictly rejects isFraud and isFlaggedFraud in edge ingress payloads.
        """
        if isinstance(data, dict):
            for forbidden in ["isFraud", "isfraud", "is_fraud", "isFlaggedFraud", "isflaggedfraud", "is_flagged_fraud"]:
                if forbidden in data:
                    raise ValueError(
                        f"Field '{forbidden}' is strictly forbidden in edge transaction assessment. "
                        "Target evaluation labels cannot be supplied to live ingestion."
                    )
        return data


class IoTRiskResponse(BaseModel):
    """
    Concise, edge-optimized response payload for microcontrollers (e.g. ESP32).
    Enables low-bandwidth JSON parsing and direct LCD/OLED display output.
    """
    model_config = ConfigDict(from_attributes=True)

    transaction_id: uuid.UUID = Field(
        ...,
        description="Relational database transaction UUID.",
    )
    client_tx_id: Optional[str] = Field(
        default=None,
        description="Echoed client sequence / idempotency identifier.",
    )
    device_code: str = Field(
        ...,
        description="Terminal device code.",
    )
    decision: str = Field(
        ...,
        description="Tri-state policy verdict ('APPROVE', 'REVIEW', 'BLOCK').",
    )
    risk_score: float = Field(
        ...,
        description="Continuous risk score (0.0 to 100.0).",
    )
    terminal_message: str = Field(
        ...,
        description="Human-readable terminal display text.",
    )
    evaluated_at: datetime = Field(
        ...,
        description="UTC timestamp of server evaluation.",
    )


class IoTHeartbeatRequest(BaseModel):
    """Periodic telemetry report sent by edge microcontrollers."""
    model_config = ConfigDict(extra="forbid")

    device_code: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Device identifier (if not provided via X-Device-Code header).",
    )
    firmware_version: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Microcontroller firmware build.",
    )
    device_status: Optional[str] = Field(
        default="ONLINE",
        max_length=32,
    )
    network_status: Optional[str] = Field(
        default="CONNECTED",
        max_length=32,
    )
    temperature: Optional[float] = Field(
        default=None,
        description="Internal SoC temperature in Celsius.",
    )
    tamper_flag: Optional[bool] = Field(
        default=False,
        description="Chassis physical intrusion status.",
    )
    uptime_seconds: Optional[int] = Field(
        default=None,
        ge=0,
    )


class IoTHeartbeatResponse(BaseModel):
    """Heartbeat acknowledgment payload."""
    status: str = "ok"
    device_code: str
    acknowledged_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    server_command: str = Field(
        default="CONTINUE",
        description="Command for edge device: CONTINUE, UPDATE_CONFIG, LOCK_TERMINAL.",
    )
