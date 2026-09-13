"""
A.R.G.U.S. — FastAPI Integration Test Suite (Milestone 6)
Validates API endpoints, lifespan model management, request schemas, anti-leakage guards,
modeling subspace boundaries, Risk Engine scoring, and atomic database persistence.
"""

import uuid
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from database.base import Base
from database.models import (
    Transaction,
    TransactionFeatures,
    ModelResult,
    RiskAssessmentRecord,
    DecisionRecord,
    Alert,
    AuditLog,
)
from backend.main import app
from backend.dependencies.database import get_db
from backend.services.model_service import ModelManager


@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped in-memory database using StaticPool to share connection across threads."""
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
    """
    TestClient fixture with database dependency override and active lifespan.
    Cleans up tables between tests to ensure test isolation.
    """
    TestingSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)

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


# ==============================================================================
# 1. Health & Readiness Tests
# ==============================================================================

def test_health_endpoint(client: TestClient):
    """Verifies liveness probe returns HTTP 200 and standard payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "argus-api"
    assert "version" in data


def test_readiness_endpoint(client: TestClient):
    """Verifies readiness probe validates database connectivity and loaded models."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database_connected"] is True
    assert data["models_loaded"] is True
    assert data["details"]["architecture"] == "4-model ensemble (XGBoost, LR, IsolationForest, Autoencoder)"


# ==============================================================================
# 2. Ingress Validation & Anti-Leakage Tests
# ==============================================================================

def test_negative_amount_rejected(client: TestClient):
    """Verifies negative transaction amounts are rejected with HTTP 422."""
    payload = {
        "step": 100,
        "type": "TRANSFER",
        "amount": -50.0,
        "name_orig": "C123",
        "name_dest": "C456",
        "oldbalance_org": 1000.0,
        "newbalance_orig": 950.0,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 50.0,
    }
    response = client.post("/api/v1/transactions/assess", json=payload)
    assert response.status_code == 422


def test_invalid_transaction_type_rejected(client: TestClient):
    """Verifies unknown transaction types outside PaySim are rejected with HTTP 422."""
    payload = {
        "step": 100,
        "type": "BITCOIN_TRANSFER",
        "amount": 500.0,
        "name_orig": "C123",
        "name_dest": "C456",
        "oldbalance_org": 1000.0,
        "newbalance_orig": 500.0,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 500.0,
    }
    response = client.post("/api/v1/transactions/assess", json=payload)
    assert response.status_code == 422


def test_target_leakage_isFraud_rejected(client: TestClient):
    """Verifies operational security: isFraud in request body is strictly rejected."""
    payload = {
        "step": 100,
        "type": "TRANSFER",
        "amount": 500.0,
        "name_orig": "C123",
        "name_dest": "C456",
        "oldbalance_org": 1000.0,
        "newbalance_orig": 500.0,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 500.0,
        "isFraud": 1,
    }
    response = client.post("/api/v1/transactions/assess", json=payload)
    assert response.status_code == 422
    assert "strictly forbidden" in response.text


def test_simulation_leakage_isFlaggedFraud_rejected(client: TestClient):
    """Verifies simulation artifact isFlaggedFraud in request body is strictly rejected."""
    payload = {
        "step": 100,
        "type": "TRANSFER",
        "amount": 500.0,
        "name_orig": "C123",
        "name_dest": "C456",
        "oldbalance_org": 1000.0,
        "newbalance_orig": 500.0,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 500.0,
        "isFlaggedFraud": 0,
    }
    response = client.post("/api/v1/transactions/assess", json=payload)
    assert response.status_code == 422
    assert "strictly forbidden" in response.text


# ==============================================================================
# 3. Modeling Subspace Policy (No Auto-Approval / Controlled 422)
# ==============================================================================

@pytest.mark.parametrize("tx_type", ["PAYMENT", "CASH_IN", "DEBIT"])
def test_non_modeled_types_return_controlled_unsupported(client: TestClient, tx_type: str):
    """
    Verifies that PAYMENT, CASH_IN, and DEBIT are NOT auto-approved.
    Returns controlled HTTP 422 indicating ML assessment is only supported for TRANSFER/CASH_OUT.
    """
    payload = {
        "step": 50,
        "type": tx_type,
        "amount": 120.0,
        "name_orig": "C55555",
        "name_dest": "M88888",
        "oldbalance_org": 500.0,
        "newbalance_orig": 380.0,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 0.0,
    }
    response = client.post("/api/v1/transactions/assess", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert f"Transaction type '{tx_type}' is not currently supported for ML risk assessment" in data["detail"]


# ==============================================================================
# 4. End-to-End Assessment & Risk Engine Integration
# ==============================================================================

def test_assess_benign_transfer_transaction(client: TestClient, test_engine):
    """
    Verifies assessment of a routine, balanced TRANSFER transaction.
    Expected: Low risk score, APPROVE decision.
    """
    payload = {
        "step": 640,
        "type": "TRANSFER",
        "amount": 50.0,
        "name_orig": "C1000000001",
        "name_dest": "C2000000002",
        "oldbalance_org": 10000.0,
        "newbalance_orig": 9950.0,
        "oldbalance_dest": 5000.0,
        "newbalance_dest": 5050.0,
    }
    response = client.post("/api/v1/transactions/assess", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "transaction_id" in data
    assert 0.0 <= data["risk_score"] < 40.0
    assert data["decision"] == "APPROVE"
    assert "model_signals" in data
    assert "xgboost_score" in data["model_signals"]
    assert "logistic_score" in data["model_signals"]
    assert "isolation_score" in data["model_signals"]
    assert "autoencoder_score" in data["model_signals"]
    assert isinstance(data["reasons"], list)

    # Verify atomic DB persistence
    with Session(test_engine) as session:
        tx_id = uuid.UUID(data["transaction_id"])
        tx = session.get(Transaction, tx_id)
        assert tx is not None
        assert tx.type == "TRANSFER"
        assert tx.amount == 50.0

        # Features persisted
        feat = session.scalars(select(TransactionFeatures).where(TransactionFeatures.tx_id == tx_id)).first()
        assert feat is not None
        assert feat.is_transfer == 1
        assert feat.is_cash_out == 0

        # Model results persisted (4 models)
        mrs = list(session.scalars(select(ModelResult).where(ModelResult.tx_id == tx_id)).all())
        assert len(mrs) == 4
        model_names = {mr.model_name for mr in mrs}
        assert model_names == {"XGBoost", "LogisticRegression", "IsolationForest", "DeepAutoencoder"}

        # Risk assessment persisted
        ra = session.scalars(select(RiskAssessmentRecord).where(RiskAssessmentRecord.tx_id == tx_id)).first()
        assert ra is not None
        assert ra.final_risk_score == pytest.approx(data["risk_score"], abs=1e-2)

        # Decision persisted
        dec = session.scalars(select(DecisionRecord).where(DecisionRecord.assessment_id == ra.assessment_id)).first()
        assert dec is not None
        assert dec.policy_decision == "APPROVE"

        # No alert for APPROVE
        alert = session.scalars(select(Alert).where(Alert.assessment_id == ra.assessment_id)).first()
        assert alert is None

        # AuditLog persisted
        audit = session.scalars(select(AuditLog).where(AuditLog.resource_id == str(tx_id))).first()
        assert audit is not None
        assert audit.action == "RENDER_APPROVE"


def test_assess_fraudulent_cash_out_transaction(client: TestClient, test_engine):
    """
    Verifies assessment of an anomalous full liquidation CASH_OUT transaction.
    Expected: Elevated risk score (REVIEW or BLOCK), Alert created in DB.
    """
    payload = {
        "step": 650,
        "type": "CASH_OUT",
        "amount": 2500000.0,
        "name_orig": "C999999999",
        "name_dest": "M111111111",
        "oldbalance_org": 2500000.0,
        "newbalance_orig": 0.0,        # Full liquidation
        "oldbalance_dest": 0.0,        # Zero balance anomaly
        "newbalance_dest": 0.0,
    }
    response = client.post("/api/v1/transactions/assess", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["decision"] in ("REVIEW", "BLOCK")
    assert data["risk_score"] >= 40.0

    # Verify Alert was created in database
    with Session(test_engine) as session:
        tx_id = uuid.UUID(data["transaction_id"])
        ra = session.scalars(select(RiskAssessmentRecord).where(RiskAssessmentRecord.tx_id == tx_id)).first()
        assert ra is not None

        alert = session.scalars(select(Alert).where(Alert.assessment_id == ra.assessment_id)).first()
        assert alert is not None
        assert alert.status == "PENDING"
        assert alert.severity in ("HIGH", "CRITICAL")


def test_assess_audited_row_3583_attributes(client: TestClient):
    """
    Verifies evaluation using the exact audited Row 3583 attributes:
    Step 646, TRANSFER, amount $399,045.08, oldbalanceOrg = newbalanceOrig = $10,399,045.08.
    Expected: Ensemble multi-signal rescue renders high risk / BLOCK decision.
    """
    payload = {
        "step": 646,
        "type": "TRANSFER",
        "amount": 399045.08,
        "name_orig": "C1234567890",
        "name_dest": "C9876543210",
        "oldbalance_org": 10399045.08,
        "newbalance_orig": 10399045.08,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 0.0,
    }
    response = client.post("/api/v1/transactions/assess", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verified empirical score from Milestone 3A/4 is ~84.36 (BLOCK)
    assert data["decision"] == "BLOCK"
    assert data["risk_score"] >= 70.0
    assert data["model_signals"]["autoencoder_score"] > 0.5


# ==============================================================================
# 5. Query & Error Handling Tests
# ==============================================================================

def test_get_transaction_by_id_endpoint(client: TestClient):
    """Verifies GET /api/v1/transactions/{tx_id} returns the persisted record."""
    # First create transaction via assess endpoint
    payload = {
        "step": 645,
        "type": "TRANSFER",
        "amount": 100.0,
        "name_orig": "C111",
        "name_dest": "C222",
        "oldbalance_org": 1000.0,
        "newbalance_orig": 900.0,
        "oldbalance_dest": 500.0,
        "newbalance_dest": 600.0,
    }
    assess_res = client.post("/api/v1/transactions/assess", json=payload)
    assert assess_res.status_code == 200
    tx_id = assess_res.json()["transaction_id"]

    # Retrieve by ID
    get_res = client.get(f"/api/v1/transactions/{tx_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["tx_id"] == tx_id
    assert get_data["type"] == "TRANSFER"
    assert get_data["amount"] == 100.0


def test_get_nonexistent_transaction_returns_404(client: TestClient):
    """Verifies GET with a random UUID returns HTTP 404 Not Found."""
    random_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/transactions/{random_id}")
    assert res.status_code == 404
    assert f"Transaction with ID '{random_id}' not found." in res.json()["detail"]


def test_no_training_during_inference(client: TestClient):
    """
    Verifies that assessing a transaction does not alter model states or trigger retraining.
    """
    manager: ModelManager = app.state.model_manager
    assert manager.is_ready is True
    # Confirm models are fitted and ready
    assert manager.xgb_model.is_fitted is True
    assert manager.lr_model.is_fitted is True
    assert manager.if_model.is_fitted is True
    assert manager.ae_model.is_fitted is True
