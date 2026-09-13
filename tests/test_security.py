"""
A.R.G.U.S. — Security & OOP Application Layer Test Suite (Milestone 7)
Verifies bcrypt password hashing, JWT authentication, RBAC authorization,
object-level IDOR protection, security audit logging, rate limiting, and security headers.
"""

import uuid
import time
from datetime import timedelta
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from database.base import Base
from database.models import User, Role, Transaction, AuditLog
from backend.main import app
from backend.dependencies.database import get_db
from backend.security.password import hash_password, verify_password, validate_password_strength
from backend.security.jwt import create_access_token, decode_access_token
from backend.security.middleware import rate_limiter
from backend.services.user_service import UserService


@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped in-memory database using StaticPool."""
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

    # Initialize standard roles
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
    rate_limiter.client_requests.clear()

    with TestClient(app) as test_client:
        yield test_client

    rate_limiter.client_requests.clear()
    app.dependency_overrides.clear()


# ==============================================================================
# 1. Cryptography & Password Hashing Tests
# ==============================================================================

def test_password_hashing_and_salting():
    """Verifies bcrypt generates distinct salts for identical plaintext passwords."""
    raw_pass = "SecurePass123!"
    hash1 = hash_password(raw_pass)
    hash2 = hash_password(raw_pass)

    assert hash1 != hash2, "bcrypt must produce distinct salts for each hash operation"
    assert verify_password(raw_pass, hash1) is True
    assert verify_password(raw_pass, hash2) is True
    assert verify_password("WrongPassword!", hash1) is False


def test_password_complexity_validation():
    """Verifies minimum complexity enforcement."""
    with pytest.raises(ValueError, match="at least 8 characters"):
        validate_password_strength("short")

    with pytest.raises(ValueError, match="cannot exceed 128"):
        validate_password_strength("a" * 130)

    # Valid
    validate_password_strength("ValidPassword123")


# ==============================================================================
# 2. JWT Token Issuance & Verification Tests
# ==============================================================================

def test_jwt_issuance_and_decoding():
    """Verifies claims encoding and decoding."""
    claims = {"sub": "analyst_sarah", "role": "ANALYST", "user_id": str(uuid.uuid4())}
    token = create_access_token(claims)
    decoded = decode_access_token(token)

    assert decoded["sub"] == "analyst_sarah"
    assert decoded["role"] == "ANALYST"
    assert "exp" in decoded
    assert "iat" in decoded


def test_jwt_expired_token_rejected():
    """Verifies expired tokens are rejected with HTTP 401."""
    claims = {"sub": "test_user"}
    expired_token = create_access_token(claims, expires_delta=timedelta(seconds=-10))

    with pytest.raises(Exception) as exc_info:
        decode_access_token(expired_token)
    assert "expired" in str(exc_info.value).lower()


# ==============================================================================
# 3. Registration & Authentication Workflow Tests
# ==============================================================================

def test_user_registration_success(client: TestClient, test_engine):
    """Verifies user registration hashes password and records audit event."""
    payload = {
        "username": "investigator_john",
        "email": "john@argus-security.org",
        "password": "StrongPassword2026!",
        "role": "USER",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "investigator_john"
    assert data["email"] == "john@argus-security.org"
    assert data["role"] == "USER"
    assert "password" not in data
    assert "hashed_password" not in data

    # Verify password in DB is hashed, not plaintext
    with Session(test_engine) as session:
        user = session.scalars(select(User).where(User.username == "investigator_john")).first()
        assert user is not None
        assert user.hashed_password != "StrongPassword2026!"
        assert verify_password("StrongPassword2026!", user.hashed_password) is True

        # Check audit log
        log = session.scalars(select(AuditLog).where(AuditLog.actor_id == "investigator_john")).first()
        assert log is not None
        assert log.event_type == "AUTH_USER_REGISTERED"


def test_duplicate_user_registration_rejected(client: TestClient):
    """Verifies duplicate username and email registrations return HTTP 409."""
    payload = {
        "username": "unique_agent",
        "email": "agent@argus.org",
        "password": "Password123!",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Duplicate username
    res_dup_user = client.post("/api/v1/auth/register", json={
        "username": "unique_agent",
        "email": "different@argus.org",
        "password": "Password123!",
    })
    assert res_dup_user.status_code == 409
    assert "already registered" in res_dup_user.json()["detail"]

    # Duplicate email
    res_dup_email = client.post("/api/v1/auth/register", json={
        "username": "other_agent",
        "email": "agent@argus.org",
        "password": "Password123!",
    })
    assert res_dup_email.status_code == 409
    assert "already registered" in res_dup_email.json()["detail"]


def test_user_login_success_and_audit(client: TestClient, test_engine):
    """Verifies login succeeds, issues JWT token, and logs success audit."""
    # Register
    client.post("/api/v1/auth/register", json={
        "username": "analyst_bob",
        "email": "bob@argus.org",
        "password": "SecretPassword123!",
        "role": "ANALYST",
    })

    # Login
    login_res = client.post("/api/v1/auth/login", json={
        "username": "analyst_bob",
        "password": "SecretPassword123!",
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["username"] == "analyst_bob"
    assert token_data["role"] == "ANALYST"

    # Verify audit log
    with Session(test_engine) as session:
        log = session.scalars(
            select(AuditLog)
            .where(AuditLog.actor_id == "analyst_bob")
            .where(AuditLog.event_type == "AUTH_LOGIN_SUCCESS")
        ).first()
        assert log is not None


def test_user_login_invalid_password_fails(client: TestClient, test_engine):
    """Verifies incorrect password returns HTTP 401 and logs failure."""
    client.post("/api/v1/auth/register", json={
        "username": "user_charlie",
        "email": "charlie@argus.org",
        "password": "ValidPassword999!",
    })

    login_res = client.post("/api/v1/auth/login", json={
        "username": "user_charlie",
        "password": "WrongPassword!",
    })
    assert login_res.status_code == 401
    assert "Invalid username or password" in login_res.json()["detail"]

    # Verify failure audit log
    with Session(test_engine) as session:
        log = session.scalars(
            select(AuditLog)
            .where(AuditLog.actor_id == "user_charlie")
            .where(AuditLog.event_type == "AUTH_LOGIN_FAILURE")
        ).first()
        assert log is not None


def test_get_me_protected_endpoint(client: TestClient):
    """Verifies /api/v1/auth/me resolves current user profile from bearer token."""
    client.post("/api/v1/auth/register", json={
        "username": "profile_tester",
        "email": "profile@argus.org",
        "password": "Password123!",
    })
    token = client.post("/api/v1/auth/login", json={
        "username": "profile_tester",
        "password": "Password123!",
    }).json()["access_token"]

    # Call with valid token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "profile_tester"

    # Call without token
    no_auth_res = client.get("/api/v1/auth/me")
    assert no_auth_res.status_code == 401


# ==============================================================================
# 4. Role-Based Access Control (RBAC) Tests
# ==============================================================================

def test_admin_endpoint_restricted_from_normal_user(client: TestClient):
    """Verifies normal USER cannot access /api/v1/admin/audit-logs (HTTP 403)."""
    # Register normal USER
    client.post("/api/v1/auth/register", json={
        "username": "regular_user",
        "email": "user@argus.org",
        "password": "Password123!",
        "role": "USER",
    })
    user_token = client.post("/api/v1/auth/login", json={
        "username": "regular_user",
        "password": "Password123!",
    }).json()["access_token"]

    # Attempt to access admin audit logs
    headers = {"Authorization": f"Bearer {user_token}"}
    res = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


def test_admin_endpoint_accessible_by_admin(client: TestClient):
    """Verifies ADMIN role can access /api/v1/admin/audit-logs."""
    client.post("/api/v1/auth/register", json={
        "username": "super_admin",
        "email": "admin@argus.org",
        "password": "AdminPassword123!",
        "role": "ADMIN",
    })
    admin_token = client.post("/api/v1/auth/login", json={
        "username": "super_admin",
        "password": "AdminPassword123!",
    }).json()["access_token"]

    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ==============================================================================
# 5. Object-Level Authorization (IDOR Defense) Tests
# ==============================================================================

def test_object_level_authorization_prevents_idor(client: TestClient):
    """
    Verifies IDOR Defense: User A creates a transaction.
    User B attempts to retrieve User A's transaction using tx_id -> HTTP 403 Forbidden.
    User A can retrieve their own transaction -> HTTP 200.
    ANALYST and ADMIN can retrieve User A's transaction -> HTTP 200.
    """
    # 1. Register User A and User B
    client.post("/api/v1/auth/register", json={
        "username": "customer_alice",
        "email": "alice@bank.org",
        "password": "PasswordAlice123!",
        "role": "USER",
    })
    token_alice = client.post("/api/v1/auth/login", json={
        "username": "customer_alice",
        "password": "PasswordAlice123!",
    }).json()["access_token"]

    client.post("/api/v1/auth/register", json={
        "username": "customer_mallory",
        "email": "mallory@bank.org",
        "password": "PasswordMallory123!",
        "role": "USER",
    })
    token_mallory = client.post("/api/v1/auth/login", json={
        "username": "customer_mallory",
        "password": "PasswordMallory123!",
    }).json()["access_token"]

    # 2. Register Analyst
    client.post("/api/v1/auth/register", json={
        "username": "fraud_analyst",
        "email": "analyst@bank.org",
        "password": "PasswordAnalyst123!",
        "role": "ANALYST",
    })
    token_analyst = client.post("/api/v1/auth/login", json={
        "username": "fraud_analyst",
        "password": "PasswordAnalyst123!",
    }).json()["access_token"]

    # 3. Alice submits a transaction with her bearer token
    payload = {
        "step": 650,
        "type": "TRANSFER",
        "amount": 200.0,
        "name_orig": "customer_alice",
        "name_dest": "C888888",
        "oldbalance_org": 2000.0,
        "newbalance_orig": 1800.0,
        "oldbalance_dest": 100.0,
        "newbalance_dest": 300.0,
    }
    assess_res = client.post(
        "/api/v1/transactions/assess",
        json=payload,
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    assert assess_res.status_code == 200
    tx_id = assess_res.json()["transaction_id"]

    # 4. Mallory (User B) tries to fetch Alice's transaction -> 403 Forbidden!
    mallory_res = client.get(
        f"/api/v1/transactions/{tx_id}",
        headers={"Authorization": f"Bearer {token_mallory}"},
    )
    assert mallory_res.status_code == 403
    assert "permission" in mallory_res.json()["detail"].lower()

    # 5. Unauthenticated request to Alice's private transaction -> 401 Unauthorized!
    anon_res = client.get(f"/api/v1/transactions/{tx_id}")
    assert anon_res.status_code == 401

    # 6. Alice fetches her own transaction -> 200 OK!
    alice_res = client.get(
        f"/api/v1/transactions/{tx_id}",
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    assert alice_res.status_code == 200
    assert alice_res.json()["tx_id"] == tx_id

    # 7. Analyst fetches Alice's transaction for monitoring -> 200 OK!
    analyst_res = client.get(
        f"/api/v1/transactions/{tx_id}",
        headers={"Authorization": f"Bearer {token_analyst}"},
    )
    assert analyst_res.status_code == 200
    assert analyst_res.json()["tx_id"] == tx_id


# ==============================================================================
# 6. Security Headers & Rate Limiting Tests
# ==============================================================================

def test_security_headers_present(client: TestClient):
    """Verifies standard defensive HTTP headers are attached to responses."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin" in response.headers.get("Referrer-Policy", "")


def test_rate_limiter_allows_and_blocks():
    """Verifies sliding window rate limiter blocks excessive calls."""
    # Test rate_limiter directly to avoid polluting test suite
    test_ip = "192.168.100.100"
    rate_limiter.client_requests[test_ip] = []

    # Should allow requests within limit
    for _ in range(rate_limiter.requests_per_window):
        assert rate_limiter.is_allowed(test_ip) is True

    # Next request exceeds limit
    assert rate_limiter.is_allowed(test_ip) is False


# ==============================================================================
# 7. Anti-Leakage & Modeling Subspace Integrity (M6 Compatibility)
# ==============================================================================

def test_anti_leakage_guards_remain_intact(client: TestClient):
    """Verifies isFraud and isFlaggedFraud are still rejected with HTTP 422."""
    payload = {
        "step": 646,
        "type": "TRANSFER",
        "amount": 100.0,
        "name_orig": "C1",
        "name_dest": "C2",
        "oldbalance_org": 1000.0,
        "newbalance_orig": 900.0,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 100.0,
        "isFraud": 1,
    }
    res = client.post("/api/v1/transactions/assess", json=payload)
    assert res.status_code == 422
    assert "strictly forbidden" in res.text


def test_unsupported_transaction_types_remain_rejected(client: TestClient):
    """Verifies PAYMENT, CASH_IN, and DEBIT continue returning controlled HTTP 422."""
    payload = {
        "step": 646,
        "type": "PAYMENT",
        "amount": 100.0,
        "name_orig": "C1",
        "name_dest": "C2",
        "oldbalance_org": 1000.0,
        "newbalance_orig": 900.0,
        "oldbalance_dest": 0.0,
        "newbalance_dest": 100.0,
    }
    res = client.post("/api/v1/transactions/assess", json=payload)
    assert res.status_code == 422
    assert "not currently supported for ML risk assessment" in res.json()["detail"]
