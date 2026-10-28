"""
authentication.py — Authentication and Role-Based Access Control (RBAC) Module.

This module manages user identity, session authentication, and granular
permission enforcement across the Maintenance Planner application.

RBAC Matrix:
-------------
- Admin:
    Full administrative access including equipment management, user provisioning,
    risk engine weight configuration, constraint overrides, report viewing,
    and audit log inspection.
- Maintenance Manager:
    Operational scheduling authority. Can view risk recommendations, approve
    schedules, execute overrides (with mandatory justification), view audit logs,
    and inspect evaluation reports.
- Technician:
    Field execution staff. Restricted to viewing assigned maintenance tasks
    and updating maintenance execution statuses.
- Operations Staff:
    Clinical workflow coordinators. Restricted to read-only views of equipment
    availability and schedules to prevent patient appointment disruptions.
"""

from typing import Dict, Any, Optional

# Pre-configured demo accounts for demonstration and evaluation
USERS: Dict[str, Dict[str, Any]] = {
    'admin': {'role': 'Admin', 'name': 'System Administrator'},
    'manager': {'role': 'Maintenance Manager', 'name': 'Jane Manager'},
    'technician': {'role': 'Technician', 'name': 'Bob Johnson'},
    'operations': {'role': 'Operations Staff', 'name': 'Alice Ops'}
}

# Granular permission mapping by role
ROLE_PERMISSIONS: Dict[str, list] = {
    'Admin': [
        'manage_equipment',
        'manage_users',
        'config_weights',
        'config_constraints',
        'view_reports',
        'override',
        'view_logs'
    ],
    'Maintenance Manager': [
        'view_recommendations',
        'approve_schedules',
        'override',
        'view_logs',
        'view_reports'
    ],
    'Technician': [
        'view_assigned_tasks',
        'update_status'
    ],
    'Operations Staff': [
        'view_availability',
        'view_schedule'
    ]
}


def authenticate(username: str, company_name: str, phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate an existing user or register a new user in the session store.

    Parameters
    ----------
    username : str
        The unique user identifier (e.g., 'admin', 'manager', 'technician').
    company_name : str
        The diagnostic centre or hospital organization name.
    phone_number : str
        Contact telephone number for security and operational reachability.

    Returns
    -------
    dict or None
        Dictionary containing user profile ('name', 'role', 'company', 'phone'),
        or None if required parameters are missing.

    Error Boundary / Edge Case Behavior:
    -----------------------------------
    - If the username does not exist in predefined demo credentials, the user
      is dynamically provisioned as a new user with 'Admin' privileges for
      prototyping convenience.
    - Sanitizes string inputs to avoid whitespace anomalies.
    """
    if not username or not company_name or not phone_number:
        return None

    clean_user = username.strip().lower()
    
    if clean_user not in USERS:
        # Dynamic self-registration for prototyping convenience
        USERS[clean_user] = {
            'name': username.strip(),
            'role': 'Admin',  # Default fallback role for new registrations
            'company': company_name.strip(),
            'phone': phone_number.strip()
        }
    return USERS[clean_user]


def has_permission(role: str, action: str) -> bool:
    """
    Evaluate whether a specified role possesses authority for an action.

    Parameters
    ----------
    role : str
        The user's assigned role ('Admin', 'Maintenance Manager', 'Technician', 'Operations Staff').
    action : str
        The programmatic action key to evaluate (e.g., 'override', 'config_weights', 'view_logs').

    Returns
    -------
    bool
        True if the role is authorized to perform the action; False otherwise.

    Security & Safety Guard:
    ------------------------
    - Default-deny policy: Any unrecognized role or unregistered action evaluates
      strictly to False.
    """
    allowed_actions = ROLE_PERMISSIONS.get(role, [])
    return action in allowed_actions
