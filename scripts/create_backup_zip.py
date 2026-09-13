"""
A.R.G.U.S. — Automated Project Backup Script
Creates a clean, comprehensive ZIP backup on the User Desktop.
Excludes virtual environment (.venv), node_modules, and cache files.
"""

import os
import sys
import time
import zipfile
from pathlib import Path

WORKSPACE_ROOT = Path(r"C:\PRO\PBL SY")
DESKTOP_DIR = Path(os.path.expanduser("~")) / "Desktop"
OUTPUT_ZIP = DESKTOP_DIR / "ARGUS_PBL_SY_Backup.zip"

EXCLUDE_DIRS = {
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".git",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
}


def create_backup():
    print(f"[*] Starting A.R.G.U.S. Project Backup...")
    print(f"[*] Source:      {WORKSPACE_ROOT}")
    print(f"[*] Destination: {OUTPUT_ZIP}")
    print(f"[*] Excluded:    {', '.join(sorted(EXCLUDE_DIRS))}")

    start_time = time.time()
    files_to_zip = []
    total_uncompressed = 0

    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
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
    print(f"[*] Compressing into ZIP archive (using DEFLATE level 1 for speed)...")

    # Ensure output directory exists
    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(OUTPUT_ZIP, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zip_file:
        for idx, (fpath, rpath, sz) in enumerate(files_to_zip, 1):
            if idx % 25 == 0 or idx == len(files_to_zip) or sz > 50 * 1024 * 1024:
                print(f"    [{idx}/{len(files_to_zip)}] Adding: {rpath} ({sz / (1024*1024):.1f} MB)")
            zip_file.write(fpath, arcname=str(rpath))

    elapsed = time.time() - start_time
    zip_size = OUTPUT_ZIP.stat().st_size

    print("\n" + "=" * 65)
    print("BACKUP COMPLETED SUCCESSFULLY!")
    print("=" * 65)
    print(f"File Location:     {OUTPUT_ZIP}")
    print(f"Archive Size:      {zip_size / (1024*1024):.2f} MB")
    print(f"Uncompressed Size: {total_uncompressed / (1024*1024):.2f} MB")
    print(f"Compression Ratio: {(1 - zip_size / total_uncompressed) * 100:.1f}% reduction")
    print(f"Total Files:       {len(files_to_zip)}")
    print(f"Time Taken:        {elapsed:.2f} seconds")
    print("=" * 65)


if __name__ == "__main__":
    create_backup()
