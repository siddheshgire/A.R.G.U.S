"""
A.R.G.U.S. — Seed Demo Users & Ensure Tables Exist
Creates database schema and default role-based test accounts for demonstration.
"""

import os
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from dotenv import load_dotenv

load_dotenv()

# Default to SQLite local database if DATABASE_URL not explicitly configured
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = f"sqlite:///{(WORKSPACE_ROOT / 'argus.db').as_posix()}"

from database.base import Base
from database.connection import get_engine, reset_engine
from database.models import User, Role
from database.repository import create_user
from backend.security.password import hash_password
from backend.services.user_service import UserService
from sqlalchemy.orm import Session

DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@argus.org",
        "password": "AdminPassword123!",
        "role": "ADMIN",
        "full_name": "System Administrator",
    },
    {
        "username": "analyst",
        "email": "analyst@argus.org",
        "password": "AnalystPassword123!",
        "role": "ANALYST",
        "full_name": "Senior Fraud Analyst",
    },
    {
        "username": "auditor",
        "email": "auditor@argus.org",
        "password": "AuditorPassword123!",
        "role": "AUDITOR",
        "full_name": "Compliance Auditor",
    },
    {
        "username": "user",
        "email": "customer@bank.org",
        "password": "UserPassword123!",
        "role": "USER",
        "full_name": "Demo Customer",
    },
]


def seed():
    print(f"[*] Initializing database at: {os.environ['DATABASE_URL']}")
    reset_engine()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        user_svc = UserService(session)

        # 1. Ensure standard roles exist
        roles = {}
        for role_name in ["USER", "ANALYST", "ADMIN", "AUDITOR"]:
            roles[role_name] = user_svc.ensure_role(role_name)
        session.commit()

        # 2. Ensure demo accounts exist
        for u in DEMO_USERS:
            existing = session.query(User).filter(User.username == u["username"]).first()
            if not existing:
                create_user(
                    session=session,
                    username=u["username"],
                    email=u["email"],
                    hashed_password=hash_password(u["password"]),
                    role_id=roles[u["role"]].role_id,
                )
                print(f"[+] Created user: {u['username']} (Role: {u['role']}, Password: {u['password']})")
            else:
                print(f"[*] User already exists: {u['username']} (Role: {u['role']})")
        session.commit()


    print("\n" + "=" * 60)
    print("DEMO CREDENTIALS READY FOR LOGIN:")
    print("=" * 60)
    for u in DEMO_USERS:
        print(f"Role: {u['role']:<8} | Username: {u['username']:<10} | Password: {u['password']}")
    print("=" * 60)


if __name__ == "__main__":
    seed()
