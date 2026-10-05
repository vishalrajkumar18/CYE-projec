import sqlite3
import pandas as pd
import os

DB_PATH = 'database/maintenance.db'
DATA_DIR = 'data/'

def init_db(force=False):
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    # Check if tables already exist, skip loading if they do.
    cursor = conn.cursor()
    cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='equipment'")
    exists = cursor.fetchone()[0] == 1
    cursor.close()
    conn.commit()

    if not force and exists:
        print("Database already initialized.")
        conn.close()
        return

    try:
        equipment_df = pd.read_csv(os.path.join(DATA_DIR, 'equipment.csv'))
        service_history_df = pd.read_csv(os.path.join(DATA_DIR, 'service_history.csv'))
        fault_codes_df = pd.read_csv(os.path.join(DATA_DIR, 'fault_codes.csv'))
        bookings_df = pd.read_csv(os.path.join(DATA_DIR, 'bookings.csv'))
        technicians_df = pd.read_csv(os.path.join(DATA_DIR, 'technicians.csv'))
        
        equipment_df.to_sql('equipment', conn, if_exists='replace', index=False)
        service_history_df.to_sql('service_history', conn, if_exists='replace', index=False)
        fault_codes_df.to_sql('fault_codes', conn, if_exists='replace', index=False)
        bookings_df.to_sql('bookings', conn, if_exists='replace', index=False)
        technicians_df.to_sql('technicians', conn, if_exists='replace', index=False)
        
        cursor = conn.cursor()
        # Create audit_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                role TEXT,
                action TEXT,
                device_id TEXT,
                old_value TEXT,
                new_value TEXT,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create maintenance_schedule table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_schedule (
                schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                recommended_date TEXT,
                scheduled_date TEXT,
                duration_hours INTEGER,
                technician_id TEXT,
                status TEXT,
                priority TEXT
            )
        ''')
        
        conn.commit()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)
    
def fetch_table(table_name):
    conn = get_connection()
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

if __name__ == "__main__":
    init_db()
