"""
test_evaluation.py — Unit tests for the traceable evaluation module.

Verifies that:
  - Results are reproducible (same seed → same numbers)
  - Baseline unplanned downtime is always >= proposed (risk-priority wins)
  - reduction_percent is >= 0
  - methodology_note and seed fields are present
  - Devices without faults contribute 0 unplanned downtime
  - A device with all faults pre-empted contributes 0 proposed unplanned
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evaluation import (
    calculate_evaluation_metrics,
    _fault_unplanned_hours,
    _calendar_maintenance_date,
    _parse_date,
    EVAL_SEED,
    BASE_DATE,
    UNPLANNED_HOURS_PER_FAULT,
    PLANNED_HOURS_CALENDAR,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_equipment(device_id='DEV001', utilisation=60, age=5,
                    criticality='Medium', last_service_date='2026-07-01',
                    interval=180):
    return pd.DataFrame([{
        'device_id': device_id,
        'device_type': 'MRI',
        'utilisation_percent': utilisation,
        'operating_hours': 1200,
        'age_years': age,
        'criticality': criticality,
        'last_service_date': last_service_date,
        'maintenance_interval_days': interval,
        'status': 'Operational',
    }])


def _make_fault(device_id, fault_date, resolved=False, resolution_hours=8,
                severity='High'):
    return {
        'fault_id': 'FLT0001',
        'device_id': device_id,
        'fault_date': fault_date,
        'fault_code': 'F001',
        'severity': severity,
        'resolved': resolved,
        'resolution_hours': resolution_hours,
    }


def _make_schedule(device_id, recommended_date, status='Pending Approval',
                   duration=2):
    return pd.DataFrame([{
        'device_id': device_id,
        'recommended_date': recommended_date,
        'duration_hours': duration,
        'technician_id': 'T001',
        'status': status,
        'priority': 'Medium',
    }])


# ── Tests: helper functions ───────────────────────────────────────────────────

def test_parse_date_valid():
    d = _parse_date('2026-07-15')
    assert d == datetime(2026, 7, 15)


def test_parse_date_none():
    assert _parse_date(None) is None
    assert _parse_date('') is None
    assert _parse_date(float('nan')) is None


def test_parse_date_with_time_prefix():
    # Ensure it handles 'YYYY-MM-DD HH:MM:SS' correctly (takes first 10 chars)
    d = _parse_date('2026-09-01 08:00:00')
    assert d == datetime(2026, 9, 1)


def test_calendar_maintenance_date_normal():
    """last_service + interval should equal calendar date."""
    cal = _calendar_maintenance_date('2026-06-01', 90)
    assert cal == datetime(2026, 8, 30)


def test_calendar_maintenance_date_missing():
    """Missing last_service_date should return BASE_DATE + 1 day."""
    cal = _calendar_maintenance_date(None, 180)
    assert cal == BASE_DATE + timedelta(days=1)


def test_fault_unplanned_hours_no_faults():
    rng = np.random.default_rng(42)
    fault_df = pd.DataFrame(columns=['device_id', 'fault_date', 'resolved', 'resolution_hours'])
    hours = _fault_unplanned_hours('DEV001', fault_df, BASE_DATE, rng)
    assert hours == 0.0


def test_fault_unplanned_hours_resolved_fault_counts_zero():
    """A resolved fault should not contribute unplanned downtime."""
    rng = np.random.default_rng(42)
    # Use a date in the planning horizon
    fault_df = pd.DataFrame([_make_fault('DEV001', '2026-09-05', resolved=True)])
    cutoff = datetime(2026, 9, 10)
    hours = _fault_unplanned_hours('DEV001', fault_df, cutoff, rng)
    assert hours == 0.0


def test_fault_unplanned_hours_preempted_fault_counts_zero():
    """A planning-horizon fault on/after maintenance_cutoff should be pre-empted."""
    rng = np.random.default_rng(42)
    # Fault on same day as cutoff → pre-empted
    fault_df = pd.DataFrame([_make_fault('DEV001', '2026-09-10', resolved=False)])
    cutoff = datetime(2026, 9, 10)
    hours = _fault_unplanned_hours('DEV001', fault_df, cutoff, rng)
    assert hours == 0.0


def test_fault_unplanned_hours_historical_fault_excluded():
    """Faults before BASE_DATE are historical and must be excluded (scope filter)."""
    rng = np.random.default_rng(42)
    # Fault is before BASE_DATE (2026-09-01) — historical, always excluded
    fault_df = pd.DataFrame([_make_fault('DEV001', '2026-08-01', resolved=False)])
    cutoff = datetime(2026, 9, 15)  # any cutoff
    hours = _fault_unplanned_hours('DEV001', fault_df, cutoff, rng)
    assert hours == 0.0


def test_fault_unplanned_hours_before_cutoff_unresolved():
    """An unresolved planning-horizon fault before cutoff should contribute downtime."""
    rng = np.random.default_rng(42)
    # Fault in planning horizon, before cutoff
    fault_df = pd.DataFrame([_make_fault('DEV001', '2026-09-02', resolved=False, resolution_hours=6)])
    cutoff = datetime(2026, 9, 10)
    hours = _fault_unplanned_hours('DEV001', fault_df, cutoff, rng)
    assert hours == 6.0


def test_fault_unplanned_hours_capped_at_max():
    """resolution_hours > UNPLANNED_HOURS_PER_FAULT should be capped."""
    rng = np.random.default_rng(42)
    # Planning-horizon fault, unresolved, very long resolution time
    fault_df = pd.DataFrame([
        _make_fault('DEV001', '2026-09-02', resolved=False, resolution_hours=48)
    ])
    cutoff = datetime(2026, 9, 10)
    hours = _fault_unplanned_hours('DEV001', fault_df, cutoff, rng)
    assert hours == UNPLANNED_HOURS_PER_FAULT


def test_fault_unplanned_hours_imputes_missing_resolution_hours():
    """Missing resolution_hours should be imputed deterministically via seeded rng."""
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    # Planning-horizon fault with missing resolution_hours
    fault_df = pd.DataFrame([_make_fault('DEV001', '2026-09-05', resolved=False, resolution_hours=None)])
    fault_df['resolution_hours'] = float('nan')
    h1 = _fault_unplanned_hours('DEV001', fault_df, datetime(2026, 9, 15), rng1)
    h2 = _fault_unplanned_hours('DEV001', fault_df, datetime(2026, 9, 15), rng2)
    # Both rng instances with the same seed should produce the same result
    assert h1 == h2


# ── Tests: calculate_evaluation_metrics ───────────────────────────────────────

def test_evaluation_reproducible():
    """Same seed → identical results."""
    eq = _make_equipment()
    # Planning-horizon fault
    fault_df = pd.DataFrame([_make_fault('DEV001', '2026-09-10', resolved=False)])
    sched = _make_schedule('DEV001', '2026-09-05 08:00:00')

    m1 = calculate_evaluation_metrics(eq, fault_df, sched, seed=EVAL_SEED)
    m2 = calculate_evaluation_metrics(eq, fault_df, sched, seed=EVAL_SEED)
    assert m1['baseline']['unplanned_downtime'] == m2['baseline']['unplanned_downtime']
    assert m1['proposed']['unplanned_downtime'] == m2['proposed']['unplanned_downtime']
    assert m1['reduction_percent'] == m2['reduction_percent']


def test_evaluation_seed_in_output():
    """The returned dict must include the seed and methodology_note."""
    eq = _make_equipment()
    fault_df = pd.DataFrame(columns=['device_id', 'fault_date', 'resolved', 'resolution_hours', 'severity'])
    sched = _make_schedule('DEV001', '2026-09-05 08:00:00')

    m = calculate_evaluation_metrics(eq, fault_df, sched, seed=99)
    assert m['seed'] == 99
    assert 'methodology_note' in m
    assert 'EVAL_SEED=99' in m['methodology_note']


def test_evaluation_no_faults_zero_unplanned():
    """No faults → zero unplanned downtime in both strategies."""
    eq = _make_equipment()
    fault_df = pd.DataFrame(columns=['device_id', 'fault_date', 'resolved', 'resolution_hours', 'severity'])
    sched = _make_schedule('DEV001', '2026-09-05 08:00:00')

    m = calculate_evaluation_metrics(eq, fault_df, sched)
    assert m['baseline']['unplanned_downtime'] == 0.0
    assert m['proposed']['unplanned_downtime'] == 0.0


def test_evaluation_proposed_less_unplanned_than_baseline():
    """Usage-based scheduling should achieve <= unplanned downtime vs calendar."""
    # Fault on 2026-09-10 — after proposed date (2026-09-05) but before calendar date
    eq = _make_equipment(last_service_date='2026-01-01', interval=365)
    fault_df = pd.DataFrame([_make_fault('DEV001', '2026-09-10', resolved=False, resolution_hours=8)])
    # Calendar date = 2026-01-01 + 365 days = 2027-01-01 → fault NOT pre-empted by calendar
    # Proposed date = 2026-09-05 → fault (2026-09-10) IS pre-empted
    sched = _make_schedule('DEV001', '2026-09-05 08:00:00')

    m = calculate_evaluation_metrics(eq, fault_df, sched)
    # Proposed pre-empts the fault, baseline doesn't
    assert m['proposed']['unplanned_downtime'] == 0.0
    assert m['baseline']['unplanned_downtime'] > 0.0
    assert m['reduction_percent'] > 0


def test_evaluation_failed_schedule_falls_back_to_calendar():
    """A failed schedule entry should fall back to calendar behaviour."""
    eq = _make_equipment(last_service_date='2026-07-01', interval=180)
    # Calendar date = 2026-07-01 + 180 = 2026-12-28
    # Fault on 2026-10-01 → not pre-empted by calendar (2026-12-28 is later, fault is before)
    fault_df = pd.DataFrame([_make_fault('DEV001', '2026-10-01', resolved=False)])
    sched = _make_schedule('DEV001', None, status='Failed: No available slot')
    sched['duration_hours'] = 2

    m = calculate_evaluation_metrics(eq, fault_df, sched)
    # Failed schedule → same unplanned as baseline
    assert m['proposed']['unplanned_downtime'] == m['baseline']['unplanned_downtime']


def test_evaluation_reduction_percent_non_negative():
    """reduction_percent must be >= 0 when proposed schedule pre-empts more faults."""
    # Fault in planning horizon (2026-09-05), proposed cuts off before it (2026-09-02)
    # Calendar cutoff is after fault (2026-12-01) so fault not pre-empted by baseline
    eq = _make_equipment(last_service_date='2026-07-01', interval=153)  # cal ~2026-12-01
    fault_df = pd.DataFrame([_make_fault('DEV001', '2026-09-05', resolved=False)])
    sched = _make_schedule('DEV001', '2026-09-03 08:00:00')  # proposed < fault → pre-empts
    m = calculate_evaluation_metrics(eq, fault_df, sched)
    assert m['reduction_percent'] >= 0


def test_evaluation_planned_downtime_matches_schedule():
    """Proposed planned downtime should equal the scheduled duration_hours."""
    eq = _make_equipment()
    fault_df = pd.DataFrame(columns=['device_id', 'fault_date', 'resolved', 'resolution_hours', 'severity'])
    sched = _make_schedule('DEV001', '2026-09-05 08:00:00', duration=3)

    m = calculate_evaluation_metrics(eq, fault_df, sched)
    assert m['proposed']['planned_downtime'] == 3.0


def test_evaluation_baseline_planned_downtime_is_fixed_calendar():
    """Baseline planned downtime = n_devices * PLANNED_HOURS_CALENDAR."""
    n = 3
    rows = [_make_equipment(f'DEV00{i+1}') for i in range(n)]
    eq = pd.concat(rows, ignore_index=True)
    fault_df = pd.DataFrame(columns=['device_id', 'fault_date', 'resolved', 'resolution_hours', 'severity'])
    sched = pd.concat([_make_schedule(f'DEV00{i+1}', '2026-09-05 08:00:00') for i in range(n)], ignore_index=True)

    m = calculate_evaluation_metrics(eq, fault_df, sched)
    assert m['baseline']['planned_downtime'] == n * PLANNED_HOURS_CALENDAR


def test_evaluation_low_disruption_higher_unplanned_than_proposed():
    """Low-disruption unplanned must always exceed proposed unplanned (by 30%)."""
    eq = _make_equipment()
    # Planning-horizon fault so it shows up in proposed unplanned
    fault_df = pd.DataFrame([_make_fault('DEV001', '2026-09-05', resolved=False)])
    sched = _make_schedule('DEV001', '2026-09-10 08:00:00')  # after fault → not pre-empted

    m = calculate_evaluation_metrics(eq, fault_df, sched)
    assert m['low_disruption']['unplanned_downtime'] >= m['proposed']['unplanned_downtime']
