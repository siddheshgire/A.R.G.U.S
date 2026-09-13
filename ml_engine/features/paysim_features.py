"""
A.R.G.U.S. — PaySim Feature Engineering & Temporal Splitting Pipeline
Implements mathematically stable, leakage-safe transformations for transaction data.
"""

from pathlib import Path
from typing import Tuple, List, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib

from .feature_config import (
    RAW_NUMERICAL_FEATURES,
    ENGINEERED_FEATURE_NAMES,
    ALL_MODEL_FEATURES,
    TARGET_COLUMN,
    TEMPORAL_SPLIT_STEPS,
    FRAUD_MODELING_TYPES,
)


def compute_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms a PaySim transaction DataFrame by adding 13 domain-engineered features.
    Guarantees numerical stability with zero NaN or Infinite values.
    
    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing PaySim transaction columns.
        
    Returns
    -------
    pd.DataFrame
        Copy of DataFrame with engineered features appended.
    """
    out = df.copy()

    # 1. Amount transformation: log1p ensures smooth handling of 0 amounts and compresses extreme skew
    amt_non_neg = np.maximum(out["amount"].to_numpy(dtype=np.float64), 0.0)
    out["log_amount"] = np.log1p(amt_non_neg)

    # 2. Transaction type indicators
    out["is_transfer"] = (out["type"] == "TRANSFER").astype(np.int8)
    out["is_cash_out"] = (out["type"] == "CASH_OUT").astype(np.int8)

    # 3. Temporal & Diurnal features (1 step = 1 hour)
    hour = (out["step"].to_numpy(dtype=np.int32) % 24)
    out["hour_of_day"] = hour.astype(np.int8)
    out["hour_sin"] = np.sin(2.0 * np.pi * hour / 24.0).astype(np.float32)
    out["hour_cos"] = np.cos(2.0 * np.pi * hour / 24.0).astype(np.float32)
    out["is_night_transaction"] = ((hour >= 1) & (hour <= 6)).astype(np.int8)

    # 4. Origin account balance consistency & liquidation
    old_orig = out["oldbalanceOrg"].to_numpy(dtype=np.float64)
    new_orig = out["newbalanceOrig"].to_numpy(dtype=np.float64)
    amt = out["amount"].to_numpy(dtype=np.float64)

    # Expected: newbalanceOrig + amount - oldbalanceOrg == 0 in balanced ledger
    orig_bal_err = new_orig + amt - old_orig
    out["orig_balance_error"] = np.nan_to_num(orig_bal_err, nan=0.0, posinf=0.0, neginf=0.0)

    # Proportion of sender account drained (+1.0 epsilon avoids division by zero)
    orig_drain = amt / (old_orig + 1.0)
    out["orig_drain_ratio"] = np.clip(np.nan_to_num(orig_drain, nan=0.0, posinf=1e6, neginf=0.0), 0.0, 1e6)

    # Complete liquidation flag
    out["is_full_liquidation"] = ((old_orig > 0.0) & (new_orig == 0.0)).astype(np.int8)

    # 5. Destination account balance consistency & anomalies
    old_dest = out["oldbalanceDest"].to_numpy(dtype=np.float64)
    new_dest = out["newbalanceDest"].to_numpy(dtype=np.float64)

    # Expected: oldbalanceDest + amount - newbalanceDest == 0 in balanced ledger
    dest_bal_err = old_dest + amt - new_dest
    out["dest_balance_error"] = np.nan_to_num(dest_bal_err, nan=0.0, posinf=0.0, neginf=0.0)

    # Destination drain ratio (+1.0 epsilon avoids division by zero)
    dest_drain = amt / (new_dest + 1.0)
    out["dest_drain_ratio"] = np.clip(np.nan_to_num(dest_drain, nan=0.0, posinf=1e6, neginf=0.0), 0.0, 1e6)

    # Mule account artifact: recipient starting and ending balance is zero despite money received
    out["dest_zero_balance_anomaly"] = (
        (old_dest == 0.0) & (new_dest == 0.0) & (amt > 0.0)
    ).astype(np.int8)

    return out


def filter_fraud_modeling_subspace(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters transactions to TRANSFER and CASH_OUT categories where 100% of PaySim fraud resides.
    
    Parameters
    ----------
    df : pd.DataFrame
        Transaction DataFrame.
        
    Returns
    -------
    pd.DataFrame
        Filtered DataFrame containing only high-risk transaction types.
    """
    return df[df["type"].isin(FRAUD_MODELING_TYPES)].copy()


def temporal_split(
    df: pd.DataFrame,
    train_max_step: int = TEMPORAL_SPLIT_STEPS["train_max_step"],
    val_max_step: int = TEMPORAL_SPLIT_STEPS["val_max_step"],
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Performs strict chronological dataset partitioning based on the 'step' column.
    Guarantees no future leakage into training partitions.
    
    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing the 'step' column.
    train_max_step : int
        Maximum step included in the training partition (default: 520, ~70%).
    val_max_step : int
        Maximum step included in the validation partition (default: 631, ~15%).
        
    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        (train_df, val_df, test_df)
    """
    train_mask = df["step"] <= train_max_step
    val_mask = (df["step"] > train_max_step) & (df["step"] <= val_max_step)
    test_mask = df["step"] > val_max_step

    train_df = df[train_mask].copy()
    val_df = df[val_mask].copy()
    test_df = df[test_mask].copy()

    return train_df, val_df, test_df


def extract_feature_matrix(
    df: pd.DataFrame,
    feature_names: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    """
    Extracts the ML feature matrix X and optional target series y from a DataFrame.
    Guarantees that target labels and excluded columns are NEVER present in X.
    
    Parameters
    ----------
    df : pd.DataFrame
        Feature-engineered DataFrame.
    feature_names : Optional[List[str]]
        List of feature column names to extract (defaults to ALL_MODEL_FEATURES).
        
    Returns
    -------
    Tuple[pd.DataFrame, Optional[pd.Series]]
        (X, y)
    """
    if feature_names is None:
        feature_names = ALL_MODEL_FEATURES

    # Strictly enforce that target and leaked columns cannot be in X
    assert TARGET_COLUMN not in feature_names, "CRITICAL ERROR: isFraud cannot be in feature matrix X!"
    assert "isFlaggedFraud" not in feature_names, "CRITICAL ERROR: isFlaggedFraud cannot be in feature matrix X!"
    assert "nameOrig" not in feature_names, "CRITICAL ERROR: nameOrig cannot be in feature matrix X!"
    assert "nameDest" not in feature_names, "CRITICAL ERROR: nameDest cannot be in feature matrix X!"

    X = df[feature_names].copy()
    y = df[TARGET_COLUMN].copy() if TARGET_COLUMN in df.columns else None

    return X, y


def fit_feature_scaler(X_train: pd.DataFrame | np.ndarray) -> StandardScaler:
    """
    Fits a standard scaler ONLY on training data.
    Never exposes validation or test data to the scaler.
    """
    scaler = StandardScaler()
    scaler.fit(X_train)
    return scaler


def save_scaler(scaler: StandardScaler, path: Path | str) -> None:
    """Serializes fitted scaler to disk."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, p)


def load_scaler(path: Path | str) -> StandardScaler:
    """Loads serialized scaler from disk."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Scaler file not found at: {p}")
    return joblib.load(p)
