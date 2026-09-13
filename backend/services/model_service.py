"""
A.R.G.U.S. — Pretrained Model Inference & Artifact Manager
Loads serialized ML/DL models once during application startup and executes inference.
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import pandas as pd
import numpy as np

from ml_engine.features import ALL_MODEL_FEATURES, load_scaler
from ml_engine.models import (
    LogisticRegressionBaseline,
    XGBoostFraudClassifier,
    IsolationForestAnomalyDetector,
    AutoencoderAnomalyDetector,
)
from ml_engine.risk import RiskSignals


class ModelManager:
    """
    Thread-safe container for pretrained ML/DL inference components.
    Eliminates redundant disk I/O by keeping fitted models in memory.
    """

    def __init__(self, models_dir: Path | str = "models"):
        self.models_dir = Path(models_dir)
        self.scaler = None
        self.xgb_model = None
        self.lr_model = None
        self.if_model = None
        self.ae_model = None
        self._is_loaded: bool = False

    @property
    def is_ready(self) -> bool:
        """Returns True if all required artifacts are loaded and ready for inference."""
        return (
            self._is_loaded
            and self.scaler is not None
            and self.xgb_model is not None
            and self.lr_model is not None
            and self.if_model is not None
            and self.ae_model is not None
        )

    def load_artifacts(self) -> None:
        """
        Loads all 4 model checkpoints and the feature scaler from disk.
        Does NOT perform any training, fitting, or dataset loading.
        """
        scaler_path = self.models_dir / "feature_scaler.joblib"
        xgb_path = self.models_dir / "xgboost_fraud_model.json"
        lr_path = self.models_dir / "logistic_baseline.joblib"
        if_path = self.models_dir / "isolation_forest.joblib"
        ae_path = self.models_dir / "autoencoder.pt"

        # 1. Load Scaler
        if not scaler_path.is_file():
            raise FileNotFoundError(f"Feature scaler artifact not found at {scaler_path}")
        self.scaler = load_scaler(scaler_path)

        # 2. Load XGBoost (Unscaled features)
        if not xgb_path.is_file():
            raise FileNotFoundError(f"XGBoost artifact not found at {xgb_path}")
        self.xgb_model = XGBoostFraudClassifier()
        self.xgb_model.load_model(xgb_path)

        # 3. Load Logistic Regression (Scaled features)
        if not lr_path.is_file():
            raise FileNotFoundError(f"Logistic Regression artifact not found at {lr_path}")
        self.lr_model = LogisticRegressionBaseline.load(lr_path)

        # 4. Load Isolation Forest (Unscaled features)
        if not if_path.is_file():
            raise FileNotFoundError(f"Isolation Forest artifact not found at {if_path}")
        self.if_model = IsolationForestAnomalyDetector.load(if_path)

        # 5. Load Deep Autoencoder (Scaled features)
        if not ae_path.is_file():
            raise FileNotFoundError(f"Deep Autoencoder artifact not found at {ae_path}")
        self.ae_model = AutoencoderAnomalyDetector.load(ae_path, device="cpu")

        self._is_loaded = True

    def predict_signals(
        self,
        features_df: pd.DataFrame,
    ) -> Tuple[RiskSignals, List[Dict[str, Any]]]:
        """
        Executes inference across the 4 models for the given feature vector.

        Parameters
        ----------
        features_df : pd.DataFrame
            DataFrame containing exactly the 18 columns in ALL_MODEL_FEATURES.

        Returns
        -------
        Tuple[RiskSignals, List[Dict[str, Any]]]
            Standardized RiskSignals domain object and model results metadata for DB storage.
        """
        if not self.is_ready:
            raise RuntimeError("ModelManager has not loaded inference artifacts. Call load_artifacts() first.")

        # Ensure correct column ordering
        X_unscaled = features_df[ALL_MODEL_FEATURES].copy()

        # Generate scaled representation for LR and Autoencoder
        X_scaled_arr = self.scaler.transform(X_unscaled)
        X_scaled_df = pd.DataFrame(X_scaled_arr, columns=ALL_MODEL_FEATURES)

        model_results_meta = []

        # 1. XGBoost (Unscaled features)
        t0 = time.perf_counter()
        xgb_prob = float(self.xgb_model.predict_proba(X_unscaled)[0])
        dt_xgb = round((time.perf_counter() - t0) * 1000, 3)
        xgb_prob = float(np.clip(xgb_prob, 0.0, 1.0))
        model_results_meta.append({
            "model_name": "XGBoost",
            "raw_output": xgb_prob,
            "normalized_signal": xgb_prob,
            "model_version": "1.0.0",
            "inference_time_ms": dt_xgb,
        })

        # 2. Logistic Regression (Scaled features)
        t0 = time.perf_counter()
        lr_prob = float(self.lr_model.predict_proba(X_scaled_df)[0])
        dt_lr = round((time.perf_counter() - t0) * 1000, 3)
        lr_prob = float(np.clip(lr_prob, 0.0, 1.0))
        model_results_meta.append({
            "model_name": "LogisticRegression",
            "raw_output": lr_prob,
            "normalized_signal": lr_prob,
            "model_version": "1.0.0",
            "inference_time_ms": dt_lr,
        })

        # 3. Isolation Forest (Unscaled features)
        t0 = time.perf_counter()
        if_score = float(self.if_model.predict_anomaly_score(X_unscaled)[0])
        dt_if = round((time.perf_counter() - t0) * 1000, 3)
        if_score = float(np.clip(if_score, 0.0, 1.0))
        model_results_meta.append({
            "model_name": "IsolationForest",
            "raw_output": if_score,
            "normalized_signal": if_score,
            "model_version": "1.0.0",
            "inference_time_ms": dt_if,
        })

        # 4. Deep Autoencoder (Scaled features)
        t0 = time.perf_counter()
        ae_score = float(self.ae_model.predict_anomaly_score(X_scaled_df)[0])
        dt_ae = round((time.perf_counter() - t0) * 1000, 3)
        ae_score = float(np.clip(ae_score, 0.0, 1.0))
        model_results_meta.append({
            "model_name": "DeepAutoencoder",
            "raw_output": ae_score,
            "normalized_signal": ae_score,
            "model_version": "1.0.0",
            "inference_time_ms": dt_ae,
        })

        signals = RiskSignals(
            xgboost_score=xgb_prob,
            logistic_score=lr_prob,
            isolation_score=if_score,
            autoencoder_score=ae_score,
        )

        return signals, model_results_meta
