"""
A.R.G.U.S. — Normalized Risk Signals Representation
Enforces consistent [0.0, 1.0] scaling across supervised and unsupervised model outputs.
"""

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np


@dataclass(frozen=True)
class RiskSignals:
    """
    Standardized internal representation of model-generated risk signals.
    All scores are normalized continuous values in [0.0, 1.0] where 1.0 = maximum risk.
    """
    xgboost_score: float
    logistic_score: float
    isolation_score: float
    autoencoder_score: float

    def __post_init__(self):
        # Validate values are finite numbers
        for name, val in [
            ("xgboost_score", self.xgboost_score),
            ("logistic_score", self.logistic_score),
            ("isolation_score", self.isolation_score),
            ("autoencoder_score", self.autoencoder_score),
        ]:
            if not np.isfinite(val):
                raise ValueError(f"Signal {name} must be a finite float, got {val}")
            if not (0.0 <= val <= 1.0):
                # Allow tiny numerical epsilon due to floating point precision
                if -1e-5 <= val <= 1.0 + 1e-5:
                    object.__setattr__(self, name, float(np.clip(val, 0.0, 1.0)))
                else:
                    raise ValueError(f"Signal {name} must be in range [0.0, 1.0], got {val}")

    def to_dict(self) -> Dict[str, float]:
        return {
            "xgboost_score": round(self.xgboost_score, 4),
            "logistic_score": round(self.logistic_score, 4),
            "isolation_score": round(self.isolation_score, 4),
            "autoencoder_score": round(self.autoencoder_score, 4),
        }
