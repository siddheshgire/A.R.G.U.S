import sys
sys.path.insert(0, ".")
import pandas as pd
import numpy as np
import joblib
import json
import torch
import xgboost as xgb
from ml_engine.risk import RiskConfig, RiskSignals, compute_risk_score, evaluate_decision, assess_transaction
from ml_engine.models import AutoencoderAnomalyDetector, IsolationForestAnomalyDetector

test_df = pd.read_csv("data/processed/test.csv")
row_3583 = test_df.iloc[3583]

feature_cols = [
    "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest",
    "log_amount", "is_transfer", "is_cash_out", "hour_of_day", "hour_sin", "hour_cos",
    "is_night_transaction", "orig_balance_error", "orig_drain_ratio", "is_full_liquidation",
    "dest_balance_error", "dest_drain_ratio", "dest_zero_balance_anomaly"
]

scaler = joblib.load("models/feature_scaler.joblib")
X_raw = test_df.loc[[3583], feature_cols]
X_scaled_np = scaler.transform(X_raw)
X_scaled_df = pd.DataFrame(X_scaled_np, columns=feature_cols)

# 1. XGBoost
xgb_model = xgb.XGBClassifier()
xgb_model.load_model("models/xgboost_fraud_model.json")
xgb_prob = float(xgb_model.predict_proba(X_raw)[0, 1])

# 2. Logistic Regression
lr_model = joblib.load("models/logistic_baseline.joblib")
lr_prob = float(lr_model.predict_proba(X_scaled_df)[0])

# 3. Isolation Forest
iso_detector = joblib.load("models/isolation_forest.joblib")
iso_norm = float(iso_detector.predict_anomaly_score(X_scaled_df)[0])

# 4. Deep Autoencoder
ae_detector = AutoencoderAnomalyDetector.load("models/autoencoder.pt")
ae_mse = float(ae_detector.predict_reconstruction_error(X_scaled_df)[0])
ae_norm = float(ae_detector.predict_anomaly_score(X_scaled_df)[0])

signals = RiskSignals(
    xgboost_score=xgb_prob,
    logistic_score=lr_prob,
    isolation_score=iso_norm,
    autoencoder_score=ae_norm,
)

config = RiskConfig()
risk_score = compute_risk_score(signals, config)
decision = evaluate_decision(risk_score, config)

print("=== EXACT VERIFIED ROW 3583 ATTRIBUTES ===")
for col in ["step", "type", "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest",
            "is_transfer", "is_cash_out", "hour_of_day", "orig_drain_ratio", "orig_balance_error",
            "dest_balance_error", "dest_drain_ratio", "dest_zero_balance_anomaly", "isFraud"]:
    print(f"{col}: {row_3583[col]}")

print("\n=== MODEL INFERENCES ===")
print(f"XGBoost model-estimated probability: {xgb_prob:.6f}")
print(f"Logistic Regression probability:     {lr_prob:.6f}")
print(f"Isolation Forest normalized anomaly: {iso_norm:.6f}")
print(f"Autoencoder raw MSE:                 {ae_mse:.6f}")
print(f"Autoencoder normalized anomaly:      {ae_norm:.6f}")

print("\n=== RISK ENGINE SCORE & DECISION ===")
print(f"Signals dict: {signals.to_dict()}")
print(f"Aggregated Risk Score: {risk_score:.4f} (rounded: {round(risk_score, 2)})")
print(f"Decision Action: {decision.value}")
