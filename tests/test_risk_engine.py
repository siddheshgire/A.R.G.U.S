"""
A.R.G.U.S. — Unit & Integration Tests for Risk Scoring & Decision Engine
Tests weight validation, signal normalization, risk score bounds, decision policy,
business rule fast path, and explanation generation.
"""

import pytest
import numpy as np

from ml_engine.risk import (
    RiskConfig,
    RiskSignals,
    compute_risk_score,
    compute_risk_scores_batch,
    DecisionAction,
    evaluate_decision,
    evaluate_decisions_batch,
    evaluate_non_model_transaction,
    generate_risk_explanations,
    RiskAssessment,
    assess_transaction,
)


def test_risk_config_validation():
    """Verifies that RiskConfig enforces valid weights and threshold hierarchy."""
    # Valid config
    config = RiskConfig(
        xgboost_weight=0.50,
        autoencoder_weight=0.20,
        isolation_weight=0.15,
        logistic_weight=0.15,
        threshold_review=40.0,
        threshold_block=70.0,
    )
    assert config.engine_version == "1.0.0"

    # Invalid weights sum
    with pytest.raises(ValueError, match="sum to 1.0"):
        RiskConfig(xgboost_weight=0.60, autoencoder_weight=0.20, isolation_weight=0.15, logistic_weight=0.15)

    # Invalid negative weight
    with pytest.raises(ValueError, match="must be in"):
        RiskConfig(xgboost_weight=-0.1, autoencoder_weight=0.5, isolation_weight=0.3, logistic_weight=0.3)

    # Invalid threshold hierarchy (review >= block)
    with pytest.raises(ValueError, match="Thresholds must satisfy"):
        RiskConfig(
            xgboost_weight=0.50,
            autoencoder_weight=0.20,
            isolation_weight=0.15,
            logistic_weight=0.15,
            threshold_review=75.0,
            threshold_block=70.0,
        )


def test_risk_signals_validation():
    """Verifies that RiskSignals enforces finite, non-negative [0, 1] inputs."""
    # Valid signals
    signals = RiskSignals(
        xgboost_score=0.95,
        logistic_score=0.88,
        isolation_score=0.65,
        autoencoder_score=0.72,
    )
    d = signals.to_dict()
    assert d["xgboost_score"] == 0.95

    # Out of range signal (> 1.0)
    with pytest.raises(ValueError, match="must be in range"):
        RiskSignals(xgboost_score=1.5, logistic_score=0.5, isolation_score=0.5, autoencoder_score=0.5)

    # NaN signal
    with pytest.raises(ValueError, match="finite float"):
        RiskSignals(xgboost_score=float("nan"), logistic_score=0.5, isolation_score=0.5, autoencoder_score=0.5)


def test_compute_risk_score_bounds_and_determinism():
    """Verifies that risk scores remain strictly within [0.0, 100.0] and are deterministic."""
    config = RiskConfig()

    # Minimum risk: all zeros -> 0.0
    min_signals = RiskSignals(0.0, 0.0, 0.0, 0.0)
    assert compute_risk_score(min_signals, config) == 0.0

    # Maximum risk: all ones -> 100.0
    max_signals = RiskSignals(1.0, 1.0, 1.0, 1.0)
    assert compute_risk_score(max_signals, config) == 100.0

    # Mixed signals: 0.50*0.80 + 0.20*0.60 + 0.15*0.40 + 0.15*0.50 = 0.40 + 0.12 + 0.06 + 0.075 = 0.655 -> 65.50
    mid_signals = RiskSignals(
        xgboost_score=0.80,
        autoencoder_score=0.60,
        isolation_score=0.40,
        logistic_score=0.50,
    )
    score1 = compute_risk_score(mid_signals, config)
    score2 = compute_risk_score(mid_signals, config)
    assert score1 == 65.50
    assert score1 == score2  # Deterministic


def test_vectorized_batch_scoring():
    """Verifies that batch vector calculations produce identical results to single-sample scoring."""
    config = RiskConfig()
    xgb = np.array([0.0, 0.5, 1.0])
    lr = np.array([0.0, 0.5, 1.0])
    ifo = np.array([0.0, 0.5, 1.0])
    ae = np.array([0.0, 0.5, 1.0])

    batch_scores = compute_risk_scores_batch(xgb, lr, ifo, ae, config)
    assert np.allclose(batch_scores, [0.0, 50.0, 100.0])


def test_decision_policy_thresholds():
    """Verifies decision threshold assignments."""
    config = RiskConfig(threshold_review=40.0, threshold_block=70.0)

    assert evaluate_decision(0.0, config) == DecisionAction.APPROVE
    assert evaluate_decision(39.99, config) == DecisionAction.APPROVE
    assert evaluate_decision(40.0, config) == DecisionAction.REVIEW
    assert evaluate_decision(69.99, config) == DecisionAction.REVIEW
    assert evaluate_decision(70.0, config) == DecisionAction.BLOCK
    assert evaluate_decision(100.0, config) == DecisionAction.BLOCK

    # Invalid score
    with pytest.raises(ValueError):
        evaluate_decision(105.0, config)


def test_business_rule_fast_path():
    """Verifies that non-modeled transactions follow fast path without error."""
    config = RiskConfig()

    # Routine payment under threshold
    routine_tx = {"type": "PAYMENT", "amount": 150.0}
    score, decision, reasons = evaluate_non_model_transaction(routine_tx, config)
    assert decision == DecisionAction.APPROVE
    assert score == 5.0
    assert any("Routine" in r for r in reasons)

    # High-value payment over threshold
    large_tx = {"type": "PAYMENT", "amount": 750000.0}
    score, decision, reasons = evaluate_non_model_transaction(large_tx, config)
    assert decision == DecisionAction.REVIEW
    assert score == 45.0
    assert any("exceeds standard fast-path ceiling" in r for r in reasons)


def test_explanation_generation():
    """Verifies separation of model signals and feature rules in explanations."""
    signals = RiskSignals(
        xgboost_score=0.92,
        logistic_score=0.75,
        isolation_score=0.62,
        autoencoder_score=0.81,
    )
    features = {
        "is_full_liquidation": 1,
        "is_night_transaction": 1,
        "dest_zero_balance_anomaly": 1,
        "orig_balance_error": 5000.0,
        "amount": 250000.0,
    }

    reasons = generate_risk_explanations(signals, features)
    assert any("XGBoost" in r for r in reasons)
    assert any("Deep Autoencoder" in r for r in reasons)
    assert any("Isolation Forest" in r for r in reasons)
    assert any("Account liquidation" in r for r in reasons)
    assert any("Nighttime execution" in r for r in reasons)
    assert any("Mule recipient" in r for r in reasons)


def test_assess_transaction_end_to_end():
    """Verifies full transaction assessment object creation."""
    signals = RiskSignals(
        xgboost_score=0.90,
        logistic_score=0.80,
        isolation_score=0.70,
        autoencoder_score=0.85,
    )
    features = {"is_full_liquidation": 1, "orig_balance_error": 0.0}

    assessment = assess_transaction(
        signals=signals,
        feature_dict=features,
        transaction_id="TX-10023",
    )

    assert isinstance(assessment, RiskAssessment)
    assert assessment.transaction_id == "TX-10023"
    assert assessment.decision == DecisionAction.BLOCK
    assert assessment.risk_score >= 70.0

    d = assessment.to_dict()
    assert d["transaction_id"] == "TX-10023"
    assert d["decision"] == "BLOCK"
    assert "signals" in d
    assert "reasons" in d
