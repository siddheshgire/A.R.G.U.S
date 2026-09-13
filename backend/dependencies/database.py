"""
A.R.G.U.S. — Database Session Dependency
Provides transactional database sessions for FastAPI route handlers.
"""

from typing import Generator
from sqlalchemy.orm import Session
from database.connection import get_db_session


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a transactional SQLAlchemy session.
    Commits on completion, rolls back on exception, and automatically closes the connection.
    """
    with get_db_session() as session:
        yield session
