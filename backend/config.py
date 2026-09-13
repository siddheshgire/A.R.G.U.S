"""
A.R.G.U.S. — API Configuration & Settings
Manages application-wide parameters, environment loading, and security configurations.
"""

from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """Configuration settings for the FastAPI backend gateway."""
    
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "A.R.G.U.S. — Risk Assessment & Fraud Detection Gateway"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Path to trained model artifacts
    MODELS_DIR: str = "models"
    
    # CORS Configuration (Default allows local frontend/dev servers)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8008",
        "http://127.0.0.1:8008",
    ]

    # JWT Authentication & Cryptography
    JWT_SECRET_KEY: str = "argus_default_secure_secret_key_change_in_production_2026_aiml_pbl_xyz"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Rate Limiting (In-Memory sliding window per client IP)
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v  # type: ignore[return-value]
        raise ValueError(v)

    @property
    def resolved_models_dir(self) -> Path:
        """Returns the resolved Path object to the models directory."""
        p = Path(self.MODELS_DIR)
        if not p.is_absolute():
            # Workspace root relative
            p = Path(__file__).resolve().parent.parent / self.MODELS_DIR
        return p

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = APISettings()
