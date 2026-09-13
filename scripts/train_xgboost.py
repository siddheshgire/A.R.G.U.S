#!/usr/bin/env python3
"""
A.R.G.U.S. — Training Script: XGBoost Supervised Fraud Classifier
Trains gradient boosted trees on unscaled PaySim features with dynamic scale_pos_weight
and validation early stopping.
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml_engine.training import load_processed_split, compute_class_imbalance_ratio
from ml_engine.models import XGBoostFraudClassifier
from ml_engine.evaluation import (
    compute_classification_metrics,
    find_optimal_threshold,
    benchmark_inference_latency,
    format_metric_report,
)


def main():
    print("=" * 70)
    print("A.R.G.U.S. — Training: XGBoost Supervised Fraud Classifier")
    print("=" * 70)

    # 1. Load unscaled datasets (Tree models are invariant to monotonic scaling)
    print("\n[*] Loading unscaled training, validation, and test datasets...")
    t0 = time.time()
    X_train, y_train = load_processed_split("train", scaled=False)
    X_val, y_val = load_processed_split("validation", scaled=False)
    X_test, y_test = load_processed_split("test", scaled=False)
    print(f"[*] Loaded datasets in {time.time() - t0:.2f}s:")
    print(f"    - Train:      {len(X_train):,} samples (Fraud: {int(y_train.sum()):,})")
    print(f"    - Validation: {len(X_val):,} samples (Fraud: {int(y_val.sum()):,})")
    print(f"    - Test:       {len(X_test):,} samples (Fraud: {int(y_test.sum()):,})")

    # 2. Dynamically compute scale_pos_weight
    imbalance_ratio = compute_class_imbalance_ratio(y_train)
    print(f"\n[*] Training class ratio (n_neg / n_pos): {imbalance_ratio:.2f}")

    # 3. Initialize XGBoost model
    print("[*] Initializing XGBoostFraudClassifier (early_stopping_rounds=30, eval_metric='aucpr')...")
    model = XGBoostFraudClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=imbalance_ratio,
        random_state=42,
        eval_metric="aucpr",
        early_stopping_rounds=30,
    )

    # 4. Train model with early stopping on validation split
    print("\n[*] Training XGBoost with early stopping on validation split...")
    t_train = time.time()
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=True,
    )
    train_duration = time.time() - t_train
    print(f"[+] XGBoost training completed in {train_duration:.2f}s")

    # 5. Predict probabilities on Validation split
    print("\n[*] Evaluating on Validation partition...")
    val_probs = model.predict_proba(X_val)

    # Find optimal threshold for F1 on validation set
    val_opt_res = find_optimal_threshold(y_val, val_probs, metric="f1")
    chosen_threshold = val_opt_res["threshold"]
    print(f"[*] Optimal Validation Threshold (Max F1): {chosen_threshold:.4f}")
    print(format_metric_report(val_opt_res, "XGBoost", "Validation"))

    # 6. Evaluate on Test split using validation-chosen threshold
    print("\n[*] Evaluating on Test partition using validation-chosen threshold...")
    test_probs = model.predict_proba(X_test)
    test_res = compute_classification_metrics(y_test, test_probs, threshold=chosen_threshold)
    print(format_metric_report(test_res, "XGBoost", "Test"))

    # 7. Benchmark latency
    print("\n[*] Benchmarking inference latency...")
    latency_res = benchmark_inference_latency(model.predict_proba, X_val[:1000])
    print(f"[*] Batch Latency (1000 tx):     {latency_res['batch_latency_ms']:.2f} ms")
    print(f"[*] Single Sample Latency:       {latency_res['single_sample_latency_ms']:.4f} ms")

    # 8. Save model artifact and metadata
    model_path = Path("models/xgboost_fraud_model.json")
    meta_path = Path("models/xgboost_meta.json")
    print(f"\n[*] Saving native XGBoost model to: {model_path}")
    model.save_model(model_path)

    metadata = {
        "model_name": "XGBoost Supervised Fraud Classifier",
        "training_samples": len(X_train),
        "fraud_samples": int(y_train.sum()),
        "features": list(X_train.columns),
        "scale_pos_weight": round(imbalance_ratio, 2),
        "training_time_seconds": round(train_duration, 2),
        "chosen_threshold": round(chosen_threshold, 4),
        "validation_metrics": val_opt_res,
        "test_metrics": test_res,
        "latency": latency_res,
    }
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[+] Metadata saved to: {meta_path}")

    print("\n" + "=" * 70)
    print("[+] XGBoost training and evaluation completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
