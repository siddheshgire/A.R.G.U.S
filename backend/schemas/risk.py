"""
A.R.G.U.S. — Risk Assessment API Response Schemas
Presents explainable fraud scores, tri-state decisions, and model signal breakdowns.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ModelSignalsResponse(BaseModel):
    """Normalized [0.0, 1.0] output signals from the four underlying models."""
    xgboost_score: float = Field(..., description="Supervised XGBoost fraud probability [0, 1]")
    logistic_score: float = Field(..., description="Supervised Logistic Regression fraud probability [0, 1]")
    isolation_score: float = Field(..., description="Unsupervised Isolation Forest anomaly score [0, 1]")
    autoencoder_score: float = Field(..., description="Unsupervised Deep Autoencoder reconstruction anomaly [0, 1]")


class TransactionAssessResponse(BaseModel):
    """
    Standard response contract for evaluated transactions.
    Directly reflects domain results from the A.R.G.U.S. Risk Engine and database persistence.
    """
    model_config = ConfigDict(populate_by_name=True)

    transaction_id: uuid.UUID = Field(..., description="Unique transaction UUID")
    risk_score: float = Field(..., description="Aggregate continuous risk score in range [0.00, 100.00]")
    decision: str = Field(..., description="Operational policy action: 'APPROVE', 'REVIEW', or 'BLOCK'")
    model_signals: ModelSignalsResponse = Field(..., description="Decomposed model signal contributions")
    reasons: List[str] = Field(..., description="Explainable diagnostic reasons explaining the decision")
    assessment_id: Optional[uuid.UUID] = Field(default=None, description="Unique risk assessment record UUID")
    engine_version: str = Field(default="1.0.0", description="Risk Engine version string")
    evaluated_by: str = Field(default="ml_ensemble", description="Evaluation authority / agent")
    created_at: Optional[datetime] = Field(default=None, description="Assessment creation timestamp")
