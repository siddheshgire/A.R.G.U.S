# A.R.G.U.S. — Development Environment Setup Guide

**Project:** A.R.G.U.S. (Automated Risk Assessment & Anomaly Detection System)  
**Semester:** B.Tech AIML (Class: B.Tech AIML – C, Year: 2026–27 Odd Semester)  
**Document:** `docs/ENVIRONMENT_SETUP.md`  

---

## 1. Selected Python Version
- **Runtime:** Python `3.13.7` (64-bit Windows)
- **Virtual Environment Directory:** `.venv/`

## 2. Why Python 3.13 Was Selected
Before creating the virtual environment, a dry-run check and package resolution test were executed against PyPI.
- **Verified Official Wheels:** PyTorch (`2.14.0+cpu`), Scikit-learn (`1.9.1`), XGBoost (`3.4.1`), Pandas (`3.0.5`), NumPy (`2.5.3`), and `psycopg2-binary` (`2.9.13`) all provide pre-built Windows x86_64 binary wheels for Python 3.13.
- **Zero Build Failures:** No local C/C++ compilation was required, guaranteeing a smooth and reproducible installation on standard student machines without needing Visual Studio C++ build tools.
- **Single Runtime Discipline:** Host machine runs Python 3.13.7. Using 3.13 natively in `.venv` avoids managing multiple parallel global Python installations while maintaining complete stability.

## 3. Virtual Environment Setup
The virtual environment was initialized at the project root:
```powershell
# Created via standard library venv module:
python -m venv .venv
```

## 4. Installed Dependency Categories
The environment has been configured with foundational libraries categorized as follows:
- **Web & API Framework:** `fastapi` (0.141.1), `uvicorn[standard]` (0.52.4), `pydantic` (2.13.5), `pydantic-settings` (2.15.0), `python-dotenv` (1.2.3), `requests` (2.34.2).
- **Database & Persistence:** `sqlalchemy` (2.0.52), `psycopg2-binary` (2.9.13).
- **Scientific Computing:** `numpy` (2.5.3), `pandas` (3.0.5).
- **Machine Learning & Deep Learning:** `scikit-learn` (1.9.1), `xgboost` (3.4.1), `torch` (2.14.0+cpu).
- **Visualization:** `matplotlib` (3.11.1), `seaborn` (0.13.2).
- **Testing:** `pytest` (9.1.1).

All constraints are specified in [`requirements.txt`](file:///c:/PRO/PBL%20SY/requirements.txt).

## 5. Git Setup
- Git repository initialized via `git init`.
- Comprehensive [`.gitignore`](file:///c:/PRO/PBL%20SY/.gitignore) created, strictly excluding:
  - Virtual environments (`.venv/`)
  - Python bytecode and caches (`__pycache__/`, `*.pyc`, `.pytest_cache/`)
  - Secrets and local configurations (`.env`, `credentials/`, `secrets/`)
  - Raw and processed datasets (`data/raw/*`, `data/processed/*`, `*.csv`)
  - Model checkpoints and weight binaries (`models/*`, `*.pt`, `*.pkl`)
  - Temporary files and database files (`*.db`, `*.sqlite3`)

## 6. Project Directory Structure
```
c:\PRO\PBL SY\
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore specification
├── README.md                 # Project introduction and status
├── requirements.txt          # Pinned dependency requirements
├── PROJECT_INITIALIZATION.md # Project charter & initialization audit
├── backend/                  # FastAPI service, routers, schemas, dependencies
├── database/                 # SQLAlchemy models, migrations, DB connection
├── ml_engine/                # Feature pipelines, ML classifiers, Deep Autoencoder
├── iot_firmware/             # ESP32 C++/MicroPython source and terminal logic
├── data/
│   ├── raw/                  # Original raw datasets (gitignored)
│   ├── processed/            # Feature-engineered splits (gitignored)
│   └── external/             # Supplementary metadata / mappings
├── models/                   # Serialized model weights & scalers (gitignored)
├── scripts/                  # Data preparation, utility, and evaluation scripts
├── tests/                    # Unit, integration, and security test suites
└── docs/                     # Architectural and milestone documentation
```

## 7. How to Activate the Environment
Open PowerShell in the project directory and execute:
```powershell
# In PowerShell:
.\.venv\Scripts\Activate.ps1

# To verify active environment path:
Get-Command python | Select-Object -ExpandProperty Source
```

## 8. How to Verify the Environment
Execute the following verification one-liner using the virtual environment Python:
```powershell
.\.venv\Scripts\python.exe -c "import numpy, pandas, sklearn, xgboost, torch, fastapi, pydantic, sqlalchemy; print('ENVIRONMENT VERIFIED SUCCESSFULLY')"
```

## 9. What Has NOT Been Implemented Yet
In strict accordance with milestone discipline:
- **No dataset downloaded:** PaySim has not been downloaded or processed.
- **No EDA executed:** Exploratory data analysis scripts have not been generated.
- **No models trained:** Baseline Logistic Regression, XGBoost, Isolation Forest, and Deep Autoencoder have not been constructed or trained.
- **No database created:** PostgreSQL schema and database connection instances have not been deployed.
- **No API endpoints created:** FastAPI routes, middleware, and schemas have not been implemented.
- **No firmware written:** ESP32 hardware firmware has not been created.
