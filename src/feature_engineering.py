import pandas as pd
import numpy as np
from datetime import datetime

def calculate_utilisation_score(utilisation_percent):
    # Simply map 0-100% to 0-100 score
    return min(max(utilisation_percent, 0), 100)

def calculate_age_score(age_years):
    # Assume max age of concern is 15 years.
    # 0 years = 0 score, 15+ years = 100 score
    return min((age_years / 15.0) * 100, 100)

def calculate_criticality_score(criticality):
    mapping = {'Low': 25, 'Medium': 50, 'High': 75, 'Critical': 100}
    return mapping.get(criticality, 50)

def calculate_fault_score(device_id, fault_df):
    device_faults = fault_df[fault_df['device_id'] == device_id]
    if device_faults.empty:
        return 0
        
    severity_weights = {'Low': 10, 'Medium': 25, 'High': 50, 'Critical': 100}
    
    total_score = 0
    for _, fault in device_faults.iterrows():
        total_score += severity_weights.get(fault['severity'], 25)
        
    # Cap at 100
    return min(total_score, 100)

def calculate_service_score(last_service_date_str, maintenance_interval_days):
    if pd.isna(last_service_date_str) or not last_service_date_str:
        # Edge case: Missing data. High risk.
        return 100
        
    try:
        last_service = datetime.strptime(last_service_date_str, '%Y-%m-%d')
        # Base date is 2026-09-01
        base_date = datetime(2026, 9, 1)
        days_since_service = (base_date - last_service).days
        
        # If days_since_service > maintenance_interval_days, score goes up quickly
        ratio = days_since_service / maintenance_interval_days
        score = ratio * 50 # 1 interval = 50, 2 intervals = 100
        return min(max(score, 0), 100)
    except:
        return 100

def engineer_features(equipment_df, fault_df):
    features = []
    
    for _, row in equipment_df.iterrows():
        device_id = row['device_id']
        u_score = calculate_utilisation_score(row['utilisation_percent'])
        a_score = calculate_age_score(row['age_years'])
        c_score = calculate_criticality_score(row['criticality'])
        f_score = calculate_fault_score(device_id, fault_df)
        s_score = calculate_service_score(row['last_service_date'], row['maintenance_interval_days'])
        
        features.append({
            'device_id': device_id,
            'utilisation_score': u_score,
            'age_score': a_score,
            'criticality_score': c_score,
            'fault_score': f_score,
            'service_score': s_score
        })
        
    return pd.DataFrame(features)
