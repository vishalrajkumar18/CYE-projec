"""
run_evaluation.py — Seeded, end-to-end evaluation script.

Usage (from project root, after activating venv):
    python run_evaluation.py

This script is designed to be run on a fresh clone immediately after
    python generate_data.py

Seeds are documented inline so results are fully reproducible.

Exit code: 0 if reduction_percent >= 20 (project target), 1 otherwise.
"""

import sys
import os
import random
import numpy as np
import pandas as pd

# ── Documented seeds ────────────────────────────────────────────────────────
DATA_SEED = 42          # matches generate_data.py
EVAL_SEED = 42          # matches evaluation.EVAL_SEED

random.seed(DATA_SEED)
np.random.seed(DATA_SEED)

# Ensure src is importable when script is run from project root
sys.path.insert(0, os.path.dirname(__file__))

from src.data_cleaning import clean_all_data
from src.feature_engineering import engineer_features
from src.risk_engine import calculate_risk_score
from src.planner import generate_schedule
from src.evaluation import calculate_evaluation_metrics, EVAL_SEED as MODULE_SEED

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

TARGET_REDUCTION_PERCENT = 20.0   # project requirement


def load_data():
    required = ['equipment.csv', 'fault_codes.csv', 'bookings.csv', 'technicians.csv']
    for f in required:
        path = os.path.join(DATA_DIR, f)
        if not os.path.exists(path):
            print(f"[ERROR] Missing data file: {path}")
            print("       Run:  python generate_data.py  to generate synthetic data.")
            sys.exit(1)

    equipment_df = pd.read_csv(os.path.join(DATA_DIR, 'equipment.csv'))
    fault_df = pd.read_csv(os.path.join(DATA_DIR, 'fault_codes.csv'))
    bookings_df = pd.read_csv(os.path.join(DATA_DIR, 'bookings.csv'))
    technicians_df = pd.read_csv(os.path.join(DATA_DIR, 'technicians.csv'))
    return equipment_df, fault_df, bookings_df, technicians_df


def main():
    print("=" * 65)
    print("  Maintenance Planner — Seeded End-to-End Evaluation")
    print(f"  DATA_SEED={DATA_SEED}  EVAL_SEED={EVAL_SEED}")
    print("=" * 65)

    # ── 1. Load ──────────────────────────────────────────────────────────
    print("\n[1/5] Loading synthetic data...")
    equipment_df, fault_df, bookings_df, technicians_df = load_data()
    print(f"      Equipment records (raw): {len(equipment_df)}")
    print(f"      Fault records     (raw): {len(fault_df)}")

    # ── 2. Clean ─────────────────────────────────────────────────────────
    print("\n[2/5] Cleaning data...")
    clean_eq, eq_stats, clean_fault, fault_stats = clean_all_data(equipment_df, fault_df)
    print(f"      Duplicates removed       : {eq_stats['duplicates_removed']}")
    print(f"      Invalid utilisation fixed: {eq_stats['invalid_utilisation_fixed']}")
    print(f"      Invalid criticality fixed: {eq_stats['invalid_criticality_fixed']}")
    print(f"      Invalid severity fixed   : {fault_stats['invalid_severity_fixed']}")
    print(f"      Missing service dates    : {eq_stats['missing_service_date_flagged']}")
    print(f"      Valid equipment records  : {eq_stats['valid_records']}")

    # ── 3. Feature Engineering & Risk Scoring ────────────────────────────
    print("\n[3/5] Engineering features and scoring risk...")
    features_df = engineer_features(clean_eq, clean_fault)
    scored_df = calculate_risk_score(features_df)
    category_counts = scored_df['risk_category'].value_counts().to_dict()
    print(f"      Risk distribution: {category_counts}")

    # ── 4. Generate Schedule ─────────────────────────────────────────────
    print("\n[4/5] Generating usage-based maintenance schedule...")
    schedule_df = generate_schedule(scored_df, bookings_df, technicians_df)
    scheduled = (schedule_df['status'] == 'Pending Approval').sum()
    failed = schedule_df['status'].str.startswith('Failed').sum()
    print(f"      Scheduled: {scheduled}/{len(schedule_df)}  |  Failed: {failed}")

    # ── 5. Evaluate ──────────────────────────────────────────────────────
    print(f"\n[5/5] Running traceable evaluation (seed={EVAL_SEED})...")

    # Pass the full (uncleaned) fault_df that still has fault_date / resolved columns
    # but use clean_eq for equipment metadata
    metrics = calculate_evaluation_metrics(
        clean_eq, fault_df, schedule_df, seed=EVAL_SEED
    )

    b = metrics['baseline']
    p = metrics['proposed']
    ld = metrics['low_disruption']
    reduction = metrics['reduction_percent']

    print("\n" + "─" * 65)
    print(f"  {'Strategy':<28} {'Unplanned(h)':>12} {'Planned(h)':>10} {'Avail%':>8}")
    print("─" * 65)
    print(f"  {'Calendar-Only (Baseline)':<28} {b['unplanned_downtime']:>12.1f} {b['planned_downtime']:>10.1f} {b['availability_percent']:>7.2f}%")
    print(f"  {'Usage-Based (Proposed)':<28} {p['unplanned_downtime']:>12.1f} {p['planned_downtime']:>10.1f} {p['availability_percent']:>7.2f}%")
    print(f"  {'Low-Disruption':<28} {ld['unplanned_downtime']:>12.1f} {ld['planned_downtime']:>10.1f} {ld['availability_percent']:>7.2f}%")
    print("─" * 65)
    print(f"\n  Unplanned downtime reduction: {reduction:.1f}%")
    print(f"  Baseline schedule conflicts : {b['schedule_conflicts']}")
    print(f"  Proposed schedule conflicts : {p['schedule_conflicts']}")
    print(f"\n  Methodology: {metrics['methodology_note']}")
    print("─" * 65)

    # ── Pass/Fail gate ──────────────────────────────────────────────────
    if reduction >= TARGET_REDUCTION_PERCENT:
        print(f"\n  ✅  PASS — Reduction {reduction:.1f}% >= target {TARGET_REDUCTION_PERCENT}%\n")
        return 0
    else:
        print(f"\n  ❌  FAIL — Reduction {reduction:.1f}% < target {TARGET_REDUCTION_PERCENT}%\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
