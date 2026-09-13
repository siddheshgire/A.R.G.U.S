"""
A.R.G.U.S. — Transaction Assessment Service
Orchestrates feature extraction, multi-model inference, risk assessment, and atomic persistence.
"""

from typing import Optional, Dict, Any
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ml_engine.features import (
    compute_engineered_features,
    ALL_MODEL_FEATURES,
)
from ml_engine.risk import (
    RiskConfig,
    assess_transaction,
)
from database.repository import (
    save_assessed_transaction,
    get_transaction_by_id,
)
from backend.schemas.transaction import (
    TransactionCreateRequest,
    SUPPORTED_FRAUD_TYPES,
    TransactionListItemResponse,
    TransactionListResponse,
    TransactionDetailResponse,
    EngineeredFeaturesResponse,
    RiskAssessmentSummaryResponse,
    DecisionSummaryResponse,
)
from backend.schemas.risk import (
    TransactionAssessResponse,
    ModelSignalsResponse,
)
from .model_service import ModelManager


class TransactionService:
    """
    Application service that coordinates end-to-end transaction fraud assessment.
    """

    def __init__(self, model_manager: ModelManager, risk_config: Optional[RiskConfig] = None):
        self.model_manager = model_manager
        self.risk_config = risk_config or RiskConfig()

    def assess_and_persist(
        self,
        request: TransactionCreateRequest,
        db: Session,
        current_user: Optional[Any] = None,
    ) -> TransactionAssessResponse:
        """
        Executes end-to-end evaluation for an incoming simulated transaction:
        1. Validates modeling subspace eligibility.
        2. Computes the exact 18 engineered features.
        3. Executes ML/DL inference across 4 models.
        4. Calculates ensemble risk score and renders tri-state policy decision.
        5. Persists all entities atomically to PostgreSQL / relational database.
        6. Formulates the response contract.
        """
        # 1. Subspace Validation: Reject non-modeled types with controlled 422 error
        if request.type not in SUPPORTED_FRAUD_TYPES:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Transaction type '{request.type}' is not currently supported for ML risk assessment. "
                    f"The A.R.G.U.S. model pipeline is strictly trained and validated on {sorted(list(SUPPORTED_FRAUD_TYPES))} transactions."
                ),
            )

        # 2. Convert incoming request to PaySim DataFrame format for feature transformation
        raw_df = pd.DataFrame([
            {
                "step": request.step,
                "type": request.type,
                "amount": request.amount,
                "nameOrig": request.name_orig,
                "nameDest": request.name_dest,
                "oldbalanceOrg": request.oldbalance_org,
                "newbalanceOrig": request.newbalance_orig,
                "oldbalanceDest": request.oldbalance_dest,
                "newbalanceDest": request.newbalance_dest,
            }
        ])

        # 3. Compute 18 features using existing feature pipeline
        feat_df = compute_engineered_features(raw_df)
        features_matrix = feat_df[ALL_MODEL_FEATURES].copy()
        features_dict = {col: float(features_matrix.iloc[0][col]) for col in ALL_MODEL_FEATURES}

        # 4. Execute inference across all 4 models
        signals, model_results_meta = self.model_manager.predict_signals(features_matrix)

        # 5. Evaluate Risk Engine (Weights: 0.50 XGB, 0.20 AE, 0.15 IF, 0.15 LR)
        assessment = assess_transaction(
            signals=signals,
            feature_dict=features_dict,
            config=self.risk_config,
        )

        # 6. Prepare raw transaction data dictionary for repository persistence
        tx_data = {
            "step": request.step,
            "type": request.type,
            "amount": request.amount,
            "name_orig": request.name_orig,
            "name_dest": request.name_dest,
            "oldbalance_org": request.oldbalance_org,
            "newbalance_orig": request.newbalance_orig,
            "oldbalance_dest": request.oldbalance_dest,
            "newbalance_dest": request.newbalance_dest,
        }

        # 7. Persist atomically to database
        user_id = current_user.user_id if current_user else None
        actor_id = current_user.username if current_user else (request.actor_id or "API_GATEWAY")

        tx_record = save_assessed_transaction(
            session=db,
            tx_data=tx_data,
            assessment=assessment,
            features_dict=features_dict,
            model_results_meta=model_results_meta,
            merchant_id=request.merchant_id,
            device_id=request.device_id,
            user_id=user_id,
            actor_id=actor_id,
            client_tx_id=request.client_tx_id,
        )

        # Extract persisted assessment ID
        assessment_id = None
        if tx_record.risk_assessment:
            assessment_id = tx_record.risk_assessment.assessment_id

        # 8. Build and return API response
        return TransactionAssessResponse(
            transaction_id=tx_record.tx_id,
            risk_score=assessment.risk_score,
            decision=assessment.decision.value,
            model_signals=ModelSignalsResponse(**assessment.signals.to_dict()),
            reasons=assessment.reasons,
            assessment_id=assessment_id,
            engine_version=assessment.engine_version,
            evaluated_by=assessment.evaluated_by,
            created_at=tx_record.created_at,
        )

    def get_authorized_transaction(
        self,
        tx_id: Any,
        db: Session,
        current_user: Optional[Any] = None,
    ) -> Any:
        """
        Retrieves a transaction enforcing Object-Level Authorization (IDOR Defense).

        Rules:
        1. 404 if transaction does not exist.
        2. If transaction belongs to a registered user (tx.user_id is not None):
           - Unauthenticated access returns HTTP 401.
           - ANALYST / ADMIN / AUDITOR can inspect any transaction.
           - The owner (matching user_id or username == name_orig) can inspect.
           - Another USER receives HTTP 403 Forbidden.
        3. If transaction is an unassigned simulation record:
           - Accessible for backward-compatible simulation queries.
           - If a USER is authenticated and transaction has name_orig matching another registered user,
             access is restricted.
        """
        tx = get_transaction_by_id(session=db, tx_id=tx_id)
        if tx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction with ID '{tx_id}' not found.",
            )

        # Object-level authorization policy
        if tx.user_id is not None:
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required to access this transaction.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user_role = current_user.role.name.upper() if current_user.role else "USER"
            is_privileged = user_role in {"ADMIN", "ANALYST", "AUDITOR"}
            is_owner = (current_user.user_id == tx.user_id) or (current_user.username == tx.name_orig)

            if not (is_privileged or is_owner):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You do not have permission to access another user's transaction record.",
                )

        return tx

    def list_transactions(
        self,
        db: Session,
        current_user: Optional[Any] = None,
        limit: int = 50,
        offset: int = 0,
        tx_type: Optional[str] = None,
        decision: Optional[str] = None,
        min_risk: Optional[float] = None,
        max_risk: Optional[float] = None,
    ) -> TransactionListResponse:
        """
        Retrieves a paginated list of transactions enforcing Scoped RBAC.
        - USER role: strictly restricted to transactions they own (user_id == current_user.user_id or name_orig == current_user.username).
        - Privileged roles (ANALYST, ADMIN, AUDITOR): granted global visibility across all transactions.
        - Unauthenticated callers: restricted to simulation records that have no assigned user.
        """
        from database.models.transaction import Transaction
        from database.models.risk_assessment import RiskAssessmentRecord
        from database.models.decision import DecisionRecord
        from sqlalchemy import select, func, or_

        stmt = (
            select(Transaction, RiskAssessmentRecord, DecisionRecord)
            .outerjoin(RiskAssessmentRecord, Transaction.tx_id == RiskAssessmentRecord.tx_id)
            .outerjoin(DecisionRecord, RiskAssessmentRecord.assessment_id == DecisionRecord.assessment_id)
        )

        # Scoped RBAC
        if current_user is None:
            stmt = stmt.where(Transaction.user_id.is_(None))
        else:
            user_role = current_user.role.name.upper() if current_user.role else "USER"
            if user_role not in {"ADMIN", "ANALYST", "AUDITOR"}:
                stmt = stmt.where(
                    or_(
                        Transaction.user_id == current_user.user_id,
                        Transaction.name_orig == current_user.username,
                    )
                )

        # Filters
        if tx_type:
            stmt = stmt.where(Transaction.type == tx_type.upper())
        if decision:
            stmt = stmt.where(DecisionRecord.policy_decision == decision.upper())
        if min_risk is not None:
            stmt = stmt.where(RiskAssessmentRecord.final_risk_score >= min_risk)
        if max_risk is not None:
            stmt = stmt.where(RiskAssessmentRecord.final_risk_score <= max_risk)

        # Server-side total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Paginated fetch
        stmt = stmt.order_by(Transaction.created_at.desc()).offset(offset).limit(limit)
        rows = db.execute(stmt).all()

        items = []
        for tx, ra, dec in rows:
            items.append(
                TransactionListItemResponse(
                    tx_id=tx.tx_id,
                    step=tx.step,
                    type=tx.type,
                    amount=tx.amount,
                    name_orig=tx.name_orig,
                    name_dest=tx.name_dest,
                    risk_score=ra.final_risk_score if ra else None,
                    decision=dec.policy_decision if dec else None,
                    created_at=tx.created_at,
                )
            )

        return TransactionListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_transaction_detail(
        self,
        tx_id: Any,
        db: Session,
        current_user: Optional[Any] = None,
    ) -> TransactionDetailResponse:
        """
        Retrieves full forensic details of a transaction including 18 engineered features,
        decomposed model signals, and operational policy decision (IDOR protected).
        """
        tx = self.get_authorized_transaction(tx_id=tx_id, db=db, current_user=current_user)

        feat_resp = None
        if tx.features:
            feat_resp = EngineeredFeaturesResponse(
                amount=tx.features.amount,
                oldbalance_org=tx.features.oldbalance_org,
                newbalance_orig=tx.features.newbalance_orig,
                oldbalance_dest=tx.features.oldbalance_dest,
                newbalance_dest=tx.features.newbalance_dest,
                log_amount=tx.features.log_amount,
                is_transfer=tx.features.is_transfer,
                is_cash_out=tx.features.is_cash_out,
                hour_of_day=tx.features.hour_of_day,
                hour_sin=tx.features.hour_sin,
                hour_cos=tx.features.hour_cos,
                is_night_transaction=tx.features.is_night_transaction,
                orig_balance_error=tx.features.orig_balance_error,
                orig_drain_ratio=tx.features.orig_drain_ratio,
                is_full_liquidation=tx.features.is_full_liquidation,
                dest_balance_error=tx.features.dest_balance_error,
                dest_drain_ratio=tx.features.dest_drain_ratio,
                dest_zero_balance_anomaly=tx.features.dest_zero_balance_anomaly,
            )

        ra_resp = None
        dec_resp = None
        if tx.risk_assessment:
            ra = tx.risk_assessment
            ra_resp = RiskAssessmentSummaryResponse(
                assessment_id=ra.assessment_id,
                final_risk_score=ra.final_risk_score,
                xgboost_signal=ra.xgboost_signal,
                logistic_signal=ra.logistic_signal,
                isolation_signal=ra.isolation_signal,
                autoencoder_signal=ra.autoencoder_signal,
                engine_version=ra.engine_version,
                evaluated_by=ra.evaluated_by,
                evaluated_at=ra.evaluated_at,
            )
            if ra.decision:
                dec_resp = DecisionSummaryResponse(
                    decision_id=ra.decision.decision_id,
                    policy_decision=ra.decision.policy_decision,
                    reasons=ra.decision.reasons or [],
                    created_at=ra.decision.created_at,
                )

        device_code = tx.device.device_code if tx.device else None
        merchant_name = tx.merchant.name if tx.merchant else None

        return TransactionDetailResponse(
            tx_id=tx.tx_id,
            step=tx.step,
            type=tx.type,
            amount=tx.amount,
            name_orig=tx.name_orig,
            name_dest=tx.name_dest,
            oldbalance_org=tx.oldbalance_org,
            newbalance_orig=tx.newbalance_orig,
            oldbalance_dest=tx.oldbalance_dest,
            newbalance_dest=tx.newbalance_dest,
            merchant_id=tx.merchant_id,
            merchant_name=merchant_name,
            device_id=tx.device_id,
            device_code=device_code,
            user_id=tx.user_id,
            client_tx_id=tx.client_tx_id,
            created_at=tx.created_at,
            risk_assessment=ra_resp,
            decision=dec_resp,
            features=feat_resp,
        )

