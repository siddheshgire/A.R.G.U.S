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
            user = os.getenv("DB_USER", "argus_user")
            password = os.getenv("DB_PASSWORD", "change_this_password")
            host = os.getenv("DB_HOST", "localhost")
            port = os.getenv("DB_PORT", "5432")
            name = os.getenv("DB_NAME", "argus_db")
            db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

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
