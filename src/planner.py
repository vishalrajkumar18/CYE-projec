"""
planner.py — Risk-Prioritized Maintenance Scheduling and Constraint Solver.

This module generates an operational preventive maintenance schedule by solving
for feasible time windows subject to hard constraints (technician working shifts,
operational facility hours, patient booking non-overlap).

Scheduling Strategy:
--------------------
1. Priority Queue: Devices are sorted by risk tier (Critical > High > Medium > Low).
   Critical assets receive earliest attention to prevent impending failures.
2. Search Horizon:
   - Critical : Target within 7 days.
   - High     : Target within 14 days.
   - Medium   : Target within 30 days.
   - Low      : Target within 90 days.
3. Constraint Satisfaction:
   Scans candidate time slots starting tomorrow at 08:00. For each candidate slot,
   checks active technicians and evaluates all hard constraints.
4. Error Boundary / Graceful Fallback:
   If no conflict-free slot can be found (e.g., 100% booking saturation), the planner
   records `'status': 'Failed: No available maintenance slot found'` rather than crashing.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
from src.constraints import check_hard_constraints, check_soft_constraints


def recommend_maintenance(
    device_id: str,
    risk_category: str,
    duration_hours: int,
    bookings_df: pd.DataFrame,
    technicians_df: pd.DataFrame,
    base_date_str: str = '2026-09-01'
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Search for the earliest feasible maintenance slot satisfying all hard constraints.

    Parameters
    ----------
    device_id : str
        Target equipment ID.
    risk_category : str
        Calculated risk category ('Critical', 'High', 'Medium', 'Low').
    duration_hours : int
        Estimated duration of the maintenance procedure in hours (default 2).
    bookings_df : pd.DataFrame
        Existing patient booking schedule.
    technicians_df : pd.DataFrame
        Technician availability and qualification records.
    base_date_str : str, default='2026-09-01'
        Planning anchor date.

    Returns
    -------
    Tuple[Optional[Dict[str, Any]], Optional[str]]
        - If feasible: (recommendation_dict, None)
          where recommendation_dict contains:
          ['recommended_date', 'end_date', 'duration_hours', 'technician_id',
           'hard_constraints', 'soft_constraints']
        - If unfeasible: (None, error_message_string)
    """
    base_date = datetime.strptime(base_date_str, '%Y-%m-%d')
    
    # Define priority target window based on risk severity
    if risk_category == 'Critical':
        target_days = 7
    elif risk_category == 'High':
        target_days = 14
    elif risk_category == 'Medium':
        target_days = 30
    else:
        target_days = 90
        
    # Begin search window starting tomorrow morning
    search_start = base_date + timedelta(days=1)
    
    # Filter to active technicians only
    active_techs = technicians_df[technicians_df['active'] == True]
    if active_techs.empty:
        return None, "No active technicians"
        
    # Search within the priority target window plus a 30-day overflow buffer
    for day_offset in range(target_days + 30):
        current_day = search_start + timedelta(days=day_offset)
        
        # Candidate daily operational hours: 08:00 to 18:00
        for hour in range(8, 18 - duration_hours + 1):
            start_dt = current_day.replace(hour=hour, minute=0, second=0)
            end_dt = start_dt + timedelta(hours=duration_hours)
            
            # Evaluate each qualified active technician for this candidate slot
            for _, tech in active_techs.iterrows():
                tech_id = tech['technician_id']
                
                is_valid, hard_constraints = check_hard_constraints(
                    start_dt, end_dt, device_id, tech_id, bookings_df, technicians_df
                )
                
                # First conflict-free slot meeting all hard constraints is selected
                if is_valid:
                    soft_constraints = check_soft_constraints(
                        start_dt, end_dt, device_id, tech_id
                    )
                    return {
                        'recommended_date': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'end_date': end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'duration_hours': duration_hours,
                        'technician_id': tech_id,
                        'hard_constraints': hard_constraints,
                        'soft_constraints': soft_constraints
                    }, None
                    
    # Hard constraints could not be satisfied within available search window
    return None, "No available maintenance slot found"


def generate_schedule(
    scored_df: pd.DataFrame,
    bookings_df: pd.DataFrame,
    technicians_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate an enterprise-wide maintenance schedule across all equipment.

    Equipment is prioritized by risk category so highest-risk machines are
    allocated optimal maintenance slots first.

    Parameters
    ----------
    scored_df : pd.DataFrame
        Equipment DataFrame containing 'device_id' and 'risk_category'.
    bookings_df : pd.DataFrame
        Active patient bookings schedule.
    technicians_df : pd.DataFrame
        Technician roster and availability.

    Returns
    -------
    pd.DataFrame
        Maintenance schedule DataFrame with columns:
        ['device_id', 'recommended_date', 'duration_hours', 'technician_id',
         'status', 'priority', 'hard_constraints', 'soft_constraints']
    """
    schedule = []
    
    # Priority rank: 1=Critical, 2=High, 3=Medium, 4=Low
    priority_order = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4}
    ordered_df = scored_df.copy()
    ordered_df['priority_rank'] = ordered_df['risk_category'].map(priority_order)
    ordered_df = ordered_df.sort_values('priority_rank')
    
    for _, row in ordered_df.iterrows():
        device_id = row['device_id']
        risk = row['risk_category']
        # Standard maintenance slot duration (2 hours)
        duration = 2
        
        rec, err = recommend_maintenance(
            device_id, risk, duration, bookings_df, technicians_df
        )
        
        if rec:
            schedule.append({
                'device_id': device_id,
                'recommended_date': rec['recommended_date'],
                'duration_hours': rec['duration_hours'],
                'technician_id': rec['technician_id'],
                'status': 'Pending Approval',
                'priority': risk,
                'hard_constraints': rec['hard_constraints'],
                'soft_constraints': rec['soft_constraints']
            })
        else:
            # Error boundary: record failure reason without halting generation loop
            schedule.append({
                'device_id': device_id,
                'recommended_date': None,
                'duration_hours': duration,
                'technician_id': None,
                'status': f'Failed: {err}',
                'priority': risk,
                'hard_constraints': {},
                'soft_constraints': {}
            })
            
    return pd.DataFrame(schedule)
