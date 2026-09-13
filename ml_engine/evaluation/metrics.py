"""
A.R.G.U.S. — Evaluation Metrics & Threshold Analysis Suite
Provides imbalanced classification metrics (PR-AUC, ROC-AUC, F1, Recall@FPR),
optimal threshold search, and inference latency benchmarking.
"""

import time
from typing import Dict, Any, Optional, Tuple, Callable
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    precision_recall_curve,
)


def compute_classification_metrics(
    y_true: np.ndarray | pd.Series,
    y_scores: np.ndarray | pd.Series,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Computes comprehensive imbalanced classification performance metrics.
    
    Parameters
    ----------
    y_true : np.ndarray | pd.Series
        Ground truth binary labels (0 or 1).
    y_scores : np.ndarray | pd.Series
        Continuous anomaly or probability scores (higher indicates greater fraud risk).
    threshold : float
        Decision threshold for binary classification.
        
    Returns
    -------
    Dict[str, Any]
        Dictionary of computed metrics.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_scores = np.asarray(y_scores, dtype=float)

    # Ranking metrics (independent of threshold)
    try:
        pr_auc = float(average_precision_score(y_true, y_scores))
    except Exception:
        pr_auc = 0.0

    try:
        roc_auc = float(roc_auc_score(y_true, y_scores))
    except Exception:
        roc_auc = 0.0

    # Thresholded binary metrics
    y_pred = (y_scores >= threshold).astype(int)

    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    return {
        "pr_auc": pr_auc,
        "roc_auc": roc_auc,
        "threshold": float(threshold),
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "fpr": fpr,
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn),
        "total_samples": int(len(y_true)),
        "total_fraud": int(np.sum(y_true == 1)),
    }


def find_optimal_threshold(
    y_true: np.ndarray | pd.Series,
    y_scores: np.ndarray | pd.Series,
    metric: str = "f1",
    target_recall: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Finds the optimal decision threshold using validation data.
    
    Parameters
    ----------
    y_true : np.ndarray | pd.Series
        Validation ground truth labels.
    y_scores : np.ndarray | pd.Series
        Validation continuous prediction or anomaly scores.
    metric : str
        Optimization goal: 'f1' (maximize F1) or 'recall_target' (achieve target recall with min FPR).
    target_recall : Optional[float]
        Required recall level if metric == 'recall_target' (e.g. 0.90).
        
    Returns
    -------
    Dict[str, Any]
        Optimal threshold and resulting performance metrics.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_scores = np.asarray(y_scores, dtype=float)

    precisions, recalls, thresholds = precision_recall_curve(y_true, y_scores)

    if metric == "f1":
        # Calculate F1 across all thresholds
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-12)
        best_idx = int(np.argmax(f1_scores[:-1])) if len(f1_scores) > 1 else 0
        best_thresh = float(thresholds[best_idx])
    elif metric == "recall_target" and target_recall is not None:
        # Find highest threshold where recall >= target_recall
        valid_indices = np.where(recalls[:-1] >= target_recall)[0]
        if len(valid_indices) > 0:
            best_idx = valid_indices[-1]  # Highest threshold among valid
            best_thresh = float(thresholds[best_idx])
        else:
            best_thresh = float(thresholds[0]) if len(thresholds) > 0 else 0.5
    else:
        best_thresh = 0.5

    # Compute full metrics at the chosen threshold
    return compute_classification_metrics(y_true, y_scores, threshold=best_thresh)


def benchmark_inference_latency(
    predict_fn: Callable[[np.ndarray | pd.DataFrame], np.ndarray],
    X_sample: np.ndarray | pd.DataFrame,
    n_iterations: int = 50,
) -> Dict[str, float]:
    """
    Benchmarks inference latency in milliseconds for batch and single-transaction execution.
    
    Parameters
    ----------
    predict_fn : Callable
        Function that accepts X and returns predictions or scores.
    X_sample : np.ndarray | pd.DataFrame
        Sample feature matrix (e.g. 1000 rows).
    n_iterations : int
        Number of benchmark iterations.
        
    Returns
    -------
    Dict[str, float]
        {'batch_latency_ms': ..., 'single_sample_latency_ms': ...}
    """
    # Warmup
    _ = predict_fn(X_sample[:10])

    # 1. Batch latency
    t_start = time.perf_counter()
    for _ in range(n_iterations):
        _ = predict_fn(X_sample)
    total_batch_time = time.perf_counter() - t_start
    avg_batch_time_ms = (total_batch_time / n_iterations) * 1000.0

    # 2. Single-sample latency
    single_x = X_sample[:1]
    t_start = time.perf_counter()
    for _ in range(n_iterations):
        _ = predict_fn(single_x)
    total_single_time = time.perf_counter() - t_start
    avg_single_time_ms = (total_single_time / n_iterations) * 1000.0

    return {
        "batch_size": len(X_sample),
        "batch_latency_ms": round(avg_batch_time_ms, 3),
        "single_sample_latency_ms": round(avg_single_time_ms, 4),
    }


def format_metric_report(metrics: Dict[str, Any], model_name: str, split_name: str) -> str:
    """Formats a clean, standardized Markdown summary of model performance."""
    lines = [
        f"### {model_name} — {split_name} Evaluation Summary",
        f"- **PR-AUC (Primary Metric):** {metrics.get('pr_auc', 0.0):.4f}",
        f"- **ROC-AUC:** {metrics.get('roc_auc', 0.0):.4f}",
        f"- **Decision Threshold:** {metrics.get('threshold', 0.5):.4f}",
        f"- **Precision:** {metrics.get('precision', 0.0):.4f}",
        f"- **Recall:** {metrics.get('recall', 0.0):.4f}",
        f"- **F1-Score:** {metrics.get('f1', 0.0):.4f}",
        f"- **False Positive Rate (FPR):** {metrics.get('fpr', 0.0):.4f} ({metrics.get('fpr', 0.0)*100:.2f}%)",
        f"- **Confusion Matrix:** TP={metrics.get('true_positives', 0):,}, FP={metrics.get('false_positives', 0):,}, TN={metrics.get('true_negatives', 0):,}, FN={metrics.get('false_negatives', 0):,}",
    ]
    if "single_sample_latency_ms" in metrics:
        lines.append(f"- **Inference Latency:** {metrics['single_sample_latency_ms']:.3f} ms / transaction")
    return "\n".join(lines)
