# Architecture

## Overview
The application is a usage-based preventive maintenance planner for shared high-value diagnostic equipment. It is built as a complete Streamlit dashboard backed by a custom Python processing pipeline and SQLite database.

## Components
1. **Data Layer (`src/database.py`)**
   - SQLite database storing equipment, service history, faults, bookings, technicians, maintenance schedules, and audit logs.
2. **Data Cleaning (`src/data_cleaning.py`)**
   - Implements error boundaries for invalid data: bounds checking (clamping utilisation $> 100\%$, operating hours $< 0$), fallback defaults for invalid severities/criticalities, and deduplication.
3. **Feature Engineering & Risk Engine (`src/feature_engineering.py`, `src/risk_engine.py`)**
   - Converts raw metrics (utilisation, age, faults, service interval) into normalized scores (0-100).
   - Implements fail-safe defaults (missing service history defaults to maximum risk score of 100).
   - Combines scores using configurable weights (default: 30% Utilisation, 20% Age, 20% Faults, 15% Service, 15% Criticality).
4. **Constraints & Planner (`src/constraints.py`, `src/planner.py`)**
   - Evaluates Hard Constraints (Technician availability, operational window 08:00–18:00, no patient bookings overlap).
   - Evaluates Soft Constraints (Low utilisation preference).
   - Generates recommended maintenance dates based on risk priority. Gracefully handles unfeasible devices without crashing.
5. **Evaluation Engine (`src/evaluation.py`)**
   - Compares the baseline (calendar-only) against the usage-based recommendation, calculating planned vs unplanned downtime and schedule conflicts.
   - Traceable and seed-deterministic (`EVAL_SEED=42`), scoping evaluation to planning-horizon faults (`>= BASE_DATE`).
6. **Access Control (`src/authentication.py`, `src/audit.py`)**
   - Implements Role-Based Access Control (Admin, Maintenance Manager, Technician, Operations Staff).
   - Audits all critical actions (login, consent, approvals, overrides, weight modifications).
   - Audit logging operates in a non-blocking `try-except` boundary to avoid disrupting operational workflows.
7. **Frontend (`app.py`)**
   - Streamlit dashboard providing interactive UI.
   - Enforces terms acknowledgement and strict separation of operational support from medical context.

## Further Technical Documentation
- [Granular Unit Testing & Error Boundaries](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/docs/testing_and_error_boundaries.md)
- [Test Cases & Edge Cases](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/docs/test_cases.md)
- [Workflow Map](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/docs/workflow.md)
- [Evaluation Details](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/docs/evaluation.md)
