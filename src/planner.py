import pandas as pd
from datetime import datetime, timedelta
from src.constraints import check_hard_constraints, check_soft_constraints

def recommend_maintenance(device_id, risk_category, duration_hours, bookings_df, technicians_df, base_date_str='2026-09-01'):
    base_date = datetime.strptime(base_date_str, '%Y-%m-%d')
    
    # Determine target window based on risk
    if risk_category == 'Critical':
        target_days = 7
    elif risk_category == 'High':
        target_days = 14
    elif risk_category == 'Medium':
        target_days = 30
    else:
        target_days = 90
        
    # We will search for the first available slot within the target days
    # Start searching from tomorrow
    search_start = base_date + timedelta(days=1)
    
    # Active technicians
    active_techs = technicians_df[technicians_df['active'] == True]
    if active_techs.empty:
        return None, "No active technicians"
        
    for day_offset in range(target_days + 30): # Search beyond target if needed
        current_day = search_start + timedelta(days=day_offset)
        
        # Try slots from 8 AM to 4 PM (assuming 2 hour duration typically)
        for hour in range(8, 18 - duration_hours + 1):
            start_dt = current_day.replace(hour=hour, minute=0, second=0)
            end_dt = start_dt + timedelta(hours=duration_hours)
            
            # Try to assign to any active tech
            for _, tech in active_techs.iterrows():
                tech_id = tech['technician_id']
                
                is_valid, hard_constraints = check_hard_constraints(start_dt, end_dt, device_id, tech_id, bookings_df, technicians_df)
                
                if is_valid:
                    soft_constraints = check_soft_constraints(start_dt, end_dt, device_id, tech_id)
                    return {
                        'recommended_date': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'end_date': end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'duration_hours': duration_hours,
                        'technician_id': tech_id,
                        'hard_constraints': hard_constraints,
                        'soft_constraints': soft_constraints
                    }, None
                    
    return None, "No available maintenance slot found"

def generate_schedule(scored_df, bookings_df, technicians_df):
    schedule = []
    
    # Prioritize critical and high risk
    priority_order = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4}
    scored_df = scored_df.copy()
    scored_df['priority_rank'] = scored_df['risk_category'].map(priority_order)
    scored_df = scored_df.sort_values('priority_rank')
    
    for _, row in scored_df.iterrows():
        device_id = row['device_id']
        risk = row['risk_category']
        # Assume standard 2 hours maintenance
        duration = 2
        
        rec, err = recommend_maintenance(device_id, risk, duration, bookings_df, technicians_df)
        
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
