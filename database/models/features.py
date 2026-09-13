"""
A.R.G.U.S. — Transaction Features Relational Model
Stores the exact 18 engineered features derived by the feature engineering pipeline.
Preserves mathematical definitions and values identical to the feature manifest.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Integer, Float, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class TransactionFeatures(Base):
    """
    Stores engineered features computed for a specific transaction.
    Maintains a strict 1-to-1 relational mapping with the parent Transaction.
    """
    __tablename__ = "transaction_features"

    feature_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    tx_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.tx_id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # 1. Monetary value
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    # 2. Sender pre-transaction balance
    oldbalance_org: Mapped[float] = mapped_column(Float, nullable=False)
    # 3. Sender post-transaction balance
    newbalance_orig: Mapped[float] = mapped_column(Float, nullable=False)
    # 4. Recipient pre-transaction balance
    oldbalance_dest: Mapped[float] = mapped_column(Float, nullable=False)
    # 5. Recipient post-transaction balance
    newbalance_dest: Mapped[float] = mapped_column(Float, nullable=False)
    # 6. Log-transformed amount
    log_amount: Mapped[float] = mapped_column(Float, nullable=False)
    # 7. Type indicator: TRANSFER
    is_transfer: Mapped[int] = mapped_column(Integer, nullable=False)
    # 8. Type indicator: CASH_OUT
    is_cash_out: Mapped[int] = mapped_column(Integer, nullable=False)
    # 9. Diurnal hour (0-23)
    hour_of_day: Mapped[float] = mapped_column(Float, nullable=False)
    # 10. Trigonometric sine cyclic encoding
    hour_sin: Mapped[float] = mapped_column(Float, nullable=False)
    # 11. Trigonometric cosine cyclic encoding
    hour_cos: Mapped[float] = mapped_column(Float, nullable=False)
    # 12. Binary night transaction flag (01:00-06:00)
    is_night_transaction: Mapped[int] = mapped_column(Integer, nullable=False)
    # 13. Sender balance conservation error
    orig_balance_error: Mapped[float] = mapped_column(Float, nullable=False)
    # 14. Sender account drainage ratio
    orig_drain_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    # 15. Binary complete liquidation flag
    is_full_liquidation: Mapped[int] = mapped_column(Integer, nullable=False)
    # 16. Recipient balance conservation error
    dest_balance_error: Mapped[float] = mapped_column(Float, nullable=False)
    # 17. Transferred funds relative to recipient ending balance
    dest_drain_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    # 18. Recipient zero balance anomaly flag
    dest_zero_balance_anomaly: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="features")

    def __repr__(self) -> str:
        return f"<TransactionFeatures(feature_id={self.feature_id}, tx_id={self.tx_id})>"
