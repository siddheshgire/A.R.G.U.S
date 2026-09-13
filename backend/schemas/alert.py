"""
A.R.G.U.S. — Alert API Schemas
Provides request and response contracts for the fraud investigation queue and triage lifecycle.
"""

import uuid
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AlertResponse(BaseModel):
    """
    Representation of a persisted fraud review alert.
    Links directly to an evaluated risk assessment and transaction.
    """
    model_config = ConfigDict(from_attributes=True)

    alert_id: uuid.UUID
    assessment_id: uuid.UUID
    transaction_id: Optional[uuid.UUID] = None
    severity: str
    status: str
    assigned_user_id: Optional[uuid.UUID] = None
    assigned_username: Optional[str] = None
    notes: Optional[str] = None
    risk_score: Optional[float] = None
    decision: Optional[str] = None
    created_at: Any
    resolved_at: Optional[Any] = None


class AlertUpdateRequest(BaseModel):
    """
    Payload submitted by an analyst to update alert triage status.
    """
    status: Optional[str] = Field(
        default=None,
        description="Updated status: 'PENDING', 'IN_REVIEW', 'RESOLVED', or 'DISMISSED'",
        examples=["RESOLVED"],
    )
    notes: Optional[str] = Field(
        default=None,
        description="Analyst investigation findings and resolution notes",
        examples=["Confirmed synthetic account takeover pattern."],
    )
    assigned_user_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Assigned analyst user UUID",
    )
