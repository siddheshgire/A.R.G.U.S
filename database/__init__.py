"""
A.R.G.U.S. — Relational Database Layer (PostgreSQL / SQLAlchemy 2.0)
Provides 3NF normalized persistence for transactions, features, models, risk scores, decisions, alerts, and audit logs.
"""

from .base import Base
from .config import DatabaseConfig
from .connection import get_engine, get_session_factory, get_db_session, reset_engine
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
from .repository import (
    save_assessed_transaction,
    get_transaction_by_id,
    get_pending_alerts,
    log_audit_event,
)
from .init_db import init_db, check_db

__all__ = [
    "Base",
    "DatabaseConfig",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "reset_engine",
    "Role",
    "User",
    "Merchant",
    "Device",
    "Transaction",
    "TransactionFeatures",
    "ModelResult",
    "RiskAssessmentRecord",
    "DecisionRecord",
    "Alert",
    "AuditLog",
    "save_assessed_transaction",
    "get_transaction_by_id",
    "get_pending_alerts",
    "log_audit_event",
    "init_db",
    "check_db",
]
