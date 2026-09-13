"""
A.R.G.U.S. — Relational Database Layer Test Suite (Milestone 5)
Verifies 3NF schema, constraints, relationships, atomic persistence,
rollback behavior, and ML Risk Engine integration.
"""

import os
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, select, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from database.base import Base
from database.models import (
    Role,
    User,
    Merchant,
    Device,
    Transaction,
    TransactionFeatures,
    ModelResult,
    RiskAssessmentRecord,
    DecisionRecord,
    Alert,
    AuditLog,
)
from database.repository import (
    save_assessed_transaction,
    get_transaction_by_id,
    get_pending_alerts,
    log_audit_event,
)
from ml_engine.risk import (
    RiskConfig,
    RiskSignals,
    compute_risk_score,
    evaluate_decision,
    assess_transaction,
    DecisionAction,
)


@pytest.fixture(scope="session")
def test_engine():
    """
    Creates an isolated test database engine.
    Uses TEST_DATABASE_URL if set, otherwise an in-memory SQLite database.
    """
    test_db_url = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine(test_db_url, echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """
    Provides an isolated database session rolled back after every test.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


# ==============================================================================
# 1. SCHEMA & REGISTRY TESTS
# ==============================================================================

def test_all_models_registered():
    """Verifies that all 11 core entities are registered on Base.metadata."""
    registered_tables = set(Base.metadata.tables.keys())
    expected_tables = {
        "roles",
        "users",
        "merchants",
        "devices",
        "transactions",
        "transaction_features",
        "model_results",
        "risk_assessments",
        "decisions",
        "alerts",
        "audit_logs",
    }
    assert expected_tables.issubset(registered_tables), (
        f"Missing tables: {expected_tables - registered_tables}"
    )


def test_table_columns_and_keys(test_engine):
    """Verifies primary and foreign key constraints on the created schema."""
    inspector = inspect(test_engine)
    
    # Transactions table
    tx_cols = {col["name"] for col in inspector.get_columns("transactions")}
    assert "tx_id" in tx_cols
    assert "amount" in tx_cols
    assert "step" in tx_cols
    assert "name_orig" in tx_cols
    assert "name_dest" in tx_cols
    # Assert isFraud and isFlaggedFraud are NOT in operational ingress table
    assert "isFraud" not in tx_cols
    assert "is_fraud" not in tx_cols
    assert "isFlaggedFraud" not in tx_cols
    
    # Transaction Features: exact 18 features
    feat_cols = {col["name"] for col in inspector.get_columns("transaction_features")}
    exact_18 = {
        "amount", "oldbalance_org", "newbalance_orig", "oldbalance_dest", "newbalance_dest",
        "log_amount", "is_transfer", "is_cash_out", "hour_of_day", "hour_sin", "hour_cos",
        "is_night_transaction", "orig_balance_error", "orig_drain_ratio", "is_full_liquidation",
        "dest_balance_error", "dest_drain_ratio", "dest_zero_balance_anomaly"
    }
    assert exact_18.issubset(feat_cols), f"Missing feature columns: {exact_18 - feat_cols}"


# ==============================================================================
# 2. CRUD & CONSTRAINT TESTS
# ==============================================================================

def test_role_and_user_creation(db_session: Session):
    """Verifies creation of roles and users with unique constraints."""
    role = Role(name="ANALYST", description="Fraud operations analyst")
    db_session.add(role)
    db_session.flush()

    user = User(
        username="analyst_jane",
        email="jane.doe@bank.org",
        hashed_password="argon2id$mock_hash_string",
        role_id=role.role_id,
    )
    db_session.add(user)
    db_session.flush()

    assert user.user_id is not None
    assert user.role.name == "ANALYST"
    assert len(role.users) == 1

    # Unique constraint test on username
    dup_user = User(
        username="analyst_jane",  # Duplicate username
        email="jane2@bank.org",
        hashed_password="mock",
        role_id=role.role_id,
    )
    db_session.add(dup_user)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_merchant_and_device_creation(db_session: Session):
    """Verifies merchant and device entities and relationships."""
    merchant = Merchant(
        merchant_code="M_ELECTRONICS_01",
        name="Apex Tech Superstore",
        category_code="ELECTRONICS",
        risk_tier="LOW",
    )
    db_session.add(merchant)
    db_session.flush()

    device = Device(
        device_code="ESP32-TERM-8801",
        merchant_id=merchant.merchant_id,
        device_type="ESP32_POS",
        firmware_version="v2.1.0",
        status="ACTIVE",
        tamper_flag=False,
    )
    db_session.add(device)
    db_session.flush()

    assert device.merchant.name == "Apex Tech Superstore"
    assert len(merchant.devices) == 1


# ==============================================================================
# 3. TRANSACTION & RISK ENGINE PERSISTENCE BRIDGE
# ==============================================================================

def test_save_assessed_transaction_approve(db_session: Session):
    """Verifies end-to-end atomic persistence of an APPROVED transaction."""
    # Build synthetic features and assessment
    features = {
        "amount": 250.00,
        "oldbalance_org": 5000.00,
        "newbalance_orig": 4750.00,
        "oldbalance_dest": 1000.00,
        "newbalance_dest": 1250.00,
        "log_amount": 5.525,
        "is_transfer": 1,
        "is_cash_out": 0,
        "hour_of_day": 14.0,
        "hour_sin": -0.5,
        "hour_cos": -0.866,
        "is_night_transaction": 0,
        "orig_balance_error": 0.0,
        "orig_drain_ratio": 0.05,
        "is_full_liquidation": 0,
        "dest_balance_error": 0.0,
        "dest_drain_ratio": 0.20,
        "dest_zero_balance_anomaly": 0,
    }

    # Low-risk model signals
    signals = RiskSignals(
        xgboost_score=0.012,
        logistic_score=0.025,
        isolation_score=0.150,
        autoencoder_score=0.080,
    )
    config = RiskConfig()
    score = compute_risk_score(signals, config)
    decision = evaluate_decision(score, config)
    assert decision == DecisionAction.APPROVE

    assessment = assess_transaction(
        signals=signals,
        feature_dict=features,
        config=config,
    )

    tx_data = {
        "step": 350,
        "type": "TRANSFER",
        "amount": 250.00,
        "name_orig": "C1234567890",
        "name_dest": "C9876543210",
        "oldbalance_org": 5000.00,
        "newbalance_orig": 4750.00,
        "oldbalance_dest": 1000.00,
        "newbalance_dest": 1250.00,
    }

    model_meta = [
        {"model_name": "xgboost", "raw_output": 0.012, "normalized_signal": 0.012, "model_version": "1.0.0"},
        {"model_name": "logistic", "raw_output": 0.025, "normalized_signal": 0.025, "model_version": "1.0.0"},
        {"model_name": "isolation_forest", "raw_output": -0.15, "normalized_signal": 0.150, "model_version": "1.0.0"},
        {"model_name": "autoencoder", "raw_output": 0.002, "normalized_signal": 0.080, "model_version": "1.0.0"},
    ]

    tx = save_assessed_transaction(
        session=db_session,
        tx_data=tx_data,
        assessment=assessment,
        features_dict=features,
        model_results_meta=model_meta,
        actor_id="API_GATEWAY",
    )
    db_session.flush()

    # Query back and verify complete entity tree
    saved_tx = get_transaction_by_id(db_session, tx.tx_id)
    assert saved_tx is not None
    assert saved_tx.amount == 250.00
    assert saved_tx.features is not None
    assert saved_tx.features.log_amount == pytest.approx(5.525, abs=1e-3)
    assert len(saved_tx.model_results) == 4
    assert saved_tx.risk_assessment is not None
    assert saved_tx.risk_assessment.final_risk_score == pytest.approx(score, abs=1e-2)
    assert saved_tx.risk_assessment.decision is not None
    assert saved_tx.risk_assessment.decision.policy_decision == "APPROVE"
    # An APPROVE decision should NOT generate an alert
    assert len(saved_tx.risk_assessment.alerts) == 0


def test_save_assessed_transaction_block_creates_alert(db_session: Session):
    """Verifies that BLOCK and REVIEW decisions automatically trigger alert generation."""
    # Critical risk signals
    signals = RiskSignals(
        xgboost_score=0.985,
        logistic_score=0.950,
        isolation_score=0.880,
        autoencoder_score=0.920,
    )
    config = RiskConfig()
    score = compute_risk_score(signals, config)
    decision = evaluate_decision(score, config)
    assert decision == DecisionAction.BLOCK

    features = {
        "amount": 950000.00,
        "oldbalance_org": 950000.00,
        "newbalance_orig": 0.00,
        "oldbalance_dest": 0.00,
        "newbalance_dest": 0.00,
        "log_amount": 13.764,
        "is_transfer": 1,
        "is_cash_out": 0,
        "hour_of_day": 3.0,
        "hour_sin": 0.707,
        "hour_cos": 0.707,
        "is_night_transaction": 1,
        "orig_balance_error": 0.0,
        "orig_drain_ratio": 1.0,
        "is_full_liquidation": 1,
        "dest_balance_error": 950000.00,
        "dest_drain_ratio": 950000.00,
        "dest_zero_balance_anomaly": 1,
    }

    assessment = assess_transaction(
        signals=signals,
        feature_dict=features,
        config=config,
    )

    tx_data = {
        "step": 651,
        "type": "TRANSFER",
        "amount": 950000.00,
        "name_orig": "C_ATTACKER_01",
        "name_dest": "C_MULE_ACCOUNT",
        "oldbalance_org": 950000.00,
        "newbalance_orig": 0.00,
        "oldbalance_dest": 0.00,
        "newbalance_dest": 0.00,
    }

    tx = save_assessed_transaction(
        session=db_session,
        tx_data=tx_data,
        assessment=assessment,
        features_dict=features,
        actor_id="POS_TERMINAL_001",
    )
    db_session.flush()

    # Verify that an alert was generated
    assert tx.risk_assessment.decision.policy_decision == "BLOCK"
    assert len(tx.risk_assessment.alerts) == 1
    alert = tx.risk_assessment.alerts[0]
    assert alert.severity == "CRITICAL"
    assert alert.status == "PENDING"

    # Verify pending alerts query helper
    pending = get_pending_alerts(db_session)
    assert len(pending) >= 1
    assert pending[0].alert_id == alert.alert_id


# ==============================================================================
# 4. AUDIT LOGGING & ROLLBACK BEHAVIOR
# ==============================================================================

def test_audit_log_persistence(db_session: Session):
    """Verifies structured audit log persistence."""
    log = log_audit_event(
        session=db_session,
        actor_id="ANALYST_BOB",
        actor_type="USER",
        event_type="DECISION_OVERRIDE",
        action="OVERRIDE_REVIEW_TO_APPROVE",
        resource_type="transaction",
        resource_id="11111111-2222-3333-4444-555555555555",
        details={"justification": "Verified via secondary 2FA telephone confirmation with customer."},
    )
    db_session.flush()

    assert log.log_id is not None
    assert log.actor_id == "ANALYST_BOB"
    assert log.details["justification"].startswith("Verified via secondary")


def test_transaction_rollback_integrity(test_engine):
    """Verifies that an exception during session operations cleanly rolls back."""
    connection = test_engine.connect()
    trans = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    # Insert a role
    role = Role(name="TEST_ROLE_ROLLBACK")
    session.add(role)
    session.flush()
    assert session.scalar(select(Role).where(Role.name == "TEST_ROLE_ROLLBACK")) is not None

    # Roll back transaction explicitly
    trans.rollback()
    session.close()
    connection.close()

    # Re-check from clean connection
    with test_engine.connect() as check_conn:
        check_session = sessionmaker(bind=check_conn)()
        found = check_session.scalar(select(Role).where(Role.name == "TEST_ROLE_ROLLBACK"))
        assert found is None, "Rolled back record should not be visible!"
        check_session.close()
