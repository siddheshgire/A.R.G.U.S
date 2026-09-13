#!/usr/bin/env python3
"""
A.R.G.U.S. — Risk Scoring & Decision Engine Validation Script
Evaluates multi-model risk score aggregation and tri-state decision policies on the Validation partition.
"""

import sys
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml_engine.training import load_processed_split
from ml_engine.models import (
    XGBoostFraudClassifier,
    LogisticRegressionBaseline,
    IsolationForestAnomalyDetector,
    AutoencoderAnomalyDetector,
)
from ml_engine.evaluation import compute_classification_metrics
from ml_engine.risk import (
    RiskConfig,
    RiskSignals,
    compute_risk_scores_batch,
    evaluate_decisions_batch,
    DecisionAction,
)


def main():
    print("=" * 70)
    print("A.R.G.U.S. — Risk Scoring & Decision Engine Validation")
    print("=" * 70)

    # 1. Load Validation partition
    print("\n[*] Loading Validation partition (unscaled & scaled)...")
    t0 = time.time()
    X_val_unscaled, y_val = load_processed_split("validation", scaled=False)
    X_val_scaled, _ = load_processed_split("validation", scaled=True)
    n_samples = len(y_val)
    n_fraud = int(y_val.sum())
    print(f"[*] Loaded {n_samples:,} validation transactions in {time.time() - t0:.2f}s (Fraud cases: {n_fraud:,}, {n_fraud/n_samples:.2%})")

    # 2. Load trained model artifacts
    print("\n[*] Loading trained model artifacts from models/...")
    xgb_model = XGBoostFraudClassifier()
    xgb_model.load_model("models/xgboost_fraud_model.json")
    print("  [+] Loaded XGBoost model")

    lr_model = LogisticRegressionBaseline.load("models/logistic_baseline.joblib")
    print("  [+] Loaded Logistic Regression baseline")

    if_model = IsolationForestAnomalyDetector.load("models/isolation_forest.joblib")
    print("  [+] Loaded Isolation Forest detector")

    ae_model = AutoencoderAnomalyDetector.load("models/autoencoder.pt")
    print("  [+] Loaded Deep Autoencoder detector")

    # 3. Generate individual model signals on Validation partition
    print("\n[*] Generating normalized model signals...")
    t_inf = time.time()
    xgb_scores = xgb_model.predict_proba(X_val_unscaled)
    lr_scores = lr_model.predict_proba(X_val_scaled)
    if_scores = if_model.predict_anomaly_score(X_val_unscaled)
    ae_scores = ae_model.predict_anomaly_score(X_val_scaled)
    print(f"[*] Inferred all 4 models across {n_samples:,} samples in {time.time() - t_inf:.2f}s")

    # 4. Compute aggregated Risk Score (0-100)
    config = RiskConfig(
        xgboost_weight=0.50,
        autoencoder_weight=0.20,
        isolation_weight=0.15,
        logistic_weight=0.15,
        threshold_review=40.0,
        threshold_block=70.0,
    )
    print(f"\n[*] Ensemble Configuration:")
    print(f"    - XGBoost Weight:     {config.xgboost_weight:.2f}")
    print(f"    - Autoencoder Weight: {config.autoencoder_weight:.2f}")
    print(f"    - Isolation Weight:   {config.isolation_weight:.2f}")
    print(f"    - Logistic Weight:    {config.logistic_weight:.2f}")
    print(f"    - Review Threshold:   {config.threshold_review:.1f}")
    print(f"    - Block Threshold:    {config.threshold_block:.1f}")

    risk_scores = compute_risk_scores_batch(xgb_scores, lr_scores, if_scores, ae_scores, config)
    print(f"\n[*] Risk Score Summary (0 to 100):")
    print(f"    - Min:    {risk_scores.min():.2f}")
    print(f"    - Median: {np.median(risk_scores):.2f}")
    print(f"    - Mean:   {risk_scores.mean():.2f}")
    print(f"    - Max:    {risk_scores.max():.2f}")

    # 5. Evaluate Decision Policy (APPROVE, REVIEW, BLOCK)
    decisions = evaluate_decisions_batch(risk_scores, config)
    y_val_arr = y_val.to_numpy()

    # Breakdown by decision
    print("\n" + "=" * 70)
    print("DECISION DISTRIBUTION & FRAUD CAPTURE (VALIDATION PARTITION)")
    print("=" * 70)
    print(f"{'Decision':<10} | {'Total Tx':<10} | {'% of Total':<10} | {'Legitimate':<12} | {'Fraud':<8} | {'Fraud Density':<14}")
    print("-" * 70)

    decision_summary = {}
    for action in [DecisionAction.APPROVE, DecisionAction.REVIEW, DecisionAction.BLOCK]:
        mask = (decisions == action.value)
        total_tx = int(mask.sum())
        legit_tx = int((mask & (y_val_arr == 0)).sum())
        fraud_tx = int((mask & (y_val_arr == 1)).sum())
        pct_total = (total_tx / n_samples) * 100
        density = (fraud_tx / total_tx * 100) if total_tx > 0 else 0.0

        decision_summary[action.value] = {
            "total_transactions": total_tx,
            "pct_of_total": round(pct_total, 2),
            "legitimate_transactions": legit_tx,
            "fraud_transactions": fraud_tx,
            "fraud_density_pct": round(density, 2),
        }
        print(f"{action.value:<10} | {total_tx:<10,} | {pct_total:>8.2f}% | {legit_tx:<12,} | {fraud_tx:<8,} | {density:>12.2f}%")

    # Operational metrics
    total_fraud_captured = decision_summary["REVIEW"]["fraud_transactions"] + decision_summary["BLOCK"]["fraud_transactions"]
    fraud_recall = (total_fraud_captured / n_fraud) * 100
    block_recall = (decision_summary["BLOCK"]["fraud_transactions"] / n_fraud) * 100
    fpr_approve_disruption = (decision_summary["REVIEW"]["legitimate_transactions"] + decision_summary["BLOCK"]["legitimate_transactions"]) / (n_samples - n_fraud) * 100

    print("-" * 70)
    print(f"Total Fraud Detected (Review + Block): {total_fraud_captured:,} / {n_fraud:,} ({fraud_recall:.2f}%)")
    print(f"Fraud Immediately Blocked:            {decision_summary['BLOCK']['fraud_transactions']:,} / {n_fraud:,} ({block_recall:.2f}%)")
    print(f"Legitimate Traffic Disruption (FPR):   {fpr_approve_disruption:.3f}% ({decision_summary['REVIEW']['legitimate_transactions'] + decision_summary['BLOCK']['legitimate_transactions']:,} tx flagged for review/block)")

    # 6. Model Comparison on Validation Partition
    print("\n" + "=" * 70)
    print("MODEL COMPARISON (VALIDATION SPLIT)")
    print("=" * 70)
    candidates = {
        "XGBoost Alone": xgb_scores,
        "Logistic Regression Alone": lr_scores,
        "Isolation Forest Alone": if_scores,
        "Deep Autoencoder Alone": ae_scores,
        "ARGUS Weighted Ensemble": risk_scores / 100.0,
    }

    model_comparison = []
    print(f"{'Candidate':<26} | {'PR-AUC':<8} | {'ROC-AUC':<8} | {'F1 @ Opt Thresh':<16} | {'Opt Thresh':<10}")
    print("-" * 75)
    for name, scores in candidates.items():
        metrics = compute_classification_metrics(y_val_arr, scores, threshold=0.5)
        # Also compute at optimal F1 threshold
        from ml_engine.evaluation import find_optimal_threshold
        opt_res = find_optimal_threshold(y_val_arr, scores, metric="f1")
        print(f"{name:<26} | {metrics['pr_auc']:.4f}   | {metrics['roc_auc']:.4f}   | {opt_res['f1']:.4f}           | {opt_res['threshold']:.4f}")
        model_comparison.append({
            "candidate": name,
            "pr_auc": round(metrics["pr_auc"], 4),
            "roc_auc": round(metrics["roc_auc"], 4),
            "opt_f1": round(opt_res["f1"], 4),
            "opt_threshold": round(opt_res["threshold"], 4),
        })

    # 7. Save Validation Summary JSON
    summary_path = Path("docs/risk_engine_validation.json")
    out_data = {
        "config": {
            "xgboost_weight": config.xgboost_weight,
            "autoencoder_weight": config.autoencoder_weight,
            "isolation_weight": config.isolation_weight,
            "logistic_weight": config.logistic_weight,
            "threshold_review": config.threshold_review,
            "threshold_block": config.threshold_block,
        },
        "validation_samples": n_samples,
        "validation_fraud": n_fraud,
        "decision_distribution": decision_summary,
        "operational_metrics": {
            "fraud_recall_pct": round(fraud_recall, 2),
            "block_recall_pct": round(block_recall, 2),
            "legitimate_disruption_fpr_pct": round(fpr_approve_disruption, 4),
        },
        "model_comparison": model_comparison,
    }
    with open(summary_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\n[+] Validation results saved to: {summary_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
