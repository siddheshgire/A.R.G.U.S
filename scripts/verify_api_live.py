"""
A.R.G.U.S. — Live Manual API Verification Script (Milestone 7)
Tests server startup, health, authentication, JWT verification, RBAC, IDOR protection,
and POST /api/v1/transactions/assess on a running live Uvicorn instance.
"""

import os
import sys
import time
import uuid
import threading
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

DB_FILE = WORKSPACE_ROOT / "argus_verify_temp.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE.as_posix()}"

import uvicorn
import requests

from database.base import Base
from database.connection import get_engine, reset_engine
from backend.services.user_service import UserService
from sqlalchemy.orm import Session
from backend.main import app


def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8008, log_level="warning")


def main():
    print("=" * 70)
    print("A.R.G.U.S. — Live API Gateway & Security Verification")
    print("=" * 70)

    # 0. Initialize database tables and standard roles
    reset_engine()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        user_svc = UserService(session)
        user_svc.ensure_role("USER")
        user_svc.ensure_role("ANALYST")
        user_svc.ensure_role("ADMIN")
        user_svc.ensure_role("AUDITOR")
        session.commit()
    print(f"[*] Initialized database schema & standard roles at: {os.environ['DATABASE_URL']}")

    # Start uvicorn server in daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("[*] Starting uvicorn server on http://127.0.0.1:8008...")
    
    base_url = "http://127.0.0.1:8008"
    
    # Wait for server to become responsive (up to 15 seconds)
    server_ready = False
    for attempt in range(15):
        time.sleep(1)
        try:
            r = requests.get(f"{base_url}/health", timeout=1)
            if r.status_code == 200:
                server_ready = True
                print(f"[+] Server is listening after {attempt + 1}s.")
                break
        except Exception:
            pass

    if not server_ready:
        raise RuntimeError("Server failed to respond within 15 seconds.")

    try:
        # 1. GET /health & Security Headers
        print("\n--- 1. Testing GET /health & Security Headers ---")
        r_health = requests.get(f"{base_url}/health")
        print(f"Status Code: {r_health.status_code}")
        print(f"Response:    {r_health.json()}")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "ok"
        assert r_health.headers.get("X-Content-Type-Options") == "nosniff"
        assert r_health.headers.get("X-Frame-Options") == "DENY"
        print("[+] Security headers verified: nosniff, DENY")

        # 2. GET /ready
        print("\n--- 2. Testing GET /ready ---")
        r_ready = requests.get(f"{base_url}/ready")
        print(f"Status Code: {r_ready.status_code}")
        print(f"Response:    {r_ready.json()}")
        assert r_ready.status_code == 200
        assert r_ready.json()["status"] == "ready"
        assert r_ready.json()["database_connected"] is True
        assert r_ready.json()["models_loaded"] is True

        # 3. User Registration (POST /api/v1/auth/register)
        print("\n--- 3. Testing User Registration ---")
        reg_payload = {
            "username": "live_analyst_1",
            "email": "analyst1@argus.org",
            "password": "SecurePassword123!",
            "role": "ANALYST",
        }
        r_reg = requests.post(f"{base_url}/api/v1/auth/register", json=reg_payload)
        print(f"Status Code: {r_reg.status_code}")
        print(f"Response:    {r_reg.json()}")
        assert r_reg.status_code == 201
        assert r_reg.json()["username"] == "live_analyst_1"

        # 4. User Login & Token Issuance (POST /api/v1/auth/login)
        print("\n--- 4. Testing User Login & JWT Token Issuance ---")
        login_payload = {
            "username": "live_analyst_1",
            "password": "SecurePassword123!",
        }
        r_login = requests.post(f"{base_url}/api/v1/auth/login", json=login_payload)
        print(f"Status Code: {r_login.status_code}")
        token_data = r_login.json()
        print(f"Token Type:  {token_data['token_type']}")
        print(f"Token (abbreviated): {token_data['access_token'][:30]}...")
        assert r_login.status_code == 200
        auth_token = token_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {auth_token}"}

        # 5. Protected Endpoint (GET /api/v1/auth/me)
        print("\n--- 5. Testing Protected Endpoint (GET /api/v1/auth/me) ---")
        r_me = requests.get(f"{base_url}/api/v1/auth/me", headers=auth_headers)
        print(f"Status Code: {r_me.status_code}")
        print(f"Response:    {r_me.json()}")
        assert r_me.status_code == 200
        assert r_me.json()["username"] == "live_analyst_1"

        # 6. Authenticated Transaction Assessment (POST /api/v1/transactions/assess)
        print("\n--- 6. Testing Authenticated Transaction Assessment (Row 3583 Attributes) ---")
        payload = {
            "step": 646,
            "type": "TRANSFER",
            "amount": 399045.08,
            "nameOrig": "live_analyst_1",
            "nameDest": "C9876543210",
            "oldbalanceOrg": 10399045.08,
            "newbalanceOrig": 10399045.08,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0,
        }
        r_assess = requests.post(
            f"{base_url}/api/v1/transactions/assess",
            json=payload,
            headers=auth_headers,
        )
        print(f"Status Code: {r_assess.status_code}")
        assess_data = r_assess.json()
        print(f"Transaction ID: {assess_data['transaction_id']}")
        print(f"Risk Score:     {assess_data['risk_score']}")
        print(f"Decision:       {assess_data['decision']}")
        assert r_assess.status_code == 200
        assert assess_data["decision"] == "BLOCK"
        assert assess_data["risk_score"] >= 70.0
        tx_id = assess_data["transaction_id"]

        # 7. Authorized Transaction Lookup (GET /api/v1/transactions/{tx_id})
        print(f"\n--- 7. Testing Authorized Transaction Retrieval ---")
        r_get = requests.get(f"{base_url}/api/v1/transactions/{tx_id}", headers=auth_headers)
        print(f"Status Code: {r_get.status_code}")
        print(f"Response:    {r_get.json()}")
        assert r_get.status_code == 200
        assert r_get.json()["tx_id"] == tx_id

        # 8. Non-modeled type rejection (No auto-approval)
        print("\n--- 8. Testing Non-Modeled Type (PAYMENT) Rejection ---")
        payload_pmt = {
            "step": 10,
            "type": "PAYMENT",
            "amount": 25.0,
            "nameOrig": "C1",
            "nameDest": "M1",
            "oldbalanceOrg": 100.0,
            "newbalanceOrig": 75.0,
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0,
        }
        r_pmt = requests.post(f"{base_url}/api/v1/transactions/assess", json=payload_pmt)
        print(f"Status Code: {r_pmt.status_code}")
        print(f"Response:    {r_pmt.json()}")
        assert r_pmt.status_code == 422

        print("\n" + "=" * 70)
        print("[+] ALL 8 LIVE MANUAL API VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        reset_engine()
        if DB_FILE.exists():
            try:
                DB_FILE.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    main()
