# A.R.G.U.S. — FastAPI Application Gateway Architecture

## 1. Purpose & Scope
This document details the architecture, design decisions, and operational lifecycle of the **FastAPI Application Gateway (Milestone 6)** within Project A.R.G.U.S. (*Automated Risk Assessment & Anomaly Detection System*), developed for B.Tech AIML (Odd Semester 2026–27).

The FastAPI backend serves as the **orchestration and API layer** of the modular monolith. It bridges incoming simulated transaction requests, real-time 18-feature engineering, multi-model ML/DL inference, the weighted Risk Engine, and the PostgreSQL relational persistence layer into a single, unified interface.

---

## 2. Target Architecture & Request Lifecycle

```
[Simulated Web Client / IoT POS Edge Terminal]
                        │
                        │ POST /api/v1/transactions/assess
                        ▼
         [FastAPI Application Gateway (backend/main.py)]
                        │
                        ▼
         [Pydantic Request Validation (backend/schemas/transaction.py)]
         ├── Type, range, and format checks (amount >= 0, step >= 1)
         └── Anti-Leakage Guard: Rejects isFraud / isFlaggedFraud (HTTP 422)
                        │
                        ▼
         [Transaction Service (backend/services/transaction_service.py)]
                        │
    ┌───────────────────┴─────────────────────────────────────────┐
    │                                                             │
    ▼ (type in {'TRANSFER', 'CASH_OUT'})                          ▼ (type in {'PAYMENT', 'CASH_IN', 'DEBIT'})
[18-Feature Engineering Pipeline]                     [Controlled Subspace Error]
(ml_engine.features.compute_engineered_features)      HTTP 422: "Transaction type not
    │                                                 currently supported for ML assessment"
    ▼                                                 (NO auto-approval, NO invented rules)
[Multi-Model Inference (ModelManager)]
├── XGBoost (Unscaled features) ────────> [0, 1] probability
├── Logistic Regression (Scaled features) ─> [0, 1] probability
├── Isolation Forest (Unscaled features) ─> [0, 1] anomaly score
└── Deep Autoencoder (Scaled features) ───> [0, 1] MSE reconstruction anomaly
    │
    ▼
[Risk Scoring & Decision Engine (ml_engine.risk)]
├── Weights: 0.50 XGB + 0.20 Autoencoder + 0.15 IsoForest + 0.15 Logistic
├── Aggregate Continuous Risk Score: 0.00 to 100.00
└── Tri-State Decision Policy:
    ├── Risk Score < 40.00       ──> APPROVE
    ├── 40.00 <= Risk Score < 70 ──> REVIEW
    └── Risk Score >= 70.00      ──> BLOCK
    │
    ▼
[PostgreSQL Relational Repository (database.repository.save_assessed_transaction)]
├── Transaction record (UUID primary key)
├── 18-Feature snapshot (transaction_features)
├── 4 Model inference records (model_results)
├── Risk assessment record (risk_assessments)
├── Decision record with explainability reasons (decisions)
├── Analyst alert (alerts) — queued automatically if REVIEW or BLOCK
└── Audit trail entry (audit_logs)
    │
    ▼
[JSON API Response (backend/schemas/risk.py)]
HTTP 200: { transaction_id, risk_score, decision, model_signals, reasons, assessment_id }
```

---

## 3. Directory Layout & Package Structure

The backend application follows a clean service-oriented separation of concerns within `backend/`:

```
backend/
├── __init__.py                # Package version metadata
├── main.py                    # FastAPI app factory, lifespan manager, exception handlers
├── config.py                  # APISettings (pydantic_settings)
├── api/
│   ├── __init__.py            # Router aggregator (mounts health & /api/v1)
│   └── routes/
│       ├── __init__.py
│       ├── health.py          # GET /health, GET /ready
│       └── transactions.py    # POST /api/v1/transactions/assess, GET /api/v1/transactions/{tx_id}
├── schemas/
│   ├── __init__.py
│   ├── common.py              # HealthResponse, ReadinessResponse, ErrorResponse
│   ├── transaction.py         # TransactionCreateRequest, TransactionResponse
│   └── risk.py                 # ModelSignalsResponse, TransactionAssessResponse
├── services/
│   ├── __init__.py
│   ├── model_service.py       # ModelManager (in-memory artifact caching & inference)
│   └── transaction_service.py # TransactionService (end-to-end orchestration)
└── dependencies/
    ├── __init__.py
    ├── database.py            # get_db() session generator
    └── models.py              # get_model_manager(), get_transaction_service()
```

---

## 4. REST Endpoints Specification

### 4.1 System Health & Diagnostics

#### `GET /health`
- **Purpose**: Liveness probe for containers and monitoring services.
- **Status Code**: `200 OK`
- **Response Schema**:
  ```json
  {
    "status": "ok",
    "service": "argus-api",
    "version": "1.0.0"
  }
  ```

#### `GET /ready`
- **Purpose**: Readiness probe verifying that database connectivity and pretrained model artifacts are available.
- **Status Code**: `200 OK`
- **Response Schema**:
  ```json
  {
    "status": "ready",
    "database_connected": true,
    "models_loaded": true,
    "details": {
      "models_dir": "C:\\PRO\\PBL SY\\models",
      "architecture": "4-model ensemble (XGBoost, LR, IsolationForest, Autoencoder)"
    }
  }
  ```

---

### 4.2 Transaction Ingress & Assessment

#### `POST /api/v1/transactions/assess`
- **Purpose**: Evaluates a simulated transaction through feature extraction, multi-model inference, Risk Engine aggregation, and atomic database persistence.
- **Status Codes**:
  - `200 OK`: Successfully evaluated and persisted.
  - `422 Unprocessable Content`: Schema validation error, anti-leakage violation, or non-modeled transaction type (`PAYMENT`, `CASH_IN`, `DEBIT`).
  - `500 Internal Server Error`: Unhandled server exception (safe response without credential leaks).

**Sample Request Body:**
```json
{
  "step": 646,
  "type": "TRANSFER",
  "amount": 399045.08,
  "nameOrig": "C1234567890",
  "nameDest": "C9876543210",
  "oldbalanceOrg": 10399045.08,
  "newbalanceOrig": 10399045.08,
  "oldbalanceDest": 0.0,
  "newbalanceDest": 0.0,
  "actor_id": "SIMULATED_CLIENT"
}
```

**Sample Response Body:**
```json
{
  "transaction_id": "49087253-c089-4a2e-b98f-a143cb98f634",
  "risk_score": 86.41,
  "decision": "BLOCK",
  "model_signals": {
    "xgboost_score": 0.7654,
    "logistic_score": 1.0,
    "isolation_score": 0.876,
    "autoencoder_score": 1.0
  },
  "reasons": [
    "High supervised fraud probability detected by XGBoost (76.54%).",
    "Significant feature reconstruction anomaly flagged by Deep Autoencoder (100.00%).",
    "Unsupervised spatial density outlier detected by Isolation Forest (87.60%).",
    "Elevated linear benchmark risk score (100.00%).",
    "Mule recipient anomaly: Destination account balance remains zero despite inbound transfer.",
    "Sender ledger balance discrepancy of $399,045.08 detected.",
    "High monetary magnitude ($399,045.08) exceeding standard monitoring baseline."
  ],
  "assessment_id": "f718915c-85a0-4fac-8972-7b959665d166",
  "engine_version": "1.0.0",
  "evaluated_by": "ml_ensemble",
  "created_at": "2026-09-12T17:51:25.429483Z"
}
```

---

#### `GET /api/v1/transactions/{tx_id}`
- **Purpose**: Queries a persisted transaction record by UUID.
- **Status Codes**:
  - `200 OK`: Record found.
  - `404 Not Found`: No transaction exists with the given UUID.

---

## 5. Critical Engineering Safeguards

### 5.1 Anti-Leakage Guard
In real operational environments, fraud detection systems must evaluate transactions **prior** to human or downstream verification. The API enforces strict anti-leakage guards at the Pydantic boundary:
- Passing `isFraud` (or case variants) raises an immediate `HTTP 422` error:
  `"Field 'isFraud' is strictly forbidden in operational transaction assessment. Target labels cannot be supplied to the live inference gateway."`
- Passing `isFlaggedFraud` (the synthetic simulation heuristic rule) is similarly forbidden.

### 5.2 Modeling Subspace Policy
In the PaySim dataset, 100% of verified fraud cases reside exclusively within `TRANSFER` and `CASH_OUT` categories. The remaining types (`PAYMENT`, `CASH_IN`, `DEBIT`) were not part of the trained ML modeling subspace.
- In accordance with rigorous scientific practice, the API does **NOT** invent arbitrary fast-path rules or grant automated approvals for non-modeled types.
- Submitting `PAYMENT`, `CASH_IN`, or `DEBIT` returns a controlled `HTTP 422`:
  `"Transaction type '{type}' is not currently supported for ML risk assessment. The A.R.G.U.S. model pipeline is strictly trained and validated on ['CASH_OUT', 'TRANSFER'] transactions."`

### 5.3 Zero Retraining & Pretrained Lifespan Loading
To prevent catastrophic latency spikes and model state corruption:
- Model artifacts (`models/feature_scaler.joblib`, `models/xgboost_fraud_model.json`, `models/logistic_baseline.joblib`, `models/isolation_forest.joblib`, `models/autoencoder.pt`) are loaded **exactly once** during application startup inside FastAPI's async `lifespan` handler.
- Zero model training, hyperparameter searches, or dataset re-processing occurs during startup or request processing.
- Requests access the cached `ModelManager` instance from application state.

---

## 6. Preprocessing & Model Input Conventions

Each model expects specific preprocessing characteristics as validated during Milestone 3:

| Model Architecture | Input Preprocessing | Output Metric | Normalized Scale |
| :--- | :--- | :--- | :--- |
| **XGBoost Classifier** | Unscaled 18 features (`ALL_MODEL_FEATURES`) | Supervised class probability $P(\text{fraud} \mid X)$ | $[0.0, 1.0]$ |
| **Logistic Regression** | `StandardScaler` transformed 18 features | Supervised class probability $P(\text{fraud} \mid X)$ | $[0.0, 1.0]$ |
| **Isolation Forest** | Unscaled 18 features (`ALL_MODEL_FEATURES`) | Continuous path-length anomaly score | $[0.0, 1.0]$ |
| **Deep Autoencoder** | `StandardScaler` transformed 18 features | MSE reconstruction error $\rightarrow$ Sigmoid anomaly | $[0.0, 1.0]$ |

---

## 7. Database Integration & Persistence Guarantee

The persistence bridge is handled atomically via `database.repository.save_assessed_transaction()`. Within a single ACID transaction, the repository persists:
1. `Transaction`: Primary entity with UUID, step, type, balances, and optional merchant/device IDs.
2. `TransactionFeatures`: The exact 18 feature values snapshot at evaluation time.
3. `ModelResult` $\times 4$: Individual model scores, inference latencies (ms), and version stamps.
4. `RiskAssessmentRecord`: Weighted Risk Score, engine version, and evaluator tag.
5. `DecisionRecord`: Tri-state policy outcome (`APPROVE`, `REVIEW`, `BLOCK`) and explainability reasons.
6. `Alert`: Automatically queued with `PENDING` status and `HIGH`/`CRITICAL` severity if decision is `REVIEW` or `BLOCK`.
7. `AuditLog`: Immutable audit trail entry recording `TRANSACTION_ASSESSED`.

---

## 8. Error Handling & Security Boundary

### Implemented Protections:
- **Pydantic Data Sanitization**: Strict types, positive value constraints, and extra field rejection (`extra="forbid"`).
- **Global Exception Filtering**: Unhandled server errors return a generic `500 Internal Server Error` envelope (`code: "INTERNAL_SERVER_ERROR"`), completely preventing Python tracebacks, database passwords, or machine directory paths from leaking to clients.
- **SQL Injection Prevention**: 100% parameterized queries via SQLAlchemy 2.0 ORM.
- **Secret Isolation**: Configuration loaded exclusively via environment variables (`.env`).

### Intentionally Deferred Features (Planned for Milestones 7–9):
- JWT Bearer Authentication & OAuth2.
- Role-Based Access Control (RBAC) enforcement on analyst queues.
- HMAC-SHA256 hardware signature verification for ESP32 POS terminals.
- TLS termination (handled via reverse proxy in deployment).

---

## 9. Academic Disclaimers

1. **Simulated Environment**: This API processes simulated mobile money and POS transactions. It does **not** connect to real-world payment networks (UPI, Visa/Mastercard rails, Google Pay, or core banking switches).
2. **Synthetic Data Foundation**: Underlying models were trained on PaySim synthetic mobile transaction data. Findings and probability scores reflect PaySim data distributions.
