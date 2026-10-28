"""
risk_engine.py — Interpretable Multi-Factor Risk Scoring and Explainability Engine.

This module computes a composite risk score (0 to 100) for diagnostic equipment
by combining five normalized dimensions using an interpretable linear weighted sum:
- Utilisation Score (default weight 30%)
- Equipment Age Score (default weight 20%)
- Fault History Score (default weight 20%)
- Service Recency Score (default weight 15%)
- Clinical Criticality Score (default weight 15%)

Explainability & Transparency:
------------------------------
For clinical and operational confidence, every score calculation includes a
`risk_breakdown` dictionary detailing the exact point contribution of each
factor (e.g., utilisation contribution, fault contribution).

Risk Tiers:
-----------
- Low      : Score in [0, 30]
- Medium   : Score in (30, 60]
- High     : Score in (60, 80]
- Critical : Score in (80, 100]
"""

import pandas as pd
from typing import Dict, Optional, Any

# Operational baseline weights (configurable by Admin in UI / API)
DEFAULT_WEIGHTS: Dict[str, float] = {
    'utilisation': 0.30,
    'age': 0.20,
    'fault': 0.20,
    'service': 0.15,
    'criticality': 0.15
}


def calculate_risk_score(
    features_df: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    """
    Compute composite risk scores, categorical tiers, and explainability breakdowns.

    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame containing normalized sub-scores produced by `engineer_features()`.
        Must include columns: 'utilisation_score', 'age_score', 'fault_score',
        'service_score', 'criticality_score'.
    weights : dict of str -> float, optional
        Custom factor weights summing to 1.0. Defaults to `DEFAULT_WEIGHTS`.

    Returns
    -------
    pd.DataFrame
        Enriched DataFrame with additional columns:
        - 'overall_risk_score': Composite float score between 0.0 and 100.0.
        - 'risk_category': Categorical classification ('Low', 'Medium', 'High', 'Critical').
        - 'risk_breakdown': Dictionary of individual factor contributions.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
        
    df = features_df.copy()
    
    # 1. Compute composite weighted sum
    df['overall_risk_score'] = (
        df['utilisation_score'] * weights['utilisation'] +
        df['age_score'] * weights['age'] +
        df['fault_score'] * weights['fault'] +
        df['service_score'] * weights['service'] +
        df['criticality_score'] * weights['criticality']
    )
    
    # 2. Categorize into standardized risk tiers
    def categorize_risk(score: float) -> str:
        if score <= 30.0:
            return 'Low'
        if score <= 60.0:
            return 'Medium'
        if score <= 80.0:
            return 'High'
        return 'Critical'
        
    df['risk_category'] = df['overall_risk_score'].apply(categorize_risk)
    
    # 3. Generate granular explainability breakdown for audit and UI transparency
    def generate_breakdown(row: pd.Series) -> Dict[str, float]:
        return {
            'utilisation_contribution': round(float(row['utilisation_score']) * weights['utilisation'], 2),
            'age_contribution': round(float(row['age_score']) * weights['age'], 2),
            'fault_contribution': round(float(row['fault_score']) * weights['fault'], 2),
            'service_contribution': round(float(row['service_score']) * weights['service'], 2),
            'criticality_contribution': round(float(row['criticality_score']) * weights['criticality'], 2)
        }
        
    df['risk_breakdown'] = df.apply(generate_breakdown, axis=1)
    
    return df
