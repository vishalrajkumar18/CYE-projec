"""
feature_engineering.py — Feature Extraction, Mathematical Normalization, and Fail-Safe Scoring.

This module converts cleaned raw equipment metrics into standardized, normalized
sub-scores on a uniform scale of 0 to 100:
- Utilisation Score (0 to 100): Operational wear from duty cycle.
- Age Score (0 to 100): Equipment obsolescence against a 15-year ceiling.
- Criticality Score (25, 50, 75, 100): Clinical and diagnostic operational priority.
- Fault Score (0 to 100): Severity-weighted penalty for recent errors.
- Service Score (0 to 100): Maintenance urgency based on elapsed interval ratio.

Safety-Critical Default Principle:
----------------------------------
In shared medical diagnostic equipment, the absence or loss of service records
must NEVER be treated as "healthy" or "low risk." If `last_service_date` is
missing, corrupted, or unparseable, `calculate_service_score` assigns the maximum
risk score of 100.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Any

# Anchor date used as reference point for synthetic dataset calculations
BASE_DATE = datetime(2026, 9, 1)


def calculate_utilisation_score(utilisation_percent: float) -> float:
    """
    Map equipment utilisation percentage directly to a 0–100 risk score.

    Parameters
    ----------
    utilisation_percent : float
        Percentage of operating hours over available hours (0% to 100%).

    Returns
    -------
    float
        Score bounded between 0 and 100.
    """
    return min(max(float(utilisation_percent), 0.0), 100.0)


def calculate_age_score(age_years: float) -> float:
    """
    Normalize equipment age against a 15-year diagnostic equipment lifecycle.

    Formula:
    --------
    Age Score = min((age_years / 15.0) * 100, 100)

    Parameters
    ----------
    age_years : float
        Equipment operating age in years.

    Returns
    -------
    float
        Score bounded between 0 (new) and 100 (15+ years old).
    """
    return min((max(float(age_years), 0.0) / 15.0) * 100.0, 100.0)


def calculate_criticality_score(criticality: str) -> float:
    """
    Map categorical clinical criticality to a discrete numeric risk level.

    Mapping:
    --------
    - 'Low'      -> 25.0
    - 'Medium'   -> 50.0
    - 'High'     -> 75.0
    - 'Critical' -> 100.0 (e.g., sole emergency department CT scanner)

    Parameters
    ----------
    criticality : str
        Criticality tier designation.

    Returns
    -------
    float
        Numeric score (defaults to 50.0 for unknown levels).
    """
    mapping = {'Low': 25.0, 'Medium': 50.0, 'High': 75.0, 'Critical': 100.0}
    return mapping.get(str(criticality).strip(), 50.0)


def calculate_fault_score(device_id: str, fault_df: pd.DataFrame) -> float:
    """
    Compute a cumulative fault penalty score based on error codes and severities.

    Severity Weights:
    -----------------
    - 'Low'      -> 10 points
    - 'Medium'   -> 25 points
    - 'High'     -> 50 points
    - 'Critical' -> 100 points

    Parameters
    ----------
    device_id : str
        Target device identifier (e.g., 'DEV001').
    fault_df : pd.DataFrame
        Fault codes dataset containing 'device_id' and 'severity' columns.

    Returns
    -------
    float
        Cumulative severity score capped at 100.0.
    """
    device_faults = fault_df[fault_df['device_id'] == device_id]
    if device_faults.empty:
        return 0.0
        
    severity_weights = {'Low': 10.0, 'Medium': 25.0, 'High': 50.0, 'Critical': 100.0}
    
    total_score = 0.0
    for _, fault in device_faults.iterrows():
        total_score += severity_weights.get(fault.get('severity', 'Medium'), 25.0)
        
    # Cap total penalty score at 100
    return min(total_score, 100.0)


def calculate_service_score(
    last_service_date_str: Optional[str],
    maintenance_interval_days: int
) -> float:
    """
    Compute maintenance urgency score based on time elapsed since last service.

    Formula:
    --------
    ratio = days_since_service / maintenance_interval_days
    score = min(max(ratio * 50, 0), 100)
    (At 1.0 interval elapsed -> score 50; at 2.0 intervals elapsed -> score 100)

    Safety-Critical Error Boundary:
    -------------------------------
    - If `last_service_date_str` is None, NaN, empty, or unparseable, this
      function returns 100.0 (maximum risk). This prevents machines with missing
      maintenance documentation from being erroneously categorized as low-risk.

    Parameters
    ----------
    last_service_date_str : str, optional
        Date string formatted as 'YYYY-MM-DD' representing last service date.
    maintenance_interval_days : int
        Recommended manufacturer maintenance cycle in days (e.g., 90, 180, 365).

    Returns
    -------
    float
        Score between 0 and 100.
    """
    if pd.isna(last_service_date_str) or not last_service_date_str:
        # Edge case / Fail-Safe: Missing data assigned maximum risk
        return 100.0
        
    try:
        last_service = datetime.strptime(str(last_service_date_str).strip()[:10], '%Y-%m-%d')
        days_since_service = (BASE_DATE - last_service).days
        
        interval = max(int(maintenance_interval_days), 1)
        ratio = days_since_service / interval
        score = ratio * 50.0  # 1 interval = 50, 2 intervals = 100
        return min(max(score, 0.0), 100.0)
    except Exception:
        # Defensive fallback: If date parsing fails, assume highest risk
        return 100.0


def engineer_features(equipment_df: pd.DataFrame, fault_df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform raw equipment and fault datasets into a normalized feature matrix.

    Parameters
    ----------
    equipment_df : pd.DataFrame
        Cleaned equipment dataset.
    fault_df : pd.DataFrame
        Cleaned fault records dataset.

    Returns
    -------
    pd.DataFrame
        Normalized feature DataFrame with columns:
        ['device_id', 'utilisation_score', 'age_score', 'criticality_score',
         'fault_score', 'service_score']
    """
    features = []
    
    for _, row in equipment_df.iterrows():
        device_id = row['device_id']
        u_score = calculate_utilisation_score(row.get('utilisation_percent', 50))
        a_score = calculate_age_score(row.get('age_years', 5))
        c_score = calculate_criticality_score(row.get('criticality', 'Medium'))
        f_score = calculate_fault_score(device_id, fault_df)
        s_score = calculate_service_score(
            row.get('last_service_date'),
            row.get('maintenance_interval_days', 180)
        )
        
        features.append({
            'device_id': device_id,
            'utilisation_score': u_score,
            'age_score': a_score,
            'criticality_score': c_score,
            'fault_score': f_score,
            'service_score': s_score
        })
        
    return pd.DataFrame(features)
