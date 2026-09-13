# Milestone 2 Report: Feature Engineering & Temporal Dataset Split

**Project:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Milestone:** 2 (Feature Engineering + Temporal Dataset Split)  
**Date:** 2026-09-11  
**Status:** Completed, Validated & Verified  

---

## 1. Feature Engineering Summary
The feature pipeline transforms raw PaySim transactions into an 18-dimensional, numerically stable feature matrix. The pipeline is implemented modularly in [`ml_engine/features/`](file:///c:/PRO/PBL%20SY/ml_engine/features/) and executed via [`scripts/build_paysim_features.py`](file:///c:/PRO/PBL%20SY/scripts/build_paysim_features.py). It addresses balance arithmetic discrepancies, account liquidation behavior, cyclical diurnal time dynamics, and mule destination zero-balance artifacts.

---

## 2. Final Feature List (18 Features)

### A. Raw Financial Features (5)
1. `amount`: Transaction monetary amount.
2. `oldbalanceOrg`: Pre-transaction sender balance.
3. `newbalanceOrig`: Post-transaction sender balance.
4. `oldbalanceDest`: Pre-transaction recipient balance.
5. `newbalanceDest`: Post-transaction recipient balance.

### B. Domain Engineered Features (13)
6. `log_amount`: Numerically safe $\log_e(\text{amount} + 1.0)$ compressing extreme positive skew.
7. `is_transfer`: Binary indicator for `TRANSFER` transaction type.
8. `is_cash_out`: Binary indicator for `CASH_OUT` transaction type.
9. `hour_of_day`: Simulated diurnal hour ($0$ to $23$).
10. `hour_sin`: Cyclical circular sine transformation of `hour_of_day`.
11. `hour_cos`: Cyclical circular cosine transformation of `hour_of_day`.
12. `is_night_transaction`: Binary indicator for hours $01\text{:}00$ to $06\text{:}00$ (high-risk fraud window).
13. `orig_balance_error`: $\text{newbalanceOrig} + \text{amount} - \text{oldbalanceOrg}$ (sender ledger deviation).
14. `orig_drain_ratio`: $\text{amount} / (\text{oldbalanceOrg} + 1.0)$ (sender fund liquidation ratio).
15. `is_full_liquidation`: Binary indicator for complete sender account drainage ($\text{old} > 0 \land \text{new} == 0$).
16. `dest_balance_error`: $\text{oldbalanceDest} + \text{amount} - \text{newbalanceDest}$ (recipient ledger deviation).
17. `dest_drain_ratio`: $\text{amount} / (\text{newbalanceDest} + 1.0)$ (recipient relative impact ratio).
18. `dest_zero_balance_anomaly`: Binary indicator for ghost/mule destination accounts ($\text{oldDest} == 0 \land \text{newDest} == 0 \land \text{amount} > 0$).

---

## 3. Excluded Features & Rationale
- **`isFraud`:** Ground truth label. Strictly preserved as target $y$; excluded from feature matrix $X$.
- **`isFlaggedFraud`:** Simulation heuristic rule ($> 200,000$). Flags only 16 rows, has $99.8\%$ false negative rate, and introduces direct target leakage. Excluded.
- **`nameOrig`:** Raw customer string ID (6.35M unique IDs). Excluded from ML features to prevent high-cardinality memorization.
- **`nameDest`:** Raw recipient string ID (2.72M unique IDs). Excluded from ML features to prevent high-cardinality memorization.
- **`type`:** Raw categorical string. Replaced by binary indicators `is_transfer` and `is_cash_out`.
- **`step`:** Monotonically increasing counter ($1$–$743$). Replaced by cyclical diurnal features; retained in split metadata.

---

## 4. Leakage Prevention Safeguards
1. **Target Isolation:** Hard assertions in `extract_feature_matrix()` strictly raise errors if `isFraud` or `isFlaggedFraud` enter $X$.
2. **Chronological Splitting:** Random k-fold cross-validation is avoided; partitioning is strictly time-based on simulation `step`.
3. **Scaler Fitting Isolation:** The `StandardScaler` (used for the Deep Autoencoder) is fitted **strictly on the Train partition** and serialized to `models/feature_scaler.joblib`. Neither validation nor test distributions leak into feature scaling.

---

## 5. Temporal Split Methodology
Partitioning was performed chronologically across the 743 unique simulation hours:
- **Train Partition:** Steps $1$ to $520$ (~$70.0\%$ of chronological time).
- **Validation Partition:** Steps $521$ to $631$ (~$14.9\%$ of chronological time).
- **Test Partition:** Steps $632$ to $743$ (~$15.1\%$ of chronological time).

---

## 6. Exact Train, Validation & Test Distribution

| Partition | Step Range | Total Transactions | Fraud Cases | Fraud Rate (%) | Imbalance Ratio | Data Quality Check |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Train** | 1 to 520 | **2,653,729** | **5,781** | **0.2178%** | 458.0 : 1 | 0 NaN, 0 Inf |
| **Validation** | 521 to 631 | **78,701** | **1,180** | **1.4993%** | 65.7 : 1 | 0 NaN, 0 Inf |
| **Test** | 632 to 743 | **37,979** | **1,252** | **3.2966%** | 29.3 : 1 | 0 NaN, 0 Inf |
| **Total (Subspace)**| 1 to 743 | **2,770,409** | **8,213** | **0.2965%** | 336.3 : 1 | 100% Fraud Retained |

---

## 7. Class Distribution Observations
- **All Partitions Contain Substantial Fraud Samples:**
  - Train has 5,781 fraud cases.
  - Validation has 1,180 fraud cases.
  - Test has 1,252 fraud cases.
- **Increasing Fraud Rate over Time:** In the PaySim simulation, the density of fraudulent transactions relative to legitimate traffic increases in later steps ($0.22\%$ in Train $\rightarrow$ $1.50\%$ in Validation $\rightarrow$ $3.30\%$ in Test). This mirrors real-world adversarial fraud attacks where attack frequency intensifies, providing an authentic test of model generalization.

---

## 8. Behavioral Feature Decisions
- Entity inspection confirmed that $99.85\%$ of senders appear only once in the dataset.
- Computing static offline multi-transaction rolling windows across the entire CSV yields near-zero variance per user and risks subtle time leakage.
- **Decision:** Transaction-level behavioral risk indicators (`orig_drain_ratio`, `is_full_liquidation`, `dest_zero_balance_anomaly`, `is_night_transaction`) are implemented directly. Multi-transaction historical state tracking is deferred to Milestone 8 (live PostgreSQL / Redis cache layer), where customer profile lookups will be computed causally at request time.

---

## 9. Modeling Subspace Decision
- **Subspace Retained:** `TRANSFER` and `CASH_OUT` transactions (2,770,409 rows; $43.54\%$ of the raw dataset).
- **Justification:** As established in Milestone 1, **100% of all 8,213 fraud cases reside exclusively in `TRANSFER` and `CASH_OUT`**. The remaining types (`PAYMENT`, `CASH_IN`, `DEBIT`) contain 0 fraud cases.
- **Benefits:**
  1. Reduces memory consumption by $56.5\%$.
  2. Reduces class imbalance from $773.7\text{:}1$ to $336.3\text{:}1$, dramatically improving gradient stability.
  3. Accelerates model training and hyperparameter search without sacrificing a single positive fraud label.
- **System-Level Handling of Other Types:** In the production A.R.G.U.S. architecture, non-fraudulent transaction types (`PAYMENT`, `CASH_IN`, `DEBIT`) will pass through a lightweight, low-latency business rule validator (`APPROVE` by default unless terminal/security rules trigger), reserving the ML/DL ensemble for high-risk movement of funds.

---

## 10. Files Created & Modified

```
ml_engine/
└── features/
    ├── __init__.py           # Package exports
    ├── feature_config.py     # Feature manifests, exclusions, split boundaries
    └── paysim_features.py    # Transformation logic, temporal split, scaler utilities

scripts/
└── build_paysim_features.py  # End-to-end dataset feature generation script

tests/
└── test_feature_pipeline.py  # Automated unit tests for numerical safety & split integrity

pytest.ini                    # Pytest configuration with pythonpath = .

docs/
├── FEATURE_ENGINEERING.md    # Detailed feature manifest specification
└── MILESTONE_2_REPORT.md     # Milestone 2 completion report

models/
└── feature_scaler.joblib     # StandardScaler fitted strictly on Train partition (gitignored)

data/processed/ (gitignored)
├── train.csv                 # 2,653,729 rows (Steps 1–520)
├── validation.csv            # 78,701 rows (Steps 521–631)
├── test.csv                  # 37,979 rows (Steps 632–743)
└── split_metadata.json       # Dataset dimensions and partition statistics
```

---

## 11. Validation Results
Automated test suite [`tests/test_feature_pipeline.py`](file:///c:/PRO/PBL%20SY/tests/test_feature_pipeline.py) was executed via `pytest`:
- `test_feature_engineering_completeness_and_safety`: **PASSED**
- `test_subspace_filter`: **PASSED**
- `test_temporal_split_integrity`: **PASSED**
- `test_leakage_prevention`: **PASSED**
- `test_scaler_training_isolation`: **PASSED**

**Result:** `5 passed in 5.32s` (100% pass rate).

---

## 12. Known Limitations
1. **Simulation Account Reuse:** Due to PaySim's agent modeling, sender account reuse is rare, limiting multi-transaction velocity modeling within this dataset alone.
2. **Temporal Volume Variations:** Later simulation steps have lower overall transaction volume, causing the percentage of fraud to increase in the validation and test splits. Models must be evaluated using PR-AUC and ROC-AUC rather than raw threshold accuracy.

---

## 13. Recommended Next Milestone
**Milestone 3: Model Development & Training (Developer-Executed)**
- Train **Logistic Regression** baseline.
- Train **XGBoost** supervised fraud classifier.
- Train **Isolation Forest** unsupervised anomaly detector.
- Build and train **Deep Autoencoder** reconstruction network (PyTorch).
- Evaluate metrics on validation split: PR-AUC, ROC-AUC, Precision, Recall, F1, Latency.
