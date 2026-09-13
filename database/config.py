"""
A.R.G.U.S. — Database Layer Configuration
Centralized configuration management for PostgreSQL connectivity and pooling.
Reads strictly from environment variables without hardcoded credentials.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    """
    Database configuration settings for PostgreSQL persistence layer.
    """
    database_url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    echo: bool = False

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """
        Builds DatabaseConfig from environment variables.
        Falls back to individual components if DATABASE_URL is not directly set.
        """
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            # Keep the checked-in demo runnable without requiring a local PostgreSQL
            # server. Deployments should always provide DATABASE_URL explicitly.
            sqlite_path = os.getenv("SQLITE_PATH", "argus.db")
            if not os.path.isabs(sqlite_path):
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                sqlite_path = os.path.join(project_root, sqlite_path)
            db_url = f"sqlite:///{sqlite_path}"

        pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))
        echo = os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes")

        return cls(
            database_url=db_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=echo,
        )
