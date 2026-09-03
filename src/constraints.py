import pandas as pd
from datetime import datetime, timedelta

def check_hard_constraints(start_dt, end_dt, device_id, technician_id, bookings_df, technicians_df):
    """
    Checks if a proposed maintenance window satisfies hard constraints.
    Returns: (is_valid, constraint_details)
    """
    constraint_details = {
        'Technician Available': False,
        'No Booking Conflict': False,
        'Operational Window Valid': False
    }
    
    # 1. Operational Window (Assuming 8 AM to 6 PM operations, maintenance can be anytime but must fit)
    # Actually, the prompt says "Maintenance cannot be scheduled outside allowed operational hours."
    # Let's define operational hours as 08:00 to 18:00
    if start_dt.hour >= 8 and end_dt.hour <= 18:
        constraint_details['Operational Window Valid'] = True
        
    # 2. Technician Available
    tech = technicians_df[technicians_df['technician_id'] == technician_id]
    if not tech.empty and tech.iloc[0]['active']:
        tech_row = tech.iloc[0]
        day_name = start_dt.strftime('%A')
        if day_name in tech_row['available_days']:
            tech_start = datetime.strptime(tech_row['start_time'], '%H:%M').time()
            tech_end = datetime.strptime(tech_row['end_time'], '%H:%M').time()
            if start_dt.time() >= tech_start and end_dt.time() <= tech_end:
                constraint_details['Technician Available'] = True
                
    # 3. No Booking Conflict
    # Get bookings for this device
    device_bookings = bookings_df[(bookings_df['device_id'] == device_id) & (bookings_df['booking_status'] == 'Scheduled')]
    conflict = False
    for _, b in device_bookings.iterrows():
        b_start = datetime.strptime(b['start_datetime'], '%Y-%m-%d %H:%M:%S')
        b_end = datetime.strptime(b['end_datetime'], '%Y-%m-%d %H:%M:%S')
        # Check overlap
        if max(start_dt, b_start) < min(end_dt, b_end):
            conflict = True
            break
            
    if not conflict:
        constraint_details['No Booking Conflict'] = True
        
    is_valid = all(constraint_details.values())
    return is_valid, constraint_details

def check_soft_constraints(start_dt, end_dt, device_id, technician_id):
    """
    Checks soft constraints.
    Returns: constraint_details
    """
    details = {
        'Low Utilisation Period': False,
        'Preferred Technician': False,
        'Preferred Day Available': False
    }
    
    # Simple heuristics for soft constraints
    if start_dt.hour < 10 or start_dt.hour > 15:
        details['Low Utilisation Period'] = True
        
    details['Preferred Technician'] = True # Assume assigned technician is preferred for simplicity
    details['Preferred Day Available'] = True
    
    return details
