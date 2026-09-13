"""
Unit and Integration Tests for A.R.G.U.S. Feature Pipeline
Tests numerical safety, absence of target leakage, and chronological splitting integrity.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from ml_engine.features import (
    ALL_MODEL_FEATURES,
    RAW_NUMERICAL_FEATURES,
    ENGINEERED_FEATURE_NAMES,
    TARGET_COLUMN,
    compute_engineered_features,
    filter_fraud_modeling_subspace,
    temporal_split,
    extract_feature_matrix,
    fit_feature_scaler,
    save_scaler,
    load_scaler,
)


@pytest.fixture
def synthetic_sample_df():
    """Generates a representative synthetic transaction DataFrame for testing edge cases."""
    data = {
        "step": [1, 5, 23, 24, 100, 520, 521, 631, 632, 743],
        "type": [
            "TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN", "DEBIT",
            "TRANSFER", "CASH_OUT", "TRANSFER", "CASH_OUT", "TRANSFER"
        ],
        "amount": [100.0, 50000.0, 25.0, 1000.0, 50.0, 0.0, 200000.0, 1500.0, 3000.0, 999999.0],
        "nameOrig": [f"C{i:09d}" for i in range(10)],
        "oldbalanceOrg": [100.0, 50000.0, 50.0, 0.0, 100.0, 0.0, 200000.0, 10000.0, 3000.0, 999999.0],
        "newbalanceOrig": [0.0, 0.0, 25.0, 1000.0, 50.0, 0.0, 0.0, 8500.0, 0.0, 0.0],
        "nameDest": [f"C{i+100:09d}" for i in range(10)],
        "oldbalanceDest": [0.0, 0.0, 0.0, 500.0, 10.0, 0.0, 0.0, 5000.0, 0.0, 0.0],
        "newbalanceDest": [0.0, 50000.0, 0.0, 1500.0, 60.0, 0.0, 0.0, 6500.0, 3000.0, 0.0],
        "isFraud": [1, 1, 0, 0, 0, 0, 1, 0, 1, 1],
        "isFlaggedFraud": [0, 0, 0, 0, 0, 0, 1, 0, 0, 1],
    }
    return pd.DataFrame(data)


def test_feature_engineering_completeness_and_safety(synthetic_sample_df):
    """Verifies that all 13 engineered features are computed without NaN or Inf values."""
    res = compute_engineered_features(synthetic_sample_df)

    # Check all expected engineered columns exist
    for col in ENGINEERED_FEATURE_NAMES:
        assert col in res.columns, f"Missing engineered feature: {col}"

    # Verify zero NaNs or Infs across all model features
    X, _ = extract_feature_matrix(res)
    assert not X.isna().any().any(), "Found unexpected NaN in feature matrix!"
    assert not np.isinf(X.values).any(), "Found unexpected Infinite value in feature matrix!"

    # Verify mathematical ranges
    assert (res["hour_of_day"] >= 0).all() and (res["hour_of_day"] <= 23).all()
    assert (res["hour_sin"] >= -1.0).all() and (res["hour_sin"] <= 1.0).all()
    assert (res["hour_cos"] >= -1.0).all() and (res["hour_cos"] <= 1.0).all()
    assert (res["log_amount"] >= 0.0).all()
    assert set(res["is_night_transaction"].unique()).issubset({0, 1})
    assert set(res["is_full_liquidation"].unique()).issubset({0, 1})
    assert set(res["dest_zero_balance_anomaly"].unique()).issubset({0, 1})


def test_subspace_filter(synthetic_sample_df):
    """Verifies that filter_fraud_modeling_subspace only keeps TRANSFER and CASH_OUT."""
    filtered = filter_fraud_modeling_subspace(synthetic_sample_df)
    assert set(filtered["type"].unique()).issubset({"TRANSFER", "CASH_OUT"})
    assert "PAYMENT" not in filtered["type"].values
    assert "CASH_IN" not in filtered["type"].values
    assert "DEBIT" not in filtered["type"].values


def test_temporal_split_integrity(synthetic_sample_df):
    """Verifies strict chronological boundaries and zero overlap across splits."""
    train_df, val_df, test_df = temporal_split(synthetic_sample_df, train_max_step=520, val_max_step=631)

    assert (train_df["step"] <= 520).all()
    assert ((val_df["step"] > 520) & (val_df["step"] <= 631)).all()
    assert (test_df["step"] > 631).all()

    # Verify disjoint partitions
    assert len(train_df) + len(val_df) + len(test_df) == len(synthetic_sample_df)


def test_leakage_prevention(synthetic_sample_df):
    """Strictly verifies that target and excluded leak variables cannot enter X."""
    featured = compute_engineered_features(synthetic_sample_df)
    X, y = extract_feature_matrix(featured)

    assert TARGET_COLUMN not in X.columns
    assert "isFlaggedFraud" not in X.columns
    assert "nameOrig" not in X.columns
    assert "nameDest" not in X.columns
    assert len(X.columns) == len(ALL_MODEL_FEATURES)
    assert y is not None
    assert len(y) == len(X)


def test_scaler_training_isolation(tmp_path):
    """Verifies that standard scaler fits on train data only and serializes cleanly."""
    np.random.seed(42)
    X_train = np.random.normal(loc=10.0, scale=2.0, size=(100, 5))
    scaler = fit_feature_scaler(X_train)

    assert np.allclose(scaler.mean_, 10.0, atol=0.5)

    scaler_file = tmp_path / "test_scaler.joblib"
    save_scaler(scaler, scaler_file)
    loaded = load_scaler(scaler_file)

    assert np.allclose(loaded.mean_, scaler.mean_)
