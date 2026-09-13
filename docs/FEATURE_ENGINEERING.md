# A.R.G.U.S. — Feature Engineering Manifest & Pipeline Specification

**Project:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Milestone:** 2 (Feature Engineering + Temporal Dataset Split)  
**Document:** `docs/FEATURE_ENGINEERING.md`  
**Package Implementation:** [`ml_engine/features/`](file:///c:/PRO/PBL%20SY/ml_engine/features/)  
**Execution Script:** [`scripts/build_paysim_features.py`](file:///c:/PRO/PBL%20SY/scripts/build_paysim_features.py)  

---

## 1. Feature Engineering Overview

The A.R.G.U.S. feature pipeline transforms raw financial transaction data into an 18-dimensional numerical feature space. The pipeline is engineered to satisfy the operational requirements of both **tree-based classifiers** (XGBoost, Isolation Forest) and **deep neural networks** (Deep Autoencoder):

1. **Numerical Safety:** Every engineered metric includes zero-division guards and epsilon clipping, guaranteeing zero `NaN` or `Infinite` values.
2. **Leakage Prevention:** Ground truth targets, simulation rule artifacts, and future temporal sequences are strictly isolated from the feature matrix.
3. **Domain Grounding:** Features explicitly capture financial ledger consistency, diurnal cycle dynamics, account liquidation behavior, and mule destination anomalies.

---

## 2. Complete Feature Manifest

The model feature matrix $X$ consists of **18 continuous and binary features** (5 raw financial quantities + 13 domain-engineered features):

| Feature Name | Formula / Transformation Method | Source Columns | Purpose / Domain Rationale | Leakage Risk & Safeguard |
| :--- | :--- | :--- | :--- | :--- |
| **`amount`** | Raw numerical float | `amount` | Base transaction monetary magnitude. | None. Present at initiation. |
| **`oldbalanceOrg`** | Raw numerical float | `oldbalanceOrg` | Pre-transaction liquidity of the originator. | None. Historic ledger balance. |
| **`newbalanceOrig`** | Raw numerical float | `newbalanceOrig` | Post-transaction balance of the originator. | Monitored via `orig_balance_error` to prevent artificial cutoff overfitting. |
| **`oldbalanceDest`** | Raw numerical float | `oldbalanceDest` | Pre-transaction balance of the recipient. | None. Known at routing time. |
| **`newbalanceDest`** | Raw numerical float | `newbalanceDest` | Post-transaction balance of the recipient. | Monitored via `dest_balance_error`. |
| **`log_amount`** | $\log_e(\text{amount} + 1.0)$ | `amount` | Compresses extreme positive skew in monetary amounts; stabilizes gradient descent in Deep Autoencoders. | None. Monotonic transformation of current amount. |
| **`is_transfer`** | $\mathbb{I}(\text{type} == \text{'TRANSFER'})$ | `type` | Encodes transfer transaction mode (high fraud concentration). | None. Header attribute available at ingress. |
| **`is_cash_out`** | $\mathbb{I}(\text{type} == \text{'CASH_OUT'})$ | `type` | Encodes cash-out liquidation mode (final fraud stage). | None. Header attribute available at ingress. |
| **`hour_of_day`** | $\text{step} \pmod{24}$ | `step` | Diurnal hour of day ($0$ to $23$). Captures human circadian patterns. | None. Causal time mapping. |
| **`hour_sin`** | $\sin\left(\frac{2\pi \cdot \text{hour\_of\_day}}{24}\right)$ | `step` | Continuous circular sine representation; preserves continuity between 23:00 and 00:00. | None. Smooth mathematical projection. |
| **`hour_cos`** | $\cos\left(\frac{2\pi \cdot \text{hour\_of\_day}}{24}\right)$ | `step` | Continuous circular cosine representation of time. | None. Smooth mathematical projection. |
| **`is_night_transaction`** | $\mathbb{I}(1 \le \text{hour\_of\_day} \le 6)$ | `step` | Flags early morning operations ($01\text{:}00$–$06\text{:}00$), where PaySim fraud concentration surges from $0.08\%$ to $22.3\%$. | None. Determined solely by current transaction timestamp. |
| **`orig_balance_error`** | $\text{newbalanceOrig} + \text{amount} - \text{oldbalanceOrg}$ | `newbalanceOrig`, `amount`, `oldbalanceOrg` | Quantifies deviation from double-entry balance accounting on the sender side. | None. Captures ledger manipulation without hard thresholds. |
| **`orig_drain_ratio`** | $\frac{\text{amount}}{\text{oldbalanceOrg} + 1.0}$ | `amount`, `oldbalanceOrg` | Fraction of total sender balance liquidated. Values $\approx 1.0$ indicate total account drainage ($+1.0$ epsilon prevents zero-division). | None. Uses pre-transaction funds and transfer amount. |
| **`is_full_liquidation`** | $\mathbb{I}(\text{oldbalanceOrg} > 0 \land \text{newbalanceOrig} == 0)$ | `oldbalanceOrg`, `newbalanceOrig` | Binary flag for complete account liquidation (observed in $97.55\%$ of PaySim fraud cases). | Evaluated alongside balance errors to prevent false alarms on routine zeroings. |
| **`dest_balance_error`** | $\text{oldbalanceDest} + \text{amount} - \text{newbalanceDest}$ | `oldbalanceDest`, `amount`, `newbalanceDest` | Quantifies deviation from expected balance addition on the recipient side. | None. Detects downstream ledger anomalies. |
| **`dest_drain_ratio`** | $\frac{\text{amount}}{\text{newbalanceDest} + 1.0}$ | `amount`, `newbalanceDest` | Ratio of transferred amount relative to recipient ending balance. | None. Bound within $[0, 10^6]$ to avoid numerical instability. |
| **`dest_zero_balance_anomaly`** | $\mathbb{I}(\text{oldDest} == 0 \land \text{newDest} == 0 \land \text{amount} > 0)$ | `oldbalanceDest`, `newbalanceDest`, `amount` | Flags transactions routed to ghost/mule destination accounts where balances remain zero despite fund arrival ($49.6\%$ of fraud). | None. Characteristic marker of mule intermediary accounts. |

---

## 3. Target Definition

| Column | Role | Data Type | Description |
| :--- | :--- | :--- | :--- |
| **`isFraud`** | **Ground Truth Target ($y$)** | `int8` ($0$ or $1$) | Label indicating actual simulated fraud. **Strictly isolated as the dependent variable and NEVER included in $X$.** |

---

## 4. Excluded Features & Rationale

| Excluded Column | Category | Reason for Exclusion from ML Feature Matrix |
| :--- | :--- | :--- |
| **`isFlaggedFraud`** | Target Leakage / Rule Artifact | An artificial rule embedded in the simulator that flags transfers $> 200,000$. It flags only 16 rows across 6.36 million transactions, misses $99.8\%$ of actual fraud, and represents a downstream policy output rather than a transaction characteristic. |
| **`nameOrig`** | High Cardinality String | 6,353,307 unique IDs with $99.85\%$ appearing exactly once. Feeding raw string IDs into ML models causes severe memorization, massive dimensionality explosion, and zero generalization. Reserved for relational DBMS primary/foreign keys. |
| **`nameDest`** | High Cardinality String | 2,722,362 unique IDs. Similar high-cardinality hazard. Merchant distinctions are cleanly captured by transaction type. Reserved for DBMS routing and behavioral profiling. |
| **`type`** | Categorical String | Replaced by clean binary indicators `is_transfer` and `is_cash_out`. |
| **`step`** | Raw Integer Counter | Raw monotonically increasing counter causes linear tree split drift. Replaced by cyclical features (`hour_sin`, `hour_cos`, `hour_of_day`, `is_night_transaction`). Retained solely in metadata for chronological dataset partitioning. |

---

## 5. Behavioral Features Strategy

In Milestone 1, entity profiling revealed that **$99.85\%$ of originators in PaySim execute only 1 transaction** (maximum observed was 3). 
- Computing offline rolling aggregates (e.g., 7-day velocity or sender rolling average) across the static PaySim CSV yields near-zero variance for individual customers and introduces serious risk of temporal target leakage if not partitioned with an event-time streaming engine.
- **Milestone 2 Decision:** Transaction-level behavioral risk indicators (`orig_drain_ratio`, `is_full_liquidation`, `dest_zero_balance_anomaly`, `is_night_transaction`) are implemented directly. Stateful multi-transaction customer profiling is architecturally assigned to the live PostgreSQL / Redis state manager in Milestone 8, where historical windows can be calculated causal-only at request ingress.

---

## 6. Scaling & Normalization Protocol

1. **Isolation from Validation/Test Data:** Scalers must NEVER see validation or test samples prior to inference.
2. **Fitted Model:** A `StandardScaler` from scikit-learn is fitted **strictly on the Train partition ($X_{\text{train}}$)**.
3. **Artifact Serialization:** The fitted scaler is saved to [`models/feature_scaler.joblib`](file:///c:/PRO/PBL%20SY/models/feature_scaler.joblib).
4. **Model Application:**
   - **XGBoost & Isolation Forest:** Train directly on unscaled features (tree models are invariant to monotonic feature scale).
   - **Deep Autoencoder:** Transformed via the serialized `feature_scaler.joblib` to center features ($\mu = 0, \sigma = 1$) for stable MSE reconstruction loss backpropagation.
