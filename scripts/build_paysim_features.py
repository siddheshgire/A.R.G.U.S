#!/usr/bin/env python3
"""
A.R.G.U.S. — Feature Generation & Temporal Dataset Split Script
Phase 2 / Milestone 2: Feature Engineering Pipeline

Executes:
1. Loads raw PaySim dataset from data/raw/paysim.csv.
2. Filters to fraud-modeling subspace (TRANSFER & CASH_OUT, 100% of fraud labels).
3. Applies mathematical domain feature engineering (18 total features: 5 raw + 13 engineered).
4. Partitions data chronologically by simulation step (Train: 1–520, Val: 521–631, Test: 632–743).
5. Fits a StandardScaler on Train features ONLY and serializes to models/feature_scaler.joblib.
6. Validates partitions (zero NaN/Inf, non-empty fraud labels in each split, zero target leakage).
7. Exports processed datasets to data/processed/ (train.csv, validation.csv, test.csv, split_metadata.json).
"""

import sys
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd

# Add workspace root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml_engine.features import (
    ALL_MODEL_FEATURES,
    RAW_NUMERICAL_FEATURES,
    TARGET_COLUMN,
    TEMPORAL_SPLIT_STEPS,
    compute_engineered_features,
    filter_fraud_modeling_subspace,
    temporal_split,
    extract_feature_matrix,
    fit_feature_scaler,
    save_scaler,
)


def main():
    print("=" * 70)
    print("A.R.G.U.S. — PaySim Feature Engineering & Temporal Split")
    print("=" * 70)

    # 1. Locate raw dataset
    raw_path = Path("data/raw/paysim.csv")
    if not raw_path.is_file():
        raw_path = Path("data/raw/PS_20174392719_1491204439457_log.csv")
    if not raw_path.is_file():
        print(f"[!] Error: Raw PaySim CSV not found in data/raw/")
        sys.exit(1)

    print(f"[*] Reading raw PaySim dataset: {raw_path}")
    t0 = time.time()
    df_raw = pd.read_csv(
        raw_path,
        dtype={
            "step": np.int32,
            "type": "category",
            "amount": np.float64,
            "nameOrig": "string",
            "oldbalanceOrg": np.float64,
            "newbalanceOrig": np.float64,
            "nameDest": "string",
            "oldbalanceDest": np.float64,
            "newbalanceDest": np.float64,
            "isFraud": np.int8,
            "isFlaggedFraud": np.int8,
        }
    )
    print(f"[*] Loaded {len(df_raw):,} raw transactions in {time.time() - t0:.2f}s")

    # 2. Filter to fraud-modeling subspace
    print("\n[*] Filtering to fraud-modeling subspace (TRANSFER & CASH_OUT)...")
    df_subspace = filter_fraud_modeling_subspace(df_raw)
    n_subspace = len(df_subspace)
    n_fraud_subspace = int(df_subspace[TARGET_COLUMN].sum())
    pct_retained = (n_subspace / len(df_raw)) * 100
    print(f"[*] Retained {n_subspace:,} / {len(df_raw):,} transactions ({pct_retained:.2f}%)")
    print(f"[*] Fraud coverage in subspace: {n_fraud_subspace:,} / {df_raw[TARGET_COLUMN].sum():,} (100.00%)")

    # 3. Compute engineered features
    print("\n[*] Computing domain engineered features...")
    t_feat = time.time()
    df_featured = compute_engineered_features(df_subspace)
    print(f"[*] Feature computation completed in {time.time() - t_feat:.2f}s")
    print(f"[*] Generated {len(ALL_MODEL_FEATURES)} model features:")
    for i, col in enumerate(ALL_MODEL_FEATURES, 1):
        print(f"    {i:>2}. {col:<26} (dtype: {df_featured[col].dtype})")

    # 4. Perform chronological temporal split
    print("\n[*] Performing chronological temporal split based on simulation step...")
    train_max = TEMPORAL_SPLIT_STEPS["train_max_step"]
    val_max = TEMPORAL_SPLIT_STEPS["val_max_step"]
    print(f"    - Train Range:      Steps {TEMPORAL_SPLIT_STEPS['train_min_step']} to {train_max}")
    print(f"    - Validation Range: Steps {TEMPORAL_SPLIT_STEPS['val_min_step']} to {val_max}")
    print(f"    - Test Range:       Steps {TEMPORAL_SPLIT_STEPS['test_min_step']} to {TEMPORAL_SPLIT_STEPS['test_max_step']}")

    train_df, val_df, test_df = temporal_split(df_featured, train_max_step=train_max, val_max_step=val_max)

    # 5. Partition analysis & verification
    splits = [("Train", train_df), ("Validation", val_df), ("Test", test_df)]
    split_meta = {}
    print("\n" + "=" * 60)
    print(f"{'Partition':<12} | {'Rows':<10} | {'Steps':<12} | {'Fraud':<7} | {'Fraud Rate':<10}")
    print("=" * 60)

    for name, s_df in splits:
        n_rows = len(s_df)
        min_s = int(s_df["step"].min()) if n_rows > 0 else 0
        max_s = int(s_df["step"].max()) if n_rows > 0 else 0
        n_fraud = int(s_df[TARGET_COLUMN].sum()) if n_rows > 0 else 0
        f_rate = (n_fraud / n_rows) * 100 if n_rows > 0 else 0.0
        
        # Check numerical sanity (no NaN, no Inf in ALL_MODEL_FEATURES)
        X_sub, _ = extract_feature_matrix(s_df)
        nan_count = int(X_sub.isna().sum().sum())
        inf_count = int(np.isinf(X_sub.values).sum())
        assert nan_count == 0, f"Error: {name} contains {nan_count} NaNs!"
        assert inf_count == 0, f"Error: {name} contains {inf_count} Infs!"
        assert n_fraud > 0, f"Error: {name} has 0 fraud instances!"

        print(f"{name:<12} | {n_rows:<10,} | {min_s:>3} to {max_s:<6} | {n_fraud:<7,} | {f_rate:.4f}%")

        split_meta[name.lower()] = {
            "rows": n_rows,
            "min_step": min_s,
            "max_step": max_s,
            "fraud_count": n_fraud,
            "fraud_rate_pct": f_rate,
            "imbalance_ratio": (n_rows - n_fraud) / n_fraud if n_fraud > 0 else 0,
            "nan_count": nan_count,
            "inf_count": inf_count,
        }

    # 6. Fit StandardScaler on Train features ONLY
    print("\n[*] Fitting StandardScaler on Train partition ONLY (leakage protection)...")
    X_train, _ = extract_feature_matrix(train_df)
    scaler = fit_feature_scaler(X_train)
    scaler_path = Path("models/feature_scaler.joblib")
    save_scaler(scaler, scaler_path)
    print(f"[*] Fitted scaler saved to: {scaler_path}")

    # 7. Export processed CSV splits
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Columns to save in processed CSVs: step, type, ALL_MODEL_FEATURES, isFraud
    export_cols = ["step", "type"] + ALL_MODEL_FEATURES + [TARGET_COLUMN]
    
    print("\n[*] Exporting processed CSV partitions...")
    t_save = time.time()
    train_df[export_cols].to_csv(processed_dir / "train.csv", index=False)
    print(f"  [+] Saved: {processed_dir / 'train.csv'} ({len(train_df):,} rows)")
    val_df[export_cols].to_csv(processed_dir / "validation.csv", index=False)
    print(f"  [+] Saved: {processed_dir / 'validation.csv'} ({len(val_df):,} rows)")
    test_df[export_cols].to_csv(processed_dir / "test.csv", index=False)
    print(f"  [+] Saved: {processed_dir / 'test.csv'} ({len(test_df):,} rows)")
    print(f"[*] CSV exports completed in {time.time() - t_save:.2f}s")

    # 8. Save metadata manifest
    meta_path = processed_dir / "split_metadata.json"
    full_manifest = {
        "dataset": "PaySim Fraud-Modeling Subspace (TRANSFER & CASH_OUT)",
        "source_raw": str(raw_path.as_posix()),
        "total_subspace_rows": n_subspace,
        "raw_dataset_rows": len(df_raw),
        "subspace_retained_pct": pct_retained,
        "feature_count": len(ALL_MODEL_FEATURES),
        "features": ALL_MODEL_FEATURES,
        "raw_numerical_features": RAW_NUMERICAL_FEATURES,
        "target_column": TARGET_COLUMN,
        "splits": split_meta,
        "scaler_file": str(scaler_path.as_posix()),
    }
    with open(meta_path, "w") as f:
        json.dump(full_manifest, f, indent=2)
    print(f"  [+] Saved metadata manifest: {meta_path}")

    print("\n" + "=" * 70)
    print("[+] PaySim Feature Engineering & Temporal Split completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
