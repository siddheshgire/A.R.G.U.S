"""
A.R.G.U.S. — Compact Project Backup (< 50 MB)
Generates an optimized project submission/backup archive under 50 MB.
Includes all code, documentation, backend, frontend, database, tests, and core models.
Excludes gigabyte-scale raw CSVs (.venv, node_modules, dist, data/raw, train.csv, isolation_forest.joblib).
"""

import os
import sys
import time
import zipfile
from pathlib import Path

WORKSPACE_ROOT = Path(r"C:\PRO\PBL SY")
DESKTOP_DIR = Path(os.path.expanduser("~")) / "Desktop"
OUTPUT_ZIP = DESKTOP_DIR / "ARGUS_PBL_SY_Backup_under50MB.zip"

EXCLUDE_DIRS = {
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".git",
}

# Specific heavy binary / raw dataset files exceeding the 50 MB threshold
EXCLUDE_FILES = {
    "paysim.csv",
    "PS_20174392719_1491204439457_log.csv",
    "train.csv",
    "isolation_forest.joblib",
    "docs.rar",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
}

NOTICE_CONTENT = """================================================================================
A.R.G.U.S. — Portable Project Archive (Compact < 50 MB Edition)
================================================================================

This archive contains the complete codebase, documentation, tests, frontend,
backend, and core machine learning models for the A.R.G.U.S. project.

To comply with the < 50 MB submission and sharing limit, the following
multi-gigabyte training files and heavy tree ensembles were excluded:
  1. data/raw/paysim.csv (470 MB)
  2. data/processed/train.csv (410 MB)
  3. models/isolation_forest.joblib (455 MB)

INCLUDED IN THIS ARCHIVE:
  [x] Complete FastAPI Backend (backend/)
  [x] Complete React 19 + Vite Frontend SPA (frontend/)
  [x] Complete Database Schema & Models (database/)
  [x] Pretrained XGBoost Model (models/xgboost_fraud_model.json)
  [x] Pretrained Deep Autoencoder PyTorch Model (models/autoencoder.pt)
  [x] Pretrained Logistic Regression Baseline (models/logistic_baseline.joblib)
  [x] Feature Scaler & Model Metadata (models/feature_scaler.joblib, *_meta.json)
  [x] Multi-Model Risk Engine (ml_engine/)
  [x] IoT Edge Terminal Firmware & Simulator (iot/, iot_firmware/)
  [x] Complete 78-Test Verification Suite (tests/)
  [x] Validation & Test Datasets (data/processed/validation.csv, test.csv)
  [x] All Documentation & Technical Reports (docs/)

HOW TO REGENERATE THE EXCLUDED ISOLATION FOREST MODEL:
  Run the existing training script:
    python scripts/train_isolation_forest.py
================================================================================
"""


def create_compact_backup():
    print(f"[*] Starting Compact (<50MB) Backup...")
    print(f"[*] Source:      {WORKSPACE_ROOT}")
    print(f"[*] Destination: {OUTPUT_ZIP}")

    start_time = time.time()
    files_to_zip = []
    total_uncompressed = 0

    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if file in EXCLUDE_FILES:
                continue
            ext = os.path.splitext(file)[1].lower()
            if ext in EXCLUDE_EXTENSIONS:
                continue

            file_path = Path(root) / file
            if file_path.is_symlink():
                continue

            rel_path = file_path.relative_to(WORKSPACE_ROOT)
            sz = file_path.stat().st_size
            files_to_zip.append((file_path, rel_path, sz))
            total_uncompressed += sz

    print(f"[*] Collected {len(files_to_zip)} files ({total_uncompressed / (1024*1024):.2f} MB uncompressed)")
    print(f"[*] Compressing into ZIP archive (DEFLATE max level 9)...")

    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(OUTPUT_ZIP, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
        # Add notice file
        zip_file.writestr("PACKAGE_NOTICE.txt", NOTICE_CONTENT)

        for idx, (fpath, rpath, sz) in enumerate(files_to_zip, 1):
            zip_file.write(fpath, arcname=str(rpath))

    elapsed = time.time() - start_time
    zip_size = OUTPUT_ZIP.stat().st_size
    zip_size_mb = zip_size / (1024 * 1024)

    print("\n" + "=" * 65)
    print("COMPACT BACKUP COMPLETED SUCCESSFULLY!")
    print("=" * 65)
    print(f"File Location:     {OUTPUT_ZIP}")
    print(f"Final ZIP Size:    {zip_size_mb:.2f} MB  (< 50 MB: {'PASS' if zip_size_mb < 50 else 'FAIL'})")
    print(f"Uncompressed Size: {total_uncompressed / (1024*1024):.2f} MB")
    print(f"Total Files:       {len(files_to_zip) + 1}")
    print(f"Time Taken:        {elapsed:.2f} seconds")
    print("=" * 65)


if __name__ == "__main__":
    create_compact_backup()
