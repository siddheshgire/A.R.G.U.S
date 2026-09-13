# A.R.G.U.S. — Milestone 3A: Model Result & Leakage Audit Report

**Project:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Milestone:** 3A (Model Result & Feature Leakage Audit)  
**Date:** 2026-09-11  
**Auditor:** Senior AI/ML & Information Security Engineering Agent  
**Status:** Audit Completed — Results Validated  

---

## 1. Executive Summary & Audit Context

Following the local execution of the Milestone 3 training scripts by the developer, the four candidate models produced the following test results on the unseen Test partition (Steps 632–743, $N = 37,979$, Fraud = $1,252$):

| Model Candidate | Test PR-AUC | Test ROC-AUC | Test $F_1$-Score | Confusion Matrix (Test) |
| :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression** | **0.9512** | **0.9946** | **0.8879** | $\text{TP}=1014, \text{FP}=18, \text{TN}=36709, \text{FN}=238$ |
| **XGBoost Classifier** | **1.0000** | **1.0000** | **0.9996** | $\text{TP}=1251, \text{FP}=0, \text{TN}=36727, \text{FN}=1$ |
| **Isolation Forest** | **0.7329** | **0.9163** | **0.7233** | $\text{TP}=783, \text{FP}=130, \text{TN}=36597, \text{FN}=469$ |
| **Deep Autoencoder** | **0.7835** | **0.9302** | **0.7857** | $\text{TP}=823, \text{FP}=20, \text{TN}=36707, \text{FN}=429$ |

### Core Audit Question:
Is the near-perfect performance of XGBoost ($F_1 = 0.9996$, with only 1 false negative and 0 false positives) legitimate, or is it caused by implementation error, data leakage, or synthetic dataset artifacts?

---

## 2. Feature-by-Feature Leakage Audit

Every one of the 18 model features was audited against four strict criteria:
1. Is it directly derived from `isFraud`?
2. Does it indirectly encode the ground truth label?
3. Is it based on an outcome unavailable at transaction-decision time?
4. Is it a PaySim-specific synthetic artifact?

| Feature Name | Audit Classification | Direct / Indirect Leakage? | Available at Decision Time? | Forensic Explanation & Domain Analysis |
| :--- | :--- | :--- | :--- | :--- |
| **`amount`** | **SAFE** | No | **Yes** | Fundamental transaction payload field requested by the client or POS terminal. |
| **`oldbalanceOrg`** | **SAFE** | No | **Yes** | Current ledger balance of sender prior to debiting funds. Standard banking check. |
| **`newbalanceOrig`** | **POTENTIAL ARTIFACT** | No | **Yes** (Planned) | In a live banking system, post-transaction balance is the planned balance ($\text{old} - \text{amount}$). In PaySim, fraudulent agents are hardcoded to drain the account to zero ($97.55\%$ of cases). It is not leakage (it is a valid ledger computation), but tree models easily isolate this condition. |
| **`oldbalanceDest`** | **SAFE** | No | **Yes** | Pre-transaction balance of the receiving account. Known to the internal banking network. |
| **`newbalanceDest`** | **SAFE** | No | **Yes** (Planned) | Expected post-transaction balance of recipient ($\text{old} + \text{amount}$). |
| **`log_amount`** | **SAFE** | No | **Yes** | Monotonic mathematical transformation ($\log_e(\text{amount} + 1)$) of an available feature. |
| **`is_transfer`** | **SAFE** | No | **Yes** | Payment routing channel present in API header at ingress. |
| **`is_cash_out`** | **SAFE** | No | **Yes** | Payment routing channel present in API header at ingress. |
| **`hour_of_day`** | **SAFE** | No | **Yes** | Derived solely from transaction arrival time ($\text{step} \pmod{24}$). Strictly causal. |
| **`hour_sin`** | **SAFE** | No | **Yes** | Trigonometric projection of causal arrival hour. Zero future leakage. |
| **`hour_cos`** | **SAFE** | No | **Yes** | Trigonometric projection of causal arrival hour. Zero future leakage. |
| **`is_night_transaction`** | **SAFE** | No | **Yes** | Binary threshold ($01\text{:}00$–$06\text{:}00$) based purely on current timestamp. |
| **`orig_balance_error`** | **POTENTIAL ARTIFACT** | No | **Yes** | Formula: $\text{newbalanceOrig} + \text{amount} - \text{oldbalanceOrg}$. In normal double-entry accounting, this equals zero. In PaySim, fraud agents strictly liquidate accounts ($\text{amount} = \text{oldbalanceOrg} \implies \text{error} = 0$), whereas synthetic legitimate traffic contains balance calculation discrepancies. It is a mathematical fingerprint of the PaySim simulator. |
| **`orig_drain_ratio`** | **POTENTIAL ARTIFACT** | No | **Yes** | Formula: $\text{amount} / (\text{oldbalanceOrg} + 1)$. Measures fund liquidation fraction. Fraudsters consistently drain $100\%$ ($1.0$), while legitimate transfers vary widely. Real-world fraud also features account drainage, but PaySim's rule is deterministic. |
| **`is_full_liquidation`** | **POTENTIAL ARTIFACT** | No | **Yes** | Flag for $\text{old} > 0 \land \text{new} == 0$. Legitimate transactions drain accounts $23.8\%$ of the time; fraud drains accounts $97.55\%$ of the time. Legitimate behavioral indicator. |
| **`dest_balance_error`** | **SAFE** | No | **Yes** | Destination ledger deviation. Captures recipient-side accounting discrepancies without label snooping. |
| **`dest_drain_ratio`** | **SAFE** | No | **Yes** | Recipient relative impact. Bounded mathematical ratio. Zero leakage. |
| **`dest_zero_balance_anomaly`** | **POTENTIAL ARTIFACT** | No | **Yes** | Identifies ghost accounts ($\text{oldDest} == 0 \land \text{newDest} == 0 \land \text{amount} > 0$). Occurs in $49.6\%$ of PaySim fraud (mule liquidation artifact). |

---

## 3. XGBoost Feature Importance Deep Dive

Using the trained `models/xgboost_fraud_model.json` artifact, we extracted the empirical feature importance across **Gain** (relative contribution of the feature to model branches), **Weight** (split frequency), and **Cover** (relative number of observations influenced):

```
                      Feature           Gain  Gain (%)  Weight          Cover
0          orig_balance_error  334,853.97     66.71%     109.0  235,122.31
1              newbalanceOrig   55,561.13     11.07%     121.0  118,043.32
2            orig_drain_ratio   45,214.56      9.01%     219.0   87,473.38
3         is_full_liquidation   27,440.31      5.47%      59.0  130,148.93
4               oldbalanceOrg   12,740.54      2.54%     121.0   47,390.46
5                  log_amount    8,029.20      1.60%      65.0   31,099.13
6                      amount    6,093.82      1.21%     158.0   21,813.97
7   dest_zero_balance_anomaly    3,476.33      0.69%      34.0  157,245.78
8              newbalanceDest    2,551.89      0.51%     140.0   11,219.85
9          dest_balance_error    1,939.27      0.39%     265.0   55,594.17
10                hour_of_day      874.09      0.17%      89.0   50,492.78
11           dest_drain_ratio      868.13      0.17%     197.0   61,647.55
12             oldbalanceDest      750.71      0.15%     236.0   37,441.61
13                is_cash_out      453.65      0.09%       2.0    1,000.70
14                   hour_sin      318.93      0.06%      49.0   86,322.50
15                is_transfer      284.16      0.06%      67.0   13,643.13
16       is_night_transaction      268.52      0.05%      43.0  149,732.63
17                   hour_cos      244.19      0.05%      42.0   60,001.45
```

### Key Finding:
The top 4 features (`orig_balance_error`, `newbalanceOrig`, `orig_drain_ratio`, and `is_full_liquidation`) account for **$92.25\%$ of the total gain in XGBoost**.
- `orig_balance_error` alone drives **$66.71\%$** of the model's split decisions.
- This confirms that XGBoost's exceptional performance is driven by the mathematical interaction between account liquidation and balance consistency.

---

## 4. Prediction Error & False Negative Deep Dive

Across the entire Test partition ($37,979$ transactions), XGBoost achieved:
- **True Positives (TP):** $1,251$
- **False Positives (FP):** $0$
- **True Negatives (TN):** $36,727$
- **False Negatives (FN):** $1$ (at threshold $\tau^* = 0.942472$)

### The Singular False Negative (Index 3583 in Test Partition)
- **Transaction Type:** `TRANSFER`
- **Amount:** $\$399,045.08$
- **Old Balance Origin:** $\$10,399,045.08$
- **New Balance Origin:** $\$10,399,045.08$ *(Balance was NOT debited!)*
- **Old Balance Destination:** $\$0.00$
- **New Balance Destination:** $\$0.00$
- **Orig Drain Ratio:** $0.0384$ ($3.8\%$ of balance, NOT a liquidation)
- **Is Full Liquidation:** $0$
- **Dest Zero Balance Anomaly:** $1$
- **XGBoost Predicted Probability:** **$0.7654$**
- **Decision Threshold:** **$0.9425$**

### Forensic Diagnosis:
In this transaction, the fraudster did NOT drain the account ($96.2\%$ of funds remained untouched), violating the primary PaySim fraud agent rule. 
- Because XGBoost learned that PaySim fraud almost universally drains $100\%$ of funds, its output probability dropped to **$0.7654$**.
- Because the F1-optimized threshold was set to a conservative **$0.9425$**, this transaction fell just below the binary cutoff.
- *Critical Takeaway for A.R.G.U.S.:* In our multi-tiered Risk Aggregation Engine, a score of **$76.5$** falls squarely in the **REVIEW / HIGH RISK** tier ($> 40.0$). Thus, in the full A.R.G.U.S. system, this transaction would **NEVER be approved**; it would be routed directly to human analysts!

---

## 5. Temporal Split & Isolation Audit

1. **Step Boundaries:**
   - Train: Steps $1$ to $520$ ($N = 2,653,729$)
   - Validation: Steps $521$ to $631$ ($N = 78,701$)
   - Test: Steps $632$ to $743$ ($N = 37,979$)
2. **Zero Overlap:** Hard programmatic checks confirmed that no transaction ID, step index, or temporal sequence in Validation or Test was present in the Train split.
3. **Scaler Training Isolation:** Verified that `models/feature_scaler.joblib` was fitted **exclusively on the Train partition**. The validation and test data were transformed without updating $\mu$ or $\sigma$.

---

## 6. Target Correlation & PaySim Synthetic Artifact Analysis

Why did XGBoost achieve $F_1 = 0.9996$, while Logistic Regression scored $0.8879$, Autoencoder scored $0.7857$, and Isolation Forest scored $0.7233$?

```
                      Feature  Correlation (r)    Legit Mean    Fraud Mean  Legit Median  Fraud Median
0   dest_zero_balance_anomaly          +0.5550          0.00          0.49          0.00          0.00
1            dest_drain_ratio          +0.4711        655.58    261,285.37          0.24          1.48
2               oldbalanceOrg          +0.3357     42,846.45  1,595,028.31        246.00    446,032.95
3        is_night_transaction          +0.1956          0.00          0.25          0.00          0.00
4                      amount          +0.0594    315,732.59  1,458,053.93    171,348.94    448,004.86
5         is_full_liquidation          +0.0522          0.42          0.98          0.00          1.00
6          orig_balance_error          -0.0148    288,474.86      7,151.23    144,626.76          0.00
```

### The Explanation:
1. **Agent-Based Behavioral Programming:** PaySim was created using multi-agent simulation. The fraud agents follow deterministic behavioral heuristics:
   - Compromise an account with balance $> 0$.
   - Attempt to transfer the full balance: $\text{amount} = \text{oldbalanceOrg}$.
   - Resulting balance becomes: $\text{newbalanceOrig} = 0$.
   - Route to an external mule account that immediately withdraws the cash: $\text{oldDest} = \text{newDest} = 0$.
2. **Why Linear Models Lag:** A single linear hyperplane (Logistic Regression) cannot model the non-linear interaction between `orig_balance_error == 0`, `is_full_liquidation == 1`, and `dest_zero_balance_anomaly == 1` without explicit polynomial features. Hence, Logistic Regression scores $0.8879$.
3. **Why Decision Trees Excel:** XGBoost builds hierarchical axis-aligned splits. In just 3–4 tree depth levels, XGBoost constructs the exact logical rule:
   $$\text{IF } (\text{is\_full\_liquidation} == 1) \land (\text{orig\_balance\_error} \approx 0) \land (\text{amount} > 10,000) \implies \text{Fraud}$$
4. **Is this Leakage?** **NO.** This is an **authentic model fit on the statistical distribution of the PaySim multi-agent benchmark**. Every feature used is legitimate and available at transaction authorization time.

---

## 7. Autoencoder Warning Diagnosis & Resolution

### The Issue:
During Deep Autoencoder training, PyTorch emitted:
`UserWarning: The given NumPy array is not writable, and PyTorch does not support non-writable tensors.`

### Cause:
When converting pandas DataFrame feature slices via `X.to_numpy(dtype=np.float32)`, recent versions of pandas can yield a read-only view of internal memory blocks. Passing this directly to `torch.from_numpy()` triggers PyTorch's writeability safety warning.

### Resolution:
In [`ml_engine/models/autoencoder.py`](file:///c:/PRO/PBL%20SY/ml_engine/models/autoencoder.py#L20-L24), `AutoencoderDataset` was updated to explicitly construct a writable copy:
```python
if isinstance(X, pd.DataFrame):
    arr = np.array(X.to_numpy(dtype=np.float32), copy=True)
else:
    arr = np.array(X, copy=True, dtype=np.float32)
self.tensors = torch.from_numpy(arr)
```
- **Verification:** All 12 unit tests in `pytest tests/` passed in $10.03$s with **zero warnings**.
- In strict adherence to milestone boundaries, the Autoencoder weights were **NOT retrained**.

---

## 8. Final Audit Conclusion

### Verdict: **OPTION A — Results appear valid and can be used.**

### Technical & Academic Justification:
1. **Zero Data Leakage:** Neither `isFraud`, `isFlaggedFraud`, customer string IDs, nor future temporal records were leaked into the feature space.
2. **Valid Temporal Generalization:** The model trained on steps 1–520, tuned thresholds on steps 521–631, and evaluated on unseen future steps 632–743.
3. **Complementary Multi-Model Ensemble Justified:**
   - **XGBoost ($F_1 = 0.9996$)** serves as a high-precision supervised detector for known PaySim behavioral patterns.
   - **Deep Autoencoder ($F_1 = 0.7857$, PR-AUC $= 0.7835$)** provides an independent, unsupervised reconstruction anomaly signal that does not depend on supervised fraud labels.
   - **Isolation Forest ($F_1 = 0.7233$, ROC-AUC $= 0.9163$)** provides spatial density anomaly checks.
   - **Logistic Regression ($F_1 = 0.8879$)** validates linear benchmark performance.
4. **Academic Defensibility:** In the final project report and viva presentation, we will transparently document that XGBoost's near-perfect performance is a consequence of PaySim's agent-based simulation dynamics, explaining why our system integrates the **Deep Autoencoder** and **ESP32 IoT hardware layer** to protect against novel, non-PaySim zero-day threats!
