"""
A.R.G.U.S. — Analytics API Response Schemas
Provides structured response contracts for dashboard metrics and aggregations.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from backend.schemas.transaction import TransactionListItemResponse


class DashboardAnalyticsResponse(BaseModel):
    """
    Structured aggregate KPIs for the Fraud Analyst Dashboard.
    All fields are computed directly from real PostgreSQL state.
    """
    model_config = ConfigDict(populate_by_name=True)

    total_transactions: int
    approved_count: int
    review_count: int
    blocked_count: int
    average_risk_score: float
    active_devices_count: int
    pending_alerts_count: int
    recent_high_risk: List[TransactionListItemResponse]
