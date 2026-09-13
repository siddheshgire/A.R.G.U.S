"""
A.R.G.U.S. — XGBoost Supervised Fraud Classifier
Primary supervised gradient boosted decision tree model with dynamic class weighting.
"""

from pathlib import Path
from typing import Optional, Union, Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from xgboost import XGBClassifier


class XGBoostFraudClassifier:
    """
    Supervised gradient boosting classifier for tabular fraud detection.
    Operates on unscaled numerical features with scale_pos_weight for extreme class imbalance.
    """

    def __init__(
        self,
        n_estimators: int = 300,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        scale_pos_weight: Optional[float] = None,
        random_state: int = 42,
        eval_metric: str = "aucpr",
        early_stopping_rounds: Optional[int] = 30,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.scale_pos_weight = scale_pos_weight
        self.random_state = random_state
        self.eval_metric = eval_metric
        self.early_stopping_rounds = early_stopping_rounds

        self.model = XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            scale_pos_weight=self.scale_pos_weight if self.scale_pos_weight else 1.0,
            random_state=self.random_state,
            eval_metric=self.eval_metric,
            early_stopping_rounds=self.early_stopping_rounds,
            tree_method="hist",
            n_jobs=-1,
        )
        self.is_fitted = False

    def fit(
        self,
        X_train: pd.DataFrame | np.ndarray,
        y_train: pd.Series | np.ndarray,
        eval_set: Optional[List[Tuple[pd.DataFrame | np.ndarray, pd.Series | np.ndarray]]] = None,
        verbose: bool = True,
    ) -> "XGBoostFraudClassifier":
        """
        Fits XGBoost classifier. If scale_pos_weight was not set, dynamically computes it.
        """
        if self.scale_pos_weight is None:
            n_pos = np.sum(np.asarray(y_train) == 1)
            n_neg = np.sum(np.asarray(y_train) == 0)
            self.scale_pos_weight = float(n_neg / n_pos) if n_pos > 0 else 1.0
            self.model.set_params(scale_pos_weight=self.scale_pos_weight)

        self.model.fit(
            X_train,
            y_train,
            eval_set=eval_set,
            verbose=verbose,
        )
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

    def save_model(self, path: Union[str, Path]) -> None:
        """Saves model in native XGBoost JSON format."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(p))

    def load_model(self, path: Union[str, Path]) -> None:
        """Loads model from native XGBoost JSON format."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Model file not found at: {p}")
        self.model.load_model(str(p))
        self.is_fitted = True
