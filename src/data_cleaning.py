import pandas as pd
import numpy as np

def clean_equipment(df):
    stats = {
        'total_records': len(df),
        'duplicates_removed': 0,
        'missing_values_filled': 0,
        'invalid_utilisation_fixed': 0,
        'invalid_hours_fixed': 0,
        'invalid_criticality_fixed': 0,
        'missing_service_date_flagged': 0
    }
    
    # Remove duplicates
    initial_len = len(df)
    df = df.drop_duplicates(subset=['device_id'])
    stats['duplicates_removed'] = initial_len - len(df)
    
    # Fill missing values
    if df['installation_date'].isnull().any():
        stats['missing_values_filled'] += df['installation_date'].isnull().sum()
        df['installation_date'] = df['installation_date'].fillna('2020-01-01')
        
    # Handle negative age
    df.loc[df['age_years'] < 0, 'age_years'] = 0
        
    # Fix Utilisation > 100%
    invalid_util = df['utilisation_percent'] > 100
    if invalid_util.any():
        stats['invalid_utilisation_fixed'] = invalid_util.sum()
        df.loc[invalid_util, 'utilisation_percent'] = 100
        
    # Fix negative operating hours
    invalid_hrs = df['operating_hours'] < 0
    if invalid_hrs.any():
        stats['invalid_hours_fixed'] = invalid_hrs.sum()
        df.loc[invalid_hrs, 'operating_hours'] = 0
        
    # Fix invalid criticality
    valid_crit = ['Low', 'Medium', 'High', 'Critical']
    invalid_crit = ~df['criticality'].isin(valid_crit)
    if invalid_crit.any():
        stats['invalid_criticality_fixed'] = invalid_crit.sum()
        df.loc[invalid_crit, 'criticality'] = 'Medium' # Default
        
    # Flag missing service dates
    missing_service = df['last_service_date'].isnull()
    if missing_service.any():
        stats['missing_service_date_flagged'] = missing_service.sum()
        # We don't remove, we just keep as None/NaN and handle in feature engineering
        
    stats['valid_records'] = len(df)
    return df, stats

def clean_fault_codes(df):
    stats = {
        'total_records': len(df),
        'invalid_severity_fixed': 0
    }
    
    valid_severity = ['Low', 'Medium', 'High', 'Critical']
    invalid_sev = ~df['severity'].isin(valid_severity)
    if invalid_sev.any():
        stats['invalid_severity_fixed'] = invalid_sev.sum()
        df.loc[invalid_sev, 'severity'] = 'Medium' # Default
        
    return df, stats

def clean_all_data(equipment_df, fault_df):
    clean_eq_df, eq_stats = clean_equipment(equipment_df)
    clean_fault_df, fault_stats = clean_fault_codes(fault_df)
    return clean_eq_df, eq_stats, clean_fault_df, fault_stats
