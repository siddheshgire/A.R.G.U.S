#!/usr/bin/env python3
"""
A.R.G.U.S. — Training Script: Deep Autoencoder Anomaly Detector (PyTorch)
Trains symmetric bottleneck neural network exclusively on legitimate transactions (y == 0)
using feature reconstruction loss (MSE) as the anomaly signal.
"""

import sys
import json
import time
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml_engine.training import load_processed_split, get_normal_training_data
from ml_engine.models import AutoencoderAnomalyDetector, AutoencoderDataset
from ml_engine.evaluation import (
    compute_classification_metrics,
    find_optimal_threshold,
    benchmark_inference_latency,
    format_metric_report,
)


def main():
    print("=" * 70)
    print("A.R.G.U.S. — Training: PyTorch Deep Autoencoder Anomaly Detector")
    print("=" * 70)

    # 1. Device check
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[*] PyTorch Compute Device: {device.upper()}")

    # 2. Load scaled datasets (Autoencoder requires normalized features)
    print("\n[*] Loading scaled training, validation, and test datasets...")
    t0 = time.time()
    X_train, y_train = load_processed_split("train", scaled=True)
    X_val, y_val = load_processed_split("validation", scaled=True)
    X_test, y_test = load_processed_split("test", scaled=True)
    print(f"[*] Loaded datasets in {time.time() - t0:.2f}s:")
    print(f"    - Train Total: {len(X_train):,} | Validation Total: {len(X_val):,} | Test Total: {len(X_test):,}")

    # 3. Filter training to legitimate transactions ONLY (Unsupervised Normal Profiling)
    X_train_normal = get_normal_training_data(X_train, y_train)
    X_val_normal = get_normal_training_data(X_val, y_val)
    print(f"\n[*] Training Subspace (Legitimate Transactions y==0 only):")
    print(f"    - Normal Train Samples:      {len(X_train_normal):,} (100% legitimate)")
    print(f"    - Normal Validation Samples: {len(X_val_normal):,}")

    # 4. Prepare PyTorch DataLoaders
    batch_size = 2048
    train_dataset = AutoencoderDataset(X_train_normal)
    val_normal_dataset = AutoencoderDataset(X_val_normal)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=False)
    val_normal_loader = DataLoader(val_normal_dataset, batch_size=batch_size, shuffle=False)

    # 5. Initialize Autoencoder
    input_dim = X_train.shape[1]
    latent_dim = 16
    print(f"\n[*] Initializing DeepAutoencoder (Input: {input_dim} -> 64 -> 32 -> Latent: {latent_dim} -> 32 -> 64 -> Output: {input_dim})...")
    detector = AutoencoderAnomalyDetector(
        input_dim=input_dim,
        latent_dim=latent_dim,
        learning_rate=1e-3,
        weight_decay=1e-5,
        device=device,
    )

    # 6. Training Loop with Early Stopping
    epochs = 15
    patience = 3
    best_val_loss = float("inf")
    patience_counter = 0
    best_model_state = None

    print(f"\n[*] Starting Autoencoder training ({epochs} epochs, batch_size={batch_size})...")
    t_train_start = time.time()

    for epoch in range(1, epochs + 1):
        t_epoch_start = time.time()
        train_loss = detector.train_epoch(train_loader)
        val_loss = detector.evaluate_loss(val_normal_loader)
        epoch_sec = time.time() - t_epoch_start

        print(f"  Epoch [{epoch:02d}/{epochs:02d}] | Train MSE: {train_loss:.6f} | Val Normal MSE: {val_loss:.6f} | Time: {epoch_sec:.1f}s")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            best_model_state = detector.model.state_dict().copy()
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"[*] Early stopping triggered at epoch {epoch} (no improvement for {patience} epochs).")
                break

    train_duration = time.time() - t_train_start
    print(f"[+] Training completed in {train_duration:.2f}s (Best Val MSE: {best_val_loss:.6f})")

    # Restore best weights
    if best_model_state is not None:
        detector.model.load_state_dict(best_model_state)

    # 7. Calibrate anomaly scores on normal validation reconstruction error distribution
    print("\n[*] Calibrating anomaly score distribution on normal validation errors...")
    val_normal_errors = detector.predict_reconstruction_error(X_val_normal)
    detector.calibrate_anomaly_scores(val_normal_errors)
    print(f"    - Normal Error Mean: {detector.error_mean_:.6f}")
    print(f"    - Normal Error Std:  {detector.error_std_:.6f}")
    print(f"    - Normal Error P95:  {detector.error_p95_:.6f}")

    # 8. Predict Anomaly Scores on full Validation split (including both normal and fraud)
    print("\n[*] Evaluating on Validation partition...")
    val_scores = detector.predict_anomaly_score(X_val)

    # Find optimal threshold for F1 on validation set
    val_opt_res = find_optimal_threshold(y_val, val_scores, metric="f1")
    chosen_threshold = val_opt_res["threshold"]
    print(f"[*] Optimal Validation Threshold (Max F1): {chosen_threshold:.4f}")
    print(format_metric_report(val_opt_res, "Deep Autoencoder", "Validation"))

    # 9. Evaluate on Test split using validation-chosen threshold
    print("\n[*] Evaluating on Test partition using validation-chosen threshold...")
    test_scores = detector.predict_anomaly_score(X_test)
    test_res = compute_classification_metrics(y_test, test_scores, threshold=chosen_threshold)
    print(format_metric_report(test_res, "Deep Autoencoder", "Test"))

    # 10. Benchmark latency
    print("\n[*] Benchmarking inference latency...")
    latency_res = benchmark_inference_latency(detector.predict_anomaly_score, X_val[:1000])
    print(f"[*] Batch Latency (1000 tx):     {latency_res['batch_latency_ms']:.2f} ms")
    print(f"[*] Single Sample Latency:       {latency_res['single_sample_latency_ms']:.4f} ms")

    # 11. Save model artifact and metadata
    model_path = Path("models/autoencoder.pt")
    meta_path = Path("models/autoencoder_meta.json")
    print(f"\n[*] Saving PyTorch model checkpoint to: {model_path}")
    detector.save(model_path)

    metadata = {
        "model_name": "Deep Autoencoder Anomaly Detector",
        "architecture": "Input(18) -> Dense(64) -> Dense(32) -> Latent(16) -> Dense(32) -> Dense(64) -> Output(18)",
        "training_samples_normal": len(X_train_normal),
        "unsupervised_normal_only": True,
        "features": list(X_train.columns),
        "training_time_seconds": round(train_duration, 2),
        "best_val_loss": round(float(best_val_loss), 6),
        "error_stats": {
            "mean": round(detector.error_mean_, 6),
            "std": round(detector.error_std_, 6),
            "p95": round(detector.error_p95_, 6),
        },
        "chosen_threshold": round(chosen_threshold, 4),
        "validation_metrics": val_opt_res,
        "test_metrics": test_res,
        "latency": latency_res,
    }
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[+] Metadata saved to: {meta_path}")

    print("\n" + "=" * 70)
    print("[+] Deep Autoencoder training and evaluation completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
