#!/usr/bin/env python3
"""
A.R.G.U.S. — PaySim Dataset Inspection & Exploratory Data Analysis Script
Phase 1: Dataset Inspection & Profiling

This script performs factual, reproducible data profiling on the local PaySim CSV:
- Verifies basic dataset dimensions, schema, and memory consumption.
- Evaluates data quality (missingness, duplicates, unique cardinality).
- Analyzes the target distribution ('isFraud') and simulation rule ('isFlaggedFraud').
- Conducts transaction, temporal, balance, and entity distribution analyses.
- Investigates balance consistency and potential target leakage vectors.
- Generates clean, publication-ready diagnostic visualizations saved to docs/figures/.
"""

import os
import sys
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


# Set styling for plots
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
    "axes.edgecolor": "#cccccc",
    "axes.linewidth": 0.8,
    "figure.autolayout": True,
})


def find_dataset_path() -> Path:
    """Locates the local PaySim CSV file."""
    candidates = [
        Path("data/raw/paysim.csv"),
        Path("data/raw/PS_20174392719_1491204439457_log.csv"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(
        f"PaySim dataset not found in data/raw/. Looked for: {[str(c) for c in candidates]}"
    )


def load_dataset(csv_path: Path) -> pd.DataFrame:
    """Loads dataset with memory reporting."""
    print(f"[*] Loading dataset from: {csv_path}")
    start_time = time.time()
    
    # Specify optimal types where possible to save memory
    df = pd.read_csv(
        csv_path,
        dtype={
            "step": np.int32,
            "type": "category",
            "amount": np.float64,
            "nameOrig": "string",
            "oldbalanceOrg": np.float64,
            "newbalanceOrig": np.float64,
            "nameDest": "string",
            "oldbalanceDest": np.float64,
            "newbalanceDest": np.float64,
            "isFraud": np.int8,
            "isFlaggedFraud": np.int8,
        }
    )
    elapsed = time.time() - start_time
    mem_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    print(f"[*] Loaded {len(df):,} rows in {elapsed:.2f}s (Memory: {mem_mb:.2f} MB)")
    return df


def inspect_basic_and_quality(df: pd.DataFrame) -> dict:
    """Computes schema, dimensions, and data quality metrics."""
    print("\n" + "=" * 60)
    print("1. BASIC INFORMATION & DATA QUALITY")
    print("=" * 60)
    
    n_rows, n_cols = df.shape
    mem_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    
    print(f"Total Rows:     {n_rows:,}")
    print(f"Total Columns:  {n_cols}")
    print(f"Memory Usage:   {mem_mb:.2f} MB")
    
    schema_info = []
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        n_unique = int(df[col].nunique())
        dtype_str = str(df[col].dtype)
        schema_info.append({
            "column": col,
            "dtype": dtype_str,
            "missing": n_missing,
            "missing_pct": (n_missing / n_rows) * 100,
            "unique": n_unique,
            "unique_pct": (n_unique / n_rows) * 100,
        })
        print(f"  - {col:<16} | {dtype_str:<10} | Missing: {n_missing:<5} (0.00%) | Unique: {n_unique:,}")

    # Check duplicates across core transaction tuple
    print("\n[*] Checking for exact row duplicates...")
    # Checking duplicate rows
    n_dupes = int(df.duplicated().sum())
    print(f"Exact Duplicate Rows: {n_dupes}")

    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "mem_mb": mem_mb,
        "schema": schema_info,
        "duplicates": n_dupes,
    }


def inspect_targets(df: pd.DataFrame) -> dict:
    """Analyzes ground truth target 'isFraud' and simulation rule 'isFlaggedFraud'."""
    print("\n" + "=" * 60)
    print("2. TARGET ANALYSIS ('isFraud' & 'isFlaggedFraud')")
    print("=" * 60)
    
    total = len(df)
    fraud_counts = df["isFraud"].value_counts().to_dict()
    n_legit = int(fraud_counts.get(0, 0))
    n_fraud = int(fraud_counts.get(1, 0))
    fraud_pct = (n_fraud / total) * 100
    imbalance_ratio = n_legit / n_fraud if n_fraud > 0 else 0
    
    print(f"Legitimate (0): {n_legit:,} ({100 - fraud_pct:.4f}%)")
    print(f"Fraudulent (1): {n_fraud:,} ({fraud_pct:.4f}%)")
    print(f"Imbalance Ratio: {imbalance_ratio:.1f} : 1")
    
    flagged_counts = df["isFlaggedFraud"].value_counts().to_dict()
    n_flagged_0 = int(flagged_counts.get(0, 0))
    n_flagged_1 = int(flagged_counts.get(1, 0))
    
    print(f"\nisFlaggedFraud Counts:")
    print(f"  0 (Not Flagged): {n_flagged_0:,}")
    print(f"  1 (Flagged):     {n_flagged_1:,}")
    
    # Cross-tabulation between isFraud and isFlaggedFraud
    ct = pd.crosstab(df["isFraud"], df["isFlaggedFraud"], margins=True)
    print("\nCross-Tabulation (isFraud vs isFlaggedFraud):")
    print(ct)
    
    flagged_fraud_df = df[df["isFlaggedFraud"] == 1]
    min_flagged_amt = float(flagged_fraud_df["amount"].min()) if len(flagged_fraud_df) > 0 else 0
    max_flagged_amt = float(flagged_fraud_df["amount"].max()) if len(flagged_fraud_df) > 0 else 0
    print(f"Flagged Transactions Amount Range: ${min_flagged_amt:,.2f} to ${max_flagged_amt:,.2f}")
    
    return {
        "n_legit": n_legit,
        "n_fraud": n_fraud,
        "fraud_pct": fraud_pct,
        "imbalance_ratio": imbalance_ratio,
        "n_flagged_0": n_flagged_0,
        "n_flagged_1": n_flagged_1,
        "cross_tab": ct.to_dict(),
    }


def inspect_transactions(df: pd.DataFrame) -> dict:
    """Analyzes transaction types, amounts, and fraud distribution per type."""
    print("\n" + "=" * 60)
    print("3. TRANSACTION TYPE & AMOUNT ANALYSIS")
    print("=" * 60)
    
    type_stats = []
    grouped = df.groupby("type", observed=True)
    
    for t_name, grp in grouped:
        total_type = len(grp)
        fraud_type = int((grp["isFraud"] == 1).sum())
        fraud_rate_pct = (fraud_type / total_type) * 100 if total_type > 0 else 0
        type_stats.append({
            "type": str(t_name),
            "count": total_type,
            "pct_of_all": (total_type / len(df)) * 100,
            "fraud_count": fraud_type,
            "fraud_rate_pct": fraud_rate_pct,
            "amount_median": float(grp["amount"].median()),
            "amount_mean": float(grp["amount"].mean()),
            "amount_max": float(grp["amount"].max()),
        })
    
    type_df = pd.DataFrame(type_stats)
    print(type_df.to_string(index=False))
    
    print("\nAmount Descriptive Statistics (All Transactions):")
    amt_desc = df["amount"].describe().to_dict()
    for k, v in amt_desc.items():
        print(f"  {k:<8}: {v:,.2f}")
        
    print("\nAmount Descriptive Statistics for Fraud Transactions:")
    fraud_amt_desc = df[df["isFraud"] == 1]["amount"].describe().to_dict()
    for k, v in fraud_amt_desc.items():
        print(f"  {k:<8}: {v:,.2f}")

    return {
        "type_stats": type_stats,
        "amt_desc": amt_desc,
        "fraud_amt_desc": fraud_amt_desc,
    }


def inspect_temporal(df: pd.DataFrame) -> dict:
    """Analyzes time progression (step: 1 step = 1 hour)."""
    print("\n" + "=" * 60)
    print("4. TEMPORAL ANALYSIS ('step')")
    print("=" * 60)
    
    min_step = int(df["step"].min())
    max_step = int(df["step"].max())
    unique_steps = int(df["step"].nunique())
    
    total_days = max_step / 24.0
    print(f"Step Range: {min_step} to {max_step} (Total Hours: {max_step}, approx {total_days:.1f} days)")
    print(f"Unique Steps Populated: {unique_steps} / {max_step}")
    
    # Diurnal cycle
    df_sample = df[["step", "isFraud"]].copy()
    df_sample["hour_of_day"] = df_sample["step"] % 24
    hour_grouped = df_sample.groupby("hour_of_day").agg(
        total_tx=("isFraud", "count"),
        fraud_tx=("isFraud", "sum")
    )
    hour_grouped["fraud_rate_pct"] = (hour_grouped["fraud_tx"] / hour_grouped["total_tx"]) * 100
    
    print("\nDiurnal Pattern Sample (Hour 0 to 5 vs Hour 12 to 17):")
    print(hour_grouped.loc[[0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17]])
    
    return {
        "min_step": min_step,
        "max_step": max_step,
        "unique_steps": unique_steps,
        "total_days": total_days,
        "diurnal": hour_grouped.to_dict(),
    }


def inspect_balances_and_leakage(df: pd.DataFrame) -> dict:
    """Investigates balance equations, discrepancies, zero-balance anomalies, and potential leakage."""
    print("\n" + "=" * 60)
    print("5. BALANCE CONSISTENCY & LEAKAGE INVESTIGATION")
    print("=" * 60)
    
    # Sender side: expected newbalance = oldbalance - amount
    # Error: newbalanceOrig + amount - oldbalanceOrg
    orig_error = df["newbalanceOrig"] + df["amount"] - df["oldbalanceOrg"]
    orig_exact_match = (orig_error.abs() < 1e-2).sum()
    
    # Destination side: expected newbalance = oldbalance + amount
    # Error: oldbalanceDest + amount - newbalanceDest
    dest_error = df["oldbalanceDest"] + df["amount"] - df["newbalanceDest"]
    dest_exact_match = (dest_error.abs() < 1e-2).sum()
    
    total = len(df)
    print(f"Origin Account Exact Balance Match:      {orig_exact_match:,} / {total:,} ({(orig_exact_match / total) * 100:.2f}%)")
    print(f"Destination Account Exact Balance Match: {dest_exact_match:,} / {total:,} ({(dest_exact_match / total) * 100:.2f}%)")
    
    # Zero balance behavior
    orig_zero_after = ((df["oldbalanceOrg"] > 0) & (df["newbalanceOrig"] == 0)).sum()
    fraud_df = df[df["isFraud"] == 1]
    legit_df = df[df["isFraud"] == 0]
    
    fraud_orig_zero_after = ((fraud_df["oldbalanceOrg"] > 0) & (fraud_df["newbalanceOrig"] == 0)).sum()
    legit_orig_zero_after = ((legit_df["oldbalanceOrg"] > 0) & (legit_df["newbalanceOrig"] == 0)).sum()
    
    pct_fraud_emptied = (fraud_orig_zero_after / len(fraud_df)) * 100
    pct_legit_emptied = (legit_orig_zero_after / len(legit_df)) * 100
    
    print(f"\nAccount Liquidation Behavior (oldbalanceOrg > 0 and newbalanceOrig == 0):")
    print(f"  In Legitimate Transactions: {legit_orig_zero_after:,} / {len(legit_df):,} ({pct_legit_emptied:.2f}%)")
    print(f"  In Fraudulent Transactions: {fraud_orig_zero_after:,} / {len(fraud_df):,} ({pct_fraud_emptied:.2f}%)")
    
    # Destination zero balances despite large transaction
    dest_both_zero = ((df["oldbalanceDest"] == 0) & (df["newbalanceDest"] == 0)).sum()
    fraud_dest_both_zero = ((fraud_df["oldbalanceDest"] == 0) & (fraud_df["newbalanceDest"] == 0)).sum()
    print(f"\nDestination Zero-Balance Artifact (oldbalanceDest == 0 and newbalanceDest == 0):")
    print(f"  All Transactions:   {dest_both_zero:,} ({(dest_both_zero / total) * 100:.2f}%)")
    print(f"  Fraud Transactions: {fraud_dest_both_zero:,} ({(fraud_dest_both_zero / len(fraud_df)) * 100:.2f}%)")
    
    return {
        "orig_exact_match_pct": (orig_exact_match / total) * 100,
        "dest_exact_match_pct": (dest_exact_match / total) * 100,
        "pct_fraud_emptied": pct_fraud_emptied,
        "pct_legit_emptied": pct_legit_emptied,
        "dest_both_zero_pct": (dest_both_zero / total) * 100,
        "fraud_dest_both_zero_pct": (fraud_dest_both_zero / len(fraud_df)) * 100,
    }


def inspect_entities(df: pd.DataFrame) -> dict:
    """Analyzes customer and merchant identifiers (nameOrig, nameDest)."""
    print("\n" + "=" * 60)
    print("6. ENTITY ANALYSIS ('nameOrig' & 'nameDest')")
    print("=" * 60)
    
    total = len(df)
    unique_orig = int(df["nameOrig"].nunique())
    unique_dest = int(df["nameDest"].nunique())
    
    print(f"Unique Originators (nameOrig):   {unique_orig:,} (Avg transactions per sender: {total / unique_orig:.2f})")
    print(f"Unique Destinations (nameDest):  {unique_dest:,} (Avg transactions per recipient: {total / unique_dest:.2f})")
    
    # Merchant destination analysis (names starting with 'M')
    is_merchant_dest = df["nameDest"].str.startswith("M")
    n_merchant_dest = int(is_merchant_dest.sum())
    fraud_merchant_dest = int((is_merchant_dest & (df["isFraud"] == 1)).sum())
    
    print(f"\nMerchant Destinations (Prefix 'M'):")
    print(f"  Total Directed to Merchants: {n_merchant_dest:,} ({(n_merchant_dest / total) * 100:.2f}%)")
    print(f"  Fraud Sent to Merchants:     {fraud_merchant_dest:,} ({(fraud_merchant_dest / n_merchant_dest) * 100 if n_merchant_dest > 0 else 0:.4f}%)")
    print(f"  Finding: Fraudsters in PaySim route funds via Customer-to-Customer (C) accounts, never Merchant (M) POS.")
    
    # Sender repeat frequency
    sender_counts = df["nameOrig"].value_counts()
    repeat_senders = int((sender_counts > 1).sum())
    max_sender_tx = int(sender_counts.max())
    print(f"Originators with > 1 transaction: {repeat_senders:,} ({(repeat_senders / unique_orig) * 100:.3f}%)")
    print(f"Maximum transactions by a single sender: {max_sender_tx}")
    
    return {
        "unique_orig": unique_orig,
        "unique_dest": unique_dest,
        "n_merchant_dest": n_merchant_dest,
        "fraud_merchant_dest": fraud_merchant_dest,
        "repeat_senders": repeat_senders,
    }


def generate_visualizations(df: pd.DataFrame, output_dir: Path) -> list:
    """Generates informative, publication-ready figures for Milestone 1 EDA."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_plots = []
    print("\n" + "=" * 60)
    print("7. GENERATING DIAGNOSTIC VISUALIZATIONS")
    print("=" * 60)
    
    # Plot 1: Transaction Type Distribution
    p1 = output_dir / "eda_01_transaction_types.png"
    plt.figure(figsize=(9, 5))
    type_counts = df["type"].value_counts()
    ax = sns.barplot(x=type_counts.index, y=type_counts.values, palette="Blues_r")
    plt.title("PaySim Transaction Volume by Type", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Transaction Type", fontsize=11)
    plt.ylabel("Number of Transactions", fontsize=11)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{x * 1e-6:.1f}M"))
    for p in ax.patches:
        height = p.get_height()
        ax.annotate(f"{height:,.0f}", (p.get_x() + p.get_width() / 2., height / 2),
                    ha="center", va="center", fontsize=9, color="white", fontweight="bold",
                    rotation=0)
    plt.savefig(p1, dpi=200)
    plt.close()
    saved_plots.append(p1)
    print(f"  [+] Saved: {p1}")

    # Plot 2: Fraud by Transaction Type
    p2 = output_dir / "eda_02_fraud_by_type.png"
    plt.figure(figsize=(9, 5))
    fraud_by_type = df.groupby("type", observed=True)["isFraud"].agg(["count", "sum", "mean"]).reset_index()
    fraud_by_type["mean_pct"] = fraud_by_type["mean"] * 100
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    sns.barplot(data=fraud_by_type, x="type", y="sum", palette="Reds_r", ax=ax1)
    ax1.set_title("Fraud Transaction Count by Type", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Transaction Type")
    ax1.set_ylabel("Fraud Cases")
    for p in ax1.patches:
        h = p.get_height()
        if h > 0:
            ax1.annotate(f"{int(h):,}", (p.get_x() + p.get_width() / 2., h + 50),
                         ha="center", va="bottom", fontsize=9, fontweight="bold")

    sns.barplot(data=fraud_by_type, x="type", y="mean_pct", palette="Oranges_r", ax=ax2)
    ax2.set_title("Fraud Rate (%) by Type", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Transaction Type")
    ax2.set_ylabel("Fraud Rate (%)")
    for p in ax2.patches:
        h = p.get_height()
        if h > 0:
            ax2.annotate(f"{h:.3f}%", (p.get_x() + p.get_width() / 2., h + 0.005),
                         ha="center", va="bottom", fontsize=9, fontweight="bold")

    plt.tight_layout()
    plt.savefig(p2, dpi=200)
    plt.close()
    saved_plots.append(p2)
    print(f"  [+] Saved: {p2}")

    # Plot 3: Amount Distribution (Legit vs Fraud, Log-Scale)
    p3 = output_dir / "eda_03_amount_distribution.png"
    plt.figure(figsize=(10, 5))
    sample_legit = df[df["isFraud"] == 0]["amount"].sample(n=100000, random_state=42)
    fraud_amt = df[df["isFraud"] == 1]["amount"]
    
    sns.kdeplot(np.log10(sample_legit.clip(lower=1)), label="Legitimate (Sample N=100k)", color="#2b5c8f", fill=True, alpha=0.3)
    sns.kdeplot(np.log10(fraud_amt.clip(lower=1)), label="Fraudulent (All N=8,213)", color="#c0392b", fill=True, alpha=0.4)
    plt.title("Transaction Amount Density (Log10 Transformed)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Log10(Amount)", fontsize=11)
    plt.ylabel("Density", fontsize=11)
    plt.legend(frameon=True)
    plt.savefig(p3, dpi=200)
    plt.close()
    saved_plots.append(p3)
    print(f"  [+] Saved: {p3}")

    # Plot 4: Temporal Volume and Fraud Rate Across 744 Steps
    p4 = output_dir / "eda_04_temporal_trend.png"
    temporal_agg = df.groupby("step").agg(
        total_tx=("isFraud", "count"),
        fraud_tx=("isFraud", "sum")
    ).reset_index()
    
    fig, ax1 = plt.subplots(figsize=(12, 5))
    color = "#2b5c8f"
    ax1.set_xlabel("Time Step (Hours 1 to 744 / Days 1 to 31)", fontsize=11)
    ax1.set_ylabel("Total Transaction Volume", color=color, fontsize=11)
    ax1.plot(temporal_agg["step"], temporal_agg["total_tx"], color=color, linewidth=1.2, alpha=0.8, label="Transaction Volume")
    ax1.tick_params(axis="y", labelcolor=color)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{x * 1e-3:.0f}k"))
    
    ax2 = ax1.twinx()
    color = "#c0392b"
    ax2.set_ylabel("Fraud Count", color=color, fontsize=11)
    ax2.scatter(temporal_agg["step"], temporal_agg["fraud_tx"], color=color, s=8, alpha=0.6, label="Fraud Cases")
    ax2.tick_params(axis="y", labelcolor=color)
    plt.title("Temporal Dynamics: Transaction Volume and Fraud Occurrence over 30 Days", fontsize=12, fontweight="bold", pad=12)
    plt.savefig(p4, dpi=200)
    plt.close()
    saved_plots.append(p4)
    print(f"  [+] Saved: {p4}")

    # Plot 5: Balance Drainage Behavior (Legit vs Fraud)
    p5 = output_dir / "eda_05_balance_drainage.png"
    plt.figure(figsize=(8, 5))
    fraud_emptied = ((df[df["isFraud"] == 1]["oldbalanceOrg"] > 0) & (df[df["isFraud"] == 1]["newbalanceOrig"] == 0)).mean() * 100
    legit_emptied = ((df[df["isFraud"] == 0]["oldbalanceOrg"] > 0) & (df[df["isFraud"] == 0]["newbalanceOrig"] == 0)).mean() * 100
    
    bars = plt.bar(["Legitimate Transactions", "Fraudulent Transactions"], [legit_emptied, fraud_emptied], color=["#2b5c8f", "#c0392b"], width=0.5)
    plt.ylabel("Percentage of Transactions Liquidation (%)", fontsize=11)
    plt.title("Origin Account Liquidation Behavior (oldbalanceOrg > 0 -> newbalanceOrig == 0)", fontsize=12, fontweight="bold", pad=12)
    plt.ylim(0, 100)
    for bar in bars:
        h = bar.get_height()
        plt.annotate(f"{h:.1f}%", (bar.get_x() + bar.get_width() / 2., h + 2),
                     ha="center", va="bottom", fontsize=10, fontweight="bold")
    plt.savefig(p5, dpi=200)
    plt.close()
    saved_plots.append(p5)
    print(f"  [+] Saved: {p5}")

    return saved_plots


def main():
    print("=" * 70)
    print("A.R.G.U.S. — PaySim Dataset Inspection & Profiling Tool")
    print("=" * 70)
    
    csv_path = find_dataset_path()
    df = load_dataset(csv_path)
    
    basic_res = inspect_basic_and_quality(df)
    target_res = inspect_targets(df)
    tx_res = inspect_transactions(df)
    temp_res = inspect_temporal(df)
    bal_res = inspect_balances_and_leakage(df)
    entity_res = inspect_entities(df)
    
    figures_dir = Path("docs/figures")
    plots = generate_visualizations(df, figures_dir)
    
    # Write summary facts to JSON for reliable report generation
    summary_path = Path("docs/paysim_inspection_summary.json")
    summary_data = {
        "basic": basic_res,
        "target": target_res,
        "transactions": tx_res,
        "temporal": {
            "min_step": temp_res["min_step"],
            "max_step": temp_res["max_step"],
            "unique_steps": temp_res["unique_steps"],
            "total_days": temp_res["total_days"],
        },
        "balance": bal_res,
        "entities": entity_res,
        "figures": [str(p.as_posix()) for p in plots],
    }
    
    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\n[+] Inspection summary facts saved to: {summary_path}")
    print("\n[+] PaySim dataset profiling completed successfully.")


if __name__ == "__main__":
    main()
