"""
A.R.G.U.S. — Multi-Model Risk Score Aggregator
Combines calibrated model signals into a deterministic normalized Risk Score (0–100).
"""

from typing import Union
import numpy as np
from .signals import RiskSignals
from .config import RiskConfig


def compute_risk_score(signals: RiskSignals, config: RiskConfig) -> float:
    """
    Computes a single normalized A.R.G.U.S. Risk Score (0.0 to 100.0) from model signals.
    
    Formula:
    Risk Score = (
        w_xgb * S_xgb +
        w_ae  * S_ae  +
        w_if  * S_if  +
        w_lr  * S_lr
    ) * 100.0
    
    Parameters
    ----------
    signals : RiskSignals
        Standardized model signals in [0.0, 1.0].
    config : RiskConfig
        Ensemble configuration specifying component weights.
        
    Returns
    -------
    float
        Deterministic Risk Score bounded strictly within [0.0, 100.0].
    """
    raw_weighted = (
        config.xgboost_weight * signals.xgboost_score
        + config.autoencoder_weight * signals.autoencoder_score
        + config.isolation_weight * signals.isolation_score
        + config.logistic_weight * signals.logistic_score
    )

    # Scale to 0-100 and enforce bounds
    score = float(np.clip(raw_weighted * 100.0, 0.0, 100.0))
    return round(score, 2)


def compute_risk_scores_batch(
    xgb_scores: np.ndarray,
    lr_scores: np.ndarray,
    if_scores: np.ndarray,
    ae_scores: np.ndarray,
    config: RiskConfig,
) -> np.ndarray:
    """
    Vectorized risk score computation for high-throughput batch evaluation.
    """
    raw_weighted = (
        config.xgboost_weight * xgb_scores
        + config.autoencoder_weight * ae_scores
        + config.isolation_weight * if_scores
        + config.logistic_weight * lr_scores
    )
    scores = np.clip(raw_weighted * 100.0, 0.0, 100.0)
    return np.round(scores, 2)
