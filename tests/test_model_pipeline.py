"""
Unit and Integration Tests for A.R.G.U.S. Model Development Pipeline
Tests model wrappers, metric evaluations, PyTorch Autoencoder forward pass, and data loaders.
"""

import pytest
import numpy as np
import pandas as pd
import torch

from ml_engine.features import ALL_MODEL_FEATURES, TARGET_COLUMN
from ml_engine.training import (
    load_processed_split,
    compute_class_imbalance_ratio,
    get_normal_training_data,
)
from ml_engine.evaluation import (
    compute_classification_metrics,
    find_optimal_threshold,
    benchmark_inference_latency,
)
from ml_engine.models import (
    LogisticRegressionBaseline,
    XGBoostFraudClassifier,
    IsolationForestAnomalyDetector,
    DeepAutoencoder,
    AutoencoderAnomalyDetector,
)


def test_model_imports_and_instantiation():
    """Verifies all four models can be instantiated with default configurations."""
    lr = LogisticRegressionBaseline()
    assert lr.model is not None

    xgb = XGBoostFraudClassifier()
    assert xgb.model is not None

    ifo = IsolationForestAnomalyDetector()
    assert ifo.model is not None

    ae = AutoencoderAnomalyDetector(input_dim=18, latent_dim=16)
    assert ae.model is not None
    assert isinstance(ae.model, DeepAutoencoder)


def test_evaluation_metrics_computation():
    """Verifies metric computation logic on synthetic labels and predictions."""
    y_true = np.array([0, 0, 0, 0, 1, 1, 0, 1])
    y_scores = np.array([0.1, 0.2, 0.15, 0.3, 0.85, 0.9, 0.4, 0.75])

    metrics = compute_classification_metrics(y_true, y_scores, threshold=0.5)

    assert "pr_auc" in metrics
    assert "roc_auc" in metrics
    assert "f1" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "fpr" in metrics

    assert 0.0 <= metrics["pr_auc"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert metrics["recall"] == 1.0  # All 3 frauds scored >= 0.75 > 0.5
    assert metrics["precision"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["fpr"] == 0.0


def test_find_optimal_threshold():
    """Verifies threshold optimization logic."""
    y_true = np.array([0, 0, 0, 1, 1])
    y_scores = np.array([0.1, 0.3, 0.4, 0.6, 0.9])

    res = find_optimal_threshold(y_true, y_scores, metric="f1")
    assert "threshold" in res
    assert 0.4 < res["threshold"] <= 0.6
    assert res["f1"] == 1.0


def test_autoencoder_architecture_forward_pass():
    """Verifies that PyTorch DeepAutoencoder handles tensor shape (B, 18) correctly."""
    batch_size = 8
    input_dim = 18
    latent_dim = 16

    model = DeepAutoencoder(input_dim=input_dim, latent_dim=latent_dim)
    model.eval()

    dummy_input = torch.randn(batch_size, input_dim)
    with torch.no_grad():
        output = model(dummy_input)

    assert output.shape == (batch_size, input_dim), f"Expected shape {(batch_size, input_dim)}, got {output.shape}"


def test_autoencoder_anomaly_scoring():
    """Verifies per-sample reconstruction error and calibration."""
    detector = AutoencoderAnomalyDetector(input_dim=18, latent_dim=16)
    dummy_x = np.random.randn(20, 18).astype(np.float32)

    # Reconstruction error
    errors = detector.predict_reconstruction_error(dummy_x, batch_size=10)
    assert len(errors) == 20
    assert (errors >= 0.0).all()

    # Score calibration
    detector.calibrate_anomaly_scores(errors[:10])
    assert detector.error_mean_ is not None
    assert detector.error_p95_ is not None

    # Anomaly scores
    scores = detector.predict_anomaly_score(dummy_x, batch_size=10)
    assert len(scores) == 20
    assert (scores >= 0.0).all() and (scores <= 1.0).all()


def test_class_imbalance_ratio_calculation():
    """Verifies class imbalance calculation."""
    y = np.array([0] * 900 + [1] * 100)
    ratio = compute_class_imbalance_ratio(y)
    assert ratio == 9.0


def test_data_loader_processed_validation():
    """Verifies that load_processed_split loads the actual processed validation set with zero leaks."""
    X_val, y_val = load_processed_split("validation", scaled=False)
    assert len(X_val) == 78701
    assert len(y_val) == 78701
    assert list(X_val.columns) == ALL_MODEL_FEATURES
    assert TARGET_COLUMN not in X_val.columns
    assert "isFlaggedFraud" not in X_val.columns
    assert not X_val.isna().any().any()
