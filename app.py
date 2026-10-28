"""
app.py — Interactive Streamlit Dashboard for Usage-Based Preventive Maintenance Planning.

This application provides the web interface for diagnostic centre administrators,
maintenance managers, certified technicians, and operations personnel.

Key Architectural Principles:
-----------------------------
1. Medical Disclaimer & Non-Clinical Scope:
   Strict separation between operational maintenance coordination and medical diagnosis.
   Users must explicitly acknowledge terms of use before entering the operational platform.
2. Role-Based Access Control (RBAC):
   Screen navigation, schedule approvals, overrides, weight adjustments, and audit log
   views are strictly filtered using `src/authentication.py::has_permission`.
3. Explainable AI / Decision Support:
   Presents interpretable risk scores with factor-by-factor point breakdowns to give
   stakeholders full visibility into scheduling recommendations.
4. Defense-in-Depth Validation:
   Mandatory override justification, risk weight normalization validation, and graceful
   handling of unfeasible scheduling requests.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Domain modules
from src.database import init_db, fetch_table, get_connection
from src.authentication import authenticate, has_permission
from src.audit import log_action, get_audit_logs
from src.data_cleaning import clean_all_data
from src.feature_engineering import engineer_features
from src.risk_engine import calculate_risk_score, DEFAULT_WEIGHTS
from src.planner import generate_schedule
from src.evaluation import calculate_evaluation_metrics

# Page configuration
st.set_page_config(page_title="Maintenance Planner", layout="wide")

# Ensure persistent database schema is initialized upon launch
init_db()

# --- Session State Management ---
# Manages user session, disclaimer consent, dynamic risk weights, and loaded data state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'consent_given' not in st.session_state:
    st.session_state.consent_given = False
if 'risk_weights' not in st.session_state:
    st.session_state.risk_weights = DEFAULT_WEIGHTS.copy()
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    
# Mandatory Medical Disclaimer displayed across all operational screens
DISCLAIMER = (
    "⚠️ This system provides operational maintenance planning support only. "
    "It does not provide medical advice, diagnosis, treatment recommendations, "
    "or equipment safety certification."
)


# --- Data Ingestion & Caching ---
@st.cache_data(ttl=60)
def load_data():
    """
    Fetch raw tables from SQLite, execute data cleaning, and compute normalized features.

    Cached for 60 seconds to optimize performance while allowing periodic refreshes.

    Returns
    -------
    tuple
        (clean_eq, clean_fault, bookings_df, technicians_df, service_history_df, features)
    """
    equipment_df = fetch_table('equipment')
    fault_codes_df = fetch_table('fault_codes')
    bookings_df = fetch_table('bookings')
    technicians_df = fetch_table('technicians')
    service_history_df = fetch_table('service_history')
    
    # Clean raw records through defensive error boundaries
    clean_eq, eq_stats, clean_fault, fault_stats = clean_all_data(equipment_df, fault_codes_df)
    
    # Engineer normalized feature sub-scores (0-100)
    features = engineer_features(clean_eq, clean_fault)
    
    return clean_eq, clean_fault, bookings_df, technicians_df, service_history_df, features


# --- Screen Implementations ---

def login_screen():
    """
    Render authentication portal for login or demo account access.

    Enforces mandatory identity capture and logs all authentication events.
    """
    st.title("Usage-Based Preventive Maintenance Planner")
    st.info(DISCLAIMER)
    
    st.subheader("Login / Register")
    username = st.text_input("Username")
    company_name = st.text_input("Company Name")
    phone_number = st.text_input("Phone Number")
    
    if st.button("Login"):
        if username and company_name and phone_number:
            user = authenticate(username, company_name, phone_number)
            if user:
                st.session_state.user = user
                log_action(user['name'], user['role'], 'Login')
                st.rerun()
            else:
                st.error("Invalid credentials.")
        else:
            st.error("Please fill in all fields.")
            
    st.markdown("---")
    st.markdown("""
    **Demo Users (Enter any company and phone number):**
    - `admin` (Admin)
    - `manager` (Maintenance Manager)
    - `technician` (Technician)
    - `operations` (Operations Staff)
    *(Any other username will be registered as a new Admin)*
    """)



def consent_screen():
    """
    Render mandatory Terms of Use & Medical Disclaimer acknowledgement screen.

    Acts as a security and compliance gate: users cannot navigate to operational
    screens without explicitly checking the agreement box and continuing.
    """
    st.title("Terms of Use")
    st.warning(DISCLAIMER)
    
    consent = st.checkbox(
        "I understand that this system provides operational maintenance planning "
        "support only and does not provide medical advice."
    )
    
    if st.button("Acknowledge & Continue"):
        if consent:
            st.session_state.consent_given = True
            log_action(st.session_state.user['name'], st.session_state.user['role'], 'Consent Given')
            st.rerun()
        else:
            st.error("You must acknowledge the terms to use the system.")


def dashboard_screen(eq_df, risk_df, sched_df):
    """
    Render aggregate operational overview, KPIs, and high-level distribution charts.

    Parameters
    ----------
    eq_df : pd.DataFrame
        Cleaned equipment dataset.
    risk_df : pd.DataFrame
        Scored equipment with risk categories and breakdowns.
    sched_df : pd.DataFrame
        Generated maintenance schedule.
    """
    st.title("Operational Dashboard")
    st.info(DISCLAIMER)
    
    # KPI metric header cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Equipment", len(eq_df))
    col2.metric("Operational", len(eq_df[eq_df['status'] == 'Operational']))
    col3.metric("Critical Risk", len(risk_df[risk_df['risk_category'] == 'Critical']))
    col4.metric("High Risk", len(risk_df[risk_df['risk_category'] == 'High']))
    
    # Interactive visualizations
    col_a, col_b = st.columns(2)
    with col_a:
        fig_risk = px.pie(
            risk_df,
            names='risk_category',
            title='Risk Distribution',
            hole=0.4,
            color='risk_category',
            color_discrete_map={
                'Critical': 'red',
                'High': 'orange',
                'Medium': 'yellow',
                'Low': 'green'
            }
        )
        st.plotly_chart(fig_risk, use_container_width=True)
        
    with col_b:
        fig_util = px.histogram(
            eq_df,
            x='utilisation_percent',
            title='Utilisation Distribution',
            nbins=20
        )
        st.plotly_chart(fig_util, use_container_width=True)


def equipment_screen(eq_df, risk_df, fault_df, service_df):
    """
    Render detailed asset inventory, multi-criteria filtering, and explainability breakdown.

    Parameters
    ----------
    eq_df : pd.DataFrame
        Cleaned equipment dataset.
    risk_df : pd.DataFrame
        Scored equipment dataset.
    fault_df : pd.DataFrame
        Historical fault code records.
    service_df : pd.DataFrame
        Historical service maintenance records.
    """
    st.title("Equipment Management")
    st.info(DISCLAIMER)
    
    # Merge asset metadata with computed risk metrics
    display_df = eq_df.merge(
        risk_df[['device_id', 'overall_risk_score', 'risk_category', 'risk_breakdown']],
        on='device_id'
    )
    
    # Multi-criteria filtering controls
    col1, col2, col3 = st.columns(3)
    type_filter = col1.multiselect("Equipment Type", eq_df['device_type'].unique())
    risk_filter = col2.multiselect("Risk Category", ['Critical', 'High', 'Medium', 'Low'])
    status_filter = col3.multiselect("Status", eq_df['status'].unique())
    
    if type_filter:
        display_df = display_df[display_df['device_type'].isin(type_filter)]
    if risk_filter:
        display_df = display_df[display_df['risk_category'].isin(risk_filter)]
    if status_filter:
        display_df = display_df[display_df['status'].isin(status_filter)]
    
    st.dataframe(
        display_df[[
            'device_id', 'device_type', 'age_years', 'utilisation_percent',
            'criticality', 'status', 'overall_risk_score', 'risk_category'
        ]]
    )
    
    # Drill-down inspection for a selected machine
    st.subheader("Equipment Details & Explainability Breakdown")
    selected_device = st.selectbox("Select Device for Details", display_df['device_id'])
    
    if selected_device:
        device_info = display_df[display_df['device_id'] == selected_device].iloc[0]
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Device ID:** {device_info['device_id']}")
            st.markdown(f"**Type:** {device_info['device_type']} ({device_info['manufacturer']} {device_info['model']})")
            st.markdown(f"**Location:** {device_info['location']}")
            st.markdown(f"**Utilisation:** {device_info['utilisation_percent']}%")
            
        with c2:
            badge_color = 'red' if device_info['risk_category'] == 'Critical' else 'orange' if device_info['risk_category'] == 'High' else 'green'
            st.markdown(f"**Risk Category:** :{badge_color}[{device_info['risk_category']}]")
            st.markdown(f"**Risk Score:** {device_info['overall_risk_score']:.2f}")
            
            # Transparent factor breakdown
            st.write("**Risk Breakdown (Explainability Contribution):**")
            bd = device_info['risk_breakdown']
            st.json(bd)
            
        st.markdown("#### Fault History")
        st.dataframe(fault_df[fault_df['device_id'] == selected_device])
        
        st.markdown("#### Service History")
        st.dataframe(service_df[service_df['device_id'] == selected_device])


def planner_screen(sched_df):
    """
    Render maintenance schedule recommendations and manager approval/override workflows.

    Enforces RBAC: Only authorized roles ('Admin', 'Maintenance Manager') can approve
    or override schedules. Overrides strictly require written justifications.

    Parameters
    ----------
    sched_df : pd.DataFrame
        Schedule generated by `src/planner.py::generate_schedule`.
    """
    st.title("Maintenance Planner")
    st.info(DISCLAIMER)
    
    st.dataframe(
        sched_df[[
            'device_id', 'priority', 'recommended_date', 'duration_hours',
            'technician_id', 'status'
        ]]
    )
    
    # RBAC gate for schedule modifications
    if has_permission(st.session_state.user['role'], 'override'):
        st.subheader("Approve / Override Schedule")
        
        device_to_mod = st.selectbox("Select Device", sched_df['device_id'])
        if device_to_mod:
            current_rec = sched_df[sched_df['device_id'] == device_to_mod].iloc[0]
            st.write(f"**Current Recommendation:** {current_rec['recommended_date']}")
            st.write("**Hard Constraints Satisfied:**")
            st.json(current_rec['hard_constraints'])
            st.write("**Soft Constraints Satisfied:**")
            st.json(current_rec['soft_constraints'])
            
            action = st.radio("Action", ["Approve", "Override", "Reject"])
            
            if action == "Override":
                new_date = st.text_input("New Date (YYYY-MM-DD HH:MM:SS)")
                reason = st.text_area("Reason for Override (Mandatory for Compliance)")
                if st.button("Submit Override"):
                    # Error boundary: enforce mandatory reason
                    if reason.strip():
                        log_action(
                            st.session_state.user['name'],
                            st.session_state.user['role'],
                            'Override Schedule',
                            device_id=device_to_mod,
                            old_value=str(current_rec['recommended_date']),
                            new_value=new_date,
                            reason=reason.strip()
                        )
                        st.success("Override submitted and logged into audit trail.")
                    else:
                        st.error("Error: Justification reason is mandatory for override compliance.")
            elif action == "Approve":
                if st.button("Submit Approval"):
                    log_action(
                        st.session_state.user['name'],
                        st.session_state.user['role'],
                        'Approve Schedule',
                        device_id=device_to_mod,
                        old_value=str(current_rec['status']),
                        new_value='Approved'
                    )
                    st.success("Schedule successfully approved and logged.")


def evaluation_screen(eq_df, fault_df, sched_df):
    """
    Render comparative evaluation report contrasting Calendar-Only vs Usage-Based planning.

    Parameters
    ----------
    eq_df : pd.DataFrame
        Cleaned equipment dataset.
    fault_df : pd.DataFrame
        Cleaned fault records dataset.
    sched_df : pd.DataFrame
        Recommended maintenance schedule.
    """
    st.title("Evaluation Report")
    st.info("Primary Objective: Demonstrate reduction in unplanned downtime vs Calendar-Only Baseline.")
    
    # Calculate seed-deterministic evaluation metrics
    eval_results = calculate_evaluation_metrics(eq_df, fault_df, sched_df)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Baseline Unplanned Downtime", f"{eval_results['baseline']['unplanned_downtime']} hrs")
    col2.metric("Usage-Based Unplanned Downtime", f"{eval_results['proposed']['unplanned_downtime']} hrs")
    
    target_achieved = "Yes" if eval_results['reduction_percent'] >= 20.0 else "No"
    col3.metric("Reduction % (Target: ≥20%)", f"{eval_results['reduction_percent']}%", target_achieved)
    
    st.subheader("Multi-Strategy Objective Comparison")
    comp_df = pd.DataFrame([
        {
            'Metric': 'Unplanned Downtime',
            'Calendar Baseline': f"{eval_results['baseline']['unplanned_downtime']} hrs",
            'Proposed Usage-Based': f"{eval_results['proposed']['unplanned_downtime']} hrs",
            'Low-Disruption Alternative': f"{eval_results['low_disruption']['unplanned_downtime']} hrs"
        },
        {
            'Metric': 'Planned Downtime',
            'Calendar Baseline': f"{eval_results['baseline']['planned_downtime']} hrs",
            'Proposed Usage-Based': f"{eval_results['proposed']['planned_downtime']} hrs",
            'Low-Disruption Alternative': f"{eval_results['low_disruption']['planned_downtime']} hrs"
        },
        {
            'Metric': 'Schedule Conflicts',
            'Calendar Baseline': eval_results['baseline']['schedule_conflicts'],
            'Proposed Usage-Based': eval_results['proposed']['schedule_conflicts'],
            'Low-Disruption Alternative': eval_results['low_disruption']['schedule_conflicts']
        },
        {
            'Metric': 'Equipment Availability',
            'Calendar Baseline': f"{eval_results['baseline']['availability_percent']}%",
            'Proposed Usage-Based': f"{eval_results['proposed']['availability_percent']}%",
            'Low-Disruption Alternative': f"{eval_results['low_disruption']['availability_percent']}%"
        }
    ])
    st.table(comp_df)
    
    st.subheader("Error Analysis & Edge Cases")
    st.markdown("""
    1. **High Usage, No Faults (DEV001):** Utilisation of 95% elevates wear score, triggering proactive scheduling.
    2. **Low Usage, High Fault Frequency (DEV002):** Unresolved error history bumps fault risk score, preventing silent failure.
    3. **Missing Data (DEV010):** Missing service records trigger fail-safe maximum risk (100) to ensure clinical safety.
    """)


def audit_screen():
    """
    Render immutable compliance audit trail.

    Enforces RBAC: Access is restricted to Admin and Maintenance Manager roles.
    """
    st.title("Audit Logs")
    if has_permission(st.session_state.user['role'], 'view_logs'):
        logs = get_audit_logs()
        st.dataframe(logs)
    else:
        st.error("Access Denied: You do not possess permission to view regulatory audit logs.")


def settings_screen():
    """
    Render administrative configuration portal for tuning risk factor weights.

    Enforces RBAC: Access is restricted to Admin role. Validates that weights sum to 1.0.
    """
    st.title("Settings")
    if has_permission(st.session_state.user['role'], 'config_weights'):
        st.subheader("Risk Score Weights Configuration")
        
        u_w = st.slider("Utilisation Weight", 0.0, 1.0, float(st.session_state.risk_weights['utilisation']), 0.05)
        a_w = st.slider("Age Weight", 0.0, 1.0, float(st.session_state.risk_weights['age']), 0.05)
        f_w = st.slider("Fault Weight", 0.0, 1.0, float(st.session_state.risk_weights['fault']), 0.05)
        s_w = st.slider("Service Weight", 0.0, 1.0, float(st.session_state.risk_weights['service']), 0.05)
        c_w = st.slider("Criticality Weight", 0.0, 1.0, float(st.session_state.risk_weights['criticality']), 0.05)
        
        total = sum([u_w, a_w, f_w, s_w, c_w])
        st.write(f"**Total Weight:** {total:.2f} (Must equal 1.00)")
        
        if st.button("Save Configuration"):
            # Error boundary: weights must sum to 1.0 within numerical tolerance
            if abs(total - 1.0) < 0.01:
                st.session_state.risk_weights = {
                    'utilisation': u_w,
                    'age': a_w,
                    'fault': f_w,
                    'service': s_w,
                    'criticality': c_w
                }
                log_action(
                    st.session_state.user['name'],
                    st.session_state.user['role'],
                    'Update Risk Weights',
                    reason=f"Weights updated to u={u_w}, a={a_w}, f={f_w}, s={s_w}, c={c_w}"
                )
                st.success("Configuration successfully saved and logged.")
            else:
                st.error("Validation Error: Weights must sum precisely to 1.0 (currently {:.2f}).".format(total))
    else:
        st.error("Access Denied: Only Administrators can modify risk weight configurations.")


# --- Main Application Router ---

if not st.session_state.user:
    # State 1: Unauthenticated -> Login Portal
    login_screen()
elif not st.session_state.consent_given:
    # State 2: Authenticated but disclaimer unacknowledged -> Consent Gate
    consent_screen()
else:
    # State 3: Fully Authenticated & Consented -> Operational Portal
    st.sidebar.title(f"Welcome, {st.session_state.user['name']}")
    st.sidebar.markdown(f"**Role:** {st.session_state.user['role']}")
    
    menu = ["Dashboard", "Equipment", "Maintenance Planner", "Evaluation", "Audit Logs", "Settings", "Logout"]
    choice = st.sidebar.radio("Navigation", menu)
    
    if choice == "Logout":
        log_action(st.session_state.user['name'], st.session_state.user['role'], 'Logout')
        st.session_state.user = None
        st.session_state.consent_given = False
        st.rerun()
        
    # Execute cached data loading and feature extraction
    eq_df, fault_df, bookings_df, technicians_df, service_df, features_df = load_data()
    risk_df = calculate_risk_score(features_df, st.session_state.risk_weights)
    sched_df = generate_schedule(risk_df, bookings_df, technicians_df)
    
    # Route to selected view
    if choice == "Dashboard":
        dashboard_screen(eq_df, risk_df, sched_df)
    elif choice == "Equipment":
        equipment_screen(eq_df, risk_df, fault_df, service_df)
    elif choice == "Maintenance Planner":
        planner_screen(sched_df)
    elif choice == "Evaluation":
        evaluation_screen(eq_df, fault_df, sched_df)
    elif choice == "Audit Logs":
        audit_screen()
    elif choice == "Settings":
        settings_screen()
