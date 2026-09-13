"""
A.R.G.U.S. — Risk Scoring & Decision Engine Package
Combines supervised and unsupervised model signals into explainable Risk Scores (0-100)
and tri-state operational decisions (APPROVE, REVIEW, BLOCK).
"""

from .config import RiskConfig
from .signals import RiskSignals
from .aggregator import compute_risk_score, compute_risk_scores_batch
from .decision import DecisionAction, evaluate_decision, evaluate_decisions_batch, evaluate_non_model_transaction
from .explanations import generate_risk_explanations
from .assessment import RiskAssessment, assess_transaction

__all__ = [
    "RiskConfig",
    "RiskSignals",
    "compute_risk_score",
    "compute_risk_scores_batch",
    "DecisionAction",
    "evaluate_decision",
    "evaluate_decisions_batch",
    "evaluate_non_model_transaction",
    "generate_risk_explanations",
    "RiskAssessment",
    "assess_transaction",
]
