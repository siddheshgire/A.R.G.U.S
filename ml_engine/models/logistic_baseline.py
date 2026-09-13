"""
A.R.G.U.S. — Logistic Regression Supervised Baseline
Serves as the linear benchmark model for fraud probability estimation.
"""

from pathlib import Path
from typing import Optional, Union, Dict, Any
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
import joblib


class LogisticRegressionBaseline:
    """
    Supervised linear baseline classifier for transaction fraud prediction.
    Utilizes scaled numerical features and balanced class weighting.
    """

    def __init__(
        self,
        C: float = 1.0,
        max_iter: int = 1000,
        class_weight: Union[str, Dict[int, float]] = "balanced",
        solver: str = "lbfgs",
        random_state: int = 42,
    ):
        self.C = C
        self.max_iter = max_iter
        self.class_weight = class_weight
        self.solver = solver
        self.random_state = random_state
        self.model = LogisticRegression(
            C=self.C,
            max_iter=self.max_iter,
            class_weight=self.class_weight,
            solver=self.solver,
            random_state=self.random_state,
        )
        self.is_fitted = False

    def fit(self, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray) -> "LogisticRegressionBaseline":
        """Fits logistic regression model on training features and labels."""
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Returns predicted fraud probability P(isFraud = 1 | X)."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict_proba.")
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: pd.DataFrame | np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Returns binary predictions at the specified decision threshold."""
        probs = self.predict_proba(X)
        return (probs >= threshold).astype(int)

    def save(self, path: Union[str, Path]) -> None:
        """Serializes model artifact to disk."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, p)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "LogisticRegressionBaseline":
        """Loads serialized model artifact from disk."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Model artifact not found at: {p}")
        return joblib.load(p)
