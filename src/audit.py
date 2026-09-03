import sqlite3
import pandas as pd
from datetime import datetime
from src.database import get_connection

def log_action(user_id, role, action, device_id=None, old_value=None, new_value=None, reason=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (user_id, role, action, device_id, old_value, new_value, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, role, action, device_id, old_value, new_value, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
    finally:
        conn.close()

def get_audit_logs():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn)
    conn.close()
    return df
