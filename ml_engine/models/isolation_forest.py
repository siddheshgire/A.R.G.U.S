"""
A.R.G.U.S. — Isolation Forest Unsupervised Anomaly Detector
Isolates anomalous transaction vectors in continuous feature space without using fraud labels.
"""

from pathlib import Path
from typing import Optional, Union, Dict, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib


class IsolationForestAnomalyDetector:
    """
    Unsupervised tree-based anomaly detector.
    Does NOT use fraud target labels during fitting.
    Transforms raw path-length scores into a calibrated continuous anomaly score [0, 1].
    """

    def __init__(
        self,
        n_estimators: int = 150,
        max_samples: Union[int, float] = 0.8,
        contamination: Union[str, float] = "auto",
        random_state: int = 42,
        n_jobs: int = -1,
    ):
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.random_state = random_state
        self.n_jobs = n_jobs

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        )
        self.score_min_ = None
        self.score_max_ = None
        self.is_fitted = False

    def fit(self, X: pd.DataFrame | np.ndarray) -> "IsolationForestAnomalyDetector":
        """
        Fits Isolation Forest on feature matrix X (unsupervised, no target y used).
        Computes training score range for min-max anomaly score normalization.
        """
        self.model.fit(X)
        # In scikit-learn, score_samples returns negative anomaly score (lower = more abnormal)
        # We invert so higher = more abnormal
        raw_train_scores = -self.model.score_samples(X)
        self.score_min_ = float(np.min(raw_train_scores))
        self.score_max_ = float(np.max(raw_train_scores))
        self.is_fitted = True
        return self

    def predict_anomaly_score(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """
        Returns normalized continuous anomaly scores in [0, 1] range.
        Higher score indicates greater anomaly / outlier deviation.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before computing anomaly scores.")
        raw_scores = -self.model.score_samples(X)
        denom = (self.score_max_ - self.score_min_) if (self.score_max_ > self.score_min_) else 1.0
        normalized_scores = np.clip((raw_scores - self.score_min_) / denom, 0.0, 1.0)
        return normalized_scores

    def predict(self, X: pd.DataFrame | np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Returns binary anomaly predictions (1 = anomaly, 0 = normal) at chosen threshold."""
        scores = self.predict_anomaly_score(X)
        return (scores >= threshold).astype(int)

    def save(self, path: Union[str, Path]) -> None:
        """Serializes fitted detector to disk."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, p)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "IsolationForestAnomalyDetector":
        """Loads serialized detector from disk."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Model artifact not found at: {p}")
        return joblib.load(p)
