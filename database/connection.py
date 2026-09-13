"""
A.R.G.U.S. — Database Connection & Session Management
Provides thread-safe engine initialization, session factories, and context managers
with automatic transaction rollback and resource cleanup.
"""

from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from .config import DatabaseConfig

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker[Session]] = None


def get_engine(config: Optional[DatabaseConfig] = None) -> Engine:
    """
    Returns or initializes the singleton SQLAlchemy Engine.
    Handles dialect-specific pooling (PostgreSQL vs SQLite).
    """
    global _engine, _session_factory
    if _engine is not None:
        return _engine

    cfg = config or DatabaseConfig.from_env()

    # Configure pooling based on dialect
    if cfg.database_url.startswith("sqlite"):
        engine_kwargs = {
            "echo": cfg.echo,
        }
    else:
        engine_kwargs = {
            "pool_size": cfg.pool_size,
            "max_overflow": cfg.max_overflow,
            "pool_timeout": cfg.pool_timeout,
            "pool_recycle": cfg.pool_recycle,
            "echo": cfg.echo,
        }

    _engine = create_engine(cfg.database_url, **engine_kwargs)
    _session_factory = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    return _engine


def get_session_factory(engine: Optional[Engine] = None) -> sessionmaker[Session]:
    """
    Returns the sessionmaker instance bound to the provided or default engine.
    """
    global _session_factory
    if _session_factory is not None and engine is None:
        return _session_factory

    eng = engine or get_engine()
    _session_factory = sessionmaker(
        bind=eng,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    return _session_factory


@contextmanager
def get_db_session(session_factory: Optional[sessionmaker[Session]] = None) -> Generator[Session, None, None]:
    """
    Context manager providing a transactional SQLAlchemy Session.
    Automatically commits on successful block execution, rolls back on exception,
    and reliably closes the session upon exit.
    """
    factory = session_factory or get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """
    Disposes active engine and resets session factory for testing or reconfiguration.
    """
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
        _engine = None
    _session_factory = None
