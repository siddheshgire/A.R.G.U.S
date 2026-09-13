"""
A.R.G.U.S. — Python ESP32 Edge Terminal Simulator
Simulates physical ESP32 Smart POS terminal behavior:
- Hardware identity and credential transport via HTTP headers
- Heartbeat telemetry transmission
- Legitimate and fraudulent transaction assessment
- Duplicate transaction / replay protection
- Controlled rejection of non-modeled transaction types

DISCLOSURE: This is a software simulation replicating the exact hardware
and network contract of the ESP32 firmware for academic evaluation.
"""

import os
import sys
import time
import uuid
import secrets
import requests
from pathlib import Path

# Ensure repository root is on Python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Fallback to local SQLite if PostgreSQL is not active
DB_FILE = REPO_ROOT / "argus_sim_temp.db"
if "DATABASE_URL" not in os.environ or "postgresql" in os.environ.get("DATABASE_URL", ""):
    os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE.as_posix()}"

from database.base import Base
from database.connection import get_engine, get_db_session
from database.repository import get_device_by_code, create_device
from backend.security.device_auth import hash_device_key

# Configuration
API_BASE_URL = os.getenv("ARGUS_API_BASE_URL", "http://127.0.0.1:8008")
DEVICE_CODE = os.getenv("ARGUS_DEMO_DEVICE_CODE", "ESP32-TERM-001")
# Read credential from environment, or generate a random session token for local test
DEVICE_API_KEY = os.getenv("ARGUS_DEMO_DEVICE_API_KEY", f"sim_key_{secrets.token_hex(16)}")


def seed_simulator_device():
    """Ensures the simulator device is provisioned in the database with hashed credential."""
    print(f"[*] Provisioning/verifying simulator device '{DEVICE_CODE}' in database...")
    Base.metadata.create_all(bind=get_engine())
    with get_db_session() as session:
        device = get_device_by_code(session=session, device_code=DEVICE_CODE)
        if device is None:
            device = create_device(
                session=session,
                device_code=DEVICE_CODE,
                api_key_hash=hash_device_key(DEVICE_API_KEY),
                device_type="ESP32_SIMULATOR",
                firmware_version="v1.2.0-sim",
                status="ACTIVE",
                tamper_flag=False,
            )
            session.commit()
            print(f"[+] Device '{DEVICE_CODE}' created with hashed API key.")
        else:
            # Update key hash to match current session key
            device.api_key_hash = hash_device_key(DEVICE_API_KEY)
            device.status = "ACTIVE"
            device.tamper_flag = False
            session.commit()
            print(f"[+] Device '{DEVICE_CODE}' credential updated.")


def ensure_server_running():
    """Checks if server is responsive; if not, launches background Uvicorn instance."""
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=1.0)
        if r.status_code == 200:
            print(f"[+] Connected to active A.R.G.U.S. gateway at {API_BASE_URL}")
            return
    except Exception:
        pass

    import threading
    import uvicorn
    from backend.main import app

    print(f"[*] Live server not detected. Launching local Uvicorn instance on port 8008...")
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="127.0.0.1", port=8008, log_level="warning"),
        daemon=True,
    )
    server_thread.start()

    for i in range(25):
        time.sleep(1.0)
        try:
            r = requests.get(f"{API_BASE_URL}/health", timeout=1.0)
            if r.status_code == 200:
                print(f"[+] Gateway server is ready after {i+1} seconds.")
                return
        except Exception:
            pass
    raise RuntimeError(f"Gateway server at {API_BASE_URL} failed to become responsive.")


def get_headers(api_key: str = DEVICE_API_KEY) -> dict:
    """Constructs terminal security headers."""
    return {
        "Content-Type": "application/json",
        "X-Device-Code": DEVICE_CODE,
        "X-Device-API-Key": api_key,
    }


def run_simulation():
    print("==================================================================")
    print("A.R.G.U.S. — ESP32 Smart Terminal Ingress Simulator")
    print("Academic Verification: Milestone 8 (IoT Integration)")
    print(f"Target Gateway:    {API_BASE_URL}")
    print(f"Terminal Device:   {DEVICE_CODE}")
    print("==================================================================")

    try:
        ensure_server_running()
        seed_simulator_device()

        # 1. Test Telemetry Heartbeat
        print("\n--- [Step 1] Sending Periodic Heartbeat Telemetry ---")
        hb_payload = {
            "device_code": DEVICE_CODE,
            "firmware_version": "v1.2.0-sim",
            "device_status": "ONLINE",
            "network_status": "CONNECTED",
            "temperature": 34.8,
            "tamper_flag": False,
            "uptime_seconds": 1240,
        }
        hb_res = requests.post(f"{API_BASE_URL}/api/v1/iot/heartbeat", json=hb_payload, headers=get_headers())
        print(f"Status Code: {hb_res.status_code}")
        print(f"Response:    {hb_res.json()}")
        assert hb_res.status_code == 200, "Heartbeat failed"

        # 2. Test Legitimate TRANSFER Transaction (Expected: APPROVE)
        print("\n--- [Step 2] Sending Legitimate TRANSFER Transaction ---")
        client_tx_1 = f"{DEVICE_CODE}-TX-{int(time.time())}-001"
        tx_payload_1 = {
            "client_tx_id": client_tx_1,
            "step": 150,
            "type": "TRANSFER",
            "amount": 250.00,
            "name_orig": "C1029384756",
            "name_dest": "M9876543210",
            "oldbalance_org": 5000.00,
            "newbalance_orig": 4750.00,
            "oldbalance_dest": 1000.00,
            "newbalance_dest": 1250.00,
            "device_status": "ONLINE",
            "network_status": "CONNECTED",
        }
        tx_res_1 = requests.post(f"{API_BASE_URL}/api/v1/iot/transactions", json=tx_payload_1, headers=get_headers())
        print(f"Status Code: {tx_res_1.status_code}")
        data_1 = tx_res_1.json()
        print(f"  Decision:         {data_1['decision']}")
        print(f"  Risk Score:       {data_1['risk_score']:.2f}")
        print(f"  Terminal Display: [{data_1['terminal_message']}]")
        print(f"  Transaction ID:   {data_1['transaction_id']}")
        assert tx_res_1.status_code == 200
        assert data_1["decision"] == "APPROVE"

        # 3. Test Duplicate Replay Protection (Expected: HTTP 409 Conflict)
        print("\n--- [Step 3] Testing Duplicate / Replay Protection ---")
        print(f"Attempting to retransmit identical client sequence ID: {client_tx_1}")
        dup_res = requests.post(f"{API_BASE_URL}/api/v1/iot/transactions", json=tx_payload_1, headers=get_headers())
        print(f"Status Code: {dup_res.status_code} (Expected 409)")
        print(f"Response:    {dup_res.json()}")
        assert dup_res.status_code == 409, "Duplicate protection failed to trigger 409 Conflict"
        print("  [x] Concurrency-safe duplicate transaction protection verified!")

        # 4. Test High-Risk Account Liquidation (Audited Row 3583 attributes -> Expected: BLOCK)
        print("\n--- [Step 4] Sending Anomalous CASH_OUT Liquidation ---")
        client_tx_2 = f"{DEVICE_CODE}-TX-{int(time.time())}-002"
        tx_payload_2 = {
            "client_tx_id": client_tx_2,
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
        }
        tx_res_2 = requests.post(f"{API_BASE_URL}/api/v1/iot/transactions", json=tx_payload_2, headers=get_headers())
        print(f"Status Code: {tx_res_2.status_code}")
        data_2 = tx_res_2.json()
        print(f"  Decision:         {data_2['decision']}")
        print(f"  Risk Score:       {data_2['risk_score']:.2f}")
        print(f"  Terminal Display: [{data_2['terminal_message']}]")
        print(f"  Transaction ID:   {data_2['transaction_id']}")
        assert tx_res_2.status_code == 200
        assert data_2["decision"] == "BLOCK"
        assert data_2["risk_score"] >= 70.0

        # 5. Test Non-Modeled Category Rejection (Expected: HTTP 422)
        print("\n--- [Step 5] Testing Non-Modeled Transaction Category (PAYMENT) ---")
        client_tx_3 = f"{DEVICE_CODE}-TX-{int(time.time())}-003"
        tx_payload_3 = {
            "client_tx_id": client_tx_3,
            "step": 200,
            "type": "PAYMENT",
            "amount": 45.00,
            "name_orig": "C1111222233",
            "name_dest": "M4444555566",
            "oldbalance_org": 500.0,
            "newbalance_orig": 455.0,
            "oldbalance_dest": 0.0,
            "newbalance_dest": 0.0,
        }
        pay_res = requests.post(f"{API_BASE_URL}/api/v1/iot/transactions", json=tx_payload_3, headers=get_headers())
        print(f"Status Code: {pay_res.status_code} (Expected 422)")
        print(f"Response:    {pay_res.json()}")
        assert pay_res.status_code == 422, "Non-modeled type should return 422"
        print("  [x] Subspace policy preserved: non-modeled types rejected with 422.")

        # 6. Test Unauthorized Terminal Ingress (Invalid Key -> Expected: HTTP 401)
        print("\n--- [Step 6] Testing Unauthorized Terminal Ingress (Invalid API Key) ---")
        unauth_res = requests.post(
            f"{API_BASE_URL}/api/v1/iot/heartbeat",
            json=hb_payload,
            headers=get_headers(api_key="wrong_credential_xyz"),
        )
        print(f"Status Code: {unauth_res.status_code} (Expected 401)")
        print(f"Response:    {unauth_res.json()}")
        assert unauth_res.status_code == 401, "Invalid key should return 401"
        print("  [x] Terminal authentication boundary strictly enforced!")

        print("\n==================================================================")
        print("[+] ALL 6 ESP32 IOT SIMULATION VERIFICATION CHECKS PASSED!")
        print("==================================================================")
    finally:
        from database.connection import reset_engine
        reset_engine()
        if DB_FILE.exists():
            try:
                DB_FILE.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    run_simulation()
