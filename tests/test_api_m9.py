"""
A.R.G.U.S. — Milestone 9 API Integration Tests
Validates the minimal backend additions for the user-facing web application:
1. Transaction History list with server-side pagination and Scoped RBAC.
2. Enriched Transaction Detail with safe 18-feature disclosure and zero target leakage.
3. Analyst Dashboard live SQL aggregate metrics.
4. Investigation Alerts queue query and triage disposition lifecycle.
5. IoT Device fleet inventory query and admin-only tamper reset.
"""

import uuid
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from database.base import Base
from database.models import (
    User,
    Role,
    Device,
    Transaction,
    RiskAssessmentRecord,
    DecisionRecord,
    Alert,
    AuditLog,
)
from backend.main import app
from backend.dependencies.database import get_db
from backend.services.user_service import UserService
from backend.services.device_service import DeviceService
from backend.security.password import hash_password


@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped in-memory database with StaticPool for thread sharing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(test_engine):
    """TestClient fixture with transactional database isolation and active lifespan."""
    TestingSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)

    # Ensure standard roles exist
    with TestingSessionLocal() as session:
        user_svc = UserService(session)
        user_svc.ensure_role("USER")
        user_svc.ensure_role("ANALYST")
        user_svc.ensure_role("ADMIN")
        user_svc.ensure_role("AUDITOR")
        session.commit()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def get_token_for_user(client: TestClient, username: str, email: str, role_name: str) -> str:
    """Helper to create or log in a user and return a JWT bearer token."""
    # Attempt registration
    client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": "Password123!",
        "role": role_name,
    })
    # Login
    res = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": "Password123!",
    })
    assert res.status_code == 200, f"Failed to login user {username}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# 1. Transaction History & Scoped RBAC Tests
# ==============================================================================

def test_list_transactions_scoped_rbac_and_filters(client: TestClient):
    """Verifies that normal USER accounts only see their own transactions, while privileged roles see all."""
    user1_token = get_token_for_user(client, "alice_user", "alice@argus.org", "USER")
    user2_token = get_token_for_user(client, "bob_user", "bob@argus.org", "USER")
    analyst_token = get_token_for_user(client, "carol_analyst", "carol@argus.org", "ANALYST")

    # Alice submits 2 transactions
    tx_alice_1 = {
        "step": 646,
        "type": "TRANSFER",
        "amount": 1000.0,
        "nameOrig": "alice_user",
        "nameDest": "C9999999999",
        "oldbalanceOrg": 50000.0,
        "newbalanceOrig": 49000.0,
        "oldbalanceDest": 0.0,
        "newbalanceDest": 1000.0,
    }
    client.post("/api/v1/transactions/assess", json=tx_alice_1, headers={"Authorization": f"Bearer {user1_token}"})

    tx_alice_2 = {
        "step": 647,
        "type": "CASH_OUT",
        "amount": 500.0,
        "nameOrig": "alice_user",
        "nameDest": "M8888888888",
        "oldbalanceOrg": 49000.0,
        "newbalanceOrig": 48500.0,
        "oldbalanceDest": 0.0,
        "newbalanceDest": 500.0,
    }
    client.post("/api/v1/transactions/assess", json=tx_alice_2, headers={"Authorization": f"Bearer {user1_token}"})

    # Bob submits 1 transaction
    tx_bob_1 = {
        "step": 648,
        "type": "TRANSFER",
        "amount": 2500.0,
        "nameOrig": "bob_user",
        "nameDest": "C7777777777",
        "oldbalanceOrg": 10000.0,
        "newbalanceOrig": 7500.0,
        "oldbalanceDest": 0.0,
        "newbalanceDest": 2500.0,
    }
    client.post("/api/v1/transactions/assess", json=tx_bob_1, headers={"Authorization": f"Bearer {user2_token}"})

    # 1. Alice queries history -> should see exactly 2 transactions (hers only)
    res_alice = client.get("/api/v1/transactions", headers={"Authorization": f"Bearer {user1_token}"})
    assert res_alice.status_code == 200
    data_alice = res_alice.json()
    assert data_alice["total"] == 2
    assert len(data_alice["items"]) == 2
    assert all(item["name_orig"] == "alice_user" for item in data_alice["items"])

    # 2. Bob queries history -> should see exactly 1 transaction (his only)
    res_bob = client.get("/api/v1/transactions", headers={"Authorization": f"Bearer {user2_token}"})
    assert res_bob.status_code == 200
    data_bob = res_bob.json()
    assert data_bob["total"] == 1
    assert data_bob["items"][0]["name_orig"] == "bob_user"

    # 3. Analyst queries history -> should see at least 3 transactions (all users)
    res_analyst = client.get("/api/v1/transactions", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res_analyst.status_code == 200
    data_analyst = res_analyst.json()
    assert data_analyst["total"] >= 3

    # 4. Test filter by type: TRANSFER
    res_filter_type = client.get("/api/v1/transactions?type=TRANSFER", headers={"Authorization": f"Bearer {user1_token}"})
    assert res_filter_type.status_code == 200
    assert all(item["type"] == "TRANSFER" for item in res_filter_type.json()["items"])


# ==============================================================================
# 2. Enriched Transaction Detail Tests
# ==============================================================================

def test_get_transaction_detail_enriched(client: TestClient):
    """Verifies that GET /api/v1/transactions/{id} safely returns the 18 engineered features and model signals."""
    user_token = get_token_for_user(client, "dave_user", "dave@argus.org", "USER")

    # Submit transaction
    tx_payload = {
        "step": 650,
        "type": "TRANSFER",
        "amount": 399045.08,
        "nameOrig": "dave_user",
        "nameDest": "M9876543210",
        "oldbalanceOrg": 10399045.08,
        "newbalanceOrig": 10000000.0,
        "oldbalanceDest": 0.0,
        "newbalanceDest": 0.0,
    }
    submit_res = client.post("/api/v1/transactions/assess", json=tx_payload, headers={"Authorization": f"Bearer {user_token}"})
    assert submit_res.status_code == 200
    tx_id = submit_res.json()["transaction_id"]

    # Retrieve detail
    detail_res = client.get(f"/api/v1/transactions/{tx_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert detail_res.status_code == 200
    detail = detail_res.json()

    assert detail["tx_id"] == tx_id
    assert detail["amount"] == 399045.08
    assert detail["risk_assessment"] is not None
    assert "final_risk_score" in detail["risk_assessment"]
    assert "xgboost_signal" in detail["risk_assessment"]
    assert "autoencoder_signal" in detail["risk_assessment"]
    assert detail["decision"] is not None
    assert "policy_decision" in detail["decision"]
    assert "reasons" in detail["decision"]
    assert isinstance(detail["decision"]["reasons"], list)

    # 18 Engineered Features Verification
    assert detail["features"] is not None
    features = detail["features"]
    assert "log_amount" in features
    assert "orig_drain_ratio" in features
    assert "orig_balance_error" in features
    assert "hour_sin" in features
    assert "hour_cos" in features
    assert "is_night_transaction" in features
    assert "dest_zero_balance_anomaly" in features

    # Strict Anti-Leakage Verification
    assert "isFraud" not in detail
    assert "is_fraud" not in detail
    assert "isFlaggedFraud" not in detail
    assert "is_flagged_fraud" not in detail


# ==============================================================================
# 3. Analyst Dashboard Analytics Tests
# ==============================================================================

def test_dashboard_analytics_endpoint(client: TestClient):
    """Verifies that GET /api/v1/analytics/dashboard computes real metrics and restricts normal users."""
    analyst_token = get_token_for_user(client, "eva_analyst", "eva@argus.org", "ANALYST")
    user_token = get_token_for_user(client, "frank_user", "frank@argus.org", "USER")

    # 1. Privileged caller gets dashboard metrics
    res = client.get("/api/v1/analytics/dashboard", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res.status_code == 200
    analytics = res.json()

    assert "total_transactions" in analytics
    assert "approved_count" in analytics
    assert "review_count" in analytics
    assert "blocked_count" in analytics
    assert "average_risk_score" in analytics
    assert "active_devices_count" in analytics
    assert "pending_alerts_count" in analytics
    assert "recent_high_risk" in analytics
    assert isinstance(analytics["recent_high_risk"], list)
    assert analytics["total_transactions"] >= 0

    # 2. Normal USER caller is forbidden
    res_user = client.get("/api/v1/analytics/dashboard", headers={"Authorization": f"Bearer {user_token}"})
    assert res_user.status_code == 403

    # 3. Unauthenticated caller is unauthorized
    res_unauth = client.get("/api/v1/analytics/dashboard")
    assert res_unauth.status_code == 401


# ==============================================================================
# 4. Alerts Lifecycle & Triage Tests
# ==============================================================================

def test_alerts_query_and_triage_lifecycle(client: TestClient):
    """Verifies that high-risk transactions generate alerts and analysts can triage/resolve them."""
    analyst_token = get_token_for_user(client, "grace_analyst", "grace@argus.org", "ANALYST")
    user_token = get_token_for_user(client, "henry_user", "henry@argus.org", "USER")

    # Submit a high-risk drain transaction to trigger a BLOCK / alert
    high_risk_tx = {
        "step": 654,
        "type": "CASH_OUT",
        "amount": 5000000.0,
        "nameOrig": "henry_user",
        "nameDest": "M9990001112",
        "oldbalanceOrg": 5000000.0,
        "newbalanceOrig": 0.0,
        "oldbalanceDest": 0.0,
        "newbalanceDest": 0.0,
    }
    client.post("/api/v1/transactions/assess", json=high_risk_tx, headers={"Authorization": f"Bearer {user_token}"})

    # Analyst queries alerts
    alerts_res = client.get("/api/v1/alerts", headers={"Authorization": f"Bearer {analyst_token}"})
    assert alerts_res.status_code == 200
    alerts_list = alerts_res.json()
    assert len(alerts_list) >= 1

    pending_alert = next((a for a in alerts_list if a["status"] == "PENDING"), None)
    assert pending_alert is not None
    alert_id = pending_alert["alert_id"]

    # Analyst triages alert
    patch_res = client.patch(
        f"/api/v1/alerts/{alert_id}",
        json={
            "status": "RESOLVED",
            "notes": "Verified synthetic liquidation pattern. Account frozen.",
        },
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert patch_res.status_code == 200
    resolved = patch_res.json()
    assert resolved["status"] == "RESOLVED"
    assert "Verified synthetic liquidation" in resolved["notes"]
    assert resolved["resolved_at"] is not None

    # Normal user cannot list or triage alerts
    user_list_res = client.get("/api/v1/alerts", headers={"Authorization": f"Bearer {user_token}"})
    assert user_list_res.status_code == 403


# ==============================================================================
# 5. IoT Fleet Inventory & Admin Tamper Reset Tests
# ==============================================================================

def test_device_fleet_inventory_and_admin_tamper_reset(client: TestClient, test_engine):
    """Verifies that devices can be queried by analysts and tamper flags can be reset only by admins."""
    admin_token = get_token_for_user(client, "admin_super", "admin@argus.org", "ADMIN")
    analyst_token = get_token_for_user(client, "isabel_analyst", "isabel@argus.org", "ANALYST")
    user_token = get_token_for_user(client, "jack_user", "jack@argus.org", "USER")

    # Register an edge terminal directly via service
    device_id = None
    with Session(test_engine) as session:
        dev_svc = DeviceService(session)
        dev = dev_svc.register_device(
            device_code="ESP32_TERM_M9_TEST",
            raw_api_key="secure_demo_key_m9",
            status="TAMPERED",
            tamper_flag=True,
        )
        device_id = str(dev.device_id)

    # 1. Analyst queries devices -> can view inventory and telemetry
    res_list = client.get("/api/v1/devices", headers={"Authorization": f"Bearer {analyst_token}"})
    assert res_list.status_code == 200
    devices = res_list.json()
    assert len(devices) >= 1
    test_dev = next((d for d in devices if d["device_code"] == "ESP32_TERM_M9_TEST"), None)
    assert test_dev is not None
    assert test_dev["tamper_flag"] is True
    assert test_dev["status"] == "TAMPERED"

    # 2. Normal user is forbidden from device inventory
    assert client.get("/api/v1/devices", headers={"Authorization": f"Bearer {user_token}"}).status_code == 403

    # 3. Analyst attempts to reset tamper -> should be HTTP 403 Forbidden (Admin only)
    res_analyst_reset = client.post(
        f"/api/v1/devices/{device_id}/reset-tamper",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res_analyst_reset.status_code == 403

    # 4. Admin resets tamper -> succeeds
    res_admin_reset = client.post(
        f"/api/v1/devices/{device_id}/reset-tamper",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin_reset.status_code == 200
    cleared_dev = res_admin_reset.json()
    assert cleared_dev["tamper_flag"] is False
    assert cleared_dev["status"] == "ACTIVE"
