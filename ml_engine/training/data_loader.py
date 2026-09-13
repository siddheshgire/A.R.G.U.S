"""
A.R.G.U.S. — Training Data Loader & Preprocessing Utilities
Loads processed temporal splits, enforces feature integrity, applies pre-fitted scaling,
and computes dynamic class weighting.
"""

from pathlib import Path
from typing import Tuple, Dict, Optional, Union
import numpy as np
import pandas as pd
import joblib

from ml_engine.features import (
    ALL_MODEL_FEATURES,
    TARGET_COLUMN,
    load_scaler,
)


def load_processed_split(
    split_name: str,
    data_dir: Union[str, Path] = "data/processed",
    scaled: bool = False,
    scaler_path: Union[str, Path] = "models/feature_scaler.joblib",
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Loads a single processed dataset partition (train, validation, or test),
    separating features X and target y with strict leakage guards.
    
    Parameters
    ----------
    split_name : str
        Partition name: 'train', 'validation', or 'test'.
    data_dir : Union[str, Path]
        Directory containing processed CSV files.
    scaled : bool
        If True, applies the pre-fitted StandardScaler to X. Does NOT fit or refit!
    scaler_path : Union[str, Path]
        Path to the serialized StandardScaler artifact.
        
    Returns
    -------
    Tuple[pd.DataFrame, pd.Series]
        (X, y) where X contains exactly ALL_MODEL_FEATURES in canonical order,
        and y contains the binary isFraud target.
    """
    csv_file = Path(data_dir) / f"{split_name}.csv"
    if not csv_file.is_file():
        raise FileNotFoundError(f"Processed dataset split not found: {csv_file}")

    # Read CSV
    df = pd.read_csv(csv_file)

    # 1. Enforce target column existence
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' not found in {csv_file}")

    y = df[TARGET_COLUMN].astype(np.int8)

    # 2. Strict feature isolation checks
    assert TARGET_COLUMN not in ALL_MODEL_FEATURES, "CRITICAL: isFraud cannot be in model features!"
    assert "isFlaggedFraud" not in df.columns or "isFlaggedFraud" not in ALL_MODEL_FEATURES, \
        "CRITICAL: isFlaggedFraud detected in features!"
    assert "nameOrig" not in ALL_MODEL_FEATURES, "CRITICAL: nameOrig cannot be in model features!"
    assert "nameDest" not in ALL_MODEL_FEATURES, "CRITICAL: nameDest cannot be in model features!"

    # 3. Extract X in strictly guaranteed canonical order
    missing_cols = [c for c in ALL_MODEL_FEATURES if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required feature columns in {split_name}: {missing_cols}")

    X = df[ALL_MODEL_FEATURES].copy()

    # 4. Check for NaNs or Infinite values
    nan_count = int(X.isna().sum().sum())
    inf_count = int(np.isinf(X.to_numpy()).sum())
    if nan_count > 0 or inf_count > 0:
        raise ValueError(f"Invalid values in {split_name}: {nan_count} NaNs, {inf_count} Infs!")

    # 5. Optional scaling (using pre-fitted scaler ONLY)
    if scaled:
        scaler = load_scaler(scaler_path)
        X_scaled_arr = scaler.transform(X)
        X = pd.DataFrame(X_scaled_arr, columns=ALL_MODEL_FEATURES, index=X.index)

    return X, y


def load_all_splits(
    data_dir: Union[str, Path] = "data/processed",
    scaled: bool = False,
    scaler_path: Union[str, Path] = "models/feature_scaler.joblib",
) -> Dict[str, Tuple[pd.DataFrame, pd.Series]]:
    """
    Loads all three chronological partitions (train, validation, test) simultaneously.
    """
    splits = {}
    for name in ["train", "validation", "test"]:
        splits[name] = load_processed_split(
            split_name=name,
            data_dir=data_dir,
            scaled=scaled,
            scaler_path=scaler_path,
        )
    return splits


def compute_class_imbalance_ratio(y: Union[pd.Series, np.ndarray]) -> float:
    """
    Dynamically computes negative-to-positive class ratio (n_neg / n_pos)
    from training target vector for use in scale_pos_weight.
    
    Parameters
    ----------
    y : Union[pd.Series, np.ndarray]
        Ground truth binary target vector.
        
    Returns
    -------
    float
        Exact negative / positive class ratio.
    """
    arr = np.asarray(y)
    n_pos = np.sum(arr == 1)
    n_neg = np.sum(arr == 0)

    if n_pos == 0:
        raise ValueError("Cannot compute imbalance ratio: positive class count is 0!")

    return float(n_neg / n_pos)


def get_normal_training_data(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> pd.DataFrame:
    """
    Filters training features to legitimate transactions ONLY (y == 0).
    Required for unsupervised Deep Autoencoder anomaly detector training.
    """
    mask = (y_train == 0)
    return X_train[mask].copy()
