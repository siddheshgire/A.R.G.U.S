"""
A.R.G.U.S. — Database Schema Initialization
Provides safe, idempotent table creation for development and deployment.
Never drops production data silently.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional
from sqlalchemy import Engine, inspect

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.base import Base
from database.connection import get_engine, get_session_factory
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


def get_existing_tables(engine: Engine) -> List[str]:
    """Inspects engine and returns list of table names present in the database."""
    inspector = inspect(engine)
    return inspector.get_table_names()


def init_db(engine: Optional[Engine] = None, drop_existing: bool = False) -> List[str]:
    """
    Idempotently initializes all database tables registered on Base.metadata.
    
    Parameters
    ----------
    engine : Optional[Engine]
        SQLAlchemy engine (defaults to singleton get_engine()).
    drop_existing : bool
        If True, drops all tables before recreating. DANGEROUS: Use only in test/dev.
        
    Returns
    -------
    List[str]
        List of all tables verified/created in the database.
    """
    eng = engine or get_engine()
    
    if drop_existing:
        print("[!] WARNING: Dropping all existing tables...")
        Base.metadata.drop_all(bind=eng)
        
    print("[*] Creating all registered tables (if not existing)...")
    Base.metadata.create_all(bind=eng)
    
    tables = get_existing_tables(eng)
    return tables


def check_db(engine: Optional[Engine] = None) -> bool:
    """
    Checks database connection and inspects registered tables against existing tables.
    """
    eng = engine or get_engine()
    try:
        with eng.connect() as conn:
            print(f"[+] Successfully connected to database: {eng.url.drivername} at {eng.url.host or 'local'}")
        
        existing = get_existing_tables(eng)
        registered = list(Base.metadata.tables.keys())
        
        print(f"[*] Registered metadata tables ({len(registered)}): {', '.join(sorted(registered))}")
        print(f"[*] Tables present in database ({len(existing)}):   {', '.join(sorted(existing)) if existing else '(none)'}")
        
        missing = set(registered) - set(existing)
        if missing:
            print(f"[-] Missing tables ({len(missing)}): {', '.join(sorted(missing))}")
            return False
        else:
            print("[+] All registered tables are present and verified.")
            return True
    except Exception as e:
        print(f"[-] Database connectivity check failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="A.R.G.U.S. Database Initialization Tool")
    parser.add_argument("--check", action="store_true", help="Check database connectivity and table status")
    parser.add_argument("--init", action="store_true", help="Create all registered tables if they do not exist")
    parser.add_argument(
        "--force-recreate", action="store_true", help="Drop all tables and recreate from scratch (TEST ONLY)"
    )
    args = parser.parse_args()

    if not (args.check or args.init or args.force_recreate):
        parser.print_help()
        sys.exit(0)

    if args.check:
        check_db()

    if args.init:
        tables = init_db(drop_existing=False)
        print(f"[+] Database initialization complete. Active tables: {', '.join(sorted(tables))}")

    if args.force_recreate:
        confirm = input("Are you sure you want to DROP and RECREATE all tables? (yes/no): ")
        if confirm.strip().lower() == "yes":
            tables = init_db(drop_existing=True)
            print(f"[+] Database recreated. Active tables: {', '.join(sorted(tables))}")
        else:
            print("Operation aborted.")


if __name__ == "__main__":
    main()
