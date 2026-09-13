"""
A.R.G.U.S. — Liveness & Readiness Health Probes
Provides monitoring endpoints for orchestrators, containers, and deployment health checks.
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.schemas.common import HealthResponse, ReadinessResponse
from backend.dependencies.database import get_db
from backend.services.model_service import ModelManager

router = APIRouter(tags=["System Health & Diagnostics"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Liveness Probe",
    description="Returns basic operational health status indicating the API gateway process is alive.",
)
def get_health() -> HealthResponse:
    return HealthResponse(status="ok", service="argus-api", version="1.0.0")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="System Readiness Probe",
    description=(
        "Verifies that core dependencies (PostgreSQL database connectivity and "
        "pretrained ML/DL model artifacts) are initialized and ready to serve live traffic."
    ),
)
def get_readiness(
    request: Request,
    db: Session = Depends(get_db),
) -> ReadinessResponse:
    # 1. Check Model Artifacts
    model_manager: ModelManager = getattr(request.app.state, "model_manager", None)
    models_ready = model_manager is not None and model_manager.is_ready

    # 2. Check Database Connectivity
    db_ready = False
    try:
        db.execute(text("SELECT 1"))
        db_ready = True
    except Exception:
        db_ready = False

    overall_ready = models_ready and db_ready
    status_str = "ready" if overall_ready else "not_ready"

    return ReadinessResponse(
        status=status_str,
        database_connected=db_ready,
        models_loaded=models_ready,
        details={
            "models_dir": str(model_manager.models_dir) if model_manager else None,
            "architecture": "4-model ensemble (XGBoost, LR, IsolationForest, Autoencoder)",
        },
    )
