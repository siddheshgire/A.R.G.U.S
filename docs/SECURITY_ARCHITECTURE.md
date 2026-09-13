# A.R.G.U.S. — Security Architecture & OOP Application Layer (Milestone 7)

## 1. Executive Summary & Scope
This document specifies the security architecture, cryptographic implementations, access control models, and Object-Oriented Programming (OOP) application service design for **Project A.R.G.U.S.** (*Automated Risk Assessment & Anomaly Detection System*), a B.Tech AIML semester project (2026–27).

Milestone 7 integrates defensive engineering practices and object-oriented service encapsulation directly into the existing FastAPI application gateway and PostgreSQL database schema. The security layer acts as an enclosing perimeter around the machine learning inference and Risk Engine components without altering their mathematical formulations or operational thresholds.

---

## 2. Authentication & Cryptographic Engineering

### 2.1 Password Hashing Architecture
- **Algorithm**: `bcrypt` (Blowfish-based adaptive key derivation function).
- **Cost Factor / Rounds**: `12` rounds ($2^{12} = 4,096$ iterations), providing robust defense against GPU/ASIC offline dictionary attacks while maintaining acceptable verification latency (<150ms).
- **Salting Policy**: Cryptographically secure pseudo-random salt (`os.urandom` via `bcrypt.gensalt`) generated per-password. Plaintext passwords are never stored, logged, or cached in memory.
- **Verification**: Constant-time byte string comparison (`bcrypt.checkpw`) to neutralize timing side-channel attacks.

### 2.2 Stateless JWT Bearer Token Workflow
- **Token Format**: RFC 7519 JSON Web Token (JWT).
- **Signature Algorithm**: `HS256` (HMAC with SHA-256).
- **Secret Key Management**: 256-bit cryptographic key read exclusively from the environment (`JWT_SECRET_KEY`).
- **Token Lifetime**: 60 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`), balancing user convenience and replay exposure windows.
- **Embedded Claims**:
  - `sub`: Authenticated username.
  - `user_id`: UUID primary key.
  - `role`: Operational role (`USER`, `ANALYST`, `ADMIN`, `AUDITOR`).
  - `iat`: Timestamp of token issuance.
  - `exp`: Timestamp of token expiration (enforced automatically by PyJWT).
  - `jti`: Unique token identifier UUID.

```
Client                             FastAPI Gateway                          Database
  │                                       │                                     │
  │── POST /api/v1/auth/login ───────────>│                                     │
  │   { username, password }              │── Query user by username ──────────>│
  │                                       │<─ Return hashed password & role ────│
  │                                       │                                     │
  │                                       │── Constant-time bcrypt.checkpw()    │
  │                                       │── Log AUTH_LOGIN_SUCCESS ──────────>│
  │                                       │── Generate signed JWT (HS256)       │
  │<─ HTTP 200 { access_token, bearer } ──│                                     │
  │                                       │                                     │
  │── GET /api/v1/transactions/{tx_id} ──>│                                     │
  │   Header: Authorization: Bearer <jwt> │── Cryptographic signature check     │
  │                                       │── Expiry validation (exp > now)     │
  │                                       │── Resolve current_user & role       │
  │                                       │── Enforce Object-Level Auth (IDOR) ─│
  │<─ HTTP 200 { transaction payload } ───│                                     │
```

---

## 3. Role-Based Access Control (RBAC)

A.R.G.U.S. enforces a four-tier operational role hierarchy:

| Role | Target Persona | Scope of Permissions |
| :--- | :--- | :--- |
| **`USER`** | Customer / Client / Merchant | Submits transactions for risk scoring; accesses **only their own** transaction history. |
| **`ANALYST`** | Fraud Investigator / Risk Analyst | Inspects any transaction, reviews flagged anomalies, inspects high-risk alerts. |
| **`AUDITOR`** | Compliance / Regulatory Inspector | Inspects complete immutable audit trails, system configurations, and alert resolutions. |
| **`ADMIN`** | System Security Administrator | Superset access: user management, role assignments, system health, and full audit logs. |

### Endpoint Permission Matrix

| Endpoint | Method | Public | USER | ANALYST | AUDITOR | ADMIN |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `/health`, `/ready` | `GET` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/api/v1/auth/register` | `POST` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/api/v1/auth/login` | `POST` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/api/v1/auth/me` | `GET` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `/api/v1/transactions/assess` | `POST` | ✅ (Sim) | ✅ | ✅ | ✅ | ✅ |
| `/api/v1/transactions/{tx_id}` | `GET` | ❌ | Owner Only | ✅ | ✅ | ✅ |
| `/api/v1/admin/audit-logs` | `GET` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `/api/v1/admin/users` | `GET` | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 4. Object-Level Authorization (IDOR Defense)

Insecure Direct Object References (IDOR) represent a critical vulnerability where an authenticated user changes an identifier (such as a UUID in the URL path) to access records belonging to other users.

### Enforcement Logic (`TransactionService.get_authorized_transaction`)
1. **Existence Check**: Queries the repository for `tx_id`. If non-existent, immediately returns `HTTP 404 Not Found` (preventing timing information leakage).
2. **Ownership Resolution**:
   - If the transaction was submitted by an authenticated user (`tx.user_id is not None`):
     - Unauthenticated requests receive `HTTP 401 Unauthorized`.
     - Users with roles `ADMIN`, `ANALYST`, or `AUDITOR` are granted universal inspection privileges.
     - Users with role `USER` are granted access **if and only if** `current_user.user_id == tx.user_id` or `current_user.username == tx.name_orig`.
     - Unauthorized users attempting to view another customer's record receive `HTTP 403 Forbidden`.
   - If the transaction is an unassigned simulation record (e.g. from automated regression tests), access is granted for backward-compatible simulation testing.

---

## 5. Input Validation & Anti-Leakage Safeguards

1. **Pydantic v2 Strong Typing**:
   - `extra="forbid"`: Disallows injection of undeclared JSON properties.
   - `amount >= 0.0`, `step >= 1`, balances non-negative.
   - Email regex format validation and username character filtering (`^[a-zA-Z0-9_\-]+$`).
2. **Strict Anti-Leakage Guard**:
   - Target labels (`isFraud`, `isFlaggedFraud`) are explicitly rejected at the request validator boundary with `HTTP 422 Unprocessable Content`. Live operational gateways evaluate unknown transactions; supplying ground truth is forbidden.
3. **Strict Modeling Subspace Restriction**:
   - PaySim fraud occurs exclusively in `TRANSFER` and `CASH_OUT`.
   - `PAYMENT`, `CASH_IN`, and `DEBIT` are rejected with a controlled `HTTP 422` error stating they are not currently supported for ML assessment. No invented fast-path rules or automatic approvals are applied.

---

## 6. Defensive HTTP Headers & Rate Limiting

### 6.1 Defensive HTTP Headers (`SecurityHeadersMiddleware`)
Every HTTP response is enriched with defensive headers:
- `X-Content-Type-Options: nosniff`: Instructs browsers not to override the declared MIME type.
- `X-Frame-Options: DENY`: Mitigates clickjacking attacks by forbidding iframe embedding.
- `Referrer-Policy: strict-origin-when-cross-origin`: Restricts referrer URL leakage on cross-origin requests.
- `Content-Security-Policy`: Configured defensively while permitting FastAPI's Swagger UI CDN scripts during development.

### 6.2 In-Memory Sliding-Window Rate Limiting (`RateLimitMiddleware`)
- **Mechanism**: In-memory timestamp sliding-window counter per client IP.
- **Threshold**: 100 requests per 60-second window (`RATE_LIMIT_REQUESTS=100`, `RATE_LIMIT_WINDOW_SECONDS=60`).
- **Response on Breach**: `HTTP 429 Too Many Requests` with standard `Retry-After: 60` header.
- **Architectural Trade-off**: Operates completely in-process without requiring external broker infrastructure (Redis/RabbitMQ), matching the prototype's academic constraints.

---

## 7. Structured Security Audit Logging

All significant security, operational, and administrative actions are persisted to the append-only `audit_logs` table:

```sql
CREATE TABLE audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    actor_id VARCHAR(64),
    actor_type VARCHAR(32) NOT NULL,    -- USER, SYSTEM, API, DEVICE
    event_type VARCHAR(64) NOT NULL,    -- AUTH_LOGIN_SUCCESS, AUTH_LOGIN_FAILURE, TRANSACTION_ASSESSED
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(64),
    details JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Logged Event Catalog:
- `AUTH_USER_REGISTERED`: New account creation with email, role, and client IP.
- `AUTH_LOGIN_SUCCESS`: Successful credentials verification with JWT issuance.
- `AUTH_LOGIN_FAILURE`: Invalid password or unknown account attempt (committed immediately before 401 raise).
- `SECURITY_ACCESS_DENIED`: Unauthorized access attempt to protected admin/analyst endpoints.
- `TRANSACTION_ASSESSED`: Automated fraud risk decision and multi-model score persistence.

*Safety Rule*: Plaintext passwords, raw JWT tokens, and cryptographic keys are strictly excluded from audit payloads.

---

## 8. Object-Oriented Programming (OOP) Architecture

The application demonstrates authentic OOP principles through a service-repository pattern:

```
FastAPI Router (Presentation / Transport)
       │
       ▼ Dependency Injection
Application Services (Business Logic)
├── AuthService        ──> Encapsulates registration & authentication workflows
├── UserService        ──> Encapsulates user/role entity lookup & resolution
├── AuditService       ──> Encapsulates security event recording & retrieval
└── TransactionService ──> Orchestrates feature engineering, ML inference, and risk scoring
       │
       ▼ Domain Objects & Persistence
Repository & Domain Entities
├── User, Role, Transaction, AuditLog (SQLAlchemy Models)
├── RiskSignals, RiskAssessment (Immutable Domain Dataclasses)
└── save_assessed_transaction() (Atomic ACID Unit of Work)
```

### OOP Principles Applied:
1. **Encapsulation**: Password verification algorithms, token expiration calculations, and audit log commits are internal to their respective services (`AuthService`, `AuditService`).
2. **Abstraction**: Route handlers interact with clean method signatures (`auth_service.authenticate(username, password)`) without dealing with raw SQL queries or JWT signing details.
3. **Composition**: `AuthService` is composed of `UserService` and `AuditService`, delegating domain lookup and compliance recording cleanly.
4. **Dependency Injection**: FastAPI's `Depends()` injects database sessions and services dynamically, facilitating modular unit testing with SQLite in-memory overrides.

---

## 9. Subject Mapping

### 9.1 Information Security
- **Authentication & Cryptography**: Salted bcrypt password hashing, stateless HS256 JWT tokens.
- **Access Control**: Role-Based Access Control (RBAC) and Object-Level Authorization (IDOR mitigation).
- **Network & Transport Defense**: HTTP security headers, CORS origin restriction, rate limiting.
- **Auditability & Accountability**: Append-only audit logging capturing security events for compliance.

### 9.2 Object-Oriented Programming (OOP)
- **Separation of Concerns**: Clean demarcation between routing, business services, and database persistence.
- **Service-Repository Pattern**: Business logic decoupled from underlying relational storage.
- **Domain Modeling**: Rich domain entities (`RiskAssessment`, `RiskSignals`, `User`, `Transaction`).

---

## 10. Verification & Quality Assurance

### 10.1 Automated Test Suites
- **M7 Security Tests (`tests/test_security.py`)**: 16 dedicated test cases covering password salting, JWT token expiry, duplicate user handling, login audit logging, RBAC enforcement, IDOR object protection, and rate limiting.
- **Complete Test Suite (`pytest -v`)**: **59 / 59 Tests Passing** across all project milestones (M0–M7):
  - 15 API Gateway Tests (`tests/test_api.py`)
  - 8 Relational Database Tests (`tests/test_database.py`)
  - 5 Feature Pipeline Tests (`tests/test_feature_pipeline.py`)
  - 7 ML/DL Model Tests (`tests/test_model_pipeline.py`)
  - 8 Risk Engine Tests (`tests/test_risk_engine.py`)
  - 16 Security Tests (`tests/test_security.py`)

### 10.2 Live Server Manual Verification
Executed `scripts/verify_api_live.py` against a running Uvicorn instance on `http://127.0.0.1:8008`:
- Server startup and single-load model initialization (~5.9s).
- Liveness probe and security headers validation (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`).
- User registration (`POST /api/v1/auth/register`) $\rightarrow$ HTTP 201.
- User login & JWT issuance (`POST /api/v1/auth/login`) $\rightarrow$ HTTP 200.
- Protected user profile query (`GET /api/v1/auth/me`) with Bearer token $\rightarrow$ HTTP 200.
- Authenticated transaction assessment (`POST /api/v1/transactions/assess`) $\rightarrow$ Risk Score 86.41, `BLOCK`.
- Authorized transaction retrieval (`GET /api/v1/transactions/{tx_id}`) $\rightarrow$ HTTP 200.
- Non-modeled type rejection (`PAYMENT`) $\rightarrow$ HTTP 422.

---

## 11. Security Limitations & Academic Boundaries

| Security Feature | Current Status in M7 Prototype | Production Deployment Requirement |
| :--- | :--- | :--- |
| **Password Storage** | `bcrypt` (12 rounds) with unique salt. | Production-grade. |
| **Token Mechanism** | Stateless HS256 JWT with 60-min expiration. | Production-grade; token revocation list / refresh tokens deferred. |
| **RBAC** | Tiered RBAC (`USER`, `ANALYST`, `ADMIN`, `AUDITOR`). | Production-grade for prototype. |
| **Object Authorization**| Owner check + privileged role override (IDOR defense). | Production-grade for prototype. |
| **Rate Limiting** | In-memory sliding-window per IP. | In distributed production, backed by Redis cluster. |
| **TLS / SSL** | Terminated via reverse proxy (Nginx / Cloudflare). | Prototype runs HTTP locally; HTTPS required in production. |
| **IoT POS Authentication**| Planned for Milestone 8 (HMAC-SHA256 ESP32 signatures). | Milestone 8 integration. |
