"""
A.R.G.U.S. — Decision Policy & Business Rule Fast Path
Maps Risk Scores to operational actions (APPROVE, REVIEW, BLOCK) and handles non-modeled transaction types.
"""

from enum import Enum
from typing import Tuple, List, Dict, Any
import numpy as np
from .config import RiskConfig


class DecisionAction(str, Enum):
    """Tri-state operational fraud risk decisions."""
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


def evaluate_decision(risk_score: float, config: RiskConfig) -> DecisionAction:
    """
    Evaluates operational decision action based on configurable threshold boundaries.
    
    Policy:
    - risk_score < threshold_review (40.0) -> APPROVE
    - threshold_review <= risk_score < threshold_block (70.0) -> REVIEW
    - risk_score >= threshold_block (70.0) -> BLOCK
    """
    if not (0.0 <= risk_score <= 100.0):
        raise ValueError(f"Risk score must be in [0.0, 100.0], got {risk_score}")

    if risk_score < config.threshold_review:
        return DecisionAction.APPROVE
    elif risk_score < config.threshold_block:
        return DecisionAction.REVIEW
    else:
        return DecisionAction.BLOCK


def evaluate_decisions_batch(risk_scores: np.ndarray, config: RiskConfig) -> np.ndarray:
    """Vectorized decision assignment for batch arrays."""
    decisions = np.empty(len(risk_scores), dtype=object)
    decisions[risk_scores < config.threshold_review] = DecisionAction.APPROVE.value
    decisions[(risk_scores >= config.threshold_review) & (risk_scores < config.threshold_block)] = DecisionAction.REVIEW.value
    decisions[risk_scores >= config.threshold_block] = DecisionAction.BLOCK.value
    return decisions


def evaluate_non_model_transaction(
    tx_dict: Dict[str, Any],
    config: RiskConfig,
) -> Tuple[float, DecisionAction, List[str]]:
    """
    Business Rule Fast Path for transactions outside the ML/DL modeling subspace (PAYMENT, CASH_IN, DEBIT).
    
    PaySim empirical findings confirmed zero fraud in these categories.
    Applies conservative deterministic rules without running heavy ML inference.
    """
    tx_type = str(tx_dict.get("type", "UNKNOWN")).upper()
    amount = float(tx_dict.get("amount", 0.0))
    reasons = [f"Transaction category '{tx_type}' evaluated via Business Rule Fast Path."]

    if amount >= config.non_model_large_amount_threshold:
        score = 45.0
        reasons.append(
            f"Transfer amount ${amount:,.2f} exceeds standard fast-path ceiling (${config.non_model_large_amount_threshold:,.2f}); flagged for analyst verification."
        )
        return score, DecisionAction.REVIEW, reasons
    else:
        score = 5.0
        reasons.append("Routine transaction category with standard amount; approved automatically.")
        return score, DecisionAction.APPROVE, reasons
