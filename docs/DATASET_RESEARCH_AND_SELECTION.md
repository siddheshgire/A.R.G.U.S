# A.R.G.U.S. — Dataset Research and Selection Report

**Phase 1: Dataset Research & Selection**  
**Document:** `docs/DATASET_RESEARCH_AND_SELECTION.md`  
**System:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Status:** Completed Evaluation — Awaiting Approval  

---

## 1. Executive Summary & Objective

The objective of Phase 1 is to evaluate candidate datasets for A.R.G.U.S. to support an end-to-end fraud risk assessment system. Unlike an isolated machine learning benchmark, A.R.G.U.S. requires a dataset that powers:
- Multi-model evaluation: Baseline Logistic Regression, Supervised XGBoost, Unsupervised Isolation Forest, and Deep Autoencoder reconstruction anomaly detection.
- Relational DBMS modeling (PostgreSQL) with relational entities (users, accounts, merchants, transactions, audit logs).
- Real-time API ingestion via FastAPI.
- Hardware-assisted IoT context injection via an ESP32 terminal.
- Explainable risk-scoring (0–100) mapped to `APPROVE`, `REVIEW`, and `BLOCK` operational actions.

The two candidate datasets under evaluation are:
1. **IEEE-CIS Fraud Detection** (Vesta Corporation / IEEE Computational Intelligence Society)
2. **PaySim Mobile Money Fraud Detection** (Lopez-Rojas et al., Blekinge Institute of Technology)

---

## 2. In-Depth Evaluation: IEEE-CIS Fraud Detection

### 1. Dataset Origin and Purpose
Released in 2019 via a Kaggle competition co-hosted by Vesta Corporation (a major e-commerce payment solution provider) and the IEEE Computational Intelligence Society (CIS). Its purpose was to benchmark advanced machine learning algorithms on real-world e-commerce card-not-present (CNP) fraud prevention.

### 2. Nature of Data
Real-world, commercial transaction logs. Due to strict financial privacy and commercial confidentiality, the data is **heavily anonymized and masked**, with numerous feature headers obfuscated (e.g., `V1`–`V339`, `id_01`–`id_38`).

### 3. Dataset Size
Approximately **2.7 GB to 3.0 GB uncompressed** across CSV files (training set ~1.5 GB, test set ~1.2 GB).

### 4. Number of Transactions / Rows
- Training Set: **590,540 transactions**
- Test Set: **506,691 transactions**
- Total: 1,097,231 transactions

### 5. Available Files
- `train_transaction.csv` (590,540 rows, 394 columns)
- `train_identity.csv` (144,233 rows, 41 columns) — joined on `TransactionID`
- `test_transaction.csv` (506,691 rows, 393 columns)
- `test_identity.csv` (141,907 rows, 41 columns)

### 6. Available Columns / Features
Total of **434 raw features** across two tables:
- `TransactionID` (unique identifier)
- `TransactionDT` (timedelta from an undisclosed reference datetime)
- `TransactionAmt` (payment amount in USD)
- `ProductCD` (product code)
- `card1`–`card6` (payment card attributes: issuer, card type, category, country)
- `addr1`, `addr2` (billing/shipping address codes)
- `dist1`, `dist2` (distances between billing address, postal code, IP, etc.)
- `P_emaildomain`, `R_emaildomain` (purchaser and recipient email domains)
- `C1`–`C14` (counting metrics, e.g., how many cards associated with address)
- `D1`–`D15` (timedeltas: days between previous transactions/actions)
- `M1`–`M9` (match flags, e.g., name on card matching billing address)
- `V1`–`V339` (rich features engineered by Vesta: entity relations, ranking, counts)
- `id_01`–`id_38` (identity/network features: IP, proxy, OS, browser build)
- `DeviceType`, `DeviceInfo` (hardware categorization)

### 7. Target / Fraud Label
`isFraud` (binary flag: `1` for fraudulent transaction, `0` for legitimate).

### 8. Fraud vs. Legitimate Class Distribution
- Total training rows: 590,540
- Legitimate (`0`): 569,877 (~96.50%)
- Fraudulent (`1`): 20,663 (~**3.50%**)
- Imbalance ratio: ~27.6 : 1

### 9. Numerical Features
Extensive (over 380 numerical features), including `TransactionAmt`, `dist1`, `dist2`, `C1`–`C14`, `D1`–`D15`, `V1`–`V339`, and numerical identity variables `id_01`–`id_11`.

### 10. Categorical Features
Notable categorical attributes: `ProductCD`, `card4` (card network: Visa, Mastercard, etc.), `card6` (credit, debit), `P_emaildomain`, `R_emaildomain`, `M1`–`M9`, `DeviceType`, `DeviceInfo`, and `id_12`–`id_38`.

### 11. Missing-Value Characteristics
**Extreme missingness.** Only a small subset of columns is fully populated.
- Only ~24.4% of transactions (144,233 / 590,540) have a corresponding record in `train_identity.csv`.
- Features like `dist2`, `id_07`, `id_08`, and many `Vxxx` columns have **70% to 90%+ missing values**.
- Handling this requires extensive imputation or missingness-indicator masks that dramatically expand memory requirements.

### 12. Transaction / Time-Related Information
`TransactionDT` is a relative integer timestamp (in seconds from an unknown baseline). It captures cyclical diurnal trends and temporal sequence, but cannot be directly mapped to calendar dates without offset estimation.

### 13. User / Customer-Related Information
There is no explicit `user_id` or `account_id`. Identifying distinct users requires complex reverse-engineering (e.g., combining `card1` + `addr1` + `D1` to track user credit cards over time).

### 14. Merchant-Related Information
No explicit merchant entity. Merchants are partially obfuscated within `ProductCD` and aggregated risk signals in the `Vxxx` feature group.

### 15. Device / Identity-Related Information
Rich web/browser telemetry: `DeviceType` (e.g., mobile, desktop), `DeviceInfo` (e.g., Windows, iOS, SM-G960F), browser strings (`id_31`), screen resolution (`id_33`), proxy usage (`id_23`). However, only ~24% of rows contain these records.

### 16. Potential Behavioural Features We Could Engineer
- Rolling transaction velocity per pseudo-card (`card1` + `addr1` count in last 1h, 24h, 7d).
- Deviation of `TransactionAmt` from historical mean per card.
- Email domain risk ratio (free webmail vs corporate).
- Delta shifts using `D1`–`D15`.

### 17. Known Limitations
- High opacity: `V1`–`V339` have no real-world semantic descriptions.
- Low identity coverage: 75% of transactions have no device/identity record.
- Lack of persistent relational keys (`user_id`, `merchant_id`).

### 18. Potential Data Leakage Concerns
`TransactionDT` split is critical. Random cross-validation leaks temporal patterns (card reuse patterns across time). Group or time-based splits (first 80% time for train, last 20% for test) are strictly required.

### 19. Computational Requirements
**Very high.** Loading and merging `train_transaction.csv` and `train_identity.csv` requires 8–16 GB of RAM. Without aggressive downcasting (`float64` $\rightarrow$ `float32`/`float16`), local development machines easily encounter Out-Of-Memory (OOM) errors during feature engineering and Deep Autoencoder training.

### 20. Suitability for a B.Tech AIML PBL Project
While prestigious and authentic for pure ML competition work, IEEE-CIS is **ill-suited for an integrated full-stack software engineering project**. Its 434 masked columns make relational schema design (DBMS) unnatural, make API payloads unwieldy (requiring hundreds of obscure parameters), and render analyst dashboard explanations uninterpretable (e.g., *"Flagged because V258 is 1.4"*).

---

## 3. In-Depth Evaluation: PaySim Mobile Money Dataset

### 1. Dataset Origin and Purpose
Developed by Edgar Lopez-Rojas et al. (Blekinge Institute of Technology, Sweden) and presented at the 28th European Modeling and Simulation Symposium (EMSS 2016). PaySim uses an agent-based simulation model parameterized by aggregated statistical distributions extracted from real-world mobile financial transaction logs provided by a financial service provider operating in an African country.

### 2. Nature of Data
**Synthetic / Agent-Based Simulation.** It accurately models customer behavior, financial transfer dynamics, and fraudulent behavior patterns without exposing confidential customer personally identifiable information (PII).

### 3. Dataset Size
Approximately **470 MB to 493 MB uncompressed** in a single CSV file.

### 4. Number of Transactions / Rows
**6,362,620 transactions.**

### 5. Available Files
Single unified file: `PS_20174392719_1491204439457_log.csv` (or standard `paysim.csv`).

### 6. Available Columns / Features
Total of **11 clean, semantically transparent columns**:
1. `step`: Integer time step (1 step = 1 hour; total 744 steps representing a 30-day simulation period).
2. `type`: Categorical transaction type (`CASH_IN`, `CASH_OUT`, `DEBIT`, `PAYMENT`, `TRANSFER`).
3. `amount`: Numerical transaction amount in local currency units.
4. `nameOrig`: Unique string ID of customer initiating transaction (e.g., `C1231006815`).
5. `oldbalanceOrg`: Initial balance of originating account before transaction.
6. `newbalanceOrig`: Balance of originating account after transaction.
7. `nameDest`: Unique string ID of recipient (customer `C...` or merchant `M...`).
8. `oldbalanceDest`: Initial balance of recipient before transaction.
9. `newbalanceDest`: Balance of recipient after transaction.
10. `isFraud`: Ground truth binary target (`1` = fraud, `0` = legitimate).
11. `isFlaggedFraud`: Baseline heuristic rule in simulation (flags attempts transferring $> 200,000$ in a single transaction).

### 7. Target / Fraud Label
`isFraud` (binary flag: `1` for fraudulent transaction, `0` for legitimate).

### 8. Fraud vs. Legitimate Class Distribution
- Total rows: 6,362,620
- Legitimate (`0`): 6,354,407 (~**99.871%**)
- Fraudulent (`1`): 8,213 (~**0.129%**)
- Imbalance ratio: ~773.7 : 1 (Extreme, authentic class imbalance representative of financial production systems).
- **Crucial behavioral finding:** Fraud occurs **strictly in `TRANSFER` and `CASH_OUT` transactions** (4,097 in `TRANSFER`, 4,116 in `CASH_OUT`). No fraud occurs in `PAYMENT`, `CASH_IN`, or `DEBIT`.

### 9. Numerical Features
- `step` (discrete temporal counter: 1–744)
- `amount` (continuous positive float)
- `oldbalanceOrg` (continuous float)
- `newbalanceOrig` (continuous float)
- `oldbalanceDest` (continuous float)
- `newbalanceDest` (continuous float)

### 10. Categorical Features
- `type`: 5 discrete categories (`CASH_IN`, `CASH_OUT`, `DEBIT`, `PAYMENT`, `TRANSFER`).
- `nameOrig`: High-cardinality entity identifiers (`C...`).
- `nameDest`: High-cardinality recipient/merchant identifiers (`C...` or `M...`).

### 11. Missing-Value Characteristics
**0 missing values (0.00% across all 11 columns).** The dataset is completely clean and complete, eliminating arbitrary imputation biases.

### 12. Transaction / Time-Related Information
The `step` feature maps directly to real-world hours:
- `hour_of_day = step % 24` (0 to 23, diurnal cyclical behavior)
- `day_of_week = (step // 24) % 7` (0 to 6, weekly patterns)
- `day_of_month = step // 24` (0 to 30)

### 13. User / Customer-Related Information
Explicit customer entity IDs (`nameOrig`, `nameDest`). Enables real-world relational database foreign-key mapping to `users` and `merchants` tables, and allows computation of customer behavioral baselines (historical mean, velocity, account age).

### 14. Merchant-Related Information
Recipients prefixed with `M` (e.g., `M1823043293`) designate merchant terminals. This provides a natural domain bridge for terminal/merchant risk assessment.

### 15. Device / Identity-Related Information
**None present in the raw synthetic log.** The dataset does not include IP addresses, browser strings, or device IDs.  
*Engineering alignment:* This is an advantage rather than a drawback. It guarantees a clear, uncorrupted boundary: PaySim powers financial transaction behavior, while our **physical ESP32 hardware terminal** supplies authentic device telemetry headers (`device_id`, hardware tamper switch status, hardware timestamp, payload HMAC).

### 16. Potential Behavioural Features We Could Engineer
PaySim's clean relational structure allows rich, domain-grounded feature engineering:
- **Balance Error Check (Sender):** `error_balance_orig = newbalanceOrig + amount - oldbalanceOrg` (detects balance manipulation or account drainage).
- **Balance Error Check (Recipient):** `error_balance_dest = oldbalanceDest + amount - newbalanceDest`.
- **Drainage Ratio:** `ratio_drained = amount / (oldbalanceOrg + 1e-5)` (fraudsters frequently liquidate 100% of available funds).
- **Zero Balance Destination Anomaly:** Flag where `oldbalanceDest == 0` and `newbalanceDest == 0` despite large transferred `amount`.
- **Cyclical Time Encoding:** $\sin(2\pi \cdot \text{hour} / 24)$ and $\cos(2\pi \cdot \text{hour} / 24)$.
- **Entity Velocity / Frequency:** Rolling transaction counts per sender within 1-hour and 24-hour windows.
- **Transaction-to-Average Ratio:** Current amount compared to the customer's historical average.
*Result:* Expands the 11 raw columns into **18–25 robust, highly descriptive numerical features**, providing an ideal multi-dimensional feature space for Deep Autoencoder bottleneck compression.

### 17. Known Limitations
- Synthetic origin: May not contain every idiosyncratic edge case found in live banking networks.
- Raw feature count is modest (11 columns), requiring explicit feature engineering to provide sufficient depth for a deep neural network.
- `isFlaggedFraud` is trivial (only flags 16 transactions $> 200,000$) and should not be used as an input feature.

### 18. Potential Data Leakage Concerns
- **Zero Balance Leakage:** In the simulator, when fraudulent transfers are executed, the perpetrator often drains the entire balance (`newbalanceOrig = 0`). Models can overfit to `newbalanceOrig == 0` if balance integrity checks are not normalized properly.
- **Temporal Ordering:** Training must respect the temporal progression of `step` (e.g., train on steps 1–500, test on steps 501–744) to prevent future transaction leakage into historical behavioral baselines.

### 19. Computational Requirements
**Moderate and highly efficient.** 
- The full 6.36 million rows load in ~2 GB of RAM.
- For local model development, an initial stratified or temporal subset (e.g., 200,000 to 500,000 transactions, or focusing on `TRANSFER` and `CASH_OUT` transaction types where fraud actually exists) trains in seconds on modern CPU/GPU hardware with minimal memory footprint.

### 20. Suitability for a B.Tech AIML PBL Project
**Exceptional.** PaySim offers the perfect balance:
- Semantically transparent, realistic financial entities.
- Direct alignment with PostgreSQL relational schema (`users`, `merchants`, `transactions`, `balances`).
- Human-interpretable features for the analyst dashboard and audit logs.
- Modest compute demands enabling iterative experimentation on local student workstations.

---

## 4. Specific Suitability Evaluation for A.R.G.U.S.

| Dimension | IEEE-CIS Fraud Detection | PaySim Mobile Money | Evaluation & Impact on A.R.G.U.S. |
| :--- | :--- | :--- | :--- |
| **A. Logistic Regression Baseline** | Viable, but requires extensive imputation, scaling, and dimensionality reduction for 434 columns. | **Excellent.** Highly stable on 15–20 engineered features with standard scaling. Clear baseline coefficients. | PaySim provides clean interpretability for weights. |
| **B. XGBoost Classifier** | Outstanding performance on competition leaderboards; naturally handles sparse NaNs. | **Outstanding.** Exceptional gradient boosting performance on tabular balance deltas, velocity, and transaction types. | Both excel; PaySim is 10x faster to train and iterate. |
| **C. Isolation Forest** | Difficult due to extreme missingness (NaNs must be heavily imputed, distorting spatial density). | **Ideal.** Multi-dimensional numerical features (amounts, velocities, balance errors) create clear outlier clusters. | Isolation Forest requires continuous, non-NaN tabular vectors. PaySim fits without synthetic imputation noise. |
| **D. Deep Autoencoder** | Possible, but high dimensionality (400+ features) with 80% NaNs makes autoencoder reconstruct imputed noise rather than true signal. | **Ideal with Feature Engineering.** Starting with 18–25 engineered features, a symmetric bottleneck (e.g., $24 \rightarrow 16 \rightarrow 8 \rightarrow 16 \rightarrow 24$) reconstructs legitimate patterns cleanly. | Deep Autoencoder requires genuine reconstruction error signals, which are degraded by heavy missingness in IEEE-CIS. |
| **E. Behavioural Anomaly Detection** | Limited by lack of explicit `user_id` and masked features. | **Directly Supported.** Explicit `nameOrig` enables historical user baseline tracking, rolling velocity, and balance drainage checks. | PaySim allows genuine customer behavioral profiling. |
| **F. Risk-Score Generation (0–100)** | Opaque scores driven by masked features ($V258$, $C1$, etc.). | **Transparent & Multi-Faceted.** Combines XGBoost probability + Autoencoder MSE + Isolation Forest anomaly + Rule checks. | Clear decomposition into risk contribution factors. |
| **G. PostgreSQL Integration** | Clunky. Storing 434 wide columns in PostgreSQL violates clean relational design; requires `JSONB` dumping. | **Natural Relational Design.** Maps directly to normalized tables: `users`, `merchants`, `transactions`, `balances`, `risk_assessments`. | PaySim reflects realistic enterprise DBMS schemas. |
| **H. IoT / ESP32 Integration** | Awkward. Dataset already has masked browser/OS fields ($id\_01$–$id\_38$); adding ESP32 context creates confusing overlap. | **Clean Orthogonal Integration.** PaySim handles financial data; ESP32 terminal provides hardware authentication & POS telemetry. | Clear academic demarcation between IoT and financial data layers. |
| **I. Real-Time Transaction Simulation** | Complex to simulate realistic API payloads with hundreds of obscure fields. | **Highly Realistic.** Lightweight JSON payload sent to FastAPI endpoint: `{origin, destination, amount, type, timestamp}`. | Perfect for live terminal demonstrations. |
| **J. Dashboard Demonstration** | Confusing for evaluators: *"Why is this flagged? Because feature V143 is 3.2."* | **Compelling.** Shows clear alerts: *"Account liquidated 100% within 2 minutes of password change via unknown terminal."* | Essential for viva and project evaluation. |
| **K. Explainability** | Black-box. SHAP values highlight masked variables with unknown physical meanings. | **Explainable by Design.** SHAP and business rules highlight actionable metrics (e.g., `amount_deviation`, `drainage_ratio`). | High academic defensibility. |
| **L. Academic Presentation** | High Kaggle prestige, but weak software engineering and DBMS integration story. | **Strong End-to-End Story.** Demonstrates full integration across Deep Learning, DBMS, InfoSec, and IoT without compromises. | Maximizes marks across all 4 mandatory PBL subjects. |

---

## 5. Dual-Dataset Approach: Evaluation

We evaluated whether utilizing **both** datasets (e.g., IEEE-CIS for web e-commerce and PaySim for mobile money) would enhance the project.

### Verdict: **NOT RECOMMENDED (Anti-Pattern for Semester PBL)**
1. **Architectural Duplication:** Using both datasets forces the creation of two separate database schemas, two distinct feature engineering pipelines, two sets of ML/DL models, and two different API ingestion contracts.
2. **Diluted Focus:** Instead of building a robust, secure, end-to-end working system with Deep Learning, DBMS, InfoSec, and IoT, development effort would be wasted managing data wrangling across two disparate domains.
3. **Evaluation Confusion:** In an academic viva, evaluators judge the coherence and depth of the demonstrated system. Splitting attention between two disconnected datasets creates unnecessary complexity without delivering additional academic value.
4. **Conclusion:** Select **one** primary dataset and implement it thoroughly.

---

## 6. Comprehensive Side-by-Side Comparison Matrix

| Attribute / Requirement | IEEE-CIS Fraud Detection | PaySim Mobile Money |
| :--- | :--- | :--- |
| **Primary Domain** | E-commerce Card-Not-Present (CNP) | Mobile Money / Peer-to-Peer & Merchant Transfers |
| **Data Nature** | Real-world, heavily masked / anonymized | Agent-Based Simulation (calibrated on real logs) |
| **File Count & Total Size** | 4 files (`train/test` $\times$ `trans/id`), ~2.8 GB | 1 file, ~470 MB |
| **Row Count** | 590,540 (train) + 506,691 (test) | 6,362,620 |
| **Raw Feature Count** | 434 features | 11 features |
| **Missing Values** | **Pervasive (up to 90%+ across many columns)** | **0.00% (Completely clean)** |
| **Fraud Rate** | 3.50% (20,663 / 590,540) | 0.129% (8,213 / 6,362,620) |
| **Relational Entities (`User`, `Merchant`)** | Obfuscated / Missing explicit keys | Explicit (`nameOrig`, `nameDest` with `C`/`M` prefixes) |
| **DBMS Normalization Suitability** | Poor (wide table, 434 cols, forces unstructured JSONB) | Excellent (clean 3NF relational schema) |
| **Feature Interpretability** | Extremely poor (V1–V339, C1–C14, D1–D15, id_01–id_38) | High (amounts, balances, types, time steps) |
| **Deep Autoencoder Suitability** | Problematic (reconstructs imputed missingness artifacts) | Excellent (reconstructs engineered behavioral vector) |
| **RAM & Compute Burden** | High (8–16 GB RAM required for basic processing) | Low–Moderate (lightweight, runs easily on local laptops) |
| **FastAPI Payload Complexity** | Unrealistic (JSON payload with 400+ fields) | Realistic (clean JSON payload with 5–8 fields) |
| **IoT / ESP32 Demarcation** | Murky (collides with existing masked device fields) | Clean (ESP32 provides distinct hardware context) |

---

## 7. Strategic Recommendations & Technical Blueprint

### 1. Recommended PRIMARY Dataset
**PaySim Mobile Money Fraud Detection** is unequivocally recommended as the primary dataset for A.R.G.U.S.

### 2. Is a SECONDARY Dataset Necessary?
**No.** A secondary dataset introduces unwarranted complexity, splits focus, and risks leaving core components unintegrated.

### 3. Technical Reasons for Recommendation
- **Relational Integrity:** Clean entity identifiers (`nameOrig`, `nameDest`) map directly to our PostgreSQL database schema (`users`, `merchants`, `transactions`, `balances`), satisfying the DBMS requirement.
- **Deep Autoencoder Effectiveness:** Autoencoders require consistent, non-NaN continuous features. PaySim's zero-missing-value property combined with domain-engineered features creates a dense, informative vector space ideal for reconstruction error analysis.
- **API and Ingestion Simplicity:** In a live demonstration, the FastAPI backend will receive transaction requests from simulated clients and the ESP32 terminal. A clean payload with transaction type, sender, recipient, and amount is realistic, demonstrable, and testable.
- **Computational Reliability:** Enables rapid training, evaluation, and hyperparameter tuning on standard development hardware without memory crashes.

### 4. Academic Reasons for Recommendation
- **End-to-End Demonstrability:** In B.Tech PBL evaluation, a fully functioning, connected prototype (ESP32 $\rightarrow$ FastAPI $\rightarrow$ ML/DL $\rightarrow$ PostgreSQL $\rightarrow$ Dashboard) carries substantially higher academic merit than an isolated Jupyter notebook struggling with 400 masked features.
- **Defensible Subject Integration:** Clearly demonstrates Deep Learning (Autoencoder reconstruction loss on behavioral vectors), DBMS (clean normalized schema), Information Security (API auth, RBAC, IoT tamper checking), and IoT (physical ESP32 telemetry).
- **Explainability:** When an evaluator asks why a transaction received a Risk Score of 85, the system can explain: *"Transaction drained 100% of balance at 3:00 AM to a new recipient with high velocity,"* which is academically rigorous and defensible.

### 5. Major Disadvantages of Selected Dataset
1. **Synthetic Nature:** While statistically grounded, it is an agent-based simulation rather than live production banking data.
2. **Modest Raw Feature Count:** Contains only 11 raw columns, which if used without feature engineering, is too small for deep learning architectures.
3. **Behavioral Bias in Fraud Types:** Fraud occurs exclusively in `TRANSFER` and `CASH_OUT` transaction types.
4. **Balance Error Artifacts:** In some synthetic transactions, balances do not mathematically balance (`newbalance != oldbalance - amount`) due to simulator cancellation mechanisms.

### 6. Mitigation Strategy for Disadvantages
1. **Feature Engineering Pipeline:** Engineer 12–15 additional domain features (balance error discrepancies, drainage ratio, rolling user transaction velocities, cyclical time encodings, destination novelty). This expands the feature space to ~25 dimensions, providing rich representation for the Deep Autoencoder.
2. **Subsetting & Stratification:** Focus model training primarily on the active fraud transaction types (`TRANSFER` and `CASH_OUT`), while handling other types (`PAYMENT`, etc.) through fast-path business rule evaluation.
3. **Balance Error as a Feature:** Instead of viewing balance discrepancies as defects, compute them explicitly as risk features (`error_balance_orig`, `error_balance_dest`), mirroring real forensic accounting techniques.
4. **Academic Transparency:** Explicitly document in all project reports that PaySim is an academically recognized, agent-based synthetic benchmark designed specifically to circumvent financial PII restrictions.

### 7. Initial Features for A.R.G.U.S. Focus
- Raw: `step`, `type`, `amount`, `oldbalanceOrg`, `newbalanceOrig`, `oldbalanceDest`, `newbalanceDest`.
- Engineered:
  - `orig_balance_error` = `newbalanceOrig + amount - oldbalanceOrg`
  - `dest_balance_error` = `oldbalanceDest + amount - newbalanceDest`
  - `orig_drain_ratio` = `amount / (oldbalanceOrg + 1.0)`
  - `dest_drain_ratio` = `amount / (newbalanceDest + 1.0)`
  - `hour_of_day` = `step % 24`
  - `hour_sin`, `hour_cos` (cyclical sine/cosine transformation)
  - `is_night_transaction` = binary indicator (hour between 00:00 and 05:00)
  - `type_encoded` = One-hot encoded transaction types (`is_transfer`, `is_cash_out`)

### 8. Features to Exclude or Treat with Caution
- **`isFlaggedFraud`:** Must be **EXCLUDED** from training features. It is a naive rule-based output ($>200,000$ transfer) embedded in the simulation. Using it causes direct target leakage.
- **`nameOrig`, `nameDest` (Raw String IDs):** Must NOT be fed directly as high-cardinality categorical inputs to ML models. Instead, use them for entity linking in PostgreSQL and to compute historical behavioral aggregates (e.g., prior transaction count, average amount).

### 9. ESP32 IoT Layer Connection (Without Falsifying Original Data)
To maintain academic integrity, we will **never claim the dataset came with IoT data**. Instead, we design an explicit **IoT POS Terminal Ingestion Architecture**:
- **The Financial Data:** PaySim provides the financial transaction content (`amount`, `type`, `sender_account`, `recipient_account`).
- **The Physical IoT Terminal:** The ESP32 represents a merchant point-of-sale terminal or payment gateway node.
- **The Hybrid Payload Structure:** When a transaction is submitted, the API receives a clean compound envelope:
  ```json
  {
    "transaction_payload": {
      "sender_id": "C1231006815",
      "recipient_id": "M1823043293",
      "amount": 4500.00,
      "transaction_type": "TRANSFER",
      "timestamp": 1726070400
    },
    "terminal_telemetry": {
      "device_id": "ESP32-TERM-0042",
      "merchant_id": "M1823043293",
      "hardware_tamper_status": 0,
      "firmware_version": "v1.0.4",
      "signal_strength_rssi": -62,
      "request_nonce": "a7b8c9d0",
      "payload_hmac_signature": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  }
  ```
- **Processing Logic:** 
  1. The Information Security / IoT validation layer verifies the terminal's HMAC signature, device registration, and tamper status.
  2. The financial payload is extracted and passed to the ML/DL pipeline for risk assessment.
  3. Terminal risk signals (e.g., unknown terminal, tamper switch tripped, signature mismatch) are integrated into the final Risk Score aggregation engine.
- This creates a realistic, defensible integration where every component has a genuine functional purpose.

### 10. Development Workflow Following Selection
1. **Acquisition & Verification:** Download the official PaySim dataset, verify its SHA256 checksum, and place it in a gitignored `data/raw/` directory.
2. **Exploratory Data Analysis (EDA):** Generate an objective, reproducible EDA report verifying row counts, class distributions, balance behaviors, and correlations.
3. **Database Schema Design (PostgreSQL):** Model `users`, `merchants`, `devices`, `transactions`, `risk_assessments`, and `audit_logs`.
4. **Feature Engineering Pipeline:** Build reproducible feature transformation modules with strict train/test temporal splitting.
5. **Model Baselines & Deep Learning:** Train Logistic Regression baseline, XGBoost classifier, Isolation Forest anomaly detector, and the Deep Autoencoder reconstruction network.
6. **Risk Engine & Integration:** Aggregate multi-model outputs into a 0–100 Risk Score, integrate with FastAPI, connect the ESP32 terminal, and build the analyst dashboard.

---

## Decision Gate

**Recommended Dataset:** PaySim Mobile Money Fraud Detection  
**Confidence:** High (95%)  
**Primary Reasons:** Perfectly aligns with all 4 PBL subjects (Deep Autoencoder, PostgreSQL schema, InfoSec API/auth, ESP32 IoT context); zero missing values; computationally reproducible on local workstations; fully explainable risk scores for viva demonstration.  
**Major Risks:** Low raw column count (mitigated by robust behavioral feature engineering) and zero-balance leakage (mitigated by explicit balance error modeling and temporal validation splits).  
**Secondary Dataset Required:** No  
**Ready to Download:** Yes (Awaiting user confirmation)  
