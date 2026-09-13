"""
A.R.G.U.S. — Feature Configuration & Manifest Definition
Defines feature names, groupings, temporal split thresholds, and exclusion rules.
"""

from typing import List, Dict, Any

# Target column
TARGET_COLUMN: str = "isFraud"

# Columns explicitly excluded from input features to prevent leakage and false signals
EXCLUDED_COLUMNS: List[str] = [
    "isFraud",         # Ground truth target (supervised label only)
    "isFlaggedFraud",  # Simulation heuristic rule artifact (99.8% false negative; direct leakage)
    "nameOrig",        # Raw customer ID (high cardinality, near 1:1; used in DB entity joins only)
    "nameDest",        # Raw recipient ID (high cardinality; used in DB entity joins only)
    "type",            # Raw categorical string (replaced by binary indicators is_transfer, is_cash_out)
    "step",            # Raw step counter (transformed into cyclical hour features; kept for splitting)
]

# Raw continuous financial features retained in the model vector
RAW_NUMERICAL_FEATURES: List[str] = [
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
]

# Engineered domain features
ENGINEERED_FEATURE_NAMES: List[str] = [
    "log_amount",                 # log1p(amount) to compress severe positive skew
    "is_transfer",                # Binary indicator: type == TRANSFER
    "is_cash_out",                # Binary indicator: type == CASH_OUT
    "hour_of_day",                # step % 24 (diurnal hour 0 to 23)
    "hour_sin",                   # sin(2 * pi * hour_of_day / 24) (cyclical continuity)
    "hour_cos",                   # cos(2 * pi * hour_of_day / 24) (cyclical continuity)
    "is_night_transaction",       # Binary indicator: 1 <= hour_of_day <= 6 (peak fraud rate window)
    "orig_balance_error",         # newbalanceOrig + amount - oldbalanceOrg (sender balance discrepancy)
    "orig_drain_ratio",           # amount / (oldbalanceOrg + 1.0) (proportion of sender funds drained)
    "is_full_liquidation",        # Binary indicator: (oldbalanceOrg > 0) & (newbalanceOrig == 0)
    "dest_balance_error",         # oldbalanceDest + amount - newbalanceDest (recipient balance discrepancy)
    "dest_drain_ratio",           # amount / (newbalanceDest + 1.0) (recipient relative impact)
    "dest_zero_balance_anomaly",  # Binary indicator: (oldbalanceDest == 0) & (newbalanceDest == 0) & (amount > 0)
]

# Complete set of features fed into ML/DL models (5 raw + 13 engineered = 18 total)
ALL_MODEL_FEATURES: List[str] = RAW_NUMERICAL_FEATURES + ENGINEERED_FEATURE_NAMES

# Chronological temporal splitting boundaries (based on 743 unique simulation steps)
# Train: Steps 1 to 520 (~70.0% of chronological timeline)
# Validation: Steps 521 to 631 (~14.9% of chronological timeline)
# Test: Steps 632 to 743 (~15.1% of chronological timeline)
TEMPORAL_SPLIT_STEPS: Dict[str, Any] = {
    "train_min_step": 1,
    "train_max_step": 520,
    "val_min_step": 521,
    "val_max_step": 631,
    "test_min_step": 632,
    "test_max_step": 743,
}

# Transaction types where fraud is observed in PaySim
FRAUD_MODELING_TYPES: List[str] = ["TRANSFER", "CASH_OUT"]
