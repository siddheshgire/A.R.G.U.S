"""
A.R.G.U.S. — ML Engine Feature Engineering Package
Provides reproducible, leakage-safe feature transformations and temporal dataset partitioning.
"""

from .feature_config import (
    RAW_NUMERICAL_FEATURES,
    ENGINEERED_FEATURE_NAMES,
    ALL_MODEL_FEATURES,
    EXCLUDED_COLUMNS,
    TARGET_COLUMN,
    TEMPORAL_SPLIT_STEPS,
)
from .paysim_features import (
    compute_engineered_features,
    extract_feature_matrix,
    temporal_split,
    filter_fraud_modeling_subspace,
    fit_feature_scaler,
    save_scaler,
    load_scaler,
)

__all__ = [
    "RAW_NUMERICAL_FEATURES",
    "ENGINEERED_FEATURE_NAMES",
    "ALL_MODEL_FEATURES",
    "EXCLUDED_COLUMNS",
    "TARGET_COLUMN",
    "TEMPORAL_SPLIT_STEPS",
    "compute_engineered_features",
    "extract_feature_matrix",
    "temporal_split",
    "filter_fraud_modeling_subspace",
    "fit_feature_scaler",
    "save_scaler",
    "load_scaler",
]
