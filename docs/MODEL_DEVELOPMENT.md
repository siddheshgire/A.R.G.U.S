# A.R.G.U.S. — Model Development & Training Architecture

**Project:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Milestone:** 3 (Model Development & Training Pipeline)  
**Document:** `docs/MODEL_DEVELOPMENT.md`  
**Status:** Pipeline Prepared & Validated — Awaiting Developer Execution  

---

## 1. Model Objectives & Taxonomy

A.R.G.U.S. evaluates four complementary models across linear, ensemble, and deep learning paradigms to ensure rigorous academic comparison and robust production risk scoring:

| Model Candidate | Model Paradigm | Supervised / Unsupervised | Input Scaling | Primary Functional Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression** | Generalized Linear Model | Supervised | **Scaled** (`feature_scaler.joblib`) | Interpretable linear baseline; establishes benchmark PR-AUC and coefficients. |
| **XGBoost** | Gradient Boosted Trees | Supervised | **Unscaled** | High-capacity tabular classifier; handles non-linear balance interactions and feature splits. |
| **Isolation Forest** | Ensemble Tree Isolation | Unsupervised | **Unscaled** | Tabular spatial outlier detector; flags anomalous transactions without using fraud labels. |
| **Deep Autoencoder** | Bottleneck Deep Neural Net | Unsupervised (Normal-only) | **Scaled** (`feature_scaler.joblib`) | Deep feature reconstruction network; computes sample-wise MSE to detect novel zero-day patterns. |

---

## 2. Feature Inputs & Scaling Strategy

All models ingest the canonical **18-feature vector** defined in [`docs/FEATURE_ENGINEERING.md`](file:///c:/PRO/PBL%20SY/docs/FEATURE_ENGINEERING.md):
- **Raw Financial (5):** `amount`, `oldbalanceOrg`, `newbalanceOrig`, `oldbalanceDest`, `newbalanceDest`.
- **Domain Engineered (13):** `log_amount`, `is_transfer`, `is_cash_out`, `hour_of_day`, `hour_sin`, `hour_cos`, `is_night_transaction`, `orig_balance_error`, `orig_drain_ratio`, `is_full_liquidation`, `dest_balance_error`, `dest_drain_ratio`, `dest_zero_balance_anomaly`.

### Scaling Isolation Policy:
1. **Tree-Based Invariance (XGBoost & Isolation Forest):** Decision trees split on rank order and are mathematically invariant to monotonic transformations. They receive **unscaled features** to maintain maximum numerical precision and human interpretability.
2. **Gradient Descent Models (Logistic Regression & Deep Autoencoder):** Neural network backpropagation and regularized logistic regression require centered, unit-variance features. They receive **scaled features** transformed via the pre-fitted [`models/feature_scaler.joblib`](file:///c:/PRO/PBL%20SY/models/feature_scaler.joblib) (fitted strictly on the Train split; never refitted on validation or test).

---

## 3. Class Imbalance Strategy

In the fraud-modeling subspace (`TRANSFER` and `CASH_OUT`), the class distribution is:
- **Train Partition (Steps 1–520):** $2,647,948$ Legitimate vs $5,781$ Fraud $\rightarrow$ Imbalance Ratio = **$458.04 : 1$**.

### Handling Across Models:
1. **Logistic Regression:** Configured with `class_weight="balanced"`. Loss weights are inversely proportional to class frequencies:
   $$w_1 = \frac{N}{2 \cdot N_{\text{fraud}}} \approx 229.02, \quad w_0 = \frac{N}{2 \cdot N_{\text{legit}}} \approx 0.50$$
2. **XGBoost:** Configured with `scale_pos_weight = 458.04` dynamically computed from $N_{\text{neg}} / N_{\text{pos}}$. This scales the positive gradients during tree construction, forcing the objective function to heavily penalize false negatives.
3. **Synthetic Resampling Avoidance:** SMOTE and random oversampling are **strictly avoided**. In temporal financial transaction series, synthetic interpolation creates artificial timestamp combinations and alters real-world diurnal arrival rates.

---

## 4. Unsupervised Anomaly Detection Methodology

### A. Isolation Forest
- **Hypothesis:** Anomalous transactions (e.g., massive rapid liquidations at 3:00 AM) are few and structurally distinct, requiring fewer random axis-aligned splits to isolate in feature trees.
- **Training Policy:** Fitted strictly on $X_{\text{train}}$ **without access to $y_{\text{train}}$ labels**.
- **Anomaly Score Formulation:** Raw path lengths $s(x, n)$ are inverted and normalized:
  $$\text{Score}(x) = \frac{-s(x) - \min(-s)}{\max(-s) - \min(-s)} \in [0, 1]$$
  Higher scores indicate higher anomaly severity.

### B. PyTorch Deep Autoencoder
- **Architecture:** Symmetric 6-layer bottleneck autoencoder:
  $$\text{Input}(18) \rightarrow \text{Dense}(64) \rightarrow \text{Dense}(32) \rightarrow \text{Latent}(16) \rightarrow \text{Dense}(32) \rightarrow \text{Dense}(64) \rightarrow \text{Output}(18)$$
- **Activation & Regularization:** `LeakyReLU(0.1)`, `BatchNorm1d`, `AdamW` optimizer ($\text{lr} = 10^{-3}$, weight decay $= 10^{-5}$).
- **Training Policy (Normal-Only):** The autoencoder is trained **exclusively on legitimate transactions ($y == 0$)**. It learns the manifold of standard banking operations.
- **Anomaly Signal (Reconstruction MSE):** When an anomalous fraudulent transaction is passed through the network, the bottleneck cannot compress or reconstruct its unlearned characteristics, resulting in high Mean Squared Error:
  $$\text{MSE}(x) = \frac{1}{D} \sum_{j=1}^D (x_j - \hat{x}_j)^2$$
- **Score Calibration:** The reconstruction error distribution on legitimate validation data is recorded ($\mu_{\text{normal}}, \sigma_{\text{normal}}, P_{95}$). Scores are normalized using a sigmoid activation centered at $P_{95}$.

---

## 5. Decision Threshold Methodology

Decision thresholds are **NEVER hardcoded to 0.5**.
- Threshold optimization is performed **strictly on the Validation partition** (Steps 521–631).
- **Optimization Criterion:** Find threshold $\tau^*$ that maximizes the **$F_1$-Score** on validation data:
  $$\tau^* = \arg\max_\tau F_1(\tau) = \arg\max_\tau \frac{2 \cdot \text{Precision}(\tau) \cdot \text{Recall}(\tau)}{\text{Precision}(\tau) + \text{Recall}(\tau)}$$
- **Unbiased Test Evaluation:** The chosen validation threshold $\tau^*$ is then evaluated on the **unseen Test partition** (Steps 632–743). The test set is never used to tune or select $\tau^*$.

---

## 6. Evaluation Framework & Metrics

Because fraud datasets suffer from severe class imbalance, **raw accuracy is rejected**. The evaluation pipeline calculates:

1. **PR-AUC (Primary Metric):** Average precision under the Precision-Recall curve. Insensitive to true negatives; directly measures fraud precision at all recall levels.
2. **ROC-AUC:** Area under the Receiver Operating Characteristic curve. Measures ranking capability.
3. **Recall at Chosen Threshold:** Fraction of all actual fraud cases successfully blocked or reviewed.
4. **Precision at Chosen Threshold:** Fraction of flagged alerts that are genuinely fraudulent.
5. **False Positive Rate (FPR):** Fraction of legitimate customer transactions inconvenienced by false alarms ($FP / (FP + TN)$).
6. **Inference Latency:** Batch latency (1000 transactions) and single-sample latency in milliseconds.

---

## 7. Model Performance Comparison (Execution Placeholders)

*The developer will execute the training scripts manually. Actual empirical results will populate the tables below.*

### Validation Set Performance (Steps 521–631 | $N = 78,701$ | Fraud = $1,180$)

| Model Name | PR-AUC | ROC-AUC | Optimal Threshold ($\tau^*$) | Precision | Recall | $F_1$-Score | FPR (%) | Single Tx Latency (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression** | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* |
| **XGBoost Classifier** | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* |
| **Isolation Forest** | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* |
| **Deep Autoencoder** | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* |

### Test Set Performance (Steps 632–743 | $N = 37,979$ | Fraud = $1,252$)

| Model Name | PR-AUC | ROC-AUC | Precision (@ $\tau^*$) | Recall (@ $\tau^*$) | $F_1$-Score (@ $\tau^*$) | FPR (%) | True Positives (TP) | False Positives (FP) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression** | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* |
| **XGBoost Classifier** | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* |
| **Isolation Forest** | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* |
| **Deep Autoencoder** | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* | *Pending Execution* |

---

## 8. Reproducibility & Execution Protocol

To execute model training, run the following standalone CLI scripts in sequence from the project root:

```powershell
# 1. Train Logistic Regression Baseline
.\.venv\Scripts\python.exe scripts/train_logistic.py

# 2. Train XGBoost Supervised Classifier
.\.venv\Scripts\python.exe scripts/train_xgboost.py

# 3. Train Isolation Forest Anomaly Detector
.\.venv\Scripts\python.exe scripts/train_isolation_forest.py

# 4. Train Deep Autoencoder Anomaly Detector
.\.venv\Scripts\python.exe scripts/train_autoencoder.py
```
Each script will train the model, evaluate validation and test metrics, benchmark latency, print a summary report, and save the serialized weights and metadata to `models/`.
