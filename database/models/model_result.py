"""
A.R.G.U.S. — Model Result Relational Model
Stores individual model inference outputs (raw output and normalized [0, 1] signal)
for each model architecture evaluated on a transaction.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class ModelResult(Base):
    """
    Individual machine learning or deep learning inference output.
    Persists raw outputs (e.g. reconstruction MSE, isolation path score, raw probabilities)
    alongside the normalized continuous signal in [0.0, 1.0].
    """
    __tablename__ = "model_results"

    result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    tx_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.tx_id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # xgboost, autoencoder, isolation_forest, logistic_regression
    raw_output: Mapped[float] = mapped_column(Float, nullable=False)
    normalized_signal: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    inference_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="model_results")

    def __repr__(self) -> str:
        return f"<ModelResult(model='{self.model_name}', signal={self.normalized_signal:.4f}, tx_id={self.tx_id})>"
