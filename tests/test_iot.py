"""
A.R.G.U.S. — IoT & ESP32 Edge Terminal Integration Test Suite (Milestone 8)
Verifies:
1. Device authentication & credential hashing verification
2. Rejection of unknown devices (401)
3. Rejection of invalid credentials (401)
4. Rejection of inactive / tampered devices (403)
5. Edge transaction assessment via full ML pipeline (TRANSFER -> APPROVE, CASH_OUT -> BLOCK)
6. Strict modeling subspace preservation (PAYMENT, CASH_IN, DEBIT -> 422)
7. Terminal-merchant association enforcement
8. Concurrency-safe duplicate transaction / replay protection (409 Conflict)
9. Device heartbeat telemetry synchronization
10. Audit log trail for device events
11. Anti-leakage preservation (isFraud / isFlaggedFraud rejected)
"""

import os
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from database.base import Base
from database.models.device import Device
from database.models.merchant import Merchant
from database.models.audit import AuditLog
from database.repository import create_device, get_device_by_code
from backend.main import create_application
from backend.config import settings
from backend.services.model_service import ModelManager
from backend.security.device_auth import hash_device_key
from backend.dependencies.database import get_db
from backend.dependencies.models import get_model_manager
from backend.services.model_service import ModelManager
from backend.security.device_auth import hash_device_key


@pytest.fixture(scope="module")
def shared_model_manager():
    """Initializes and loads the 4 ML/DL model artifacts once for the test module."""
    manager = ModelManager(models_dir=settings.resolved_models_dir)
    manager.load_artifacts()
    return manager


@pytest.fixture
def db_session():
    """Provides an isolated in-memory SQLite database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session, shared_model_manager: ModelManager):
    """Provides a FastAPI test client configured with overridden DB and Model dependencies."""
    app = create_application()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_models():
        return shared_model_manager

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_model_manager] = override_get_models

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def provisioned_device(db_session: Session):
    """Creates a sample active ESP32 device with merchant association."""
    merchant = Merchant(
        merchant_id=uuid.uuid4(),
        merchant_code="M_SUPERSTORE_01",
        name="Apex Superstore",
        risk_tier="LOW",
    )
    db_session.add(merchant)
    db_session.flush()

    raw_key = "secure_esp32_test_api_key_8899"
    device = create_device(
        session=db_session,
        device_code="ESP32-TERM-001",
        api_key_hash=hash_device_key(raw_key),
        merchant_id=merchant.merchant_id,
        device_type="ESP32_POS",
        firmware_version="v1.2.0",
        status="ACTIVE",
        tamper_flag=False,
    )
    db_session.commit()
    return {
        "device": device,
        "raw_key": raw_key,
        "device_code": "ESP32-TERM-001",
        "merchant": merchant,
    }


# ==============================================================================
# 1. DEVICE AUTHENTICATION & ACCESS CONTROL TESTS
# ==============================================================================

def test_device_auth_success(client: TestClient, provisioned_device: dict):
    """Verifies that an active, registered device authenticates successfully with valid credentials."""
    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": provisioned_device["raw_key"],
    }
    payload = {
        "device_code": provisioned_device["device_code"],
        "firmware_version": "v1.2.0",
        "device_status": "ONLINE",
        "network_status": "CONNECTED",
        "temperature": 32.5,
        "uptime_seconds": 3600,
    }
    response = client.post("/api/v1/iot/heartbeat", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["device_code"] == provisioned_device["device_code"]


def test_unknown_device_rejected(client: TestClient):
    """Verifies that an unregistered device code is rejected with HTTP 401."""
    headers = {
        "X-Device-Code": "UNKNOWN-DEVICE-999",
        "X-Device-API-Key": "some_random_key",
    }
    payload = {"device_status": "ONLINE"}
    response = client.post("/api/v1/iot/heartbeat", json=payload, headers=headers)
    assert response.status_code == 401
    assert "not registered" in response.json()["detail"].lower()


def test_invalid_device_credential_rejected(client: TestClient, provisioned_device: dict):
    """Verifies that an invalid API key for a registered device is rejected with HTTP 401."""
    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": "completely_wrong_key_12345",
    }
    payload = {"device_status": "ONLINE"}
    response = client.post("/api/v1/iot/heartbeat", json=payload, headers=headers)
    assert response.status_code == 401
    assert "invalid api key" in response.json()["detail"].lower()


def test_inactive_device_rejected(client: TestClient, db_session: Session, provisioned_device: dict):
    """Verifies that a decommissioned or inactive device is rejected with HTTP 403."""
    device = db_session.get(Device, provisioned_device["device"].device_id)
    device.status = "INACTIVE"
    db_session.commit()

    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": provisioned_device["raw_key"],
    }
    payload = {"device_status": "ONLINE"}
    response = client.post("/api/v1/iot/heartbeat", json=payload, headers=headers)
    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


def test_tampered_device_rejected(client: TestClient, db_session: Session, provisioned_device: dict):
    """Verifies that a hardware-tampered device is locked out with HTTP 403."""
    device = db_session.get(Device, provisioned_device["device"].device_id)
    device.tamper_flag = True
    db_session.commit()

    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": provisioned_device["raw_key"],
    }
    payload = {"device_status": "ONLINE"}
    response = client.post("/api/v1/iot/heartbeat", json=payload, headers=headers)
    assert response.status_code == 403
    assert "tamper" in response.json()["detail"].lower()


# ==============================================================================
# 2. EDGE TRANSACTION EVALUATION & SUBSPACE POLICY TESTS
# ==============================================================================

def test_iot_transfer_assessment_approve(client: TestClient, provisioned_device: dict):
    """Verifies end-to-end evaluation of a benign TRANSFER from an edge terminal."""
    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": provisioned_device["raw_key"],
    }
    payload = {
        "client_tx_id": "TX-ESP32-1001",
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
    response = client.post("/api/v1/iot/transactions", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVE"
    assert data["risk_score"] < 40.0
    assert data["terminal_message"] == "TRANSACTION APPROVED"
    assert data["client_tx_id"] == "TX-ESP32-1001"
    assert data["device_code"] == provisioned_device["device_code"]


def test_iot_cash_out_assessment_block(client: TestClient, provisioned_device: dict):
    """Verifies end-to-end evaluation of high-risk CASH_OUT from an edge terminal."""
    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": provisioned_device["raw_key"],
    }
    payload = {
        "client_tx_id": "TX-ESP32-1002",
        "step": 646,
        "type": "CASH_OUT",
        "amount": 399045.08,
        "name_orig": "C1039904508",
        "name_dest": "M0000000001",
        "oldbalance_org": 10399045.08,
        "newbalance_orig": 10399045.08,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 0.0,
    }
    response = client.post("/api/v1/iot/transactions", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "BLOCK"
    assert data["risk_score"] >= 70.0
    assert "BLOCKED" in data["terminal_message"]


@pytest.mark.parametrize("unsupported_type", ["PAYMENT", "CASH_IN", "DEBIT"])
def test_iot_non_modeled_types_return_controlled_422(
    client: TestClient,
    provisioned_device: dict,
    unsupported_type: str,
):
    """Verifies that non-modeled types received from terminals strictly return controlled HTTP 422."""
    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": provisioned_device["raw_key"],
    }
    payload = {
        "step": 100,
        "type": unsupported_type,
        "amount": 50.00,
        "name_orig": "C12345",
        "name_dest": "M67890",
        "oldbalance_org": 100.0,
        "newbalance_orig": 50.0,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 0.0,
    }
    response = client.post("/api/v1/iot/transactions", json=payload, headers=headers)
    assert response.status_code == 422
    assert "not currently supported for ml risk assessment" in response.json()["detail"].lower()


def test_device_merchant_mismatch_rejected(client: TestClient, provisioned_device: dict):
    """Verifies that attempting to route a transaction under an unassociated merchant is rejected."""
    mismatched_merchant_id = uuid.uuid4()
    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": provisioned_device["raw_key"],
    }
    payload = {
        "merchant_id": str(mismatched_merchant_id),
        "step": 150,
        "type": "TRANSFER",
        "amount": 100.00,
        "name_orig": "C1029384756",
        "name_dest": "M9876543210",
        "oldbalance_org": 5000.00,
        "newbalance_orig": 4900.00,
        "oldbalance_dest": 1000.00,
        "newbalance_dest": 1100.00,
    }
    response = client.post("/api/v1/iot/transactions", json=payload, headers=headers)
    assert response.status_code == 400
    assert "not associated with merchant" in response.json()["detail"].lower()


# ==============================================================================
# 3. DUPLICATE / REPLAY PROTECTION TESTS
# ==============================================================================

def test_duplicate_client_tx_id_rejected_with_409(client: TestClient, provisioned_device: dict):
    """Verifies that duplicate client sequence IDs from the same terminal return HTTP 409 Conflict."""
    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": provisioned_device["raw_key"],
    }
    payload = {
        "client_tx_id": "REPLAY-TX-55555",
        "step": 150,
        "type": "TRANSFER",
        "amount": 300.00,
        "name_orig": "C1029384756",
        "name_dest": "M9876543210",
        "oldbalance_org": 5000.00,
        "newbalance_orig": 4700.00,
        "oldbalance_dest": 1000.00,
        "newbalance_dest": 1300.00,
    }

    # First attempt: succeeds
    res1 = client.post("/api/v1/iot/transactions", json=payload, headers=headers)
    assert res1.status_code == 200

    # Second attempt with identical client_tx_id: rejected with 409
    res2 = client.post("/api/v1/iot/transactions", json=payload, headers=headers)
    assert res2.status_code == 409
    assert "duplicate transaction" in res2.json()["detail"].lower()


# ==============================================================================
# 4. AUDIT LOGGING & SECURITY INTEGRITY TESTS
# ==============================================================================

def test_device_audit_logs_created(client: TestClient, db_session: Session, provisioned_device: dict):
    """Verifies that device operations generate structured audit log entries in audit_logs table."""
    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": provisioned_device["raw_key"],
    }
    # Execute heartbeat
    client.post(
        "/api/v1/iot/heartbeat",
        json={"device_status": "ONLINE", "uptime_seconds": 500},
        headers=headers,
    )

    # Execute transaction
    client.post(
        "/api/v1/iot/transactions",
        json={
            "client_tx_id": "TX-AUDIT-TEST",
            "step": 120,
            "type": "TRANSFER",
            "amount": 100.00,
            "name_orig": "C1",
            "name_dest": "C2",
            "oldbalance_org": 500.0,
            "newbalance_orig": 400.0,
            "oldbalance_dest": 100.0,
            "newbalance_dest": 200.0,
        },
        headers=headers,
    )

    logs = db_session.query(AuditLog).all()
    event_types = {log.event_type for log in logs}
    assert "DEVICE_AUTH_SUCCESS" in event_types
    assert "DEVICE_HEARTBEAT" in event_types
    assert "DEVICE_TRANSACTION_RECEIVED" in event_types


def test_anti_leakage_guards_reject_is_fraud(client: TestClient, provisioned_device: dict):
    """Verifies that anti-leakage guards reject attempts to pass isFraud from edge terminals."""
    headers = {
        "X-Device-Code": provisioned_device["device_code"],
        "X-Device-API-Key": provisioned_device["raw_key"],
    }
    payload = {
        "step": 150,
        "type": "TRANSFER",
        "amount": 250.00,
        "name_orig": "C1029384756",
        "name_dest": "M9876543210",
        "oldbalance_org": 5000.00,
        "newbalance_orig": 4750.00,
        "oldbalance_dest": 1000.00,
        "newbalance_dest": 1250.00,
        "isFraud": 1,  # Strictly forbidden
    }
    response = client.post("/api/v1/iot/transactions", json=payload, headers=headers)
    assert response.status_code == 422
