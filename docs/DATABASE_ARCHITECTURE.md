# A.R.G.U.S. — Relational Database Architecture (Milestone 5)

**Project:** A.R.G.U.S. — Automated Risk Assessment & Anomaly Detection System  
**Subtitle:** AI-Based Real-Time Fraud Detection and Transaction Risk Monitoring System  
**Stage:** Milestone 5 — PostgreSQL Database Layer  
**Implementation Date:** 2026-09-12  
**ORM Framework:** SQLAlchemy 2.0  
**Database Driver:** `psycopg2-binary` (PostgreSQL)  

---

## 1. Architectural Overview & Design Philosophy

The A.R.G.U.S. database layer provides a high-throughput, ACID-compliant persistence backbone for financial transactions, domain feature vectors, multi-model inferences, ensemble risk scores, operational decisions, fraud analyst alerts, and tamper-evident audit trails.

Designed according to **Third Normal Form (3NF)** principles, the relational schema enforces strict separation of concerns between operational financial ingress, feature engineering outputs, model-level inference diagnostics, and human workflow entities.

```
                    ┌─────────────────────────────────────────┐
                    │               merchants                 │
                    │ PK: merchant_id (UUID)                  │
                    └────────────────────┬────────────────────┘
                                         │ 1:N
                    ┌────────────────────┴────────────────────┐
                    │                devices                  │
                    │ PK: device_id (UUID)                    │
                    │ FK: merchant_id (UUID)                  │
                    └────────────────────┬────────────────────┘
                                         │ 1:N
                    ┌────────────────────▼────────────────────┐
                    │              transactions               │
                    │ PK: tx_id (UUID)                        │
                    │ FK: merchant_id, device_id              │
                    │ Raw ledger attributes (isFraud omitted) │
                    └──────┬─────────────┬─────────────┬──────┘
                           │ 1:1         │ 1:N         │ 1:1
       ┌───────────────────┘             │             └───────────────────┐
       ▼                                 ▼                                 ▼
┌─────────────────────────┐   ┌─────────────────────┐   ┌─────────────────────────┐
│  transaction_features   │   │    model_results    │   │    risk_assessments     │
│ PK: feature_id (UUID)   │   │ PK: result_id (UUID)│   │ PK: assessment_id (UUID)│
│ FK: tx_id (UUID, UNIQUE)│   │ FK: tx_id (UUID)    │   │ FK: tx_id (UUID, UNIQUE)│
│ Exact 18 features       │   │ 4 model signals     │   │ Aggregated score (0-100)│
└─────────────────────────┘   └─────────────────────┘   └────────────┬────────────┘
                                                                     │ 1:1
                                                        ┌────────────┴────────────┐
                                                        │                         │
                                                        ▼                         ▼
                                             ┌──────────────────────┐  ┌──────────────────────┐
                                             │      decisions       │  │        alerts        │
                                             │ PK: decision_id      │  │ PK: alert_id         │
                                             │ FK: assessment_id    │  │ FK: assessment_id    │
                                             │ Policy + reasons     │  │ FK: assigned_user_id │
                                             └──────────────────────┘  └──────────┬───────────┘
                                                                                  │ N:1
                                                                       ┌──────────▼───────────┐
                                                                       │        users         │
                                                                       │ PK: user_id (UUID)   │
                                                                       │ FK: role_id (UUID)   │
                                                                       └──────────┬───────────┘
                                                                                  │ N:1
                                                                       ┌──────────▼───────────┐
                                                                       │        roles         │
                                                                       │ PK: role_id (UUID)   │
                                                                       │ ADMIN/ANALYST/AUDITOR│
                                                                       └──────────────────────┘
```

---

## 2. Relational Schema Specification (11 Core Entities)

### 2.1 Entity: `roles`
Defines system access tiers and operational privilege boundaries.
- `role_id` (`UUID`, Primary Key, default `uuid.uuid4`)
- `name` (`VARCHAR(50)`, Unique, Not Null, Index) — Operational role (`ADMIN`, `ANALYST`, `AUDITOR`).
- `description` (`VARCHAR(255)`, Nullable) — Human-readable description of authority.
- `created_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).

### 2.2 Entity: `users`
Represents administrators and fraud operations analysts.
- `user_id` (`UUID`, Primary Key, default `uuid.uuid4`)
- `username` (`VARCHAR(50)`, Unique, Not Null, Index).
- `email` (`VARCHAR(255)`, Unique, Not Null, Index).
- `hashed_password` (`VARCHAR(255)`, Not Null).
- `role_id` (`UUID`, Foreign Key $\to$ `roles.role_id`, Not Null, Index).
- `is_active` (`BOOLEAN`, Not Null, default `TRUE`).
- `created_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).
- `updated_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).

### 2.3 Entity: `merchants`
Commercial recipient accounts and business partner profiles.
- `merchant_id` (`UUID`, Primary Key, default `uuid.uuid4`).
- `merchant_code` (`VARCHAR(64)`, Unique, Not Null, Index) — Business code (e.g. `M12345678`).
- `name` (`VARCHAR(128)`, Not Null).
- `category_code` (`VARCHAR(32)`, Nullable) — MCC category (e.g. `RETAIL`, `ELECTRONICS`).
- `risk_tier` (`VARCHAR(16)`, Not Null, default `STANDARD`) — Risk profile tier.
- `is_active` (`BOOLEAN`, Not Null, default `TRUE`).
- `created_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).

### 2.4 Entity: `devices`
Physical edge point-of-sale terminals and payment hardware devices (e.g. ESP32).
- `device_id` (`UUID`, Primary Key, default `uuid.uuid4`).
- `device_code` (`VARCHAR(64)`, Unique, Not Null, Index) — Terminal identifier (e.g. `ESP32-TERM-0001`).
- `merchant_id` (`UUID`, Foreign Key $\to$ `merchants.merchant_id`, Nullable, Index).
- `device_type` (`VARCHAR(32)`, Not Null, default `POS_TERMINAL`).
- `firmware_version` (`VARCHAR(32)`, Nullable).
- `status` (`VARCHAR(32)`, Not Null, default `ACTIVE`) — Operational state (`ACTIVE`, `OFFLINE`, `TAMPERED`).
- `tamper_flag` (`BOOLEAN`, Not Null, default `FALSE`) — Edge tamper switch indicator.
- `last_seen_at` (`TIMESTAMPTZ`, Nullable).
- `created_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).

### 2.5 Entity: `transactions`
Operational financial ledger ingress table representing fund movement.
- `tx_id` (`UUID`, Primary Key, default `uuid.uuid4`).
- `step` (`INTEGER`, Not Null, Index) — Chronological simulation step or operational timestamp hour.
- `type` (`VARCHAR(32)`, Not Null, Index) — Ingress transfer channel (`TRANSFER`, `CASH_OUT`, `PAYMENT`, `CASH_IN`, `DEBIT`).
- `amount` (`DOUBLE PRECISION`, Not Null) — Monetary value requested.
- `name_orig` (`VARCHAR(64)`, Not Null, Index) — Originating sender account identifier.
- `name_dest` (`VARCHAR(64)`, Not Null, Index) — Destination recipient account identifier.
- `oldbalance_org` (`DOUBLE PRECISION`, Not Null) — Sender balance prior to transaction.
- `newbalance_orig` (`DOUBLE PRECISION`, Not Null) — Sender balance after transaction execution.
- `oldbalance_dest` (`DOUBLE PRECISION`, Not Null) — Recipient balance prior to transaction.
- `newbalance_dest` (`DOUBLE PRECISION`, Not Null) — Recipient balance after transaction.
- `merchant_id` (`UUID`, Foreign Key $\to$ `merchants.merchant_id`, Nullable, Index).
- `device_id` (`UUID`, Foreign Key $\to$ `devices.device_id`, Nullable, Index).
- `created_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).

> [!IMPORTANT]
> **Operational Leakage Prevention:** The `isFraud` ground-truth label and `isFlaggedFraud` heuristic flag are strictly **excluded** from the live `transactions` schema. Operational transactions represent incoming financial payloads evaluated in real time without access to downstream forensic fraud labels.

### 2.6 Entity: `transaction_features`
Stores the exact 18 numerical domain features engineered for model inference.
- `feature_id` (`UUID`, Primary Key, default `uuid.uuid4`).
- `tx_id` (`UUID`, Foreign Key $\to$ `transactions.tx_id` ON DELETE CASCADE, Unique, Not Null, Index).
- `amount` (`DOUBLE PRECISION`, Not Null).
- `oldbalance_org` (`DOUBLE PRECISION`, Not Null).
- `newbalance_orig` (`DOUBLE PRECISION`, Not Null).
- `oldbalance_dest` (`DOUBLE PRECISION`, Not Null).
- `newbalance_dest` (`DOUBLE PRECISION`, Not Null).
- `log_amount` (`DOUBLE PRECISION`, Not Null).
- `is_transfer` (`INTEGER`, Not Null).
- `is_cash_out` (`INTEGER`, Not Null).
- `hour_of_day` (`DOUBLE PRECISION`, Not Null).
- `hour_sin` (`DOUBLE PRECISION`, Not Null).
- `hour_cos` (`DOUBLE PRECISION`, Not Null).
- `is_night_transaction` (`INTEGER`, Not Null).
- `orig_balance_error` (`DOUBLE PRECISION`, Not Null).
- `orig_drain_ratio` (`DOUBLE PRECISION`, Not Null).
- `is_full_liquidation` (`INTEGER`, Not Null).
- `dest_balance_error` (`DOUBLE PRECISION`, Not Null).
- `dest_drain_ratio` (`DOUBLE PRECISION`, Not Null).
- `dest_zero_balance_anomaly` (`INTEGER`, Not Null).
- `created_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).

### 2.7 Entity: `model_results`
Stores raw and normalized inference signals for each model architecture evaluated.
- `result_id` (`UUID`, Primary Key, default `uuid.uuid4`).
- `tx_id` (`UUID`, Foreign Key $\to$ `transactions.tx_id` ON DELETE CASCADE, Not Null, Index).
- `model_name` (`VARCHAR(32)`, Not Null, Index) — `xgboost`, `autoencoder`, `isolation_forest`, `logistic_regression`.
- `raw_output` (`DOUBLE PRECISION`, Not Null) — Raw prediction (probabilities, reconstruction MSE, isolation path score).
- `normalized_signal` (`DOUBLE PRECISION`, Not Null) — Normalized risk signal scaled to $[0.0, 1.0]$.
- `model_version` (`VARCHAR(64)`, Not Null) — Serialized artifact filename or hash.
- `inference_time_ms` (`DOUBLE PRECISION`, Nullable) — Evaluation latency in milliseconds.
- `evaluated_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).

### 2.8 Entity: `risk_assessments`
Ensemble multi-signal aggregation output produced by the Risk Engine.
- `assessment_id` (`UUID`, Primary Key, default `uuid.uuid4`).
- `tx_id` (`UUID`, Foreign Key $\to$ `transactions.tx_id` ON DELETE CASCADE, Unique, Not Null, Index).
- `xgboost_signal` (`DOUBLE PRECISION`, Not Null) — $S_{\text{xgb}} \in [0.0, 1.0]$.
- `logistic_signal` (`DOUBLE PRECISION`, Not Null) — $S_{\text{lr}} \in [0.0, 1.0]$.
- `isolation_signal` (`DOUBLE PRECISION`, Not Null) — $S_{\text{if}} \in [0.0, 1.0]$.
- `autoencoder_signal` (`DOUBLE PRECISION`, Not Null) — $S_{\text{ae}} \in [0.0, 1.0]$.
- `final_risk_score` (`DOUBLE PRECISION`, Not Null, Index) — Aggregated score $\in [0.00, 100.00]$.
- `engine_version` (`VARCHAR(32)`, Not Null, default `'1.0.0'`).
- `evaluated_by` (`VARCHAR(32)`, Not Null, default `'ml_ensemble'`).
- `evaluated_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).

### 2.9 Entity: `decisions`
Operational triage action rendered by policy rules.
- `decision_id` (`UUID`, Primary Key, default `uuid.uuid4`).
- `assessment_id` (`UUID`, Foreign Key $\to$ `risk_assessments.assessment_id` ON DELETE CASCADE, Unique, Not Null, Index).
- `policy_decision` (`VARCHAR(16)`, Not Null, Index) — `APPROVE`, `REVIEW`, `BLOCK`.
- `reasons` (`JSON`, Not Null) — Structured list of diagnostic rule explanations.
- `created_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).

### 2.10 Entity: `alerts`
Work queue items generated for transactions requiring human analyst review or immediate escalation.
- `alert_id` (`UUID`, Primary Key, default `uuid.uuid4`).
- `assessment_id` (`UUID`, Foreign Key $\to$ `risk_assessments.assessment_id` ON DELETE CASCADE, Not Null, Index).
- `severity` (`VARCHAR(16)`, Not Null, default `'HIGH'`, Index) — `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- `status` (`VARCHAR(16)`, Not Null, default `'PENDING'`, Index) — `PENDING`, `IN_REVIEW`, `RESOLVED`, `DISMISSED`.
- `assigned_user_id` (`UUID`, Foreign Key $\to$ `users.user_id`, Nullable, Index).
- `notes` (`TEXT`, Nullable) — Analyst forensic case notes.
- `created_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`).
- `resolved_at` (`TIMESTAMPTZ`, Nullable).

### 2.11 Entity: `audit_logs`
Immutable, append-only security and operational audit trail.
- `log_id` (`BIGINT`, Primary Key, Autoincrement) — 64-bit sequence counter.
- `actor_id` (`VARCHAR(64)`, Nullable, Index) — ID of human analyst, device, or system service.
- `actor_type` (`VARCHAR(32)`, Not Null, default `'SYSTEM'`, Index) — `USER`, `DEVICE`, `SYSTEM`, `API`.
- `event_type` (`VARCHAR(64)`, Not Null, Index) — e.g. `TRANSACTION_ASSESSED`, `DECISION_OVERRIDE`, `CONFIG_CHANGED`.
- `action` (`VARCHAR(64)`, Not Null) — Specific action verb.
- `resource_type` (`VARCHAR(64)`, Not Null, Index) — e.g. `transaction`, `alert`, `config`.
- `resource_id` (`VARCHAR(64)`, Nullable, Index).
- `details` (`JSON`, Nullable) — Event metadata, parameters, or forensic snapshot.
- `created_at` (`TIMESTAMPTZ`, Not Null, default `UTC NOW`, Index).

---

## 3. Third Normal Form (3NF) Justification

The schema satisfies 3NF requirements:
1. **1NF Compliance:** All attributes contain atomic values; arrays or multi-valued attributes are eliminated; primary keys uniquely identify every row.
2. **2NF Compliance:** All non-key attributes are fully functionally dependent on the entire primary key (no partial dependencies on composite keys, as all tables utilize single-column UUID or sequential primary keys).
3. **3NF Compliance:** No transitive functional dependencies exist ($X \to Y \to Z$):
   - Merchant details (category, risk tier) reside in `merchants`, not inside `devices` or `transactions`.
   - Device attributes (firmware version, status) reside in `devices`, not in `transactions`.
   - Feature vectors reside in `transaction_features`, avoiding column bloat in `transactions`.
   - Analyst roles reside in `roles`, avoiding repeating role descriptions across `users`.

---

## 4. Connection & Session Management Architecture

Database access is centralized in `database/connection.py`:
- **Connection Pooling:** In PostgreSQL environments, SQLAlchemy maintains an efficient connection pool with `pool_size=10`, `max_overflow=20`, `pool_timeout=30s`, and `pool_recycle=1800s`.
- **Atomic Unit of Work (`get_db_session`):** A context manager yields a scoped session. If the block completes successfully, `session.commit()` is issued automatically. If an exception occurs, `session.rollback()` is executed before re-raising, preventing orphaned transactions or dirty database state.
- **Repository Integration (`save_assessed_transaction`):** Bridges the ML Risk Engine's immutable domain entity (`RiskAssessment`) directly into database persistence in a single ACID transaction.

---

## 5. Schema Initialization Mechanism

The CLI tool `database/init_db.py` provides safe schema deployment:
- **Connectivity Check:**
  ```powershell
  .\.venv\Scripts\python.exe database/init_db.py --check
  ```
- **Idempotent Table Creation:**
  ```powershell
  .\.venv\Scripts\python.exe database/init_db.py --init
  ```
- **Data Safety Guarantee:** `init_db()` uses `Base.metadata.create_all()` which inspects existing catalog tables and only creates missing entities. Existing rows and tables are never dropped or altered without explicit confirmation via `--force-recreate`.

---

## 6. Testing & Quality Assurance

The test suite in `tests/test_database.py` verifies:
- **Registry Completeness:** All 11 tables are registered in `Base.metadata`.
- **Schema & Key Integrity:** Verifies primary keys, foreign keys, and absence of target labels from operational tables.
- **Constraint Enforcement:** Verifies unique constraints on roles, usernames, and merchant codes.
- **End-to-End Persistence:** Tests saving an `APPROVE` transaction, verifying full relational tree linkage across `transactions`, `transaction_features`, `model_results`, `risk_assessments`, and `decisions`.
- **Automated Alert Generation:** Tests saving a `BLOCK` transaction, verifying that an automated `CRITICAL` alert is queued for analyst review.
- **Audit Logging:** Tests structured audit log recording and retrieval.
- **Rollback Behavior:** Verifies that failed operations rollback completely without leaving partial database artifacts.

### Test Execution Results
```
tests/test_database.py::test_all_models_registered PASSED                [ 12%]
tests/test_database.py::test_table_columns_and_keys PASSED               [ 25%]
tests/test_database.py::test_role_and_user_creation PASSED               [ 37%]
tests/test_database.py::test_merchant_and_device_creation PASSED         [ 50%]
tests/test_database.py::test_save_assessed_transaction_approve PASSED    [ 62%]
tests/test_database.py::test_save_assessed_transaction_block_creates_alert PASSED [ 75%]
tests/test_database.py::test_audit_log_persistence PASSED                [ 87%]
tests/test_database.py::test_transaction_rollback_integrity PASSED       [100%]
============================== 8 passed in 1.20s ==============================
```

All 28 project tests across Milestones 0 to 5 pass cleanly (100% test pass rate).

---

## 7. Implementation Boundary Audit

| System Component | Status in Milestone 5 | Verification / Next Steps |
| :--- | :--- | :--- |
| **3NF Relational Schema (11 tables)** | **IMPLEMENTED** | Verified in `database/models/` via SQLAlchemy 2.0. |
| **Session & Transaction Lifecycle** | **IMPLEMENTED** | Verified in `database/connection.py` with auto-rollback. |
| **Risk Engine Persistence Bridge** | **IMPLEMENTED** | Verified in `database/repository.py` (`save_assessed_transaction`). |
| **Schema Initialization Tool** | **IMPLEMENTED** | Verified in `database/init_db.py` (`--check`, `--init`). |
| **Automated Database Test Suite** | **IMPLEMENTED** | Verified in `tests/test_database.py` (8/8 passed). |
| **FastAPI REST Service** | **PLANNED (Milestone 6)** | Endpoints `/api/v1/assess` will ingest transactions and call database repository. |
| **ESP32 IoT POS Hardware Flashing** | **PLANNED (Milestone 7)** | Hardware firmware will sign payloads and submit to API gateway. |
| **React/Next.js Analyst Dashboard** | **PLANNED (Milestone 8)** | Frontend portal will query `alerts` and `risk_assessments`. |
| **Continuous Learning Pipeline** | **PLANNED (Milestone 9)** | Retraining worker will sample historical transactions and audit logs. |
