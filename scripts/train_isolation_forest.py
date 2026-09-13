#!/usr/bin/env python3
"""
A.R.G.U.S. — Training Script: Isolation Forest Unsupervised Anomaly Detector
Fits isolation trees on unscaled features without target labels.
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml_engine.training import load_processed_split
from ml_engine.models import IsolationForestAnomalyDetector
from ml_engine.evaluation import (
    compute_classification_metrics,
    find_optimal_threshold,
    benchmark_inference_latency,
    format_metric_report,
)


def main():
    print("=" * 70)
    print("A.R.G.U.S. — Training: Isolation Forest Anomaly Detector")
    print("=" * 70)

    # 1. Load unscaled datasets (Tree-based model operates on unscaled features)
    print("\n[*] Loading unscaled training, validation, and test datasets...")
    t0 = time.time()
    X_train, y_train = load_processed_split("train", scaled=False)
    X_val, y_val = load_processed_split("validation", scaled=False)
    X_test, y_test = load_processed_split("test", scaled=False)
    print(f"[*] Loaded datasets in {time.time() - t0:.2f}s:")
    print(f"    - Train:      {len(X_train):,} samples (Unsupervised: labels NOT used during training)")
    print(f"    - Validation: {len(X_val):,} samples (Fraud: {int(y_val.sum()):,})")
    print(f"    - Test:       {len(X_test):,} samples (Fraud: {int(y_test.sum()):,})")

    # 2. Initialize Isolation Forest
    print("\n[*] Initializing IsolationForestAnomalyDetector (n_estimators=150, max_samples=0.8)...")
    model = IsolationForestAnomalyDetector(
        n_estimators=150,
        max_samples=0.8,
        contamination="auto",
        random_state=42,
        n_jobs=-1,
    )

    # 3. Fit detector on X_train ONLY (Unsupervised)
    print("[*] Fitting Isolation Forest on training features...")
    t_train = time.time()
    model.fit(X_train)
    train_duration = time.time() - t_train
    print(f"[+] Isolation Forest fitting completed in {train_duration:.2f}s")
    print(f"    - Raw Score Range: [{model.score_min_:.4f}, {model.score_max_:.4f}]")

    # 4. Predict continuous anomaly scores on Validation split
    print("\n[*] Evaluating anomaly scores on Validation partition...")
    val_scores = model.predict_anomaly_score(X_val)

    # Find optimal threshold for F1 on validation set
    val_opt_res = find_optimal_threshold(y_val, val_scores, metric="f1")
    chosen_threshold = val_opt_res["threshold"]
    print(f"[*] Optimal Validation Threshold (Max F1): {chosen_threshold:.4f}")
    print(format_metric_report(val_opt_res, "Isolation Forest", "Validation"))

    # 5. Evaluate on Test split using validation-chosen threshold
    print("\n[*] Evaluating on Test partition using validation-chosen threshold...")
    test_scores = model.predict_anomaly_score(X_test)
    test_res = compute_classification_metrics(y_test, test_scores, threshold=chosen_threshold)
    print(format_metric_report(test_res, "Isolation Forest", "Test"))

    # 6. Benchmark latency
    print("\n[*] Benchmarking inference latency...")
    latency_res = benchmark_inference_latency(model.predict_anomaly_score, X_val[:1000])
    print(f"[*] Batch Latency (1000 tx):     {latency_res['batch_latency_ms']:.2f} ms")
    print(f"[*] Single Sample Latency:       {latency_res['single_sample_latency_ms']:.4f} ms")

    # 7. Save model artifact and metadata
    model_path = Path("models/isolation_forest.joblib")
    meta_path = Path("models/isolation_forest_meta.json")
    print(f"\n[*] Saving model artifact to: {model_path}")
    model.save(model_path)

    metadata = {
        "model_name": "Isolation Forest Unsupervised Anomaly Detector",
        "training_samples": len(X_train),
        "unsupervised": True,
        "features": list(X_train.columns),
        "score_range": {"min": model.score_min_, "max": model.score_max_},
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
    print("[+] Isolation Forest training and evaluation completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
