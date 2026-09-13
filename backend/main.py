"""
A.R.G.U.S. — FastAPI Application Entry Point
Automated Risk Assessment & Anomaly Detection System
AI-Based Real-Time Fraud Detection and Transaction Risk Monitoring System
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.services.model_service import ModelManager
from backend.api import api_router
from backend.security import SecurityHeadersMiddleware, RateLimitMiddleware
from database.connection import reset_engine, get_engine
from database.base import Base
from database.models import Role, User
from backend.security.password import hash_password
from sqlalchemy.orm import Session

logger = logging.getLogger("argus.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Event Handler:
    - Startup: Loads pretrained ML/DL models and scaler once into memory.
    - Shutdown: Closes database connection pools and frees runtime resources.
    """
    logger.info("[*] A.R.G.U.S. API Gateway starting up...")
    logger.info(f"[*] Loading pretrained model artifacts from: {settings.resolved_models_dir}")

    # Initialize the schema before dependencies receive their first request.
    # This makes the local SQLite demo self-starting while preserving explicit
    # DATABASE_URL configuration for deployed PostgreSQL environments.
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # The repository includes demo credentials for local evaluation. Seed them
    # only when the active database is SQLite and contains no users; production
    # databases are never populated implicitly.
    if engine.url.drivername.startswith("sqlite"):
        with Session(engine) as session:
            if session.query(User).count() == 0:
                role_names = ["USER", "ANALYST", "ADMIN", "AUDITOR"]
                roles = {}
                for name in role_names:
                    role = session.query(Role).filter(Role.name == name).one_or_none()
                    if role is None:
                        role = Role(name=name, description=f"{name} access role")
                        session.add(role)
                    roles[name] = role
                session.flush()
                session.add_all([
                    User(username="admin", email="admin@argus.org", hashed_password=hash_password("AdminPassword123!"), role=roles["ADMIN"]),
                    User(username="analyst", email="analyst@argus.org", hashed_password=hash_password("AnalystPassword123!"), role=roles["ANALYST"]),
                ])
                session.commit()
                logger.info("[+] Seeded local demo users: admin and analyst")

    # Initialize and load model artifacts once
    model_manager = ModelManager(models_dir=settings.resolved_models_dir)
    try:
        model_manager.load_artifacts()
        logger.info("[+] Successfully loaded all 4 ML/DL models and feature scaler into memory.")
    except Exception as e:
        logger.error(f"[-] Failed to load model artifacts: {e}", exc_info=True)
        raise RuntimeError(f"Startup failed due to model artifact error: {e}") from e

    app.state.model_manager = model_manager

    yield

    logger.info("[*] A.R.G.U.S. API Gateway shutting down. Disposing database engine...")
    reset_engine()
    logger.info("[+] Resources cleanly disposed.")


def create_application() -> FastAPI:
    """Factory function initializing the configured FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "### A.R.G.U.S. — Automated Risk Assessment & Anomaly Detection System\n\n"
            "**Academic B.Tech AIML Semester Project (2026–27 Odd Semester)**\n"
            "*AI-Based Real-Time Fraud Detection and Transaction Risk Monitoring System*\n\n"
            "#### Operational Capabilities:\n"
            "- **18-Feature Feature Engineering**: Real-time extraction with zero leakage.\n"
            "- **Multi-Model Inference**: Evaluates Supervised XGBoost, Logistic Regression, "
            "Unsupervised Isolation Forest, and Deep Autoencoder reconstruction loss.\n"
            "- **Ensemble Risk Engine**: Aggregates signals into continuous 0-100 Risk Score.\n"
            "- **Tri-State Operational Decisions**: `APPROVE` (<40), `REVIEW` (40-69), `BLOCK` (>=70).\n"
            "- **PostgreSQL 3NF Persistence**: Complete audit trail, features, assessments, and analyst alerts.\n\n"
            "**Notice:** This API processes SIMULATED transactions. It does NOT integrate with "
            "live banking rails, Google Pay, UPI, or financial institutions."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Security Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # In-Memory Sliding Window Rate Limiting Middleware
    app.add_middleware(RateLimitMiddleware)

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Unhandled Exception Handler (Prevents stack trace leaks & credentials leakage)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )
        logger.error(f"Unhandled exception during {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred while processing the transaction.",
                }
            },
        )

    # Include Routes
    app.include_router(api_router)

    return app


app = create_application()
