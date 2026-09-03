import pandas as pd

DEFAULT_WEIGHTS = {
    'utilisation': 0.30,
    'age': 0.20,
    'fault': 0.20,
    'service': 0.15,
    'criticality': 0.15
}

def calculate_risk_score(features_df, weights=None):
    if weights is None:
        weights = DEFAULT_WEIGHTS
        
    df = features_df.copy()
    
    # Calculate overall risk score
    df['overall_risk_score'] = (
        df['utilisation_score'] * weights['utilisation'] +
        df['age_score'] * weights['age'] +
        df['fault_score'] * weights['fault'] +
        df['service_score'] * weights['service'] +
        df['criticality_score'] * weights['criticality']
    )
    
    # Categorize
    def categorize_risk(score):
        if score <= 30: return 'Low'
        if score <= 60: return 'Medium'
        if score <= 80: return 'High'
        return 'Critical'
        
    df['risk_category'] = df['overall_risk_score'].apply(categorize_risk)
    
    # Generate explainability breakdown
    def generate_breakdown(row):
        return {
            'utilisation_contribution': round(row['utilisation_score'] * weights['utilisation'], 2),
            'age_contribution': round(row['age_score'] * weights['age'], 2),
            'fault_contribution': round(row['fault_score'] * weights['fault'], 2),
            'service_contribution': round(row['service_score'] * weights['service'], 2),
            'criticality_contribution': round(row['criticality_score'] * weights['criticality'], 2)
        }
        
    df['risk_breakdown'] = df.apply(generate_breakdown, axis=1)
    
    return df
