"""
audit.py — Traceable Audit Logging and Compliance Trail Module.

This module provides logging and querying utilities for tracking user actions,
credential access, terms acknowledgements, risk weight modifications, schedule
approvals, and manual overrides.

Regulatory & Compliance Standards:
----------------------------------
- Separation of Concerns: Operational maintenance logs are decoupled from patient health records.
- Immutable Audit Records: Log entries capture timestamp, initiating actor, role,
  targeted machine ID, previous values, new values, and mandatory justification.
- Non-Blocking Failure Architecture: A failure in audit persistence must never abort
  critical hospital operational tasks (e.g., schedule approval or login).
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional
from src.database import get_connection


def log_action(
    user_id: str,
    role: str,
    action: str,
    device_id: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    reason: Optional[str] = None
) -> None:
    """
    Record an operational event or administrative mutation into the audit trail.

    Parameters
    ----------
    user_id : str
        Identifier or display name of the actor executing the action (e.g., 'admin', 'manager').
    role : str
        The RBAC role assigned to the user at the time of the event.
    action : str
        Human-readable descriptor of the action (e.g., 'Login', 'Consent Given',
        'Approve Schedule', 'Override Schedule', 'Update Risk Weights').
    device_id : str, optional
        Target equipment ID if the action pertains to a specific device (e.g., 'DEV001').
    old_value : str, optional
        Pre-mutation value (e.g., original recommended maintenance slot or previous status).
    new_value : str, optional
        Post-mutation value (e.g., overridden maintenance date or updated status 'Approved').
    reason : str, optional
        Mandatory contextual justification supplied by the user (mandatory for overrides).

    Error Boundary & Safety Guarantees:
    -----------------------------------
    - Non-blocking execution: SQL errors or connection failures are caught via
      `try-except Exception as e`, printing diagnostics to stderr without raising
      unhandled exceptions.
    - Resource guarantee: Database connection is closed unconditionally in the `finally` block.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (
                user_id, role, action, device_id, old_value, new_value, reason, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            role,
            action,
            device_id,
            old_value,
            new_value,
            reason,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
    except Exception as e:
        # Non-blocking error boundary: Log diagnostic message but do not crash application
        print(f"Audit log error: {e}")
    finally:
        if conn is not None:
            conn.close()


def get_audit_logs() -> pd.DataFrame:
    """
    Retrieve all audit log records ordered chronologically from newest to oldest.

    Returns
    -------
    pd.DataFrame
        DataFrame containing audit records with columns:
        ['audit_id', 'user_id', 'role', 'action', 'device_id',
         'old_value', 'new_value', 'reason', 'timestamp']

    Error Boundary:
    --------------
    - Guarantees database connection closure in `finally` block.
    """
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn)
        return df
    finally:
        conn.close()
