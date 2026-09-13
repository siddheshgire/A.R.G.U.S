"""
A.R.G.U.S. — Common API Response & Health Schemas
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness probe response model."""
    status: str = Field(default="ok", description="Liveness status indicator")
    service: str = Field(default="argus-api", description="Service identifier")
    version: str = Field(default="1.0.0", description="API version")


class ReadinessResponse(BaseModel):
    """Readiness probe response model."""
    status: str = Field(..., description="Overall readiness: 'ready' or 'not_ready'")
    database_connected: bool = Field(..., description="PostgreSQL / SQLite connectivity")
    models_loaded: bool = Field(..., description="Status of ML/DL inference artifact readiness")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Diagnostic readiness details")


class ErrorDetail(BaseModel):
    """Detailed error object."""
    code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable error explanation")
    field: Optional[str] = Field(default=None, description="Request parameter associated with error")


class ErrorResponse(BaseModel):
    """Standardized error envelope."""
    error: ErrorDetail = Field(..., description="Error specifics")
