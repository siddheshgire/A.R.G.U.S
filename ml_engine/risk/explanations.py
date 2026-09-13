"""
A.R.G.U.S. — Explainable Risk Generation
Generates factual human-readable explanations distinguishing model signals from observable feature patterns.
"""

from typing import List, Dict, Any, Optional
from .signals import RiskSignals
from .config import RiskConfig


def generate_risk_explanations(
    signals: RiskSignals,
    feature_dict: Optional[Dict[str, Any]] = None,
    config: Optional[RiskConfig] = None,
) -> List[str]:
    """
    Synthesizes human-readable risk explanations.
    
    Clearly separates:
    1. Model Signals (XGBoost, Autoencoder, Isolation Forest, Logistic Regression)
    2. Observable Domain Feature Patterns (liquidation, balance error, night window, mule destination)
    
    Parameters
    ----------
    signals : RiskSignals
        Normalized model signals.
    feature_dict : Optional[Dict[str, Any]]
        Observable transaction features (amounts, balances, type).
    config : Optional[RiskConfig]
        Engine configuration.
        
    Returns
    -------
    List[str]
        List of concise, factual reasons for the risk assessment.
    """
    reasons = []

    # 1. Model-Level Explanations
    if signals.xgboost_score >= 0.70:
        reasons.append(f"High supervised fraud probability detected by XGBoost ({signals.xgboost_score:.2%}).")
    elif signals.xgboost_score >= 0.40:
        reasons.append(f"Moderate supervised fraud risk detected by XGBoost ({signals.xgboost_score:.2%}).")

    if signals.autoencoder_score >= 0.70:
        reasons.append(
            f"Significant feature reconstruction anomaly flagged by Deep Autoencoder ({signals.autoencoder_score:.2%})."
        )

    if signals.isolation_score >= 0.60:
        reasons.append(
            f"Unsupervised spatial density outlier detected by Isolation Forest ({signals.isolation_score:.2%})."
        )

    if signals.logistic_score >= 0.70:
        reasons.append(f"Elevated linear benchmark risk score ({signals.logistic_score:.2%}).")

    # 2. Observable Feature-Level Explanations (if features provided)
    if feature_dict is not None:
        if feature_dict.get("is_full_liquidation", 0) == 1:
            reasons.append("Account liquidation pattern detected: 100% of origin account balance drained to zero.")

        if feature_dict.get("dest_zero_balance_anomaly", 0) == 1:
            reasons.append("Mule recipient anomaly: Destination account balance remains zero despite inbound transfer.")

        if feature_dict.get("is_night_transaction", 0) == 1:
            reasons.append("Nighttime execution: Transaction initiated during high-fraud window (01:00–06:00).")

        orig_err = feature_dict.get("orig_balance_error", 0.0)
        if abs(orig_err) > 100.0:
            reasons.append(f"Sender ledger balance discrepancy of ${orig_err:,.2f} detected.")

        amt = feature_dict.get("amount", 0.0)
        if amt >= 200000.0:
            reasons.append(f"High monetary magnitude (${amt:,.2f}) exceeding standard monitoring baseline.")

    # Fallback if no specific high-risk triggers fired
    if not reasons:
        reasons.append("Transaction behavioral and model metrics remain within standard operational tolerances.")

    return reasons
