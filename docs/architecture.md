# Architecture

## Overview
The application is a usage-based preventive maintenance planner for shared high-value diagnostic equipment. It is built as a complete Streamlit dashboard backed by a custom Python processing pipeline and SQLite database.

## Components
1. **Data Layer (`src/database.py`)**
   - SQLite database storing equipment, service history, faults, bookings, technicians, and audit logs.
2. **Data Cleaning (`src/data_cleaning.py`)**
   - Handles missing dates, bounds checking (e.g., utilisation > 100%), and defaults invalid severities/criticalities.
3. **Feature Engineering & Risk Engine (`src/feature_engineering.py`, `src/risk_engine.py`)**
   - Converts raw metrics (utilisation, age, faults) into normalized scores (0-100).
   - Combines scores using configurable weights (default: 30% Utilisation, 20% Age, 20% Faults, 15% Service, 15% Criticality).
4. **Constraints & Planner (`src/constraints.py`, `src/planner.py`)**
   - Evaluates Hard Constraints (Technician availability, operational window, no patient bookings overlap).
   - Evaluates Soft Constraints (Low utilisation preference).
   - Generates recommended maintenance dates based on risk priority.
5. **Evaluation Engine (`src/evaluation.py`)**
   - Compares the baseline (calendar-only) against the usage-based recommendation, calculating planned vs unplanned downtime and schedule conflicts.
6. **Access Control (`src/authentication.py`, `src/audit.py`)**
   - Implements Role-Based Access Control (Admin, Maintenance Manager, Technician, Operations Staff).
   - Audits all critical actions (login, consent, overrides).
7. **Frontend (`app.py`)**
   - Streamlit dashboard providing interactive UI. Ensure clear separation of operational vs medical context.
