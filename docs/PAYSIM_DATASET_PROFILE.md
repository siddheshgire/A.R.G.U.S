# PaySim Dataset Profile & Exploratory Data Analysis

**Project:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Milestone:** 1 (Dataset Inspection & Exploratory Data Analysis)  
**Dataset Source:** `data/raw/paysim.csv` (SHA-verified local file, 493,534,783 bytes)  
**Document:** `docs/PAYSIM_DATASET_PROFILE.md`  
**Execution Tool:** [`scripts/inspect_paysim.py`](file:///c:/PRO/PBL%20SY/scripts/inspect_paysim.py)  

---

## 1. Dataset Overview

PaySim is an agent-based financial simulator developed by Edgar Lopez-Rojas et al. (Blekinge Institute of Technology, Sweden), parameterized by aggregated statistical distributions extracted from real-world mobile financial transaction logs. 

The dataset captures 30.95 days (743 simulated hours) of mobile money operations across customer-to-customer transfers, merchant payments, cash-ins, and cash-outs.

---

## 2. Dataset Dimensions

- **Total Transactions (Rows):** `6,362,620`
- **Total Features (Columns):** `11`
- **Raw File Size:** `470.67 MB` (493,534,783 bytes)
- **In-Memory Size (Pandas Optimized):** `1,007.05 MB`
- **Execution Runtime of Full Profiling:** `52.23 seconds`

---

## 3. Schema & Column Specifications

| Column Name | Data Type | Description | Unique Values | Missing Values (%) | Observed Range / Examples |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`step`** | `int32` | Maps simulation hour from start ($1 \text{ step} = 1 \text{ hour}$) | 743 | 0 (0.00%) | 1 to 743 (~31 days) |
| **`type`** | `category` | Transaction category (5 distinct types) | 5 | 0 (0.00%) | `CASH_IN`, `CASH_OUT`, `DEBIT`, `PAYMENT`, `TRANSFER` |
| **`amount`** | `float64` | Transaction monetary value in local currency | 5,316,900 | 0 (0.00%) | $0.00 to $92,445,516.64 |
| **`nameOrig`** | `string` | Customer account identifier initiating the transaction | 6,353,307 | 0 (0.00%) | Prefixed with `C` (e.g., `C1231006815`) |
| **`oldbalanceOrg`** | `float64` | Initial balance of sender before transaction | 1,845,844 | 0 (0.00%) | $0.00 to $59,585,040.37 |
| **`newbalanceOrig`** | `float64` | Final balance of sender after transaction | 2,682,586 | 0 (0.00%) | $0.00 to $49,585,040.37 |
| **`nameDest`** | `string` | Recipient account identifier (Customer or Merchant) | 2,722,362 | 0 (0.00%) | Prefixed with `C` (customer) or `M` (merchant) |
| **`oldbalanceDest`** | `float64` | Initial balance of recipient before transaction | 3,614,697 | 0 (0.00%) | $0.00 to $356,015,889.35 |
| **`newbalanceDest`** | `float64` | Final balance of recipient after transaction | 3,555,499 | 0 (0.00%) | $0.00 to $356,179,278.92 |
| **`isFraud`** | `int8` | Ground truth binary fraud target (`1` = Fraud, `0` = Legitimate) | 2 | 0 (0.00%) | `0` or `1` |
| **`isFlaggedFraud`** | `int8` | Simulator heuristic rule flagging transfers $> 200,000$ | 2 | 0 (0.00%) | `0` or `1` (Only 16 positive cases) |

---

## 4. Data Quality Assessment

- **Missing Values:** **0 missing values** across all 11 columns (100% complete dataset).
- **Exact Duplicate Rows:** **0 duplicate rows** found across all 6,362,620 transactions.
- **Constant / Near-Constant Columns:**
  - `isFlaggedFraud` is near-constant: 6,362,604 zeros and only 16 ones (99.9997% constant).
- **Unusual / Extreme Values:**
  - `amount == 0.00`: Found in 16 fraudulent transactions. In these cases, fraudsters attempted to execute transfers after already liquidating the sender account.
  - Maximum transaction amount: $92,445,516.64 (legitimate transfer).

---

## 5. Target Distribution (`isFraud`)

- **Legitimate Transactions (`0`):** `6,354,407` (**99.8709%**)
- **Fraudulent Transactions (`1`):** `8,213` (**0.1291%**)
- **Class Imbalance Ratio:** **773.7 : 1** (For every 1 fraudulent transaction, there are approximately 774 legitimate transactions).

### Academic & Operational Implications
Raw accuracy is a meaningless evaluation metric on this dataset. A trivial model predicting all zeros achieves 99.87% accuracy while completely failing to detect fraud. A.R.G.U.S. must rely on:
- **Precision-Recall AUC (PR-AUC)**
- **Recall at constrained False Positive Rates (FPR)**
- **F1-Score on the fraud class**

---

## 6. Transaction Type Analysis

Empirical breakdown across all 5 transaction categories:

| Transaction Type | Total Count | % of All Transactions | Fraud Count | Fraud Rate (%) | Amount Median ($) | Amount Mean ($) | Amount Max ($) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`CASH_OUT`** | 2,237,500 | 35.17% | **4,116** | **0.1840%** | $147,072.19 | $176,273.96 | $10,000,000.00 |
| **`PAYMENT`** | 2,151,495 | 33.81% | 0 | 0.0000% | $9,482.19 | $13,057.60 | $238,637.98 |
| **`CASH_IN`** | 1,399,284 | 21.99% | 0 | 0.0000% | $143,427.71 | $168,920.24 | $1,915,267.90 |
| **`TRANSFER`** | 532,909 | 8.38% | **4,097** | **0.7688%** | $486,308.39 | $910,647.01 | $92,445,516.64 |
| **`DEBIT`** | 41,432 | 0.65% | 0 | 0.0000% | $3,048.99 | $5,483.67 | $569,077.51 |

### Critical Behavioral Findings:
1. **Zero Fraud in `PAYMENT`, `CASH_IN`, `DEBIT`:** 100% of all 8,213 fraud cases occur exclusively within `TRANSFER` (4,097) and `CASH_OUT` (4,116).
2. **The Fraud Modus Operandi:** Fraudsters compromise an account, execute an unauthorized `TRANSFER` to a mule account, and immediately execute a `CASH_OUT` to liquidate the stolen funds outside the banking network.
3. **Filtering Strategy:** When training supervised classifiers and deep autoencoders in Milestone 3+, we can filter the training space to `TRANSFER` and `CASH_OUT` transactions (total 2,770,409 rows), increasing model sensitivity and cutting computational overhead by 56%.

---

## 7. Temporal Dynamics (`step`)

- **Range:** Step 1 to Step 743 (743 hours = 30.95 days).
- **Diurnal Behavior:** 
  - Transaction volume follows a distinct diurnal curve: Daytime peak (12:00–17:00) sees ~440,000 to 480,000 transactions per hour.
  - Night trough (02:00–05:00) drops to 1,200 to 9,000 transactions per hour.
- **Night Fraud Spike:**
  - While legitimate volume drops sharply at night, fraud attempts remain steady (~300–370 fraud attempts per hour regardless of time of day).
  - Consequently, **the fraud rate during early morning hours (03:00–05:00) spikes to 16.2% – 22.3%** compared to **0.08% at midday**.
  - *Engineering Action:* Cyclical time encoding ($\sin / \cos$ of hour) and night transaction flags will be high-importance features in the risk engine.

---

## 8. Transaction Amount Analysis

| Statistic | All Transactions ($) | Fraud Transactions ($) | Ratio (Fraud / All) |
| :--- | :--- | :--- | :--- |
| **Count** | 6,362,620 | 8,213 | — |
| **Mean** | $179,861.90 | $1,467,967.30 | **8.16x** |
| **Standard Deviation** | $603,858.23 | $2,404,252.95 | 3.98x |
| **Minimum** | $0.00 | $0.00 | — |
| **25th Percentile** | $13,389.57 | $127,091.33 | 9.49x |
| **Median (50th)** | $74,871.94 | $441,423.44 | **5.90x** |
| **75th Percentile** | $208,721.48 | $1,517,771.48 | 7.27x |
| **Maximum** | $92,445,516.64 | $10,000,000.00 | (Capped at 10M in simulation) |

Fraud amounts are substantially larger than legitimate transactions across all quartiles, with a median fraud amount roughly 6x higher. In the simulation, individual fraud transactions are capped at $10,000,000.00.

---

## 9. Balance Consistency Analysis

In a standard ledger, balances satisfy:
1. Origin Balance: $\text{oldbalanceOrg} - \text{amount} = \text{newbalanceOrig}$
2. Destination Balance: $\text{oldbalanceDest} + \text{amount} = \text{newbalanceDest}$

Empirical validation results:
- **Origin Exact Balance Match:** Only **20.14%** (1,281,435 / 6,362,620) match the expected balance arithmetic.
- **Destination Exact Balance Match:** Only **34.17%** (2,173,973 / 6,362,620) match.

### Account Liquidation Behavior:
- **Condition:** $\text{oldbalanceOrg} > 0 \text{ and } \text{newbalanceOrig} == 0$ (Account completely drained).
- **Legitimate Transactions:** Occurs in **23.80%** of transactions.
- **Fraudulent Transactions:** Occurs in **97.55%** of transactions (8,012 out of 8,213).
- *Finding:* In 97.55% of fraud cases, the perpetrator attempts to drain 100% of the available funds in a single transaction.

### Destination Zero-Balance Anomaly:
- In **49.63% of fraudulent transactions** (4,076 / 8,213), both `oldbalanceDest == 0` and `newbalanceDest == 0` despite hundreds of thousands of dollars being transferred. This occurs in the PaySim simulator when funds are transferred to an external mule account that immediately liquidates the cash.

---

## 10. Entity Analysis (`nameOrig` & `nameDest`)

- **Unique Senders (`nameOrig`):** `6,353,307` unique IDs across 6,362,620 rows.
  - Senders with $>1$ transaction: Only `9,298` (0.146%).
  - Maximum transactions by a single sender: `3`.
  - Average transactions per sender: `1.001`.
- **Unique Destinations (`nameDest`):** `2,722,362` unique IDs.
  - Average transactions per destination: `2.34`.
- **Merchant Destinations (`M...` prefix):**
  - Directed to merchants: `2,151,495` (33.81% of all transactions).
  - Fraud transactions directed to merchants: **0 (0.0000%)**.
  - All merchant destinations belong exclusively to the `PAYMENT` transaction type.
  - Fraudsters exclusively route money between customer accounts (`C...` to `C...`), never to merchant terminals (`M...`).

### Machine Learning Modeling Implication:
Feeding raw string IDs (`nameOrig`, `nameDest`) as one-hot or categorical features into an ML model is an anti-pattern (high cardinality, near-zero repetition per sender). Instead, entity identifiers must be used in PostgreSQL for relational joins and to compute behavioral aggregations.

---

## 11. Target Leakage Investigation

| Feature / Artifact | Reason for Concern | Empirical Evidence from PaySim | Final Decision for A.R.G.U.S. |
| :--- | :--- | :--- | :--- |
| **`isFlaggedFraud`** | Directly represents simulation heuristic rule targeting large transfers ($>200,000$). | Cross-tabulation shows it flags only 16 rows (all 16 are fraud). It is an outcome rule, not an inherent transaction property. | **EXCLUDE completely.** Using this causes direct target leakage and introduces an ungeneralizable rule artifact into models. |
| **`newbalanceOrig == 0`** | 97.55% of frauds drain account to zero; models could trivially overfit to `newbalanceOrig == 0`. | Legitimate accounts also drain to zero 23.8% of the time (e.g. routine bill payments). Blindly splitting on `newbalanceOrig == 0` generates high false positives. | **TRANSFORM via Balance Error.** Do not use raw balance as a hard filter; engineer `orig_balance_error` and `orig_drain_ratio`. |
| **`oldbalanceDest == newbalanceDest == 0`** | Destination accounts with zero balances before and after large transfers occur in 49.6% of frauds. | Characteristic of mule account creation in PaySim. | **KEEP as engineered interaction feature.** (`dest_zero_balance_anomaly = (oldDest == 0) & (newDest == 0) & (amount > 0)`). |
| **Temporal Sequence (`step`)** | Random k-fold cross-validation leaks future transaction patterns into past training. | Transactions evolve over 743 hours. Splitting randomly allows a model to learn from future steps to predict past ones. | **ENFORCE Temporal Train/Val/Test Split.** Use steps 1–500 for training, 501–620 for validation, and 621–743 for testing. |

---

## 12. Candidate Feature Engineering Ideas for Milestone 2

Based on our empirical analysis, the following 14 candidate features will be evaluated for the feature engineering pipeline:

1. **`orig_balance_error`:** $\text{newbalanceOrig} + \text{amount} - \text{oldbalanceOrg}$ (quantifies mathematical discrepancy in sender account).
2. **`dest_balance_error`:** $\text{oldbalanceDest} + \text{amount} - \text{newbalanceDest}$ (quantifies destination discrepancy).
3. **`orig_drain_ratio`:** $\frac{\text{amount}}{\text{oldbalanceOrg} + 1.0}$ (measures proportion of total account balance liquidated; values near 1.0 signal liquidation).
4. **`dest_drain_ratio`:** $\frac{\text{amount}}{\text{newbalanceDest} + 1.0}$.
5. **`is_full_liquidation`:** Binary flag where $\text{oldbalanceOrg} > 0 \text{ and } \text{newbalanceOrig} == 0$.
6. **`dest_zero_balance_anomaly`:** Binary flag where $\text{oldbalanceDest} == 0 \text{ and } \text{newbalanceDest} == 0 \text{ and } \text{amount} > 0$.
7. **`hour_of_day`:** $\text{step} \pmod{24}$ (integer 0–23).
8. **`hour_sin`:** $\sin(2\pi \cdot \text{hour\_of\_day} / 24)$ (cyclical time representation).
9. **`hour_cos`:** $\cos(2\pi \cdot \text{hour\_of\_day} / 24)$ (cyclical time representation).
10. **`is_night_transaction`:** Binary flag indicating whether transaction occurred between 01:00 and 06:00 (high fraud rate window).
11. **`is_transfer`:** One-hot indicator for `TRANSFER` transactions.
12. **`is_cash_out`:** One-hot indicator for `CASH_OUT` transactions.
13. **`log_amount`:** $\log_{10}(\text{amount} + 1.0)$ (compresses extreme positive skew).
14. **`orig_has_zero_balance`:** Binary flag for transactions initiated with zero starting balance.

---

## 13. Dataset Suitability for A.R.G.U.S.

- **Supervised Classification (XGBoost / Baseline):** The combination of transaction types, amounts, balance errors, and diurnal cycles provides strong discriminatory signal for gradient boosting.
- **Isolation Forest Anomaly Detection:** The continuous multi-dimensional space formed by amount, drain ratio, and balance errors naturally isolates anomalous transactions as spatial outliers.
- **Deep Autoencoder Anomaly Detection:** By engineering ~18–22 dense, non-NaN continuous features, the Deep Autoencoder can learn the manifold of normal transactions and generate high reconstruction loss ($\text{MSE}$) on anomalous patterns.
- **PostgreSQL DBMS Schema:** Relational structure maps cleanly into `users` (`nameOrig`), `merchants` (`nameDest`), `transactions`, and `risk_assessments`.
- **Known Synthetic Limitations:** 
  - Low repeat sender velocity (avg 1.0 tx/sender). Velocity features must be simulated or tracked over short evaluation windows.
  - Clear-cut fraud types (`TRANSFER` and `CASH_OUT` only). In live systems, payment and refund fraud also exist.

---

## 14. Milestone 1 Conclusions

1. **PaySim Integrity Verified:** The local CSV contains 6,362,620 rows and 11 columns with zero missing values and zero duplicate rows.
2. **Fraud Concentration Identified:** Fraud is 100% concentrated in `TRANSFER` and `CASH_OUT` transactions, enabling targeted model training on high-risk transaction types.
3. **Leakage Risks Mitigated:** `isFlaggedFraud` is identified as an artificial rule artifact and will be excluded. Balance liquidation behavior is explicitly modeled as a continuous error feature rather than an arbitrary threshold.
4. **Temporal Separation Confirmed:** Transactions exhibit clear diurnal cycles and temporal progression across 743 hours, confirming the necessity of chronological (temporal) train/val/test splitting in Milestone 2.
