USERS = {
    'admin': {'role': 'Admin', 'name': 'System Administrator'},
    'manager': {'role': 'Maintenance Manager', 'name': 'Jane Manager'},
    'technician': {'role': 'Technician', 'name': 'Bob Johnson'},
    'operations': {'role': 'Operations Staff', 'name': 'Alice Ops'}
}

def authenticate(username, company_name, phone_number):
    if username not in USERS:
        USERS[username] = {
            'name': username,
            'role': 'Admin', # Default role for new users
            'company': company_name,
            'phone': phone_number
        }
    return USERS[username]

def has_permission(role, action):
    permissions = {
        'Admin': ['manage_equipment', 'manage_users', 'config_weights', 'config_constraints', 'view_reports', 'override', 'view_logs'],
        'Maintenance Manager': ['view_recommendations', 'approve_schedules', 'override', 'view_logs', 'view_reports'],
        'Technician': ['view_assigned_tasks', 'update_status'],
        'Operations Staff': ['view_availability', 'view_schedule']
    }
    return action in permissions.get(role, [])
