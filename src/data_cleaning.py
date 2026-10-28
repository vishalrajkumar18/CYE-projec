"""
data_cleaning.py — Defensive Data Hygiene, Boundary Clamping, and Ingestion Validation.

This module sanitizes raw datasets (equipment and fault codes) prior to feature
engineering and constraint solving. It serves as the primary system-level error
boundary against malformed hospital records, sensor glitches, and data corruption.

Defensive Boundaries Implemented:
---------------------------------
1. Deduplication: Eliminates duplicate equipment entries by device_id.
2. Clamping / Range Checks:
   - Utilisation percent > 100% clamped to 100%.
   - Operating hours < 0 clamped to 0.
   - Negative age < 0 clamped to 0.
3. Categorical Fallbacks:
   - Criticality outside valid set defaulted to 'Medium'.
   - Fault severity outside valid set defaulted to 'Medium'.
4. Missing Value Imputation:
   - Missing installation date imputed to '2020-01-01'.
   - Missing last_service_date explicitly flagged and passed through for downstream
     fail-safe maximum risk assignment.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any


def clean_equipment(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Sanitize the equipment DataFrame and enforce physical operational boundaries.

    Parameters
    ----------
    df : pd.DataFrame
        Raw equipment dataset containing device specifications, usage, and service dates.

    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, Any]]
        A tuple containing:
        - Cleaned pandas DataFrame with invalid values corrected.
        - Statistics dictionary summarizing sanitization actions.

    Defensive Rules:
    ----------------
    - Deduplicates on 'device_id'.
    - Imputes null 'installation_date' with baseline '2020-01-01'.
    - Clamps negative 'age_years' to 0.
    - Clamps 'utilisation_percent' > 100% to 100.0%.
    - Resets negative 'operating_hours' to 0.
    - Resets invalid 'criticality' (not in ['Low', 'Medium', 'High', 'Critical']) to 'Medium'.
    - Flags null 'last_service_date' without dropping rows.
    """
    stats = {
        'total_records': len(df),
        'duplicates_removed': 0,
        'missing_values_filled': 0,
        'invalid_utilisation_fixed': 0,
        'invalid_hours_fixed': 0,
        'invalid_criticality_fixed': 0,
        'missing_service_date_flagged': 0
    }
    
    # 1. Deduplication: Keep first occurrence of each unique device
    initial_len = len(df)
    df = df.drop_duplicates(subset=['device_id'])
    stats['duplicates_removed'] = initial_len - len(df)
    
    # 2. Impute missing installation dates with a conservative baseline
    if df['installation_date'].isnull().any():
        stats['missing_values_filled'] += df['installation_date'].isnull().sum()
        df['installation_date'] = df['installation_date'].fillna('2020-01-01')
        
    # 3. Handle negative age values resulting from input error
    df.loc[df['age_years'] < 0, 'age_years'] = 0
        
    # 4. Enforce physical upper bound on utilisation (cannot exceed 100%)
    invalid_util = df['utilisation_percent'] > 100
    if invalid_util.any():
        stats['invalid_utilisation_fixed'] = int(invalid_util.sum())
        df.loc[invalid_util, 'utilisation_percent'] = 100
        
    # 5. Fix negative operating hours
    invalid_hrs = df['operating_hours'] < 0
    if invalid_hrs.any():
        stats['invalid_hours_fixed'] = int(invalid_hrs.sum())
        df.loc[invalid_hrs, 'operating_hours'] = 0
        
    # 6. Fallback invalid criticality strings to safe default 'Medium'
    valid_crit = ['Low', 'Medium', 'High', 'Critical']
    invalid_crit = ~df['criticality'].isin(valid_crit)
    if invalid_crit.any():
        stats['invalid_criticality_fixed'] = int(invalid_crit.sum())
        df.loc[invalid_crit, 'criticality'] = 'Medium'
        
    # 7. Flag missing last service dates for safety-critical feature engineering
    missing_service = df['last_service_date'].isnull()
    if missing_service.any():
        stats['missing_service_date_flagged'] = int(missing_service.sum())
        # Retain None/NaN so feature engineering can trigger fail-safe maximum risk
        
    stats['valid_records'] = len(df)
    return df, stats


def clean_fault_codes(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Sanitize the fault codes DataFrame and validate error severities.

    Parameters
    ----------
    df : pd.DataFrame
        Raw fault codes dataset containing event logs, severities, and resolution hours.

    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, Any]]
        A tuple containing:
        - Cleaned pandas DataFrame.
        - Statistics dictionary summarizing sanitization actions.

    Defensive Rules:
    ----------------
    - Checks severity strings against allowed set: ['Low', 'Medium', 'High', 'Critical'].
    - Replaces invalid or unknown severities with fallback default 'Medium'.
    """
    stats = {
        'total_records': len(df),
        'invalid_severity_fixed': 0
    }
    
    valid_severity = ['Low', 'Medium', 'High', 'Critical']
    invalid_sev = ~df['severity'].isin(valid_severity)
    if invalid_sev.any():
        stats['invalid_severity_fixed'] = int(invalid_sev.sum())
        df.loc[invalid_sev, 'severity'] = 'Medium'  # Safe operational default
        
    return df, stats


def clean_all_data(
    equipment_df: pd.DataFrame,
    fault_df: pd.DataFrame
) -> Tuple[pd.DataFrame, Dict[str, Any], pd.DataFrame, Dict[str, Any]]:
    """
    Execute full data cleaning pipeline for equipment and fault datasets.

    Parameters
    ----------
    equipment_df : pd.DataFrame
        Raw equipment dataset.
    fault_df : pd.DataFrame
        Raw fault records dataset.

    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, Any], pd.DataFrame, Dict[str, Any]]
        Cleaned equipment DataFrame, equipment cleaning stats,
        cleaned fault DataFrame, fault cleaning stats.
    """
    clean_eq_df, eq_stats = clean_equipment(equipment_df)
    clean_fault_df, fault_stats = clean_fault_codes(fault_df)
    return clean_eq_df, eq_stats, clean_fault_df, fault_stats
