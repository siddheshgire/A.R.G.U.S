#!/usr/bin/env python3
"""
A.R.G.U.S. — Training Script: Logistic Regression Baseline
Executes supervised linear baseline training on scaled PaySim features.
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml_engine.training import load_processed_split
from ml_engine.models import LogisticRegressionBaseline
from ml_engine.evaluation import (
    compute_classification_metrics,
    find_optimal_threshold,
    benchmark_inference_latency,
    format_metric_report,
)


def main():
    print("=" * 70)
    print("A.R.G.U.S. — Training: Logistic Regression Baseline")
    print("=" * 70)

    # 1. Load scaled datasets (Logistic Regression requires scaled features)
    print("\n[*] Loading scaled training and validation datasets...")
    t0 = time.time()
    X_train, y_train = load_processed_split("train", scaled=True)
    X_val, y_val = load_processed_split("validation", scaled=True)
    X_test, y_test = load_processed_split("test", scaled=True)
    print(f"[*] Loaded datasets in {time.time() - t0:.2f}s:")
    print(f"    - Train:      {len(X_train):,} samples (Fraud: {int(y_train.sum()):,})")
    print(f"    - Validation: {len(X_val):,} samples (Fraud: {int(y_val.sum()):,})")
    print(f"    - Test:       {len(X_test):,} samples (Fraud: {int(y_test.sum()):,})")

    # 2. Instantiate model with balanced class weights
    print("\n[*] Initializing LogisticRegressionBaseline (class_weight='balanced')...")
    model = LogisticRegressionBaseline(
        C=1.0,
        max_iter=1000,
        class_weight="balanced",
        solver="lbfgs",
        random_state=42,
    )

    # 3. Fit model
    print("[*] Fitting Logistic Regression on training partition...")
    t_train = time.time()
    model.fit(X_train, y_train)
    train_duration = time.time() - t_train
    print(f"[+] Training completed in {train_duration:.2f}s")

    # 4. Predict probabilities on Validation split
    print("\n[*] Evaluating on Validation partition...")
    val_probs = model.predict_proba(X_val)

    # Find optimal threshold for F1 on validation set
    val_opt_res = find_optimal_threshold(y_val, val_probs, metric="f1")
    chosen_threshold = val_opt_res["threshold"]
    print(f"[*] Optimal Validation Threshold (Max F1): {chosen_threshold:.4f}")
    print(format_metric_report(val_opt_res, "Logistic Regression", "Validation"))

    # 5. Evaluate on Test split using validation-chosen threshold
    print("\n[*] Evaluating on Test partition using validation-chosen threshold...")
    test_probs = model.predict_proba(X_test)
    test_res = compute_classification_metrics(y_test, test_probs, threshold=chosen_threshold)
    print(format_metric_report(test_res, "Logistic Regression", "Test"))

    # 6. Benchmark latency
    print("\n[*] Benchmarking inference latency...")
    latency_res = benchmark_inference_latency(model.predict_proba, X_val[:1000])
    print(f"[*] Batch Latency (1000 tx):     {latency_res['batch_latency_ms']:.2f} ms")
    print(f"[*] Single Sample Latency:       {latency_res['single_sample_latency_ms']:.4f} ms")

    # 7. Save model artifact and metadata
    model_path = Path("models/logistic_baseline.joblib")
    meta_path = Path("models/logistic_baseline_meta.json")
    print(f"\n[*] Saving model artifact to: {model_path}")
    model.save(model_path)

    metadata = {
        "model_name": "Logistic Regression Baseline",
        "training_samples": len(X_train),
        "fraud_samples": int(y_train.sum()),
        "features": list(X_train.columns),
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
    print("[+] Logistic Regression Baseline training and evaluation completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
