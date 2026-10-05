"""
test_audit.py — Unit tests for the audit logging module.

Tests use an in-memory SQLite database to avoid touching the production DB.

Note on mocking strategy
------------------------
audit.log_action calls conn.close() in a finally block, which destroys
in-memory SQLite databases.  We wrap the real connection in a MagicMock
that stubs out close() while forwarding all other calls to the real
connection, so we can inspect inserted rows after log_action returns.
"""

import pytest
import sqlite3
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime

import src.audit as audit_module


# ── Helpers ──────────────────────────────────────────────────────────────────

def _in_memory_conn():
    """Return a fresh in-memory SQLite connection with the audit_logs table."""
    conn = sqlite3.connect(':memory:')
    conn.execute('''
        CREATE TABLE audit_logs (
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
    conn.commit()
    return conn


def _no_close(real_conn):
    """
    Wrap a real sqlite3 connection so that close() is a no-op.

    Prevents the in-memory DB from being destroyed when log_action
    calls conn.close() in its finally block.
    """
    mock = MagicMock(spec=real_conn)
    mock.cursor.side_effect = real_conn.cursor
    mock.commit.side_effect = real_conn.commit
    mock.execute.side_effect = real_conn.execute
    mock.close.return_value = None
    return mock


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_log_action_inserts_row():
    """log_action should insert one row into audit_logs."""
    conn = _in_memory_conn()
    with patch.object(audit_module, 'get_connection', return_value=_no_close(conn)):
        audit_module.log_action(user_id='admin', role='Admin', action='LOGIN')
    rows = conn.execute("SELECT * FROM audit_logs").fetchall()
    assert len(rows) == 1
    assert rows[0][1] == 'admin'   # user_id
    assert rows[0][2] == 'Admin'   # role
    assert rows[0][3] == 'LOGIN'   # action


def test_log_action_with_all_fields():
    """log_action with all optional fields should store them correctly."""
    conn = _in_memory_conn()
    with patch.object(audit_module, 'get_connection', return_value=_no_close(conn)):
        audit_module.log_action(
            user_id='manager',
            role='Maintenance Manager',
            action='OVERRIDE',
            device_id='DEV001',
            old_value='2026-09-10',
            new_value='2026-09-05',
            reason='Urgent clinical need',
        )
    row = conn.execute("SELECT * FROM audit_logs").fetchone()
    assert row[4] == 'DEV001'
    assert row[5] == '2026-09-10'
    assert row[6] == '2026-09-05'
    assert row[7] == 'Urgent clinical need'


def test_log_action_multiple_entries():
    """Multiple log_action calls should create multiple rows."""
    conn = _in_memory_conn()
    # Each call gets a fresh mock wrapper but they all share the same real conn
    with patch.object(audit_module, 'get_connection',
                      side_effect=lambda: _no_close(conn)):
        audit_module.log_action('admin', 'Admin', 'LOGIN')
        audit_module.log_action('manager', 'Maintenance Manager', 'APPROVE',
                                device_id='DEV002')
        audit_module.log_action('admin', 'Admin', 'CONFIG_CHANGE',
                                reason='Adjusted weights')

    rows = conn.execute("SELECT * FROM audit_logs").fetchall()
    assert len(rows) == 3
    actions = [r[3] for r in rows]
    assert 'LOGIN' in actions
    assert 'APPROVE' in actions
    assert 'CONFIG_CHANGE' in actions


def test_log_action_graceful_on_db_error(capsys):
    """log_action must not raise on DB errors; it should print an error message."""
    broken_conn = MagicMock()
    broken_conn.cursor.side_effect = Exception("DB connection failed")
    with patch.object(audit_module, 'get_connection', return_value=broken_conn):
        audit_module.log_action('admin', 'Admin', 'LOGIN')  # should not raise
    captured = capsys.readouterr()
    assert 'Audit log error' in captured.out


def test_get_audit_logs_returns_dataframe():
    """get_audit_logs should return a pandas DataFrame with expected columns."""
    conn = _in_memory_conn()
    conn.execute(
        "INSERT INTO audit_logs (user_id, role, action, timestamp) VALUES (?, ?, ?, ?)",
        ('admin', 'Admin', 'LOGIN', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    # get_audit_logs calls conn.close() too — same wrapper trick
    with patch.object(audit_module, 'get_connection', return_value=_no_close(conn)):
        df = audit_module.get_audit_logs()

    assert isinstance(df, pd.DataFrame)
    assert 'user_id' in df.columns
    assert 'action' in df.columns
    assert len(df) == 1


def test_get_audit_logs_ordered_by_timestamp_desc():
    """get_audit_logs should return rows newest-first."""
    conn = _in_memory_conn()
    conn.execute(
        "INSERT INTO audit_logs (user_id, role, action, timestamp) VALUES (?, ?, ?, ?)",
        ('user1', 'Admin', 'FIRST', '2026-09-01 08:00:00')
    )
    conn.execute(
        "INSERT INTO audit_logs (user_id, role, action, timestamp) VALUES (?, ?, ?, ?)",
        ('user2', 'Technician', 'SECOND', '2026-09-02 09:00:00')
    )
    conn.commit()
    with patch.object(audit_module, 'get_connection', return_value=_no_close(conn)):
        df = audit_module.get_audit_logs()

    assert df.iloc[0]['action'] == 'SECOND'
    assert df.iloc[1]['action'] == 'FIRST'


def test_log_action_device_id_none_by_default():
    """Omitting device_id should store NULL in the DB."""
    conn = _in_memory_conn()
    with patch.object(audit_module, 'get_connection', return_value=_no_close(conn)):
        audit_module.log_action('tech', 'Technician', 'VIEW_TASK')
    row = conn.execute("SELECT device_id FROM audit_logs").fetchone()
    assert row[0] is None
