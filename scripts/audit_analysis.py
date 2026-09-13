"""
A.R.G.U.S. — Milestone 3A Audit Analysis Helper
Performs empirical feature importance extraction, false-negative deep dive,
and univariate target separation analysis.
"""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBClassifier

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml_engine.training import load_processed_split
from ml_engine.models import XGBoostFraudClassifier
from ml_engine.features import ALL_MODEL_FEATURES, TARGET_COLUMN


def main():
    print("=" * 70)
    print("A.R.G.U.S. — Milestone 3A Audit Analysis")
    print("=" * 70)

    # 1. Load Test split (unscaled)
    print("[*] Loading test split...")
    X_test, y_test = load_processed_split("test", scaled=False)
    
    # 2. Load trained XGBoost model
    xgb_wrapper = XGBoostFraudClassifier()
    xgb_wrapper.load_model("models/xgboost_fraud_model.json")
    
    # Extract native Booster
    booster = xgb_wrapper.model.get_booster()

    # 3. Feature Importance (Gain, Weight, Cover)
    print("\n--- 1. XGBoost Feature Importance ---")
    score_gain = booster.get_score(importance_type="gain")
    score_weight = booster.get_score(importance_type="weight")
    score_cover = booster.get_score(importance_type="cover")

    importance_df = pd.DataFrame({
        "feature": ALL_MODEL_FEATURES,
        "gain": [score_gain.get(f, 0.0) for f in ALL_MODEL_FEATURES],
        "weight": [score_weight.get(f, 0.0) for f in ALL_MODEL_FEATURES],
        "cover": [score_cover.get(f, 0.0) for f in ALL_MODEL_FEATURES],
    })
    total_gain = importance_df["gain"].sum()
    importance_df["gain_pct"] = (importance_df["gain"] / total_gain) * 100
    importance_df = importance_df.sort_values(by="gain", ascending=False).reset_index(drop=True)
    print(importance_df.to_string())

    # 4. Predictions & False Negative Inspection
    print("\n--- 2. Predictions & Error Analysis ---")
    val_meta = json.load(open("models/xgboost_meta.json"))
    threshold = val_meta["chosen_threshold"]
    print(f"Chosen threshold: {threshold:.6f}")

    test_probs = xgb_wrapper.predict_proba(X_test)
    test_preds = (test_probs >= threshold).astype(int)

    # Find False Negatives: y_true == 1, test_preds == 0
    fn_indices = np.where((y_test.values == 1) & (test_preds == 0))[0]
    print(f"\nFalse Negative Count: {len(fn_indices)}")

    fn_details = []
    for idx in fn_indices:
        row_dict = X_test.iloc[idx].to_dict()
        row_dict["probability"] = float(test_probs[idx])
        row_dict["actual_label"] = int(y_test.iloc[idx])
        row_dict["index_in_test"] = int(idx)
        fn_details.append(row_dict)
        print(f"\n[!] False Negative Row Details (Index {idx}):")
        print(f"    Probability: {test_probs[idx]:.6f}")
        for k, v in row_dict.items():
            if k not in ["probability", "actual_label", "index_in_test"]:
                print(f"    {k:<28}: {v}")

    # Top confident legitimate and fraud
    print("\n--- Top Confident Legitimate ---")
    legit_indices = np.argsort(test_probs)[:3]
    for idx in legit_indices:
        print(f"Index {idx} | Prob: {test_probs[idx]:.8f} | True Label: {y_test.iloc[idx]}")

    print("\n--- Top Confident Fraud ---")
    fraud_indices = np.argsort(test_probs)[-3:]
    for idx in fraud_indices:
        print(f"Index {idx} | Prob: {test_probs[idx]:.8f} | True Label: {y_test.iloc[idx]}")

    # 5. Univariate Correlation & Separation Audit on Train Partition
    print("\n--- 3. Univariate Correlation & Separation (Train Split) ---")
    X_train, y_train = load_processed_split("train", scaled=False)
    
    corrs = []
    for col in ALL_MODEL_FEATURES:
        col_vals = X_train[col].to_numpy(dtype=float)
        # Point biserial correlation with y_train
        std_val = np.std(col_vals)
        corr = np.corrcoef(col_vals, y_train.to_numpy(dtype=float))[0, 1] if std_val > 0 else 0.0
        
        # Means for legit vs fraud
        mean_legit = float(col_vals[y_train == 0].mean())
        mean_fraud = float(col_vals[y_train == 1].mean())
        median_legit = float(np.median(col_vals[y_train == 0]))
        median_fraud = float(np.median(col_vals[y_train == 1]))
        
        corrs.append({
            "feature": col,
            "correlation_with_fraud": round(corr, 4),
            "mean_legit": round(mean_legit, 2),
            "mean_fraud": round(mean_fraud, 2),
            "median_legit": round(median_legit, 2),
            "median_fraud": round(median_fraud, 2),
        })
    
    corr_df = pd.DataFrame(corrs).sort_values(by="correlation_with_fraud", key=abs, ascending=False).reset_index(drop=True)
    print(corr_df.to_string())

    # Save findings for report
    audit_output = {
        "importance": importance_df.to_dict(orient="records"),
        "false_negatives": fn_details,
        "correlations": corr_df.to_dict(orient="records"),
    }
    with open("docs/audit_summary.json", "w") as f:
        json.dump(audit_output, f, indent=2)
    print("\n[+] Audit summary saved to docs/audit_summary.json")


if __name__ == "__main__":
    main()
