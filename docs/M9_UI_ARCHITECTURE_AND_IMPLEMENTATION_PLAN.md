# A.R.G.U.S. — Milestone 9 Architecture & Implementation Plan
## Web UI, Fraud Analyst Dashboard & Final End-to-End System Integration (CORRECTED PLAN)

**Project:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Subtitle:** AI-Based Real-Time Fraud Detection and Transaction Risk Monitoring System  
**Academic Programme:** B.Tech AIML – Semester PBL (Odd Semester 2026–27)  
**Document Type:** Milestone 9 Architectural Blueprint & Technical Implementation Plan (PLANNING ONLY)  
**Status:** REVISED & APPROVED PENDING IMPLEMENTATION AUTHORIZATION  

---

## 1. Executive Summary

Milestones 0 through 8 have successfully established and validated the computational, database, machine learning, and security foundation of Project **A.R.G.U.S.**:
- Feature engineering on the PaySim benchmark dataset with 18 extracted features and strict temporal anti-leakage guards.
- A 4-model machine learning and deep learning ensemble:
  - Supervised XGBoost (50% weight) — Model-estimated probability
  - Unsupervised Deep PyTorch Autoencoder (20% weight) — Reconstruction anomaly signal
  - Unsupervised Isolation Forest (15% weight) — Anomaly signal
  - Supervised Logistic Regression (15% weight) — Model-estimated probability
- An ensemble Risk Engine producing continuous 0–100 risk scores and tri-state operational policy decisions (`APPROVE` $<40$, `REVIEW` $40$–$69$, `BLOCK` $\ge 70$).
- A 3NF PostgreSQL persistence layer maintaining atomic transaction features, model signals, decisions, alerts, and security audit records.
- A hardened FastAPI gateway with JWT bearer authentication, Role-Based Access Control (RBAC) across 5 operational roles, sliding-window rate limiting, and HTTP security headers.
- Physical edge IoT POS terminal ingestion via ESP32 microcontrollers with SHA-256 header authentication and database-level unique replay protection.
- A verified baseline test suite with **73 / 73 unit and integration tests passing**.

**Milestone 9 Objective:**  
The objective of Milestone 9 is to build a professional, high-performance, and visually communicative web application on top of the validated FastAPI backend. The interface strictly avoids generic admin templates; it visually and functionally communicates the core purpose of A.R.G.U.S.:
$$\text{TRANSACTION INGRESS} \longrightarrow \text{FEATURE EXTRACTION} \longrightarrow \text{MULTI-MODEL SIGNALS} \longrightarrow \text{RISK ENGINE SCORE} \longrightarrow \text{TRI-STATE DECISION}$$

---

## 2. Current Repository Findings & Baseline State

A systematic inspection of the codebase yields the following baseline findings:

1. **Active Environment**:
   - Python 3.13.7 in `.venv` with FastAPI 0.115+, PyTorch 2.5+, XGBoost 2.1+, scikit-learn 1.5+, SQLAlchemy 2.0+, psycopg2-binary, and PyJWT.
   - Node.js `v24.11.0` and npm `11.6.1` installed and operational on the host system.
   - Test suite status: **73 passed, 0 failed** in 117.59s across all modules.

2. **Backend Gateway & CORS Configuration (`backend/config.py`)**:
   - Allowed origins:
     ```python
     CORS_ORIGINS = [
         "http://localhost:3000",
         "http://127.0.0.1:3000",
         "http://localhost:8000",
         "http://127.0.0.1:8000",
         "http://localhost:8008",
         "http://127.0.0.1:8008",
     ]
     ```
   - Running the frontend development server on port `3000` satisfies CORS out-of-the-box without modifying backend configuration.

3. **Database Entities (`database/models/`)**:
   - `User` & `Role`: Identity, bcrypt password hash, roles (`USER`, `ANALYST`, `ADMIN`, `AUDITOR`).
   - `Transaction`: Raw transaction attributes, temporal step, balances, merchant/device FKs.
   - `TransactionFeatures`: 18 engineered features.
   - `ModelResult`: Individual inference outputs and execution latencies.
   - `RiskAssessmentRecord`: Normalized model signals, final continuous risk score (0–100).
   - `DecisionRecord`: Operational policy verdict (`APPROVE`, `REVIEW`, `BLOCK`) and explainable reason list.
   - `Alert`: Review queue records (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) with statuses (`PENDING`, `IN_REVIEW`, `RESOLVED`, `DISMISSED`).
   - `Device`: IoT terminals, device codes, status (`ACTIVE`, `OFFLINE`, `TAMPERED`), firmware version, last seen timestamp.
   - `AuditLog`: Security and transaction audit log of actor actions, event types, and metadata.

4. **Modeling Subspace Policy**:
   - Only `TRANSFER` and `CASH_OUT` are evaluated by the machine learning pipeline.
   - Non-modeled types (`PAYMENT`, `CASH_IN`, `DEBIT`) return a controlled `HTTP 422 Unprocessable Entity`.
   - Anti-leakage guards reject any request containing `isFraud` or `isFlaggedFraud`.

---

## 3. Current API Inventory

The table below documents every endpoint that **currently exists** in the backend:

| HTTP Method | Route | Auth / Role Required | Request Body / Query | Response Model | Operational Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | None (Public) | None | `HealthResponse` | Liveness check |
| `GET` | `/ready` | None (Public) | None | `ReadinessResponse` | DB & model artifact readiness |
| `POST` | `/api/v1/auth/register` | None (Public) | `UserRegisterRequest` | `UserResponse` | User account self-registration |
| `POST` | `/api/v1/auth/login` | None (Public) | `UserLoginRequest` | `TokenResponse` | Issues HS256 JWT bearer token |
| `GET` | `/api/v1/auth/me` | Bearer JWT (Any active role) | None | `UserResponse` | Current user profile and role |
| `POST` | `/api/v1/transactions/assess` | Optional JWT (Tracks user if logged in) | `TransactionCreateRequest` | `TransactionAssessResponse` | Ingress, features, ML inference, persistence |
| `GET` | `/api/v1/transactions/{tx_id}` | Optional / RBAC (IDOR protected) | Path `tx_id` | `TransactionResponse` | Raw transaction fields by ID |
| `GET` | `/api/v1/admin/audit-logs` | Bearer JWT (`ADMIN`, `AUDITOR`) | `limit`, `offset`, `event_type` | `List[AuditLogResponse]` | Security event history |
| `GET` | `/api/v1/admin/users` | Bearer JWT (`ADMIN`) | `limit`, `offset` | `List[UserResponse]` | System user roster |
| `POST` | `/api/v1/iot/transactions` | Edge Header (`X-Device-Code`, `X-Device-API-Key`) | `IoTTransactionRequest` | `IoTRiskResponse` | ESP32 POS transaction ingestion |
| `POST` | `/api/v1/iot/heartbeat` | Edge Header (`X-Device-Code`, `X-Device-API-Key`) | `IoTHeartbeatRequest` | `IoTHeartbeatResponse` | ESP32 telemetry & tamper update |

---

## 4. Frontend Technology Recommendation

- **Stack**: **React 19 + Vite + React Router v6 + Vanilla CSS (CSS Modules & Design Tokens)**
- **Port**: `http://localhost:3000` (strictly matching `backend/config.py` CORS origins).
- **Rationale**:
  - Zero external UI library bloat (avoids generic Bootstrap or heavy Tailwind dependencies).
  - Clean CSS custom properties for a cohesive cybersecurity aesthetic (**Deep Obsidian `#0B0F19`**, **Charcoal Slate `#111827`**, and **Tri-State Risk Palette**).
  - Rapid local development with sub-second Hot Module Replacement (HMR).
  - Deterministic build to `frontend/dist/`.

---

## 5. UI Architecture & API-First Data Flow

The frontend strictly communicates with PostgreSQL via the FastAPI application layer. The browser never accesses the database directly.

```
+──────────────────────────────────────────────────────────────────────+
|                           React Application                          |
|                                                                      |
|  +────────────────────────────────────────────────────────────────+  |
|  |             Authentication Context (User, Role, Token)         |  |
|  +────────────────────────────────────────────────────────────────+  |
|                                │                                     |
|                                ▼                                     |
|  +────────────────────────────────────────────────────────────────+  |
|  |                 App Layout (Sidebar + Top Navbar)              |  |
|  +────────────────────────────────────────────────────────────────+  |
|         │                  │                    │             │      |
|         ▼                  ▼                    ▼             ▼      |
|  [ Simulator ]      [ Dashboard ]       [ Transactions ]   [ Alerts ]
|  [ Risk Result ]    (Analyst/Admin)     [ Detail View ]    (Analyst) |
|         │                  │                    │             │      |
|         ▼                  ▼                    ▼             ▼      |
|  +────────────────────────────────────────────────────────────────+  |
|  |                   Centralized API Client Layer                 |  |
|  |  - Bearer Token Interceptor   - Error & Toast Notification     |  |
|  |  - 401 Redirect to Login      - 422 Non-Modeled Type Modal     |  |
|  |  - 429 Rate Limit Warning     - Network Failure Fallback       |  |
|  +────────────────────────────────────────────────────────────────+  |
+──────────────────────────────────────────────────────────────────────+
                                 │
                                 ▼ (HTTP REST on http://localhost:8000)
+──────────────────────────────────────────────────────────────────────+
|                        FastAPI Gateway Layer                         |
|  - RateLimitMiddleware           - SecurityHeadersMiddleware         |
|  - JWT Bearer Authentication     - RBAC & Object Authorization (IDOR)|
+──────────────────────────────────────────────────────────────────────+
                                 │
                                 ▼
+──────────────────────────────────────────────────────────────────────+
|                       Application Services                           |
|  - TransactionService  - AuthService  - AuditService  - DeviceService|
+──────────────────────────────────────────────────────────────────────+
                                 │
                                 ▼
+──────────────────────────────────────────────────────────────────────+
|                    Repository & PostgreSQL (3NF)                     |
+──────────────────────────────────────────────────────────────────────+
```

---

## 6. Information Architecture & Navigation

### Role-Based Navigation Matrix

> [!IMPORTANT]
> **Client-Side Navigation $\neq$ Security Boundary**:  
> Frontend role checks exist solely for user experience. The FastAPI backend remains the authoritative enforcement point for all data access and actions.

| Route | Page / View | Allowed Roles | Functional Scope |
| :--- | :--- | :--- | :--- |
| `/login` | Authentication Portal | Public | Credential login and account registration |
| `/simulator` | A.R.G.U.S. Transaction Simulator | `USER`, `ANALYST`, `ADMIN` | Interactive transaction entry and live risk evaluation |
| `/simulator/result/:id` | Risk Assessment Verdict | `USER`, `ANALYST`, `ADMIN` | Score gauge, model signals breakdown, explainable reasons |
| `/dashboard` | Fraud Monitoring Overview | `ANALYST`, `ADMIN`, `AUDITOR` | Live database KPI metrics, risk trend, recent high-risk table |
| `/transactions` | Transaction History | `USER` (own), `ANALYST`, `ADMIN`, `AUDITOR` | Paginated transaction explorer with server-side filters |
| `/transactions/:id` | Transaction Detail Inspector | `USER` (own), `ANALYST`, `ADMIN`, `AUDITOR` | Engineered model features, model signals, device info |
| `/alerts` | Investigation Queue | `ANALYST`, `ADMIN` | Persisted fraud alerts, triage actions, resolution notes |
| `/devices` | IoT Edge Terminal Fleet | `ANALYST`, `ADMIN`, `AUDITOR` | ESP32 hardware status, telemetry, tamper locks |
| `/admin/audit` | Security Audit Explorer | `ADMIN`, `AUDITOR` | Event history with actor, action, resource, timestamp |
| `/admin/users` | User Administration | `ADMIN` | User accounts, role assignment, activation status |

---

## 7. Flow 2: Transaction Simulator UX (Simulation Boundary Clarification)

- **Simulator Designation**: The interface is strictly titled **"A.R.G.U.S. Transaction Simulator"** or **"A.R.G.U.S. Secure Transaction Terminal"**. It does NOT claim integration with Google Pay, UPI, or commercial banking rails.
- **Viva Presets as Real Requests**: Presets ONLY pre-fill form input fields. They do NOT hardcode outcomes. When submitted, a real HTTP request is dispatched to `POST /api/v1/transactions/assess`, executing the actual ML/DL inference and Risk Engine logic.

### Preset Scenarios (Form Inputs Only)
1. **Preset 1 (Benign Daytime Transfer)**: Small amount (₹1,200), balanced origin account, daytime hour $\rightarrow$ Form pre-fill only.
2. **Preset 2 (Synthetic Account Drain Attack)**: Large amount (₹399,045.08), complete balance drain, zero destination balance before and after, night hour $\rightarrow$ Form pre-fill only.
3. **Preset 3 (Suspicious Cash-Out)**: Rapid liquidation (₹45,000), borderline drain $\rightarrow$ Form pre-fill only.
4. **Preset 4 (Non-Modeled Category)**: Transaction type `PAYMENT` $\rightarrow$ Demonstrates controlled `HTTP 422` handling.

### Wireframe: Transaction Simulator
```
+────────────────────────────────────────────────────────────────────────────────────────────────────────+
| A.R.G.U.S. TRANSACTION SIMULATOR                                      [Load Preset: Account Drain ▼]  |
+────────────────────────────────────────────────────────────────────────────────────────────────────────+
|  Simulation Step (Hour)               Transaction Type                                                 |
|  [ 646                        ]       [ TRANSFER                     ▼ ]                               |
|                                                                                                        |
|  Transfer Amount (₹)                  Origin Account ID                                                |
|  [ 399,045.08                 ]       [ C1234567890                  ]                                 |
|                                                                                                        |
|  Origin Initial Balance (₹)           Origin Post-Transaction Balance (₹)                              |
|  [ 10,399,045.08              ]       [ 10,000,000.00                ]                                 |
|                                                                                                        |
|  Destination Account ID               Destination Initial Balance (₹)                                  |
|  [ M9876543210                ]       [ 0.00                         ]                                 |
|                                                                                                        |
|  Destination Post-Balance (₹)         Simulated Client TX Sequence ID                                  |
|  [ 0.00                       ]       [ CLI-TX-2026-9901             ]                                 |
|                                                                                                        |
|  [ ANALYZE TRANSACTION WITH A.R.G.U.S. RISK ENGINE ]                                                  |
+────────────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 8. Flow 3: Risk Result UX & Model Signal Terminology

The Risk Result screen renders the exact backend output returned by `POST /api/v1/transactions/assess`.

### Accurate Terminology & Policy Thresholds
- **Policy Decisions**:
  - `Risk Score < 40` $\longrightarrow$ **APPROVE** (Emerald `#10B981`)
  - `40 ≤ Risk Score < 70` $\longrightarrow$ **REVIEW** (Amber `#F59E0B`)
  - `Risk Score ≥ 70` $\longrightarrow$ **BLOCK** (Crimson `#EF4444`)
- **Model Signal Labels (Not Calibrated Probabilities)**:
  - Supervised XGBoost (50% weight): `"Model-estimated probability"`
  - Supervised Logistic Regression (15% weight): `"Model-estimated probability"`
  - Unsupervised Isolation Forest (15% weight): `"Anomaly signal"`
  - Unsupervised Deep Autoencoder (20% weight): `"Anomaly signal"`

### Wireframe: Risk Assessment Verdict
```
+────────────────────────────────────────────────────────────────────────────────────────────────────────+
| RISK ASSESSMENT VERDICT                                                Transaction ID: 7f8a9b...       |
+────────────────────────────────────────────────────────────────────────────────────────────────────────+
|  +───────────────────────────────────+   +──────────────────────────────────────────────────────────+  |
|  |           FINAL RISK SCORE        |   |                 MODEL SIGNAL DECOMPOSITION               |  |
|  |                                   |   |                                                          |  |
|  |              84.36                |   |  Supervised XGBoost (50% weight)                         |  |
|  |             / 100                 |   |  [██████████████████████████████░░░░] 78.4% (model prob) |  |
|  |                                   |   |                                                          |  |
|  |             [ BLOCK ]             |   |  Unsupervised Deep Autoencoder (20% weight)              |  |
|  |      Action: IMMEDIATE REJECTION  |   |  [██████████████████████████████████] 98.2% (anomaly)    |  |
|  |                                   |   |                                                          |  |
|  |  Thresholds:                      |   |  Unsupervised Isolation Forest (15% weight)              |  |
|  |  <40: APPROVE                     |   |  [██████████████████████████░░░░░░░░] 71.0% (anomaly)    |  |
|  |  40–69: REVIEW                    |   |                                                          |  |
|  |  >=70: BLOCK                      |   |  Supervised Logistic Regression (15% weight)             |  |
|  |                                   |   |  [██████████████████████████████████] 100.0% (model prob)|  |
|  +───────────────────────────────────+   +──────────────────────────────────────────────────────────+  |
|                                                                                                        |
|  EXPLAINABLE FORENSIC REASONS:                                                                         |
|  • High XGBoost model-estimated fraud probability (0.784)                                             |
|  • Extreme Deep Autoencoder reconstruction error indicates spatial anomaly (0.982)                    |
|  • Destination account zero-balance anomaly (newbalanceDest is 0 after transfer)                      |
|  • Large monetary magnitude exceeding typical customer baseline                                       |
|                                                                                                        |
|  [ View Engineered Features ]       [ Submit Another Transaction ]       [ View in Analyst Queue ]     |
+────────────────────────────────────────────────────────────────────────────────────────────────────────+
```

---

## 9. Flow 4: Transaction Detail & Engineered Model Features

When inspecting an individual transaction, the detail page displays the **Engineered Model Features** computed by the backend feature pipeline.

- **Safe Disclosure Rules**:
  - Exposes the 18 engineered features safely under the section **"Engineered Model Features"** (e.g. `log_amount`, `orig_drain_ratio`, `orig_balance_error`, `hour_sin`, `hour_cos`, `is_night_transaction`).
  - Raw customer identifiers (`name_orig`, `name_dest`) are displayed with appropriate context.
  - Target labels (`isFraud`, `isFlaggedFraud`) are strictly **never** exposed to the frontend.
  - Zero duplicate feature-engineering code in React; all values originate from the backend persistence layer.

---

## 10. Flow 5: Analyst Dashboard (Real PostgreSQL Data & Empty States)

All metrics displayed on the dashboard are driven by backend SQL aggregations:
- **Zero Mock Metrics**: Total Evaluated, Approved Count, Review Count, Blocked Count, Average Risk Score, and Active Devices are fetched from `GET /api/v1/analytics/dashboard`.
- **Meaningful Trends & Empty State Handling**:
  - The risk trend displays actual time-bucketed or step-based transaction volume and average score.
  - On a fresh installation with minimal or zero transactions, the UI displays a clean empty state:
    > *"No historical transaction data available yet. Use the Transaction Simulator or IoT Terminal to evaluate live transactions."*
  - No decorative charts with fabricated historical data.

---

## 11. Flow 6: Alerts & Investigation Queue

- Alerts are real records persisted in PostgreSQL table `alerts` when transactions receive `REVIEW` or `BLOCK`.
- Resolving an alert in the UI triggers `PATCH /api/v1/alerts/{alert_id}`, updating the record status (`IN_REVIEW`, `RESOLVED`, `DISMISSED`) and persisting analyst notes and user assignment in PostgreSQL.
- Resolving an alert emits a structured `ALERT_RESOLVED` event in `audit_logs`.

---

## 12. Flow 7: Transaction History (Server-Side Pagination & Scoped RBAC)

- The transaction history endpoint `GET /api/v1/transactions` enforces strict authorization:
  - **`USER` Role**: Scoped strictly to transactions submitted by the user (`user_id == current_user.user_id` or `name_orig == current_user.username`). Normal users cannot view transactions belonging to other users.
  - **`ANALYST`, `ADMIN`, `AUDITOR` Roles**: Granted system-wide visibility across all transaction records for fraud monitoring and compliance.
- All pagination and filtering (`type`, `decision`, `min_risk`, `max_risk`) are executed server-side via PostgreSQL queries.

---

## 13. Flow 8: IoT & Edge Terminal Fleet Monitor (Real Hardware Telemetry)

Reflects actual device records registered in the `devices` table:
- **Telemetry Fields**: Device Code, Registered Merchant, Device Status (`ACTIVE`, `OFFLINE`, `TAMPERED`), Firmware Version, Last Seen timestamp, SoC Internal Temperature, Network Status, Uptime, and Tamper Flag.
- **Honest Telemetry Representation**: If a terminal has not sent a heartbeat report within 120 seconds, its status is displayed as `OFFLINE`. Status is never fabricated.
- **Admin Tamper Reset**: A hardware-tampered terminal locked with `tamper_flag=True` can be reset only by an `ADMIN` user via `POST /api/v1/devices/{device_id}/reset-tamper`.

---

## 14. Flow 9: Security Audit Explorer

The Admin/Auditor governance view consumes the existing M7 endpoint `GET /api/v1/admin/audit-logs`.
- **Title**: **"Security Audit Explorer — Security Event History"** (avoids the term "immutable" since standard PostgreSQL tables are not cryptographically sealed ledgers).
- **Sanitized Metadata**: Passwords, raw JWT tokens, API keys, and database secrets are never returned by the API or displayed in the UI.
- **Auditor Access**: `AUDITOR` accounts have full read-only access to query all audit logs, but cannot alter users, trigger simulator presets, or mutate database state.

---

## 15. Real-Time Behavior Architecture

- To maintain academic simplicity and avoid unnecessary infrastructure (Kafka, Redis, WebSockets), real-time monitoring utilizes **deterministic REST polling**:
  - The Analyst Dashboard provides a configurable auto-refresh selector: `[ Off ]`, `[ 15s ]`, `[ 30s ]`, `[ 60s ]`, along with an explicit `[ Refresh Now ]` button.
  - WebSocket/SSE streaming is deferred to future production hardening.

---

## 16. API Integration Matrix

| UI Component | Required API Route | Current State | Required M9 Action |
| :--- | :--- | :--- | :--- |
| **Login** | `POST /api/v1/auth/login` | **EXISTING** | Connect UI login form |
| **User Profile & Role** | `GET /api/v1/auth/me` | **EXISTING** | Connect session loader |
| **System Liveness & Readiness** | `GET /health` & `GET /ready` | **EXISTING** | Connect header status badge |
| **Simulate Transaction** | `POST /api/v1/transactions/assess` | **EXISTING** | Connect simulator form submission |
| **Transaction History** | `GET /api/v1/transactions` | **MISSING** | **Implement M9 endpoint (scoped RBAC & server-side pagination)** |
| **Transaction Detail & Features** | `GET /api/v1/transactions/{tx_id}` | **EXISTING (PARTIAL)** | **Enrich response to include assessment, decision & 18 features** |
| **Analyst Dashboard KPIs** | `GET /api/v1/analytics/dashboard` | **MISSING** | **Implement M9 endpoint (SQL aggregates & recent high-risk)** |
| **Alerts Queue** | `GET /api/v1/alerts` | **MISSING** | **Implement M9 endpoint (pending alerts query)** |
| **Alert Triage & Disposition** | `PATCH /api/v1/alerts/{alert_id}` | **MISSING** | **Implement M9 endpoint (update status, notes & audit log)** |
| **IoT Fleet Inventory** | `GET /api/v1/devices` | **MISSING** | **Implement M9 endpoint (list registered devices & telemetry)** |
| **Reset Device Tamper** | `POST /api/v1/devices/{id}/reset-tamper` | **MISSING** | **Implement M9 endpoint (admin-only tamper reset)** |
| **Security Audit Explorer** | `GET /api/v1/admin/audit-logs` | **EXISTING** | Connect Audit Explorer view |
| **User Administration** | `GET /api/v1/admin/users` | **EXISTING** | Connect User Management view |

---

## 17. Detailed Specification of Required Backend Changes

All additions adhere strictly to existing M6–M8 architecture (Pydantic schemas, dependency injection, service layer, SQLAlchemy queries, and RBAC).

### 1. Transaction History (`GET /api/v1/transactions`)
- **File**: `backend/api/routes/transactions.py`
- **Permissions**: `USER` (filtered to own records), `ANALYST`, `ADMIN`, `AUDITOR` (all records).
- **Query Parameters**: `limit: int = 50`, `offset: int = 0`, `type: Optional[str] = None`, `decision: Optional[str] = None`, `min_risk: Optional[float] = None`, `max_risk: Optional[float] = None`.
- **Response**: List of transaction items including `tx_id`, `step`, `type`, `amount`, `name_orig`, `name_dest`, `risk_score`, `decision`, `created_at`.

### 2. Enriched Transaction Detail (`GET /api/v1/transactions/{tx_id}`)
- **File**: `backend/schemas/transaction.py` & `backend/services/transaction_service.py`
- **Enrichment**: Return `TransactionDetailResponse` containing:
  - Raw attributes (`tx_id`, `step`, `type`, `amount`, `name_orig`, `name_dest`, balances).
  - Risk assessment (`final_risk_score`, `evaluated_by`, `evaluated_at`).
  - Operational decision (`policy_decision`, `reasons`).
  - Model signals decomposed (`xgboost_score`, `autoencoder_score`, `isolation_score`, `logistic_score`).
  - Engineered model features (`log_amount`, `orig_drain_ratio`, `orig_balance_error`, `hour_sin`, `hour_cos`, `is_night_transaction`).
  - Associated device code and merchant name if present.
- **Anti-Leakage**: Strictly excludes `isFraud` and `isFlaggedFraud`.

### 3. Analyst Dashboard Analytics (`GET /api/v1/analytics/dashboard`)
- **File**: `backend/api/routes/analytics.py` (New route)
- **Permissions**: Restricted to `ANALYST`, `ADMIN`, `AUDITOR`.
- **Response Schema**:
  ```json
  {
    "total_transactions": 1420,
    "approved_count": 1180,
    "review_count": 145,
    "blocked_count": 95,
    "average_risk_score": 24.8,
    "active_devices_count": 2,
    "pending_alerts_count": 8,
    "recent_high_risk": [ ...5 latest transactions with risk >= 70... ]
  }
  ```

### 4. Alerts Review & Disposition (`/api/v1/alerts`)
- **File**: `backend/api/routes/alerts.py` (New route)
- **Permissions**: Restricted to `ANALYST`, `ADMIN`.
- **Endpoints**:
  - `GET /api/v1/alerts`: Returns alerts filtered by `status` (`PENDING`, `IN_REVIEW`, `RESOLVED`, `DISMISSED`) and `severity`.
  - `PATCH /api/v1/alerts/{alert_id}`: Accepts `status`, `notes`, and `assigned_user_id`. Updates PostgreSQL record and logs `ALERT_RESOLVED` in `audit_logs`.

### 5. IoT Fleet Inventory (`/api/v1/devices`)
- **File**: `backend/api/routes/devices.py` (New route)
- **Permissions**: `ANALYST`, `ADMIN`, `AUDITOR` for listing; `ADMIN` only for tamper reset.
- **Endpoints**:
  - `GET /api/v1/devices`: Returns device inventory with real telemetry from heartbeats.
  - `POST /api/v1/devices/{device_id}/reset-tamper`: Sets `tamper_flag=False` and status back to `ACTIVE`.

---

## 18. API Error Handling Architecture

The frontend centralizes error handling via Axios/fetch response interceptors, preventing technical stack traces from leaking to the UI:

| HTTP Status | Trigger Condition | User-Facing Display Message |
| :--- | :--- | :--- |
| **401 Unauthorized** | Token missing, invalid, or expired | *"Your session has expired. Please log in again."* (Redirects to `/login`) |
| **403 Forbidden** | User lacks required role for resource | *"Access Denied: You do not have permission to access this resource."* |
| **409 Conflict** | Duplicate `client_tx_id` from edge device | *"Duplicate transaction detected. The sequence ID has already been processed."* |
| **422 Unprocessable** | Unsupported transaction type (`PAYMENT`) | *"Transaction type 'PAYMENT' is not currently supported for ML risk assessment. A.R.G.U.S. evaluates TRANSFER and CASH_OUT categories."* |
| **422 Unprocessable** | Target label passed (`isFraud`) | *"Anti-leakage violation: Ground-truth fraud labels cannot be supplied to live inference."* |
| **429 Rate Limited** | Request rate exceeds 100 req/min | *"Too many requests. Please wait a moment before retrying."* |
| **500 Server Error** | Unexpected backend exception | *"An internal server error occurred while processing the transaction."* |
| **Network Failure** | Backend server is unreachable | *"Unable to communicate with the A.R.G.U.S. Gateway. Check if backend is running."* |

---

## 19. Cross-Curricular Academic Subject Integration

During project viva, the UI directly demonstrates all six required semester subject areas:

| Academic Subject Area | Direct UI Manifestation | Underlying Technical Component |
| :--- | :--- | :--- |
| **Deep Learning** | Autoencoder Anomaly Signal (20% weight) | PyTorch Deep Autoencoder reconstruction loss bar |
| **DBMS** | Relational Event History & Filtered History | PostgreSQL 3NF tables, foreign key integrity, atomic persistence |
| **Computational Techniques**| 18 Engineered Features & Ensemble Score | Temporal sine/cosine encoding, log transforms, weighted score aggregation |
| **Information Security** | RBAC, Event History, Rate Limiting Banner | JWT bearer authentication, PBKDF2/bcrypt hashing, tamper protection |
| **IoT & Embedded Systems** | ESP32 POS Fleet Monitor & Telemetry | Microcontroller C++ firmware, hardware tamper lockout, SHA-256 header auth |
| **Object-Oriented Programming**| Clean Frontend Component Hierarchy | Decoupled UI components, API clients, Service/Repository backend |

---

## 20. Proposed Frontend Directory Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── index.css
│   ├── assets/
│   │   └── argus_logo.svg
│   ├── api/
│   │   ├── client.js           (Axios/fetch client with JWT interceptor)
│   │   ├── auth.js             (login, register, me)
│   │   ├── transactions.js     (assess, getById, list)
│   │   ├── analytics.js        (dashboard KPIs, trend data)
│   │   ├── alerts.js           (list, update disposition)
│   │   ├── devices.js          (list, reset tamper)
│   │   └── admin.js            (audit-logs, users)
│   ├── context/
│   │   └── AuthContext.jsx     (user, role, token, login, logout)
│   ├── components/
│   │   ├── common/
│   │   │   ├── Navbar.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── MetricCard.jsx
│   │   │   ├── DecisionBadge.jsx
│   │   │   ├── RiskGauge.jsx
│   │   │   ├── ModelSignalBars.jsx
│   │   │   ├── Modal.jsx
│   │   │   └── Toast.jsx
│   │   └── layout/
│   │       └── AppLayout.jsx
│   └── pages/
│       ├── LoginPage.jsx
│       ├── SimulatorPage.jsx
│       ├── AssessmentResultPage.jsx
│       ├── DashboardPage.jsx
│       ├── TransactionsPage.jsx
│       ├── TransactionDetailPage.jsx
│       ├── AlertsPage.jsx
│       ├── DevicesPage.jsx
│       ├── AuditLogsPage.jsx
│       └── UsersPage.jsx
```

---

## 21. M9 Implementation Phases

```
[M9.1 Backend Endpoints] ──► [M9.2 Frontend Setup] ──► [M9.3 Auth UX] ──► [M9.4 Simulator] ──► [M9.5 Risk Result]
                                                                                                        │
[M9.10 Final Polish] ◄── [M9.9 IoT & Admin] ◄── [M9.8 History & Alerts] ◄── [M9.7 Dashboard] ◄─────────┘
```

1. **Phase M9.1: Backend Integration Endpoints**:
   - Implement missing endpoints: `GET /api/v1/transactions`, enriched `GET /api/v1/transactions/{id}`, `GET /api/v1/analytics/dashboard`, `GET /api/v1/alerts`, `PATCH /api/v1/alerts/{id}`, `GET /api/v1/devices`, `POST /api/v1/devices/{id}/reset-tamper`.
   - Add unit/integration tests in `tests/test_api_m9.py`.
2. **Phase M9.2: Frontend Foundation & Design Tokens**:
   - Initialize Vite + React on port `3000`.
   - Configure design tokens in `index.css` (Deep Obsidian `#0B0F19`, Slate `#111827`, Tri-State palette).
3. **Phase M9.3: Authentication & Role-Based Navigation**:
   - Implement `AuthContext`, login/register views, and client-side role guards.
4. **Phase M9.4: A.R.G.U.S. Transaction Simulator**:
   - Build simulation form with PaySim validation and the 4 demonstration scenario presets (pre-fills only).
5. **Phase M9.5: Explainable Risk Result View**:
   - Implement continuous 0–100 SVG Risk Gauge, 4-model decomposed signal bars with accurate labels, and forensic reason tags.
6. **Phase M9.6: Analyst Fraud Monitoring Dashboard**:
   - Build live KPI metric cards, volume trend visualization, and recent high-risk transaction table from PostgreSQL data.
7. **Phase M9.7: Transaction History & Forensic Detail View**:
   - Implement server-side paginated explorer with scoped RBAC filters and engineered feature inspector.
8. **Phase M9.8: Investigation Alerts Queue**:
   - Build alert triage board, analyst assignment, and disposition modal with notes.
9. **Phase M9.9: IoT Terminal Fleet & Security Audit Explorer**:
   - Implement ESP32 device monitor (real telemetry, tamper status) and Security Audit Explorer.
10. **Phase M9.10: End-to-End System Testing & Viva Run-Through**:
    - Validate full user story (Login $\rightarrow$ Simulation $\rightarrow$ Risk Verdict $\rightarrow$ Dashboard $\rightarrow$ Alert Triage $\rightarrow$ Event History).
    - Ensure zero test regressions across all 73 existing backend tests.

---

## 22. Testing Strategy

1. **Backend Integration Tests (`tests/test_api_m9.py`)**:
   - Test transaction history pagination and scoped RBAC (verify `USER` cannot see other users' transactions).
   - Test enriched transaction detail endpoint and verify anti-leakage guards.
   - Test analytics dashboard aggregate calculation accuracy.
   - Test alert retrieval and disposition status updates.
   - Test device fleet query and admin tamper reset action.
2. **Backend Regression Testing**:
   - Run complete suite (`.venv\Scripts\pytest`) to verify all 73 existing tests continue to pass with 0 regressions.
3. **Frontend Build Validation**:
   - Run `npm run build` in `frontend/` to confirm clean compilation with zero JSX/syntax errors.
4. **End-to-End Integration Verification**:
   - Execute the 4 core scenario presets against live PostgreSQL and verify that all UI views reflect real database state.

---

## 23. Definition of Done (DoD)

Milestone 9 will be considered complete when:
- [ ] User can log in via JWT and session persists across page reloads.
- [ ] User can submit a real simulated transaction through the simulator.
- [ ] Backend performs actual ML/DL inference across all 4 models and Risk Engine.
- [ ] Actual Risk Engine result (0–100 score and `APPROVE`/`REVIEW`/`BLOCK`) renders accurately.
- [ ] Transaction persists in PostgreSQL with complete 3NF entities.
- [ ] Transaction appears in Transaction History under appropriate RBAC scope.
- [ ] Analyst can monitor live transactions and metrics on the Dashboard.
- [ ] Alerts originate from real backend data and can be resolved with notes.
- [ ] IoT devices reflect real database records and heartbeat telemetry.
- [ ] Admin/auditor security views respect RBAC and consume real audit logs.
- [ ] No fake final dashboard data or hardcoded counts remain.
- [ ] No secrets, passwords, or API keys are exposed to the client.
- [ ] Frontend production build (`npm run build`) succeeds.
- [ ] All 73 existing backend tests pass without regression.
- [ ] All newly added M9 backend tests pass.
- [ ] Complete end-to-end demo flow succeeds from login to audit trail inspection.
