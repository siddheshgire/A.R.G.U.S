# Milestone 0 Report: Environment & Repository Setup

**Project:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Milestone:** 0 (Environment & Repository Setup)  
**Date:** 2026-09-11  
**Status:** Successfully Completed & Verified  

---

## 1. Environment
- **Operating System:** Windows 10/11 (64-bit)
- **Shell:** PowerShell
- **Host Python:** `Python 3.13.7` (Path: `C:\Users\siddharth\AppData\Local\Programs\Python\Python313\python.exe`)
- **Host Git:** `git version 2.55.0.windows.2`
- **Virtual Environment:** Dedicated `.venv` created at `c:\PRO\PBL SY\.venv` using standard library `venv`.

---

## 2. Python Version Decision
- **Selected Version:** Python `3.13.7`
- **Rationale:** 
  A pre-installation dry-run verified that official, pre-compiled Windows x86_64 binary wheels exist for all required core libraries: PyTorch (`2.14.0+cpu`), XGBoost (`3.4.1`), Scikit-learn (`1.9.1`), NumPy (`2.5.3`), Pandas (`3.0.5`), and psycopg2-binary (`2.9.13`). Installation completed with zero C++ compilation steps, avoiding Microsoft C++ Build Tools dependencies. Using the host's native 3.13 runtime simplifies developer setup without incurring compatibility penalties.

---

## 3. Dependencies
All required libraries were successfully installed from [`requirements.txt`](file:///c:/PRO/PBL%20SY/requirements.txt) into `.venv`:
- **API & Web:** `fastapi` (0.141.1), `uvicorn[standard]` (0.52.4), `pydantic` (2.13.5), `pydantic-settings` (2.15.0), `python-dotenv` (1.2.3), `requests` (2.34.2)
- **Database:** `sqlalchemy` (2.0.52), `psycopg2-binary` (2.9.13)
- **Data & Scientific Computing:** `numpy` (2.5.3), `pandas` (3.0.5)
- **Machine Learning & Deep Learning:** `scikit-learn` (1.9.1), `xgboost` (3.4.1), `torch` (2.14.0+cpu)
- **Visualization:** `matplotlib` (3.11.1), `seaborn` (0.13.2)
- **Testing:** `pytest` (9.1.1)

---

## 4. Git Repository
- Repository initialized via `git init`.
- Comprehensive [`.gitignore`](file:///c:/PRO/PBL%20SY/.gitignore) created, protecting:
  - Virtual environments (`.venv/`)
  - Python bytecode (`__pycache__/`, `*.pyc`)
  - Secrets and credentials (`.env`, `secrets/`)
  - Data directories and files (`data/raw/*`, `data/processed/*`, `*.csv`)
  - Serialized model weights (`models/*`, `*.pt`, `*.pkl`)
  - Test and IDE artifacts (`.pytest_cache/`, `.vscode/`, `.idea/`)

---

## 5. Project Structure
The initial modular directory structure has been created:
```
c:\PRO\PBL SY\
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── PROJECT_INITIALIZATION.md
├── backend/                  (.gitkeep)
├── database/                 (.gitkeep)
├── ml_engine/                (.gitkeep)
├── iot_firmware/             (.gitkeep)
├── tests/                    (.gitkeep)
├── models/                   (.gitkeep)
├── scripts/                  (.gitkeep)
├── data/
│   ├── raw/                  (.gitkeep)
│   ├── processed/            (.gitkeep)
│   └── external/             (.gitkeep)
└── docs/
    ├── DATASET_RESEARCH_AND_SELECTION.md
    ├── ENVIRONMENT_SETUP.md
    └── MILESTONE_0_REPORT.md
```

---

## 6. Verification Results
A lightweight verification script was executed directly using `.\.venv\Scripts\python.exe`.

| Target Module | Verified Version | Verification Status |
| :--- | :--- | :--- |
| **Python** | `3.13.7` | ✅ Verified |
| **pip** | `25.2` | ✅ Verified |
| **NumPy** | `2.5.3` | ✅ Verified |
| **Pandas** | `3.0.5` | ✅ Verified |
| **Scikit-learn** | `1.9.1` | ✅ Verified |
| **XGBoost** | `3.4.1` | ✅ Verified |
| **PyTorch** | `2.14.0+cpu` | ✅ Verified |
| **FastAPI** | `0.141.1` | ✅ Verified |
| **Pydantic** | `2.13.5` | ✅ Verified |
| **SQLAlchemy** | `2.0.52` | ✅ Verified |

**Execution Log Output:** `ALL_IMPORTS_SUCCESSFUL`

---

## 7. Files Created
1. [`.gitignore`](file:///c:/PRO/PBL%20SY/.gitignore) — Comprehensive ignore rules for Python, data, secrets, models, and cache.
2. [`.env.example`](file:///c:/PRO/PBL%20SY/.env.example) — Application, database, JWT, IoT secret, and threshold templates.
3. [`requirements.txt`](file:///c:/PRO/PBL%20SY/requirements.txt) — Pinned core project dependencies.
4. [`README.md`](file:///c:/PRO/PBL%20SY/README.md) — Project introduction, architecture, academic subject integration, and quickstart.
5. [`docs/ENVIRONMENT_SETUP.md`](file:///c:/PRO/PBL%20SY/docs/ENVIRONMENT_SETUP.md) — Environment setup guide, version justification, and verification instructions.
6. [`docs/MILESTONE_0_REPORT.md`](file:///c:/PRO/PBL%20SY/docs/MILESTONE_0_REPORT.md) — Factual completion report for Milestone 0.
7. Directory `.gitkeep` markers for empty project subdirectories.

---

## 8. Known Issues
- **None.** All packages resolved cleanly with pre-built binary wheels on Python 3.13 Windows x86_64.
- In strict adherence to milestone boundaries, no models have been trained, no data downloaded, and no database or API services have been deployed.

---

## 9. Next Recommended Milestone
**Milestone 1: Dataset Acquisition & Exploratory Data Analysis (EDA)**
- Download and place the approved PaySim dataset in `data/raw/` (gitignored).
- Verify file size and SHA256 integrity checksum.
- Perform exploratory data analysis verifying the 11 columns, class distributions, balance behaviors, and zero-balance characteristics.
- Document findings in `docs/DATASET_EDA_REPORT.md`.
