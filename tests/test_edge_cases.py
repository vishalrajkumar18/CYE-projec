import pytest
import pandas as pd
from datetime import datetime

from src.data_cleaning import clean_all_data
from src.feature_engineering import engineer_features
from src.risk_engine import calculate_risk_score
from src.constraints import check_hard_constraints
from src.authentication import has_permission

def test_case_1_high_usage_no_faults():
    eq_df = pd.DataFrame([{
        'device_id': 'DEV001', 'device_type': 'MRI', 'age_years': 5, 
        'utilisation_percent': 95, 'operating_hours': 1900, 'criticality': 'High',
        'installation_date': '2021-01-01', 'last_service_date': '2025-01-01', 'maintenance_interval_days': 180, 'status': 'Operational'
    }])
    fault_df = pd.DataFrame(columns=['device_id', 'severity']) # No faults
    
    clean_eq, _, clean_fault, _ = clean_all_data(eq_df, fault_df)
    features = engineer_features(clean_eq, clean_fault)
    risk = calculate_risk_score(features).iloc[0]
    
    # High utilisation alone should bump risk score
    # 95 utilisation = 95 score -> 95 * 0.30 = 28.5
    # age 5 = (5/15)*100 = 33.3 -> 33.3 * 0.20 = 6.66
    # crit High = 75 -> 75 * 0.15 = 11.25
    # Service (2025-01-01 to 2026-09-01 = ~600 days) -> score 100 * 0.15 = 15
    # Total ~ 61 -> High risk
    assert risk['overall_risk_score'] > 50

def test_case_2_low_usage_high_faults():
    eq_df = pd.DataFrame([{
        'device_id': 'DEV002', 'device_type': 'MRI', 'age_years': 2, 
        'utilisation_percent': 20, 'operating_hours': 400, 'criticality': 'Low',
        'installation_date': '2024-01-01', 'last_service_date': '2026-08-01', 'maintenance_interval_days': 180, 'status': 'Operational'
    }])
    faults = [{'device_id': 'DEV002', 'severity': 'High'} for _ in range(10)]
    fault_df = pd.DataFrame(faults)
    
    clean_eq, _, clean_fault, _ = clean_all_data(eq_df, fault_df)
    features = engineer_features(clean_eq, clean_fault)
    risk = calculate_risk_score(features).iloc[0]
    
    # Low usage but high faults -> max fault score 100 -> 100 * 0.2 = 20
    assert risk['risk_breakdown']['fault_contribution'] >= 20.0

def test_case_3_no_available_slot():
    # If device is booked 8-18 every day, hard constraint should fail
    start_dt = datetime(2026, 9, 2, 9, 0)
    end_dt = datetime(2026, 9, 2, 11, 0)
    
    # Booking conflicts with start_dt
    bookings_df = pd.DataFrame([{
        'booking_id': 'B1', 'device_id': 'DEV003', 'booking_status': 'Scheduled',
        'start_datetime': '2026-09-02 08:00:00', 'end_datetime': '2026-09-02 18:00:00'
    }])
    technicians_df = pd.DataFrame([{
        'technician_id': 'T001', 'active': True, 'available_days': 'Wednesday',
        'start_time': '08:00', 'end_time': '16:00'
    }])
    
    is_valid, constraints = check_hard_constraints(start_dt, end_dt, 'DEV003', 'T001', bookings_df, technicians_df)
    assert not is_valid
    assert constraints['No Booking Conflict'] == False

def test_case_4_unauthorised_override():
    # Technician role trying to override
    assert not has_permission('Technician', 'override')
    assert has_permission('Maintenance Manager', 'override')
    assert has_permission('Admin', 'override')
    assert not has_permission('Operations Staff', 'override')

def test_case_5_missing_data():
    eq_df = pd.DataFrame([{
        'device_id': 'DEV010', 'device_type': 'MRI', 'age_years': 5, 
        'utilisation_percent': 50, 'operating_hours': 1000, 'criticality': 'Medium',
        'installation_date': '2021-01-01', 'last_service_date': None, 'maintenance_interval_days': 180, 'status': 'Operational'
    }])
    fault_df = pd.DataFrame(columns=['device_id', 'severity'])
    
    clean_eq, stats, clean_fault, _ = clean_all_data(eq_df, fault_df)
    features = engineer_features(clean_eq, clean_fault)
    
    # Should flag missing data
    assert stats['missing_service_date_flagged'] == 1
    # Feature eng should handle it gracefully and assign high risk (100) for service score
    assert features.iloc[0]['service_score'] == 100
