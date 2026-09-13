# A.R.G.U.S. — Automated Risk Assessment & Anomaly Detection System

> **AI-Based Real-Time Fraud Detection and Transaction Risk Monitoring System**  
> Semester Project-Based Learning (PBL) | B.Tech Artificial Intelligence & Machine Learning (Class C, 2026–27)

---

## Overview

**A.R.G.U.S.** is an end-to-end transaction risk monitoring and fraud detection system. It ingests financial transactions alongside physical IoT hardware context, evaluates risk using complementary supervised machine learning and unsupervised deep learning models, and computes a normalized **Risk Score (0–100)** to drive operational actions:

- **APPROVE** (Low Risk)
- **REVIEW** (Medium Risk / Human Analyst Queue)
- **BLOCK** (High Risk / Critical Anomaly)

Rather than operating as an isolated ML notebook, A.R.G.U.S. is engineered as a robust, production-style modular monolith integrating API services, relational DBMS persistence, hardware telemetry, and an analyst operations portal.

---

## Academic Subject Integration

| Subject | Functional Responsibility in A.R.G.U.S. |
| :--- | :--- |
| **Deep Learning** | **Deep Autoencoder** trained on legitimate transactions to capture subtle, novel anomalies via feature reconstruction error ($\text{MSE}$). |
| **DBMS** | **PostgreSQL** relational database managing users, merchants, transactions, computed risk assessments, and immutable audit logs. |
| **Information Security** | Role-Based Access Control (RBAC), JWT authentication, input validation, password hashing, and HMAC cryptographic verification of IoT terminal payloads. |
| **IoT** | **ESP32** hardware point-of-sale terminal generating authentic physical telemetry (tamper switch status, device ID, hardware timestamps, signal strength). |

---

## Architecture

```
[ESP32 IoT POS Terminal] ──┐
                           ▼ (HTTPS / HMAC Payload)
              [FastAPI Gateway Layer]
                           │
             [Validation & Profiling]
                           │
       ┌───────────────────┴───────────────────┐
       ▼                                       ▼
[Supervised ML (XGBoost)]         [Deep Autoencoder (Reconstruction Error)]
       │                                       │
       └───────────────────┬───────────────────┘
                           ▼
               [Risk Aggregation Engine]
              (Normalized Score: 0 - 100)
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
        APPROVE         REVIEW          BLOCK
                           │
                           ▼
          [PostgreSQL Database & Audit Trail]
                           │
             [Analyst Operations Portal]
```

---

## Current Project Status

- **Milestone 0 (Environment & Repository Setup):** ✅ **Completed**
  - Git repository initialized with comprehensive `.gitignore`.
  - Python `3.13.7` virtual environment `.venv` configured and verified.
  - Core dependencies installed: FastAPI, PyTorch, XGBoost, Scikit-learn, SQLAlchemy, Pandas, NumPy, pytest.
- **Milestone 1 (Dataset Acquisition & EDA):** ⏳ **Next Milestone**
  - Primary Dataset Approved: **PaySim Mobile Money Fraud Detection**.

---

## Quickstart

### 1. Prerequisites
- Python 3.13+ (64-bit)
- Git

### 2. Environment Activation & Setup
```powershell
# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Verify installed packages
python -c "import numpy, pandas, sklearn, xgboost, torch, fastapi, pydantic, sqlalchemy; print('All core modules verified successfully!')"
```

### 3. Environment Variables
Copy `.env.example` to `.env` and configure local development secrets:
```powershell
Copy-Item .env.example .env
```

---

## Documentation
- [`PROJECT_INITIALIZATION.md`](file:///c:/PRO/PBL%20SY/PROJECT_INITIALIZATION.md) — Master project charter and initial workspace inspection.
- [`docs/DATASET_RESEARCH_AND_SELECTION.md`](file:///c:/PRO/PBL%20SY/docs/DATASET_RESEARCH_AND_SELECTION.md) — Technical and academic evaluation of candidate datasets (IEEE-CIS vs PaySim).
- [`docs/ENVIRONMENT_SETUP.md`](file:///c:/PRO/PBL%20SY/docs/ENVIRONMENT_SETUP.md) — Detailed environment configuration and dependency audit.
- [`docs/MILESTONE_0_REPORT.md`](file:///c:/PRO/PBL%20SY/docs/MILESTONE_0_REPORT.md) — Milestone 0 completion report.
