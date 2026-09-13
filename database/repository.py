"""
A.R.G.U.S. — Database Repository & Persistence Bridge
Provides clean service/repository operations to persist evaluated transactions,
feature vectors, model signals, risk assessments, decisions, alerts, and audit events.
"""

import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from .models import (
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
from ml_engine.risk.assessment import RiskAssessment
from ml_engine.risk.decision import DecisionAction


def save_assessed_transaction(
    session: Session,
    tx_data: Dict[str, Any],
    assessment: RiskAssessment,
    features_dict: Optional[Dict[str, Any]] = None,
    model_results_meta: Optional[List[Dict[str, Any]]] = None,
    merchant_id: Optional[uuid.UUID] = None,
    device_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    actor_id: Optional[str] = None,
    client_tx_id: Optional[str] = None,
) -> Transaction:
    """
    Persists a complete transaction evaluation lifecycle in an atomic unit of work:
    1. Transaction record
    2. 18-feature vector (if provided)
    3. Model results (if provided)
    4. Risk assessment record
    5. Operational decision record
    6. Alert record (automatically generated if policy is REVIEW or BLOCK)
    7. Structured audit log entry

    Parameters
    ----------
    session : Session
        Active SQLAlchemy session.
    tx_data : Dict[str, Any]
        Raw transaction attributes (step, type, amount, name_orig, name_dest, balances).
    assessment : RiskAssessment
        Domain entity output from ml_engine.risk.assess_transaction().
    features_dict : Optional[Dict[str, Any]]
        Dictionary of exact 18 engineered features.
    model_results_meta : Optional[List[Dict[str, Any]]]
        List of dicts specifying model_name, raw_output, normalized_signal, model_version, inference_time_ms.
    merchant_id : Optional[uuid.UUID]
        Foreign key reference to merchants table.
    device_id : Optional[uuid.UUID]
        Foreign key reference to devices table.
    user_id : Optional[uuid.UUID]
        Foreign key reference to users table (submitting user).
    actor_id : Optional[str]
        Identifier of the actor or system initiating assessment.

    Returns
    -------
    Transaction
        Fully populated Transaction entity with loaded relationships.
    """
    tx_id = uuid.uuid4()
    if assessment.transaction_id:
        try:
            tx_id = uuid.UUID(str(assessment.transaction_id))
        except (ValueError, AttributeError):
            pass

    # 1. Create Transaction
    tx = Transaction(
        tx_id=tx_id,
        step=int(tx_data["step"]),
        type=str(tx_data["type"]),
        amount=float(tx_data["amount"]),
        name_orig=str(tx_data.get("name_orig", tx_data.get("nameOrig", "UNKNOWN"))),
        name_dest=str(tx_data.get("name_dest", tx_data.get("nameDest", "UNKNOWN"))),
        oldbalance_org=float(tx_data.get("oldbalance_org", tx_data.get("oldbalanceOrg", 0.0))),
        newbalance_orig=float(tx_data.get("newbalance_orig", tx_data.get("newbalanceOrig", 0.0))),
        oldbalance_dest=float(tx_data.get("oldbalance_dest", tx_data.get("oldbalanceDest", 0.0))),
        newbalance_dest=float(tx_data.get("newbalance_dest", tx_data.get("newbalanceDest", 0.0))),
        merchant_id=merchant_id,
        device_id=device_id,
        user_id=user_id,
        client_tx_id=client_tx_id,
    )
    session.add(tx)

    # 2. Create TransactionFeatures (if provided)
    if features_dict:
        feat = TransactionFeatures(
            tx_id=tx.tx_id,
            amount=float(features_dict["amount"]),
            oldbalance_org=float(features_dict.get("oldbalance_org", features_dict.get("oldbalanceOrg", 0.0))),
            newbalance_orig=float(features_dict.get("newbalance_orig", features_dict.get("newbalanceOrig", 0.0))),
            oldbalance_dest=float(features_dict.get("oldbalance_dest", features_dict.get("oldbalanceDest", 0.0))),
            newbalance_dest=float(features_dict.get("newbalance_dest", features_dict.get("newbalanceDest", 0.0))),
            log_amount=float(features_dict["log_amount"]),
            is_transfer=int(features_dict["is_transfer"]),
            is_cash_out=int(features_dict["is_cash_out"]),
            hour_of_day=float(features_dict["hour_of_day"]),
            hour_sin=float(features_dict["hour_sin"]),
            hour_cos=float(features_dict["hour_cos"]),
            is_night_transaction=int(features_dict["is_night_transaction"]),
            orig_balance_error=float(features_dict["orig_balance_error"]),
            orig_drain_ratio=float(features_dict["orig_drain_ratio"]),
            is_full_liquidation=int(features_dict["is_full_liquidation"]),
            dest_balance_error=float(features_dict["dest_balance_error"]),
            dest_drain_ratio=float(features_dict["dest_drain_ratio"]),
            dest_zero_balance_anomaly=int(features_dict["dest_zero_balance_anomaly"]),
        )
        session.add(feat)

    # 3. Create ModelResults (if provided)
    if model_results_meta:
        for m_meta in model_results_meta:
            mr = ModelResult(
                tx_id=tx.tx_id,
                model_name=str(m_meta["model_name"]),
                raw_output=float(m_meta["raw_output"]),
                normalized_signal=float(m_meta["normalized_signal"]),
                model_version=str(m_meta.get("model_version", "1.0.0")),
                inference_time_ms=m_meta.get("inference_time_ms"),
            )
            session.add(mr)

    # 4. Create RiskAssessmentRecord
    signals_dict = assessment.signals.to_dict()
    ra = RiskAssessmentRecord(
        tx_id=tx.tx_id,
        xgboost_signal=float(signals_dict["xgboost_score"]),
        logistic_signal=float(signals_dict["logistic_score"]),
        isolation_signal=float(signals_dict["isolation_score"]),
        autoencoder_signal=float(signals_dict["autoencoder_score"]),
        final_risk_score=float(assessment.risk_score),
        engine_version=assessment.engine_version,
        evaluated_by=assessment.evaluated_by,
    )
    session.add(ra)
    session.flush()  # Populates ra.assessment_id

    # 5. Create DecisionRecord
    dec = DecisionRecord(
        assessment_id=ra.assessment_id,
        policy_decision=assessment.decision.value,
        reasons=list(assessment.reasons),
    )
    session.add(dec)

    # 6. Generate Alert if action requires analyst attention (REVIEW or BLOCK)
    if assessment.decision in (DecisionAction.REVIEW, DecisionAction.BLOCK):
        severity = "CRITICAL" if assessment.decision == DecisionAction.BLOCK else "HIGH"
        alert = Alert(
            assessment_id=ra.assessment_id,
            severity=severity,
            status="PENDING",
            notes=f"Automated {assessment.decision.value} alert generated with Risk Score {assessment.risk_score:.2f}.",
        )
        session.add(alert)

    # 7. Create AuditLog entry
    audit = AuditLog(
        actor_id=actor_id or "SYSTEM_RISK_ENGINE",
        actor_type="SYSTEM",
        event_type="TRANSACTION_ASSESSED",
        action=f"RENDER_{assessment.decision.value}",
        resource_type="transaction",
        resource_id=str(tx.tx_id),
        details={
            "risk_score": assessment.risk_score,
            "decision": assessment.decision.value,
            "engine_version": assessment.engine_version,
            "evaluated_by": assessment.evaluated_by,
        },
    )
    session.add(audit)

    return tx


def get_transaction_by_id(session: Session, tx_id: uuid.UUID) -> Optional[Transaction]:
    """Queries transaction by primary key."""
    return session.get(Transaction, tx_id)


def get_pending_alerts(session: Session, limit: int = 50) -> List[Alert]:
    """Retrieves pending alerts for analyst investigation queue."""
    stmt = select(Alert).where(Alert.status == "PENDING").order_by(Alert.created_at.desc()).limit(limit)
    return list(session.scalars(stmt).all())


def log_audit_event(
    session: Session,
    event_type: str,
    action: str,
    resource_type: str,
    actor_id: Optional[str] = None,
    actor_type: str = "SYSTEM",
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Helper to record an arbitrary system or security audit event."""
    log = AuditLog(
        actor_id=actor_id,
        actor_type=actor_type,
        event_type=event_type,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )
    session.add(log)
    return log


def get_user_by_id(session: Session, user_id: uuid.UUID) -> Optional[User]:
    """Retrieves user by primary key UUID."""
    return session.get(User, user_id)


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """Retrieves user by unique username."""
    stmt = select(User).where(User.username == username)
    return session.scalars(stmt).first()


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """Retrieves user by unique email."""
    stmt = select(User).where(User.email == email)
    return session.scalars(stmt).first()


def get_role_by_name(session: Session, name: str) -> Optional[Role]:
    """Retrieves operational role by name (USER, ANALYST, ADMIN, AUDITOR)."""
    stmt = select(Role).where(Role.name == name)
    return session.scalars(stmt).first()


def create_role_if_not_exists(session: Session, name: str, description: Optional[str] = None) -> Role:
    """Idempotently gets or creates a system role."""
    role = get_role_by_name(session, name)
    if role is None:
        role = Role(
            role_id=uuid.uuid4(),
            name=name,
            description=description or f"Operational role for {name}",
        )
        session.add(role)
        session.flush()
    return role


def create_user(
    session: Session,
    username: str,
    email: str,
    hashed_password: str,
    role_id: uuid.UUID,
    is_active: bool = True,
) -> User:
    """Creates a new user record with hashed password."""
    user = User(
        user_id=uuid.uuid4(),
        username=username,
        email=email,
        hashed_password=hashed_password,
        role_id=role_id,
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user


def get_audit_logs(
    session: Session,
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
) -> List[AuditLog]:
    """Queries security and operational audit trail records."""
    stmt = select(AuditLog)
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    return list(session.scalars(stmt).all())


def get_users_list(session: Session, limit: int = 100, offset: int = 0) -> List[User]:
    """Retrieves paginated users list."""
    stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    return list(session.scalars(stmt).all())


def get_device_by_code(session: Session, device_code: str) -> Optional[Device]:
    """Retrieves terminal by unique device code string."""
    stmt = select(Device).where(Device.device_code == device_code)
    return session.scalars(stmt).first()


def get_device_by_id(session: Session, device_id: uuid.UUID) -> Optional[Device]:
    """Retrieves terminal by primary key UUID."""
    return session.get(Device, device_id)


def create_device(
    session: Session,
    device_code: str,
    api_key_hash: Optional[str] = None,
    merchant_id: Optional[uuid.UUID] = None,
    device_type: str = "POS_TERMINAL",
    firmware_version: Optional[str] = "v1.0.0",
    status: str = "ACTIVE",
    tamper_flag: bool = False,
) -> Device:
    """Creates or provisions an edge terminal record."""
    device = Device(
        device_id=uuid.uuid4(),
        device_code=device_code,
        api_key_hash=api_key_hash,
        merchant_id=merchant_id,
        device_type=device_type,
        firmware_version=firmware_version,
        status=status,
        tamper_flag=tamper_flag,
    )
    session.add(device)
    session.flush()
    return device


def update_device_heartbeat(
    session: Session,
    device: Device,
    firmware_version: Optional[str] = None,
    tamper_flag: Optional[bool] = None,
) -> Device:
    """Updates last_seen_at timestamp and telemetry status upon receiving heartbeat."""
    from datetime import datetime, timezone
    device.last_seen_at = datetime.now(timezone.utc)
    if firmware_version is not None:
        device.firmware_version = firmware_version
    if tamper_flag is not None:
        device.tamper_flag = tamper_flag
        if tamper_flag:
            device.status = "TAMPERED"
    session.flush()
    return device


def check_duplicate_device_tx(
    session: Session,
    device_id: uuid.UUID,
    client_tx_id: str,
) -> bool:
    """Checks if a client_tx_id from the specified device already exists."""
    stmt = select(Transaction.tx_id).where(
        Transaction.device_id == device_id,
        Transaction.client_tx_id == client_tx_id,
    )
    return session.scalars(stmt).first() is not None


