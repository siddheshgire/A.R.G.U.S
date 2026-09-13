"""
A.R.G.U.S. — Model Manager & Service Dependencies
Provides preloaded ML/DL models and transaction service instances to routes.
"""

from fastapi import Request, Depends
from backend.services.model_service import ModelManager
from backend.services.transaction_service import TransactionService


def get_model_manager(request: Request) -> ModelManager:
    """Retrieves the preloaded singleton ModelManager from FastAPI application state."""
    manager: ModelManager = getattr(request.app.state, "model_manager", None)
    if manager is None or not manager.is_ready:
        raise RuntimeError("Model inference engine is not ready or failed to load.")
    return manager


def get_transaction_service(
    model_manager: ModelManager = Depends(get_model_manager),
) -> TransactionService:
    """Dependency provider for TransactionService."""
    return TransactionService(model_manager=model_manager)
