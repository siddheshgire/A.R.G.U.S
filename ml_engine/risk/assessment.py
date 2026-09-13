"""
A.R.G.U.S. — Risk Assessment Domain Entity
Encapsulates complete risk assessment results independent of API or database layers.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .signals import RiskSignals
from .config import RiskConfig
from .decision import DecisionAction, evaluate_decision
from .aggregator import compute_risk_score
from .explanations import generate_risk_explanations


@dataclass(frozen=True)
class RiskAssessment:
    """
    Immutable domain entity representing an end-to-end transaction risk evaluation.
    """
    risk_score: float
    decision: DecisionAction
    signals: RiskSignals
    reasons: List[str]
    engine_version: str
    evaluated_by: str = "ml_ensemble"
    transaction_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Converts assessment to serializable dictionary."""
        return {
            "transaction_id": self.transaction_id,
            "risk_score": self.risk_score,
            "decision": self.decision.value,
            "signals": self.signals.to_dict(),
            "reasons": self.reasons,
            "evaluated_by": self.evaluated_by,
            "engine_version": self.engine_version,
            "timestamp": self.timestamp,
        }


def assess_transaction(
    signals: RiskSignals,
    feature_dict: Optional[Dict[str, Any]] = None,
    config: Optional[RiskConfig] = None,
    transaction_id: Optional[str] = None,
) -> RiskAssessment:
    """
    High-level factory function that computes the Risk Score, assigns a Decision Action,
    and generates explainable reasons.
    
    Parameters
    ----------
    signals : RiskSignals
        Normalized model outputs.
    feature_dict : Optional[Dict[str, Any]]
        Observable transaction features.
    config : Optional[RiskConfig]
        Engine configuration (defaults to standard RiskConfig()).
    transaction_id : Optional[str]
        Optional identifier for tracking.
        
    Returns
    -------
    RiskAssessment
        Comprehensive risk assessment object.
    """
    if config is None:
        config = RiskConfig()

    risk_score = compute_risk_score(signals, config)
    decision = evaluate_decision(risk_score, config)
    reasons = generate_risk_explanations(signals, feature_dict, config)

    return RiskAssessment(
        risk_score=risk_score,
        decision=decision,
        signals=signals,
        reasons=reasons,
        engine_version=config.engine_version,
        evaluated_by="ml_ensemble",
        transaction_id=transaction_id,
    )
