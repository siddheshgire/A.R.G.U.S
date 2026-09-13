# A.R.G.U.S. Project Initialization

## 1. Current Workspace
- **Absolute Path:** `c:\PRO\PBL SY`
- **Environment:** Windows, PowerShell shell
- **Tooling Detected:**
  - Python: `3.13.7`
  - Git: `2.55.0.windows.2`
- **Workspace State:** Brand new directory, uninitialized (no source files, no virtual environment, no `.git` repository present).

## 2. Existing Files
- **Files Found:** None (directory is currently empty prior to this report).
- **Directory Contents:** `0` files, `0` subdirectories.

## 3. Existing Code/Documentation
- **Code Status:** No source code exists in the workspace.
- **Documentation Status:** No documentation, configuration files, or notebooks exist yet. All design specifications and requirements currently stem from the initial master project prompt.

## 4. Project Requirements
- **Core System:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System), an AI-driven transaction risk monitoring system.
- **Output:** Normalized Risk Score (0–100) mapped to actionable tri-state decisions: `APPROVE`, `REVIEW`, and `BLOCK`.
- **System Nature:** Complete end-to-end working system (FastAPI backend, PostgreSQL persistence, ML/DL anomaly & classification engine, IoT hardware context, secure APIs, audit logging, and analyst dashboard), rather than an isolated Jupyter notebook.
- **Academic Focus:** Semester Project-Based Learning (PBL) for B.Tech AIML (Class: B.Tech AIML – C, Year: 2026–27 Odd Semester).
- **Quality & Methodology Standard:** Factual reporting, no fabricated benchmark metrics, test-driven validation, structured version control, and modular architecture.

## 5. Proposed Architecture
A modular monolith architecture prioritizing maintainability, debuggability, and low operational overhead:

```
[IoT Terminal / POS / ESP32] & [Client / Web Simulator]
                         │
                         ▼ (HTTPS / MQTT with Token & Signature Auth)
         [FastAPI Gateway / REST API Layer]
                         │
        [Validation & Normalization (Pydantic)]
                         │
      [Feature Extraction & Behavioral Profiler]
                         │
   ┌─────────────────────┴─────────────────────┐
   ▼                                           ▼
[Supervised ML Model]              [Unsupervised Anomaly / Deep Autoencoder]
(e.g., XGBoost / Baseline)         (Reconstruction Error Normalization)
   │                                           │
   └─────────────────────┬─────────────────────┘
                         ▼
             [Risk Aggregation Engine]
         (Weighted Score 0–100 + Business Rules)
                         │
                         ▼
        [Decision: APPROVE / REVIEW / BLOCK]
                         │
        [PostgreSQL Storage & Audit Ledger]
  (Transactions, Assessments, Devices, Audit Logs)
                         │
                         ▼
       [Analyst Dashboard & Review Portal]
```

- **Avoidance of Overengineering:** No premature microservices, message brokers (Kafka/RabbitMQ), or Kubernetes clusters. Standard asynchronous processing and background tasks within FastAPI will be utilized unless concrete scale demands otherwise.

## 6. Subject Integration
Every subject is assigned a distinct, functional, non-cosmetic responsibility:
1. **Deep Learning:** Deep Autoencoder trained on normal transaction patterns. Reconstruction loss ($\text{MSE}$) acts as an unsupervised anomaly detection signal, capturing novel fraud patterns unseen in supervised labels.
2. **DBMS (PostgreSQL):** Relational schema storing users, merchants, transactions, device metadata, computed risk scores, human review outcomes, model metadata, and immutable audit logs with appropriate indexing, foreign keys, and constraints.
3. **Information Security:** Role-Based Access Control (RBAC) for analysts/admins, JWT/API key authentication, input validation and sanitization, secure password hashing (Argon2/bcrypt), tamper detection / HMAC verification for IoT payloads, TLS communication, and audit logging.
4. **IoT:** ESP32-based hardware terminal/context generator providing physical transaction telemetry (device ID, tamper switch status, hardware timestamp, network signal/status, merchant terminal context).
5. **Supporting Pillars (OOPs & Computational Techniques):** Clean service-repository pattern, strict domain typing, statistical normalization, feature transformation pipelines, and threshold calibration.

## 7. Dataset Requirement
- **Status:** Not yet acquired or integrated.
- **Candidate Datasets:**
  - IEEE-CIS Fraud Detection (rich device & identity attributes, transaction timing, real-world complexity).
  - PaySim (synthetic mobile money transfer data, clear transaction types like TRANSFER/CASH_OUT).
- **Mandatory Pre-Implementation Protocol:**
  - Before writing data pipelines, inspect raw columns, class imbalance ratio, missing value distributions, numerical/categorical cardinality, and potential temporal target leakage.
  - Separate IoT context data cleanly: if public datasets lack specific hardware/sensor telemetry, design a synthetic/ESP32 augmentation layer that injects authentic IoT terminal context without corrupting the core dataset distribution.

## 8. ML/DL Strategy
- **Baseline:** Logistic Regression / Random Forest to establish baseline precision-recall and ROC-AUC.
- **Supervised Classifier:** XGBoost or LightGBM to handle tabular non-linear relationships, class imbalance (via scale_pos_weight or focal loss), and feature interactions.
- **Unsupervised Anomaly Detection:** Isolation Forest for tabular outlier detection.
- **Deep Learning (Deep Autoencoder):**
  - Architecture: Symmetric bottleneck network (e.g., Input $\rightarrow$ Dense(64) $\rightarrow$ Dense(32) $\rightarrow$ Latent(16) $\rightarrow$ Dense(32) $\rightarrow$ Dense(64) $\rightarrow$ Output).
  - Loss: Mean Squared Error ($\text{MSE}$) on normalized input features.
  - Training Policy: Train exclusively or predominantly on legitimate/normal transactions; calculate reconstruction error threshold on validation set.
- **Evaluation Criteria:** Prioritize Precision, Recall, F1-Score, PR-AUC (Precision-Recall AUC), and False Positive Rate over raw Accuracy due to extreme fraud class imbalance.
- **Retraining Policy:** Scheduled, batch-evaluated, traceable retraining with model versioning—no unvalidated instant online retraining on individual analyst actions.

## 9. IoT Strategy
- **Hardware Platform:** ESP32 microcontroller acting as a secure POS/payment terminal prototype.
- **Telemetry Payload:** `device_id`, `merchant_id`, `hardware_timestamp`, `firmware_version`, `tamper_flag`, `network_status`, and `payload_signature`.
- **Communication Protocol:** HTTPS REST endpoint or MQTT (with TLS).
- **Hardware-Software Integrity:** Mutual authentication or HMAC-SHA256 signature verification to prevent rogue devices from injecting false transactions.

## 10. Security Strategy
- **Authentication & Authorization:** Secure user authentication using JWT access/refresh tokens with RBAC (e.g., `Admin`, `Analyst`, `Auditor`, `IoT_Device`).
- **IoT Device Security:** Pre-shared cryptographic keys or client certificates, per-request nonce/timestamp validation to prevent replay attacks.
- **Data Protection:** Passwords hashed with standard modern hashing (Argon2id/bcrypt); sensitive transaction attributes encrypted or masked; SQL injection prevented via ORM/parameterized queries.
- **Audit Logging:** Append-only audit trail logging risk scores, analyst overrides, configuration modifications, and authentication events.

## 11. Identified Risks / Contradictions
1. **Python 3.13 Runtime vs. ML/DL Frameworks:**
   - *Risk:* Host machine has Python `3.13.7`. Deep learning libraries like PyTorch and TensorFlow, as well as specific compiled C-extensions (such as older scikit-learn or XGBoost binary wheels), frequently experience wheel availability delays or build issues on newly released Python minor versions.
   - *Mitigation:* Verify PyTorch / TensorFlow / Scikit-learn / XGBoost wheel compatibility on Python 3.13 before creating the virtual environment. If wheels are missing or unstable, utilize a Python 3.11 or 3.12 virtual environment.
2. **Autoencoder Role Definition:**
   - *Risk:* Common pitfall in academic projects is conflating an autoencoder with a classifier.
   - *Clarification:* The autoencoder is strictly an unsupervised reconstruction anomaly detector; its reconstruction error will be calibrated and normalized into an anomaly score, feeding into the aggregate risk calculation alongside the supervised classifier.
3. **Dataset vs. IoT Domain Mismatch:**
   - *Risk:* Public fraud datasets (like PaySim or IEEE-CIS) do not contain physical ESP32 telemetry fields.
   - *Clarification:* Clearly define an ingestion adapter that merges physical device terminal headers (ESP32) with transaction payload data, maintaining clear demarcation between credit/financial risk features and terminal security features.
4. **Arbitrary Risk Thresholding:**
   - *Risk:* Setting rigid thresholds (e.g. 0-40 Approve, 41-70 Review, 71-100 Block) without cost-benefit calibration will yield poor precision or flood human analysts.
   - *Mitigation:* Determine thresholds systematically using PR curves and operational trade-offs during Phase 7.

## 12. Recommended First Milestone (Milestone 0 & 1)
- **Milestone 0: Project Setup & Environment Initialization**
  - Initialize Git repository with proper `.gitignore` (Python, virtual environments, datasets, secrets).
  - Create Python virtual environment and test installation of foundational dependencies (`fastapi`, `uvicorn`, `pydantic`, `scikit-learn`, `xgboost`, `torch`/`tensorflow`, `psycopg2`/`asyncpg`, `pytest`).
  - Establish modular directory structure (`backend/`, `ml_engine/`, `iot_firmware/`, `database/`, `tests/`, `docs/`).
- **Milestone 1: Dataset Acquisition, Inspection & Exploratory Data Analysis (EDA)**
  - Acquire candidate dataset(s) locally.
  - Produce an objective, factual dataset profile report verifying schema, missing values, distribution, and target characteristics.

## 13. Immediate Next Actions
1. Confirm choice of Python version / virtual environment setup approach (validating Python 3.13 vs. 3.11/3.12 compatibility).
2. Initialize `.gitignore`, Git repo, and base project directory layout.
3. Select and download the primary dataset (IEEE-CIS or PaySim) for Phase 1 inspection.
