"""
A.R.G.U.S. — ML & DL Model Architectures Package
Contains model wrappers for Logistic Regression, XGBoost, Isolation Forest, and Deep Autoencoder.
"""

from .logistic_baseline import LogisticRegressionBaseline
from .xgboost_model import XGBoostFraudClassifier
from .isolation_forest import IsolationForestAnomalyDetector
from .autoencoder import (
    DeepAutoencoder,
    AutoencoderAnomalyDetector,
    AutoencoderDataset,
)

__all__ = [
    "LogisticRegressionBaseline",
    "XGBoostFraudClassifier",
    "IsolationForestAnomalyDetector",
    "DeepAutoencoder",
    "AutoencoderAnomalyDetector",
    "AutoencoderDataset",
]
