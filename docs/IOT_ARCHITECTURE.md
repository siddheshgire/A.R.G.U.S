# A.R.G.U.S. — IoT Edge Integration Architecture (Milestone 8)
## Secure IoT Transaction-Source & Telemetry Layer for Academic Prototype

---

## 1. System Overview & Ingestion Boundary

In Project **A.R.G.U.S.** (Automated Risk Assessment & Anomaly Detection System), the IoT layer represents the physical point-of-sale (POS) and smart transaction-source terminals deployed at the edge of the banking/merchant network.

```
+-------------------------------------------------------------+
|               ESP32 Smart POS Edge Terminal                 |
|  - Role: Transaction Ingress & Hardware Telemetry           |
|  - Microcontroller: Espressif ESP32-WROOM-32 / ESP32-S3     |
|  - Actuators: Status LEDs / OLED Display                    |
|  - Sensors: Chassis Tamper Switch, SoC Temperature Sensor   |
|  - Firmware: Arduino C++ (FreeRTOS)                         |
|  - STRICT BOUNDARY: NO Machine Learning or Deep Learning    |
+-------------------------------------------------------------+
                              |
                              | HTTP / TLS 1.3 (HTTPS)
                              | Security Headers:
                              |   X-Device-Code: ESP32-TERM-001
                              |   X-Device-API-Key: <hashed_on_server>
                              v
+-------------------------------------------------------------+
|              A.R.G.U.S. FastAPI Gateway API                 |
|  - Cryptographic Device Authentication (SHA-256 / Constant) |
|  - Merchant Association Verification                        |
|  - Concurrency-Safe Database Replay Defense (uq_device_tx)  |
|  - Anti-Leakage Guards (Blocks isFraud / isFlaggedFraud)    |
|  - Subspace Policy Enforcement (TRANSFER / CASH_OUT only)   |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                Core AI / ML Inference Engine                |
|  - 18 Real-Time Engineered Features                         |
|  - 4 Model Architectures:                                   |
|      1. Supervised XGBoost (weight = 0.50)                  |
|      2. Deep Autoencoder (weight = 0.20)                    |
|      3. Isolation Forest (weight = 0.15)                    |
|      4. Logistic Regression (weight = 0.15)                 |
|  - Ensemble Multi-Signal Risk Engine (0-100 Score)          |
|  - Tri-State Decision Policy: APPROVE / REVIEW / BLOCK      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 PostgreSQL 3NF Persistence                  |
|  - Transaction Record (Linked to device_id & client_tx_id)  |
|  - 18-Feature Vector                                        |
|  - Decomposed Model Inference Signals                       |
|  - Risk Assessment Record & Tri-State Decision              |
|  - Analyst Alerts (for REVIEW and BLOCK decisions)          |
|  - Immutable Audit Log Trail (audit_logs table)             |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 Terminal Response Contract                  |
|  - Response: JSON (transaction_id, decision, risk_score)    |
|  - Display: Local LCD Message & LED Actuation               |
+-------------------------------------------------------------+
```

### Core Ingestion Principle
The ESP32 is strictly an **ingestion and actuation device**. The edge microcontroller does **NOT** run XGBoost, Logistic Regression, Isolation Forest, or the Deep Autoencoder, nor does it evaluate business rules or thresholds. All machine learning transformations and risk decisions remain centrally orchestrated by the A.R.G.U.S. backend.

---

## 2. Hardware Status & Academic Verification Disclosure

To maintain strict scientific and academic honesty, the operational status of all components is explicitly cataloged:

| Component | Status | Verification Mechanism |
| :--- | :--- | :--- |
| **Relational Schema (`devices`, `transactions`)** | **`IMPLEMENTED`** | PostgreSQL/SQLite schema migrations, unique constraints |
| **API Endpoints (`/transactions`, `/heartbeat`)** | **`IMPLEMENTED`** | FastAPI routing, dependency injection, Pydantic v2 schemas |
| **Cryptographic Device Authentication** | **`IMPLEMENTED`** | SHA-256 hashing, constant-time `secrets.compare_digest` |
| **Concurrency-Safe Replay Protection** | **`IMPLEMENTED`** | UniqueConstraint `uq_device_client_tx`, `HTTP 409 Conflict` |
| **Audit Trail Integration (`audit_logs`)** | **`IMPLEMENTED`** | Immutable persistence of device actions via `AuditService` |
| **Arduino C++ ESP32 Firmware** | **`IMPLEMENTED`** | Compile-oriented Arduino C++ (`iot/esp32/argus_esp32.ino`) |
| **Python Edge Terminal Simulator** | **`IMPLEMENTED`** | Fully automated end-to-end client (`scripts/simulate_esp32.py`) |
| **Automated Test Suite (14 IoT Tests)** | **`IMPLEMENTED`** | `pytest -v tests/test_iot.py` (14/14 passed) |
| **Full Regression Suite (73 Tests)** | **`IMPLEMENTED`** | `pytest -v` across M0–M8 (73/73 passed) |
| **Live Network Simulator Execution** | **`SIMULATED`** | Executed against live running Uvicorn server on port 8008 |
| **Physical ESP32 Bench Verification** | **`SIMULATED`** | Physical microcontroller bench flashing is **NOT** claimed |

> [!NOTE]
> Physical hardware bench testing was **NOT** executed during this development session because no physical ESP32 was connected to the automated testbed. All network, cryptographic, and transaction behaviors were verified using the Python edge simulator (`scripts/simulate_esp32.py`), which implements the exact HTTP and JSON contract of the Arduino firmware.

---

## 3. Edge Device Identity & Cryptographic Authentication

### Authentication Boundary
Device authentication is strictly separated from human operator JWT authentication:
- Human users (investigators, analysts, administrators) authenticate via `/api/v1/auth/login` and receive stateless Bearer JWTs.
- Edge terminals (ESP32 microcontrollers) authenticate via machine identity headers on every request:
  - `X-Device-Code`: Unique hardware identifier string (e.g., `ESP32-TERM-001`).
  - `X-Device-API-Key`: High-entropy device secret token.

### Cryptographic Credential Hashing
Plaintext API keys are **never** stored in the database or logged in application traces:
1. When a device is provisioned via `DeviceService.register_device()`, the raw API key is hashed using SHA-256:
   $$\text{api\_key\_hash} = \text{SHA-256}(\text{raw\_key})$$
2. During ingress, `verify_device_credentials()` computes the SHA-256 hash of the presented key and executes a constant-time comparison against `device.api_key_hash` using `secrets.compare_digest()`.
3. If the device does not exist, an `HTTP 401 Unauthorized` is returned, and a `DEVICE_AUTH_FAILURE` audit event is recorded.
4. If the key does not match, an `HTTP 401 Unauthorized` is returned, and a `DEVICE_AUTH_FAILURE` audit event is recorded.
5. If the device is marked `INACTIVE` or `DECOMMISSIONED`, access is denied with `HTTP 403 Forbidden`.
6. If the device has `tamper_flag = True`, access is denied with `HTTP 403 Forbidden` (`Terminal locked`).

---

## 4. Transport Security & Network Architecture

### Credential Transport vs. Transport Confidentiality
- **Credential Transport**: HTTP headers (`X-Device-Code`, `X-Device-API-Key`) provide application-level identity transmission.
- **Transport Confidentiality & Integrity**: Secure communication depends entirely on TLS/HTTPS. Plain HTTP does **not** protect against eavesdropping or man-in-the-middle credential interception.

```
LOCAL DEVELOPMENT / TESTBED:
ESP32 / Python Simulator -----> Plain HTTP (localhost:8008 / LAN) -----> FastAPI Gateway

PRODUCTION DEPLOYMENT (MANDATORY):
ESP32 (WiFiClientSecure) ------> TLS 1.3 / HTTPS (Port 443) ----------> Reverse Proxy (Nginx / Caddy) -> FastAPI
```

> [!IMPORTANT]
> **Production Requirement**: Device credentials must be transmitted only over **TLS/HTTPS** when communicating across an untrusted or production network. The Arduino C++ firmware is architected with conditional support for `WiFiClientSecure` with root CA certificate validation.

---

## 5. IoT API Contracts & Schemas

### A. Edge Transaction Ingress: `POST /api/v1/iot/transactions`

#### Request Payload (`IoTTransactionRequest`)
```json
{
  "client_tx_id": "ESP32-TERM-001-TX-1001",
  "step": 646,
  "type": "CASH_OUT",
  "amount": 399045.08,
  "name_orig": "C1039904508",
  "name_dest": "M0000000001",
  "oldbalance_org": 10399045.08,
  "newbalance_orig": 10399045.08,
  "oldbalance_dest": 0.0,
  "newbalance_dest": 0.0,
  "device_status": "ONLINE",
  "network_status": "CONNECTED",
  "firmware_version": "v1.2.0-esp32",
  "uptime_seconds": 1240
}
```

#### Ingress Headers
- `X-Device-Code`: `ESP32-TERM-001`
- `X-Device-API-Key`: `<provisioned_key>`
- `Content-Type`: `application/json`

#### Terminal Response Payload (`IoTRiskResponse`)
```json
{
  "transaction_id": "555d236a-8979-466d-9913-ae678db79ed4",
  "client_tx_id": "ESP32-TERM-001-TX-1001",
  "device_code": "ESP32-TERM-001",
  "decision": "BLOCK",
  "risk_score": 76.58,
  "terminal_message": "TRANSACTION BLOCKED - HIGH RISK",
  "evaluated_at": "2026-09-12T18:28:09.123456Z"
}
```

### B. Device Telemetry & Heartbeat: `POST /api/v1/iot/heartbeat`

#### Request Payload (`IoTHeartbeatRequest`)
```json
{
  "device_code": "ESP32-TERM-001",
  "firmware_version": "v1.2.0-esp32",
  "device_status": "ONLINE",
  "network_status": "CONNECTED",
  "temperature": 34.8,
  "tamper_flag": false,
  "uptime_seconds": 3600
}
```

#### Response Payload (`IoTHeartbeatResponse`)
```json
{
  "status": "ok",
  "device_code": "ESP32-TERM-001",
  "acknowledged_at": "2026-09-12T18:28:08.446703Z",
  "server_command": "CONTINUE"
}
```

---

## 6. Concurrency-Safe Duplicate & Replay Protection

To prevent double-spending and network replay attacks originating from unreliable edge wireless connections, A.R.G.U.S. implements a multi-tier duplicate prevention mechanism:

1. **Client Sequence Identifier**: Each terminal generates a monotonic or UUID-based sequence ID (`client_tx_id`), transmitted with the payload.
2. **Application Pre-Check**: `IoTTransactionService` queries `check_duplicate_device_tx(session, device_id, client_tx_id)`. If found, it immediately halts processing with `HTTP 409 Conflict`.
3. **Database-Level Atomic Guarantee**:
   In `database/models/transaction.py`, a composite unique constraint is enforced at the database catalog level:
   ```python
   __table_args__ = (
       UniqueConstraint("device_id", "client_tx_id", name="uq_device_client_tx"),
   )
   ```
4. **Race-Condition Safety**: If two identical transaction payloads are submitted simultaneously in parallel threads, the database constraint raises an `IntegrityError`. The transaction service catches this exception, rolls back the session, and cleanly responds with `HTTP 409 Conflict` without leaking raw SQL details.

---

## 7. Decoupled Tamper vs. Fraud Policy

- **Fraud BLOCK $\neq$ Physical Tamper**: A high-risk transaction resulting in a `BLOCK` decision indicates anomalous financial attributes (e.g. account drain, mule beneficiary). It does **not** indicate that the terminal hardware was physically opened. The terminal is **not** locked out from processing future legitimate transactions.
- **Hardware Tamper Switch**: If the physical chassis intrusion switch on the terminal is tripped (`tamper_flag = true`), the terminal reports this via heartbeat or header. The server updates `device.tamper_flag = True` and sets `status = "TAMPERED"`, permanently locking out the device from financial ingress until an administrator inspects and clears the hardware.

---

## 8. Anti-Leakage & Modeling Subspace Preservation

- **Anti-Leakage Guard**: `IoTTransactionRequest` inherits Pydantic model validation that inspects payload keys and strictly forbids `isFraud`, `isfraud`, `is_fraud`, `isFlaggedFraud`, or `is_flagged_fraud`. Attempts to pass target labels result in immediate `HTTP 422 Unprocessable Entity`.
- **Strict Modeling Subspace**: PaySim ground-truth fraud was exclusively observed and evaluated on `TRANSFER` and `CASH_OUT`. Non-modeled categories (`PAYMENT`, `CASH_IN`, `DEBIT`) submitted from edge terminals are **never** auto-approved and strictly return a controlled `HTTP 422`:
  ```json
  {
    "detail": "Transaction type 'PAYMENT' is not currently supported for ML risk assessment. The A.R.G.U.S. model pipeline is strictly trained and validated on ['CASH_OUT', 'TRANSFER'] transactions."
  }
  ```

---

## 9. Academic Subject Concept Mappings

Milestone 8 directly connects core engineering disciplines within the B.Tech AIML curriculum:

### 1. Internet of Things (IoT)
- **Edge Microcontroller Constraints**: Demonstrates memory-conscious JSON payloads, lightweight heartbeat intervals, and edge actuation (LED/LCD verdicts) on Espressif ESP32 hardware.
- **Sensor Telemetry**: Ingestion of hardware telemetry (internal SoC temperature via `temperatureRead()`, uptime via `millis()`, and hardware chassis switch states).

### 2. Information Security
- **Defense in Depth**: Separation of machine credentials from human session tokens.
- **Cryptographic Hashing**: Server-side storage of high-entropy API key digests using SHA-256.
- **Side-Channel Mitigation**: Constant-time verification using `secrets.compare_digest()` to eliminate timing analysis.
- **Idempotency & Replay Defense**: Cryptographic tracking of `(device_id, client_tx_id)` preventing replay attacks.
- **Immutable Security Auditing**: Detailed event records (`DEVICE_AUTH_SUCCESS`, `DEVICE_AUTH_FAILURE`, `DEVICE_ACCESS_DENIED`, `DEVICE_TRANSACTION_RECEIVED`, `DEVICE_HEARTBEAT`) stored in the relational `audit_logs` table.

### 3. Database Management Systems (DBMS)
- **3NF Relational Modeling**: Reuses the normalized `devices` entity, linked via foreign keys to `merchants` and `transactions`.
- **Catalog Constraints**: Enforces table-level `UniqueConstraint("device_id", "client_tx_id")` ensuring data integrity and concurrency safety.
- **ACID Transaction Management**: Multi-table persistence (Transaction, Features, Model Results, Risk Assessment, Decision, Alert, Audit Log) within a single atomic commit.

### 4. Machine Learning & Deep Learning Integration
- **Hybrid Multi-Model Ensemble**: Seamless delegation from edge ingress into the validated 4-model inference pipeline (XGBoost, Logistic Regression, Isolation Forest, Deep Autoencoder).
- **Subspace Isolation**: Guarantees that unmodeled transaction types are rejected without corrupting model inference distributions.

### 5. Object-Oriented Programming (OOP)
- **Clean Separation of Concerns**:
  - `DeviceService`: Terminal lookup, provisioning, and heartbeat management.
  - `IoTTransactionService`: Edge contract translation, merchant validation, and duplicate prevention.
  - `TransactionService`: ML feature extraction, multi-model execution, and persistence bridge.
  - `AuditService`: Structured audit trail creation.
- **Dependency Injection**: Constructor-based service composition allowing isolated unit testing and mock database sessions.

---

## 10. Known Limitations & Future Work

1. **In-Memory Rate Limiting**: The current rate limiter tracks sliding request windows in process memory per IP. A distributed Redis cluster would be required for multi-replica Kubernetes clusters.
2. **Mutual TLS (mTLS)**: For high-security banking hardware, client-side X.509 certificates (mTLS) can be flashed into the ESP32's secure element (e.g. ATECC608A) rather than API key headers.
3. **Firmware Over-The-Air (OTA)**: Future releases can utilize the `server_command` field in `IoTHeartbeatResponse` to deliver signed OTA firmware binary updates directly to the terminal.
