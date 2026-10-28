"""
database.py — Database Management, Schema Initialization, and Persistence Layer.

This module provides data access primitives for the SQLite database
(`database/maintenance.db`). It manages table creation, synthetic data ingestion,
connection lifecycle management, and thread-safe data frame extraction.

Database Schema Overview:
-------------------------
1. equipment:
   Primary diagnostic asset inventory (device_id, type, age, utilisation, criticality, etc.).
2. service_history:
   Historical maintenance logs (service_id, device_id, date, duration, technician, result).
3. fault_codes:
   Historical and forward-looking error codes (fault_id, device_id, date, severity, resolved).
4. bookings:
   Patient scan appointments defining operational hard constraints (booking_id, times, status).
5. technicians:
   Maintenance personnel profiles, certifications, and working shifts (technician_id, active).
6. audit_logs:
   Traceable compliance log of security and scheduling operations (audit_id, user, role, action).
7. maintenance_schedule:
   Computed and approved maintenance recommendations (schedule_id, device_id, dates, status).
"""

import sqlite3
import pandas as pd
import os
from typing import Optional

# File system paths for persistent storage
DB_PATH = 'database/maintenance.db'
DATA_DIR = 'data/'


def init_db(force: bool = False) -> None:
    """
    Initialize SQLite database schema and populate with CSV data if needed.

    Parameters
    ----------
    force : bool, default=False
        If True, re-imports all CSV data from `data/` into database tables,
        overwriting existing table records. If False, skips initialization
        if the `equipment` table already exists.

    Operational Workflow:
    --------------------
    1. Ensures the target `database/` directory exists.
    2. Queries `sqlite_master` to check for prior initialization.
    3. If uninitialized or `force=True`, reads baseline CSV datasets:
       - `equipment.csv` -> table `equipment`
       - `service_history.csv` -> table `service_history`
       - `fault_codes.csv` -> table `fault_codes`
       - `bookings.csv` -> table `bookings`
       - `technicians.csv` -> table `technicians`
    4. Creates `audit_logs` and `maintenance_schedule` tables if not present.
    5. Commits transactions and closes connection gracefully.

    Error Boundary:
    --------------
    - All operations wrapped in try-except-finally.
    - Exceptions are caught and reported to stdout to prevent fatal startup crashes.
    - Database connection is guaranteed to close in the `finally` block.
    """
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Check if tables already exist, skip loading if they do and force is False
        cursor = conn.cursor()
        cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='equipment'")
        exists = cursor.fetchone()[0] == 1
        cursor.close()

        if not force and exists:
            print("Database already initialized. Skipping CSV ingestion.")
            return

        # Load synthetic CSV files into SQLite tables
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
        
        # Table: audit_logs (Regulatory audit trail for actions, logins, overrides)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                action TEXT NOT NULL,
                device_id TEXT,
                old_value TEXT,
                new_value TEXT,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table: maintenance_schedule (Recommended and approved maintenance slots)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_schedule (
                schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                recommended_date TEXT,
                scheduled_date TEXT,
                duration_hours INTEGER,
                technician_id TEXT,
                status TEXT NOT NULL,
                priority TEXT
            )
        ''')
        
        conn.commit()
        print("Database initialized successfully with all tables.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        conn.close()


def get_connection() -> sqlite3.Connection:
    """
    Establish and return a connection to the SQLite database.

    Returns
    -------
    sqlite3.Connection
        Active connection handle to `database/maintenance.db`.
        Callers must ensure the connection is closed after query execution.
    """
    return sqlite3.connect(DB_PATH)


def fetch_table(table_name: str) -> pd.DataFrame:
    """
    Fetch all rows from the specified table as a pandas DataFrame.

    Parameters
    ----------
    table_name : str
        Name of the SQLite table to query (e.g., 'equipment', 'fault_codes').

    Returns
    -------
    pd.DataFrame
        DataFrame containing all table records.

    Error Boundary:
    --------------
    - Guarantees database connection closure even if SQL query execution fails.
    """
    conn = get_connection()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        return df
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
