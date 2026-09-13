"""
A.R.G.U.S. — Risk Engine Configuration
Defines ensemble model weights, decision thresholds, and business rule configurations.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass(frozen=True)
class RiskConfig:
    """
    Configuration for multi-model risk score aggregation and decision thresholds.
    
    Weights reflect model confidence and diversity:
    - xgboost_weight (0.50): Primary supervised gradient-boosted fraud detector.
    - autoencoder_weight (0.20): Unsupervised deep reconstruction anomaly detector.
    - isolation_weight (0.15): Unsupervised spatial density outlier detector.
    - logistic_weight (0.15): Calibrated linear baseline benchmark.
    """
    xgboost_weight: float = 0.50
    autoencoder_weight: float = 0.20
    isolation_weight: float = 0.15
    logistic_weight: float = 0.15

    # Decision policy thresholds on normalized 0-100 score
    threshold_review: float = 40.0
    threshold_block: float = 70.0

    # Business rule fast path for non-modeled transaction types (PAYMENT, CASH_IN, DEBIT)
    non_model_default_decision: str = "APPROVE"
    non_model_large_amount_threshold: float = 500000.0  # Large transfer triggers review

    # Engine metadata
    engine_version: str = "1.0.0"
    model_versions: Dict[str, str] = field(default_factory=lambda: {
        "xgboost": "xgboost_fraud_model.json",
        "logistic": "logistic_baseline.joblib",
        "isolation_forest": "isolation_forest.joblib",
        "autoencoder": "autoencoder.pt",
    })

    def __post_init__(self):
        # Validate weights sum to 1.0 within floating point tolerance
        total_weight = (
            self.xgboost_weight
            + self.autoencoder_weight
            + self.isolation_weight
            + self.logistic_weight
        )
        if abs(total_weight - 1.0) > 1e-4:
            raise ValueError(f"Ensemble weights must sum to 1.0, got {total_weight:.4f}")

        # Validate individual weights are in [0, 1]
        for name, w in [
            ("xgboost_weight", self.xgboost_weight),
            ("autoencoder_weight", self.autoencoder_weight),
            ("isolation_weight", self.isolation_weight),
            ("logistic_weight", self.logistic_weight),
        ]:
            if not (0.0 <= w <= 1.0):
                raise ValueError(f"Weight {name} must be in [0.0, 1.0], got {w}")

        # Validate threshold hierarchy
        if not (0.0 < self.threshold_review < self.threshold_block < 100.0):
            raise ValueError(
                f"Thresholds must satisfy 0 < review ({self.threshold_review}) < block ({self.threshold_block}) < 100"
            )
