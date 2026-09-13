"""
A.R.G.U.S. — Analytics Service (OOP Application Layer)
Computes real-time aggregate fraud metrics, decision distributions, and high-risk feeds
directly from PostgreSQL state with zero hardcoded or fabricated statistics.
"""

from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from database.models.transaction import Transaction
from database.models.decision import DecisionRecord
from database.models.risk_assessment import RiskAssessmentRecord
from database.models.device import Device
from database.models.alert import Alert
from backend.schemas.analytics import DashboardAnalyticsResponse
from backend.schemas.transaction import TransactionListItemResponse


class AnalyticsService:
    """Application service providing live metrics for the Fraud Analyst Dashboard."""

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_analytics(self) -> DashboardAnalyticsResponse:
        """
        Executes real database aggregations across transactions, decisions,
        risk assessments, devices, and alerts.
        """
        # 1. Total transactions
        total_tx = self.db.scalar(select(func.count(Transaction.tx_id))) or 0

        # 2. Decision counts
        approved_count = self.db.scalar(
            select(func.count(DecisionRecord.decision_id)).where(DecisionRecord.policy_decision == "APPROVE")
        ) or 0
        review_count = self.db.scalar(
            select(func.count(DecisionRecord.decision_id)).where(DecisionRecord.policy_decision == "REVIEW")
        ) or 0
        blocked_count = self.db.scalar(
            select(func.count(DecisionRecord.decision_id)).where(DecisionRecord.policy_decision == "BLOCK")
        ) or 0

        # 3. Average risk score
        avg_score_raw = self.db.scalar(select(func.avg(RiskAssessmentRecord.final_risk_score)))
        avg_risk_score = round(float(avg_score_raw), 2) if avg_score_raw is not None else 0.0

        # 4. Active devices count
        active_devices = self.db.scalar(
            select(func.count(Device.device_id)).where(Device.status == "ACTIVE")
        ) or 0

        # 5. Pending alerts count
        pending_alerts = self.db.scalar(
            select(func.count(Alert.alert_id)).where(Alert.status == "PENDING")
        ) or 0

        # 6. Recent high-risk transactions (risk_score >= 70.0, limit 5)
        stmt = (
            select(Transaction, RiskAssessmentRecord, DecisionRecord)
            .join(RiskAssessmentRecord, Transaction.tx_id == RiskAssessmentRecord.tx_id)
            .outerjoin(DecisionRecord, RiskAssessmentRecord.assessment_id == DecisionRecord.assessment_id)
            .where(RiskAssessmentRecord.final_risk_score >= 70.0)
            .order_by(Transaction.created_at.desc())
            .limit(5)
        )
        rows = self.db.execute(stmt).all()

        recent_high_risk = []
        for tx, ra, dec in rows:
            recent_high_risk.append(
                TransactionListItemResponse(
                    tx_id=tx.tx_id,
                    step=tx.step,
                    type=tx.type,
                    amount=tx.amount,
                    name_orig=tx.name_orig,
                    name_dest=tx.name_dest,
                    risk_score=ra.final_risk_score if ra else None,
                    decision=dec.policy_decision if dec else None,
                    created_at=tx.created_at,
                )
            )

        return DashboardAnalyticsResponse(
            total_transactions=total_tx,
            approved_count=approved_count,
            review_count=review_count,
            blocked_count=blocked_count,
            average_risk_score=avg_risk_score,
            active_devices_count=active_devices,
            pending_alerts_count=pending_alerts,
            recent_high_risk=recent_high_risk,
        )
