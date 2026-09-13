# A.R.G.U.S. — Risk Scoring & Decision Engine Specification

**Project:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Milestone:** 4 (Risk Scoring & Decision Engine)  
**Document:** `docs/RISK_ENGINE.md`  
**Status:** Implemented, Validated & Tested  

---

> [!NOTE]
> *The initial weights and thresholds are configurable engineering baselines and are not claimed to be globally optimal.*

---

## 1. Purpose & Scope

The A.R.G.U.S. Risk Scoring and Decision Engine synthesizes the predictions and anomaly signals from four distinct machine learning and deep learning models into a single, calibrated **Risk Score (0–100)**. The engine transforms this continuous risk metric into actionable operational directives:

- **APPROVE** (Low Risk $\rightarrow$ Automated instant processing)
- **REVIEW** (Medium Risk $\rightarrow$ Queued for human fraud analyst investigation)
- **BLOCK** (High Risk $\rightarrow$ Automated transaction rejection & account security lockdown)

The engine is engineered as a modular, deterministic, explainable subsystem designed for seamless integration into the upcoming FastAPI backend and PostgreSQL persistence layer.

---

## 2. Engine Architecture

```
[Transaction Feature Vector X (18 features)]
                     │
     ┌───────────────┼───────────────┬───────────────┐
     ▼               ▼               ▼               ▼
[XGBoost]    [Deep Autoencoder] [Isolation Forest] [Logistic Reg]
 P(fraud)        Norm MSE          Score [0,1]       P(fraud)
     │               │               │               │
     ▼ (w=0.50)      ▼ (w=0.20)      ▼ (w=0.15)      ▼ (w=0.15)
     └───────────────┼───────────────┴───────────────┘
                     ▼
          [Risk Score Aggregator]
       Risk Score = Sum(w_i * S_i) * 100
                     │
                     ▼ (Risk Score: 0.0 to 100.0)
          [Decision Policy Engine]
                     │
     ┌───────────────┼───────────────┐
     ▼               ▼               ▼
  APPROVE         REVIEW           BLOCK
 (Score < 40)   (40 <= Score < 70)  (Score >= 70)
     │               │               │
     └───────────────┼───────────────┘
                     ▼
         [Explanation Synthesizer]
   (Factual Model Signals + Feature Rules)
                     │
                     ▼
          [RiskAssessment Entity]
```

---

## 3. Model Signal Definitions

The four models provide complementary signals across supervised and unsupervised domains:

1. **XGBoost ($S_{\text{xgb}} \in [0.0, 1.0]$):**
   - *Meaning:* Supervised conditional fraud probability $P(\text{fraud} \mid X)$.
   - *Strength:* High-capacity gradient boosting capturing non-linear balance discrepancies and account liquidation heuristics.
2. **Deep Autoencoder ($S_{\text{ae}} \in [0.0, 1.0]$):**
   - *Meaning:* Deep reconstruction anomaly severity based on sample-wise Mean Squared Error ($\text{MSE}$).
   - *Strength:* Trained exclusively on legitimate transactions ($y == 0$); detects subtle deviations from normal banking operations independently of supervised fraud labels.
3. **Isolation Forest ($S_{\text{if}} \in [0.0, 1.0]$):**
   - *Meaning:* Unsupervised tree isolation path length normalized via training distribution extrema.
   - *Strength:* Identifies multi-dimensional geometric outliers without assuming functional form.
4. **Logistic Regression ($S_{\text{lr}} \in [0.0, 1.0]$):**
   - *Meaning:* Calibrated linear benchmark probability using balanced class weights.
   - *Strength:* Well-conditioned linear baseline resistant to high-dimensional overfitting.

---

## 4. Signal Normalization Strategy

To combine signals safely, all raw outputs are transformed into a standard $[0.0, 1.0]$ scale where $1.0$ represents maximum fraud risk:

| Model | Raw Output | Transformation to Normalized Signal $S \in [0.0, 1.0]$ | Normalization Parameters |
| :--- | :--- | :--- | :--- |
| **XGBoost** | Positive class probability | Identity: $S_{\text{xgb}} = \text{clip}(P(\text{fraud} \mid X), 0.0, 1.0)$ | Direct probability mapping |
| **Logistic Regression** | Positive class probability | Identity: $S_{\text{lr}} = \text{clip}(P(\text{fraud} \mid X), 0.0, 1.0)$ | Direct probability mapping |
| **Isolation Forest** | Decision path length $s(x)$ | Inversion & Min-Max: $S_{\text{if}} = \frac{-s(x) - \min(-s_{\text{train}})}{\max(-s_{\text{train}}) - \min(-s_{\text{train}})}$ | Learned from Train split: $[\min=0.3395, \max=0.7949]$ |
| **Deep Autoencoder** | Per-sample MSE: $\frac{1}{D}\sum (x - \hat{x})^2$ | Validation Sigmoid: $S_{\text{ae}} = \frac{1}{1 + \exp\left(-\frac{\text{MSE} - P_{95}}{\sigma}\right)}$ | Learned from Normal Validation: $[P_{95}=0.0090, \sigma=0.0143]$ |

---

## 5. Initial Weights & Rationale

$$\sum w_i = w_{\text{xgb}} + w_{\text{ae}} + w_{\text{if}} + w_{\text{lr}} = 0.50 + 0.20 + 0.15 + 0.15 = 1.00$$

### Engineering Justification:
1. **$w_{\text{xgb}} = 0.50$ (Primary Weight):** XGBoost demonstrates exceptional discrimination on tabular financial features ($F_1 = 0.9996$, PR-AUC $= 0.9997$ on validation data), justifying its role as the primary supervised anchor.
2. **$w_{\text{ae}} = 0.20$ (Deep Learning Pillar):** The Deep Autoencoder operates without label supervision and directly fulfills the academic Deep Learning mandate. Giving it $20\%$ weight ensures that novel zero-day patterns unlearned by supervised models can elevate the risk score into the REVIEW queue.
3. **$w_{\text{if}} = 0.15$ (Unsupervised Spatial Density):** Isolation Forest provides complementary tree-based anomaly isolation, checking whether transactions fall into sparse feature regions.
4. **$w_{\text{lr}} = 0.15$ (Linear Regularizer):** Logistic Regression acts as a stable regularizer against extreme tree split boundaries.

---

## 6. Risk Score Formulation

$$\text{Aggregated Risk} = w_{\text{xgb}} S_{\text{xgb}} + w_{\text{ae}} S_{\text{ae}} + w_{\text{if}} S_{\text{if}} + w_{\text{lr}} S_{\text{lr}}$$
$$\text{ARGUS Risk Score} = \text{round}\left(\text{clip}\left(\text{Aggregated Risk} \times 100.0, 0.0, 100.0\right), 2\right)$$

- **Domain:** Continuous float bounded within $[0.00, 100.00]$.
- **Interpretation:** A normalized index of transaction risk combining statistical anomaly signals and supervised classification probability.

---

## 7. Decision Policy & Thresholds

| Decision Action | Score Range | Operational Meaning | Action in Full System |
| :--- | :--- | :--- | :--- |
| **`APPROVE`** | $\text{Score} < 40.0$ | Low Risk: Standard operational behavior. | Immediate transaction authorization. |
| **`REVIEW`** | $40.0 \le \text{Score} < 70.0$ | Moderate Risk: Suspicious or anomalous pattern. | Transaction held; routed to human analyst review portal. |
| **`BLOCK`** | $\text{Score} \ge 70.0$ | High Risk: Severe anomaly or high fraud confidence. | Transaction rejected; automated terminal/account alert generated. |

---

## 8. Validation Performance (Empirical Audit)

Evaluated on the full Validation partition ($N = 78,701$ transactions, Fraud $= 1,180$ cases, Steps 521–631):

### Decision Distribution & Fraud Capture:
```
Decision   | Total Tx   | % of Total | Legitimate   | Fraud    | Fraud Density 
----------------------------------------------------------------------
APPROVE    | 77,473     |    98.44% | 77,472       | 1        |         0.00%
REVIEW     | 165        |     0.21% | 49           | 116      |        70.30%
BLOCK      | 1,063      |     1.35% | 0            | 1,063    |       100.00%
----------------------------------------------------------------------
Total Fraud Detected (Review + Block): 1,179 / 1,180 (99.92% Recall)
Fraud Immediately Blocked:            1,063 / 1,180 (90.08% Block Recall)
Legitimate Traffic Disruption (FPR):   0.063% (49 legitimate transactions flagged for review)
```

### Key Operational Findings:
1. **$99.92\%$ Fraud Capture Rate:** Out of 1,180 fraud cases, $1,179$ were caught ($1,063$ blocked outright, $116$ held for review).
2. **Zero False Blocks:** Exactly $0$ legitimate transactions received a score $\ge 70.0$.
3. **Manageable Analyst Queue:** Only $165$ transactions ($0.21\%$ of total volume) were routed to the review queue, with a remarkable **$70.3\%$ fraud density**.
4. **Ensemble Ranking Performance:** The aggregated ensemble achieved **$\text{PR-AUC} = 1.0000$** and **$\text{ROC-AUC} = 1.0000$** on the validation partition.

---

## 9. Business Rule Fast Path (Non-Modeled Types)

In Milestone 1, empirical analysis proved that PaySim transactions of type `PAYMENT`, `CASH_IN`, and `DEBIT` contain **0 fraud cases** across 6.36 million rows.
- In the full A.R.G.U.S. pipeline, routing these types through 4 ML/DL models is computationally wasteful and increases latency.
- **Fast Path Policy:**
  - If `type` $\in \{\text{'PAYMENT'}, \text{'CASH_IN'}, \text{'DEBIT'}\}$ and $\text{amount} < \$500,000.00$:
    $\rightarrow$ Assessed as $\text{Score} = 5.0$, `DecisionAction.APPROVE`.
  - If `amount} \ge \$500,000.00$ (extraordinary transfer):
    $\rightarrow$ Assessed as $\text{Score} = 45.0$, `DecisionAction.REVIEW` for analyst verification.

---

## 10. Explainability Architecture

Every `RiskAssessment` domain object generates factual, human-readable explanations that strictly separate:
1. **Model Signals:**
   - *"High supervised fraud probability detected by XGBoost (95.54%)."*
   - *"Significant feature reconstruction anomaly flagged by Deep Autoencoder (82.10%)."*
   - *"Unsupervised spatial density outlier detected by Isolation Forest (64.30%)."*
2. **Observable Feature Patterns:**
   - *"Account liquidation pattern detected: 100% of origin account balance drained to zero."*
   - *"Mule recipient anomaly: Destination account balance remains zero despite inbound transfer."*
   - *"Nighttime execution: Transaction initiated during high-fraud window (01:00–06:00)."*
   - *"Sender ledger balance discrepancy of $399,045.08 detected."*

---

## 11. Known Limitations & Future Improvements

1. **Static Weights:** Current weights are statically configured. Milestone 7 could explore dynamic risk gating (e.g., if Deep Autoencoder anomaly score is extreme, boost risk even if supervised model confidence is moderate).
2. **IoT Hardware Penalty:** Physical ESP32 telemetry (tamper switch status, HMAC signature failure) is not yet factored into the calculation. Milestone 10 will add direct IoT security penalty points (+30 to +50 points) to the score.
