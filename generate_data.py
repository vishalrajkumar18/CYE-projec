import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

def generate_equipment(num_records=50):
    equipment_types = ['MRI', 'CT', 'X-Ray', 'Ultrasound', 'Mammography', 'PET/CT']
    manufacturers = ['HealthTech', 'MedSys', 'ScanCorp', 'ImagingPro']
    status_list = ['Operational', 'Under Maintenance', 'Out of Service']
    locations = ['Scan Room 1', 'Scan Room 2', 'Scan Room 3', 'Emergency', 'Imaging Wing A', 'Imaging Wing B']
    criticality_levels = ['Low', 'Medium', 'High', 'Critical']
    
    data = []
    base_date = datetime(2026, 9, 1)
    
    for i in range(num_records):
        device_id = f"DEV{str(i+1).zfill(3)}"
        device_type = random.choice(equipment_types)
        manufacturer = random.choice(manufacturers)
        model = f"{device_type}-X{random.randint(100, 999)}"
        
        # Age between 1 and 15 years
        age_years = random.randint(1, 15)
        installation_date = base_date - timedelta(days=365*age_years)
        
        # Edge cases
        if i == 0:
            # Case 1: High Usage, No Faults
            utilisation_percent = 95
        elif i == 1:
            # Case 2: Low Usage, High Fault Frequency
            utilisation_percent = 20
        else:
            utilisation_percent = random.randint(30, 95)
            
        # Introduce some bad data
        if i == 5: utilisation_percent = 150  # Bad data > 100
        if i == 6: age_years = -5 # Bad data
        
        available_hours = 2000
        operating_hours = int((utilisation_percent / 100) * available_hours)
        if i == 7: operating_hours = -100 # Negative hours
        
        criticality = random.choice(criticality_levels)
        if i == 8: criticality = "SuperHigh" # Invalid criticality
        
        # Last service date (usually within last 1-2 years)
        if i == 9:
            last_service_date = None # Missing data
        else:
            days_since_service = random.randint(30, 400)
            last_service_date = base_date - timedelta(days=days_since_service)
        
        maintenance_interval_days = random.choice([90, 180, 365])
        status = random.choice(status_list)
        location = random.choice(locations)
        
        data.append({
            'device_id': device_id,
            'device_type': device_type,
            'manufacturer': manufacturer,
            'model': model,
            'installation_date': installation_date.strftime('%Y-%m-%d') if installation_date else None,
            'age_years': age_years,
            'utilisation_percent': utilisation_percent,
            'operating_hours': operating_hours,
            'available_hours': available_hours,
            'criticality': criticality,
            'last_service_date': last_service_date.strftime('%Y-%m-%d') if last_service_date else None,
            'maintenance_interval_days': maintenance_interval_days,
            'status': status,
            'location': location
        })
        
    # Edge case 5: Missing service history completely. 
    # Device DEV010 (i=9) has None last_service_date.
    
    df = pd.DataFrame(data)
    # Add some duplicate records
    df = pd.concat([df, df.iloc[[2, 3]]], ignore_index=True)
    return df

def generate_service_history(equipment_df):
    service_types = ['Preventive Maintenance', 'Corrective Maintenance', 'Inspection', 'Calibration']
    results = ['Success', 'Follow-up Required', 'Parts Ordered']
    
    data = []
    service_id_counter = 1
    base_date = datetime(2026, 9, 1)
    
    for _, row in equipment_df.iterrows():
        device_id = row['device_id']
        
        # Exclude device 10 from service history (Missing data edge case)
        if device_id == 'DEV010':
            continue
            
        num_services = random.randint(1, 5)
        for _ in range(num_services):
            service_date = base_date - timedelta(days=random.randint(10, 700))
            data.append({
                'service_id': f"SRV{str(service_id_counter).zfill(4)}",
                'device_id': device_id,
                'service_date': service_date.strftime('%Y-%m-%d'),
                'service_type': random.choice(service_types),
                'duration_hours': random.randint(1, 8),
                'technician_id': f"T{str(random.randint(1, 5)).zfill(3)}",
                'service_result': random.choice(results),
                'issues_found': 'None' if random.random() > 0.3 else 'Minor issue repaired'
            })
            service_id_counter += 1
            
    df = pd.DataFrame(data)
    return df

def generate_fault_codes(equipment_df):
    fault_codes_list = ['F001 - Temperature Warning', 'F002 - Sensor Error', 'F003 - Power Error', 'F004 - Communication Error', 'F005 - Calibration Warning']
    severities = ['Low', 'Medium', 'High', 'Critical']
    
    data = []
    fault_id_counter = 1
    base_date = datetime(2026, 9, 1)
    
    for _, row in equipment_df.iterrows():
        device_id = row['device_id']
        
        # Case 1: High Usage, No Faults -> DEV001
        if device_id == 'DEV001':
            num_faults = 0
        # Case 2: Low Usage, High Faults -> DEV002
        elif device_id == 'DEV002':
            num_faults = 10
        else:
            num_faults = random.randint(0, 4)
            
        for _ in range(num_faults):
            fault_date = base_date - timedelta(days=random.randint(1, 365))
            severity = random.choice(severities)
            # Introduce bad severity for data cleaning
            if fault_id_counter == 15: severity = 'Unknown'
            
            data.append({
                'fault_id': f"FLT{str(fault_id_counter).zfill(4)}",
                'device_id': device_id,
                'fault_date': fault_date.strftime('%Y-%m-%d'),
                'fault_code': random.choice(fault_codes_list),
                'severity': severity,
                'resolved': random.choice([True, False]),
                'resolution_hours': random.randint(1, 48) if random.random() > 0.2 else None
            })
            fault_id_counter += 1
            
    df = pd.DataFrame(data)
    return df

def generate_bookings(equipment_df):
    statuses = ['Scheduled', 'Completed', 'Cancelled']
    
    data = []
    booking_id_counter = 1
    base_date = datetime(2026, 9, 1)
    
    for _, row in equipment_df.iterrows():
        device_id = row['device_id']
        # Generate bookings for the next 30 days
        num_bookings = random.randint(10, 40)
        
        for _ in range(num_bookings):
            day_offset = random.randint(0, 30)
            hour_start = random.randint(8, 16) # 8 AM to 4 PM
            start_datetime = base_date + timedelta(days=day_offset, hours=hour_start)
            end_datetime = start_datetime + timedelta(hours=random.choice([1, 2]))
            
            data.append({
                'booking_id': f"BKG{str(booking_id_counter).zfill(4)}",
                'device_id': device_id,
                'start_datetime': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'end_datetime': end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'booking_status': random.choice(statuses)
            })
            booking_id_counter += 1
            
    # Case 3: No available slots for DEV003
    # Let's fully book it from 8 AM to 6 PM for the next 7 days
    device_id = 'DEV003'
    for day_offset in range(7):
        for hour in range(8, 18):
            start_datetime = base_date + timedelta(days=day_offset, hours=hour)
            end_datetime = start_datetime + timedelta(hours=1)
            data.append({
                'booking_id': f"BKG{str(booking_id_counter).zfill(4)}",
                'device_id': device_id,
                'start_datetime': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'end_datetime': end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'booking_status': 'Scheduled'
            })
            booking_id_counter += 1
            
    df = pd.DataFrame(data)
    return df

def generate_technicians():
    data = [
        {'technician_id': 'T001', 'name': 'Alice Smith', 'specialisation': 'MRI, CT', 'available_days': 'Monday, Tuesday, Wednesday, Thursday, Friday', 'start_time': '08:00', 'end_time': '16:00', 'active': True},
        {'technician_id': 'T002', 'name': 'Bob Johnson', 'specialisation': 'X-Ray, Ultrasound', 'available_days': 'Monday, Wednesday, Friday', 'start_time': '09:00', 'end_time': '17:00', 'active': True},
        {'technician_id': 'T003', 'name': 'Charlie Brown', 'specialisation': 'All', 'available_days': 'Tuesday, Thursday, Saturday', 'start_time': '10:00', 'end_time': '18:00', 'active': True},
        {'technician_id': 'T004', 'name': 'Diana Prince', 'specialisation': 'Mammography, PET/CT', 'available_days': 'Monday, Tuesday, Wednesday, Thursday, Friday', 'start_time': '08:00', 'end_time': '16:00', 'active': True},
        {'technician_id': 'T005', 'name': 'Evan Wright', 'specialisation': 'MRI', 'available_days': 'Monday, Friday', 'start_time': '08:00', 'end_time': '16:00', 'active': False},
    ]
    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    
    np.random.seed(42)
    random.seed(42)
    
    equipment_df = generate_equipment(50)
    equipment_df.to_csv('data/equipment.csv', index=False)
    print("Generated equipment.csv")
    
    service_history_df = generate_service_history(equipment_df)
    service_history_df.to_csv('data/service_history.csv', index=False)
    print("Generated service_history.csv")
    
    fault_codes_df = generate_fault_codes(equipment_df)
    fault_codes_df.to_csv('data/fault_codes.csv', index=False)
    print("Generated fault_codes.csv")
    
    bookings_df = generate_bookings(equipment_df)
    bookings_df.to_csv('data/bookings.csv', index=False)
    print("Generated bookings.csv")
    
    technicians_df = generate_technicians()
    technicians_df.to_csv('data/technicians.csv', index=False)
    print("Generated technicians.csv")
    
    print("All synthetic datasets generated successfully.")
