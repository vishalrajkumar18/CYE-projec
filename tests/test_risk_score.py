import pytest
import pandas as pd
from src.feature_engineering import calculate_utilisation_score, calculate_age_score, calculate_criticality_score, calculate_service_score
from src.risk_engine import calculate_risk_score, DEFAULT_WEIGHTS

def test_utilisation_score():
    assert calculate_utilisation_score(50) == 50
    assert calculate_utilisation_score(150) == 100 # Capped
    assert calculate_utilisation_score(-10) == 0

def test_age_score():
    assert calculate_age_score(0) == 0
    assert calculate_age_score(15) == 100
    assert calculate_age_score(30) == 100

def test_criticality_score():
    assert calculate_criticality_score('Low') == 25
    assert calculate_criticality_score('Critical') == 100

def test_service_score():
    # Missing date -> 100
    assert calculate_service_score(None, 180) == 100

def test_risk_score_calculation():
    features = pd.DataFrame([{
        'device_id': 'DEV001',
        'utilisation_score': 100,
        'age_score': 100,
        'criticality_score': 100,
        'fault_score': 100,
        'service_score': 100
    }])
    
    result = calculate_risk_score(features, DEFAULT_WEIGHTS)
    assert result.iloc[0]['overall_risk_score'] == 100.0
    assert result.iloc[0]['risk_category'] == 'Critical'
