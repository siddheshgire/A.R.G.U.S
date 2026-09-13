# Milestone 3 Report: Model Development & Training Pipeline

**Project:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Milestone:** 3 (Model Development & Training Pipeline Preparation)  
**Date:** 2026-09-11  
**Status:** Completed & Validated — Training Execution Ready  

---

## 1. Executive Summary
The model development and evaluation infrastructure for A.R.G.U.S. has been created, modularized, and tested. Four distinct model architectures have been implemented across linear, gradient boosted, and deep learning paradigms:
1. **Logistic Regression Baseline** (Linear Supervised Benchmark)
2. **XGBoost Classifier** (Supervised Gradient Boosted Decision Trees)
3. **Isolation Forest** (Unsupervised Outlier Isolation Trees)
4. **PyTorch Deep Autoencoder** (Unsupervised Bottleneck Neural Network)

In strict accordance with the workflow constraints, **no heavy training has been executed by the agent**. Standalone executable scripts have been prepared for the developer to train each model locally.

---

## 2. Model Architecture & Specifications

### 1. Logistic Regression Baseline ([`ml_engine/models/logistic_baseline.py`](file:///c:/PRO/PBL%20SY/ml_engine/models/logistic_baseline.py))
- **Paradigm:** Supervised Linear Classifier
- **Features:** 18 scaled features (via `feature_scaler.joblib`)
- **Optimization:** L-BFGS solver with L2 regularization ($C = 1.0$)
- **Imbalance Handling:** `class_weight="balanced"`
- **Artifact:** `models/logistic_baseline.joblib`

### 2. XGBoost Fraud Classifier ([`ml_engine/models/xgboost_model.py`](file:///c:/PRO/PBL%20SY/ml_engine/models/xgboost_model.py))
- **Paradigm:** Supervised Gradient Boosted Trees
- **Features:** 18 unscaled features (histogram-based splits)
- **Hyperparameters:** `n_estimators=300`, `max_depth=6`, `learning_rate=0.05`, `subsample=0.8`, `colsample_bytree=0.8`
- **Imbalance Handling:** `scale_pos_weight = 458.04` (dynamically computed from $N_{\text{neg}} / N_{\text{pos}}$ in train split)
- **Validation Tuning:** Early stopping with 30-round patience monitored on validation PR-AUC (`aucpr`)
- **Artifact:** `models/xgboost_fraud_model.json` (native XGBoost format)

### 3. Isolation Forest ([`ml_engine/models/isolation_forest.py`](file:///c:/PRO/PBL%20SY/ml_engine/models/isolation_forest.py))
- **Paradigm:** Unsupervised Anomaly Detection
- **Features:** 18 unscaled features
- **Training Labels:** **None used ($y$ is strictly withheld)**
- **Hyperparameters:** `n_estimators=150`, `max_samples=0.8`, `contamination="auto"`
- **Anomaly Score:** Inverted path length normalized to $[0, 1]$
- **Artifact:** `models/isolation_forest.joblib`

### 4. PyTorch Deep Autoencoder ([`ml_engine/models/autoencoder.py`](file:///c:/PRO/PBL%20SY/ml_engine/models/autoencoder.py))
- **Paradigm:** Deep Learning Feature Reconstruction Anomaly Detection
- **Features:** 18 scaled features
- **Architecture:** Symmetric 6-layer bottleneck:
  - **Encoder:** `Input(18) -> Linear(64) -> BatchNorm1d -> LeakyReLU(0.1) -> Linear(32) -> BatchNorm1d -> LeakyReLU(0.1) -> Linear(16) [Latent]`
  - **Decoder:** `Latent(16) -> Linear(32) -> BatchNorm1d -> LeakyReLU(0.1) -> Linear(64) -> BatchNorm1d -> LeakyReLU(0.1) -> Linear(18) [Reconstruction]`
- **Loss Function:** Mean Squared Error ($\text{MSE}$)
- **Training Policy:** Trained **exclusively on legitimate transactions ($y == 0$)** ($2,647,948$ samples)
- **Anomaly Signal:** Sample-wise reconstruction loss normalized via normal-validation error distribution statistics ($\mu, \sigma, P_{95}$)
- **Artifact:** `models/autoencoder.pt`

---

## 3. Dataset Usage & Temporal Splitting
The models operate on the chronological splits generated in Milestone 2:
- **Train (Steps 1–520):** $2,653,729$ total samples ($5,781$ fraud cases, $0.2178\%$ fraud rate).
- **Validation (Steps 521–631):** $78,701$ total samples ($1,180$ fraud cases, $1.4993\%$ fraud rate).
- **Test (Steps 632–743):** $37,979$ total samples ($1,252$ fraud cases, $3.2966\%$ fraud rate).

---

## 4. Evaluation Methodology & Metrics
Evaluation relies on ranking and imbalanced metrics rather than accuracy:
- **PR-AUC (Average Precision):** Primary metric for ranking fraud under extreme class imbalance.
- **ROC-AUC:** Area under ROC curve measuring discrimination capability.
- **Optimal Threshold Search:** Threshold $\tau^*$ is selected on the **Validation set** to maximize $F_1$-score.
- **Test Set Evaluation:** The chosen validation threshold $\tau^*$ is evaluated on the unseen Test set to measure true generalization without data leakage.
- **Inference Latency:** Benchmarked for batch (1000 transactions) and single-transaction execution.

---

## 5. Automated Validation & Test Suite
Unit tests in [`tests/test_model_pipeline.py`](file:///c:/PRO/PBL%20SY/tests/test_model_pipeline.py) and [`tests/test_feature_pipeline.py`](file:///c:/PRO/PBL%20SY/tests/test_feature_pipeline.py) verify:
- Model instantiation and parameter handling
- PR-AUC, ROC-AUC, F1, and threshold search algorithms
- PyTorch DeepAutoencoder forward pass with synthetic tensors $(B, 18)$
- Per-sample reconstruction error and calibration scoring
- Data loader feature isolation (`isFraud`, `isFlaggedFraud`, and raw IDs strictly excluded)

**Test Results:** `12 passed in 15.53s` (100% pass rate).

---

## 6. Execution Instructions for Developer

The developer can train each model individually using the prepared scripts. Execute the following commands in PowerShell from the project root:

### 1. Train Logistic Regression Baseline
```powershell
.\.venv\Scripts\python.exe scripts/train_logistic.py
```
*Expected Output:* Trains in ~30–60 seconds; outputs validation & test PR-AUC, ROC-AUC, F1, latency, and saves `models/logistic_baseline.joblib`.

### 2. Train XGBoost Supervised Classifier
```powershell
.\.venv\Scripts\python.exe scripts/train_xgboost.py
```
*Expected Output:* Trains with early stopping; outputs iteration logs, optimal threshold, PR-AUC, confusion matrix, and saves `models/xgboost_fraud_model.json`.

### 3. Train Isolation Forest Anomaly Detector
```powershell
.\.venv\Scripts\python.exe scripts/train_isolation_forest.py
```
*Expected Output:* Unsupervised fitting without target labels; outputs normalized score distribution, PR-AUC, optimal threshold, and saves `models/isolation_forest.joblib`.

### 4. Train Deep Autoencoder (PyTorch)
```powershell
.\.venv\Scripts\python.exe scripts/train_autoencoder.py
```
*Expected Output:* Trains for 15 epochs on normal transactions ($y == 0$); prints epoch loss, calibrates reconstruction error distribution, evaluates PR-AUC, and saves `models/autoencoder.pt`.

---

## 7. Next Recommended Milestone
**Milestone 4: Model Evaluation, Comparison & Risk Aggregation Engine**
- Collect empirical training metrics from the four models.
- Populate comparison tables in [`docs/MODEL_DEVELOPMENT.md`](file:///c:/PRO/PBL%20SY/docs/MODEL_DEVELOPMENT.md).
- Design the Risk Aggregation Engine combining supervised probability ($P_{\text{xgb}}$), Autoencoder reconstruction error ($\text{MSE}_{\text{ae}}$), Isolation Forest anomaly score ($S_{\text{if}}$), and rule penalties into a normalized **Risk Score (0–100)** mapped to `APPROVE`, `REVIEW`, and `BLOCK`.
