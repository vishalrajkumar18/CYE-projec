# Test Cases & Edge Cases

The system enforces automated testing (via `PYTHONPATH=. pytest tests/ -v`) covering critical functional scenarios, error boundaries, and edge cases.

For complete, granular technical documentation covering all 38 unit tests, mocking architecture, and multi-tier error boundaries, see [testing_and_error_boundaries.md](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/docs/testing_and_error_boundaries.md).

---

## 1. Automated Test Suites Summary

The test suite consists of **38 automated tests** across four test files:

| Test File | Test Count | Scope | Primary Purpose |
|---|---|---|---|
| [`tests/test_edge_cases.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/tests/test_edge_cases.py) | 5 | Integration & System Boundaries | Verifies edge cases (DEV001, DEV002, DEV003, DEV010, RBAC) |
| [`tests/test_risk_score.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/tests/test_risk_score.py) | 5 | Unit Tests | Validates mathematical feature scoring functions & linear risk combination |
| [`tests/test_evaluation.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/tests/test_evaluation.py) | 21 | Unit & Simulation Tests | Validates pre-emption rules, reproducibility, RNG determinism, date parsing |
| [`tests/test_audit.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/tests/test_audit.py) | 7 | Unit & Mock Tests | Validates audit persistence, in-memory SQLite isolation, and error resilience |

```bash
# Execute the full test suite
PYTHONPATH=. pytest tests/ -v
```

---

## 2. Documented Edge Cases

### Edge Case 1: High Usage, Zero Faults (Device DEV001)
- **Scenario**: A high-demand scanner has 95% utilisation (1,900 operating hours out of 2,000 available), but has recorded 0 historical faults.
- **Risk**: In a purely fault-reactive system, this machine would be neglected until catastrophic breakdown occurs.
- **System Behavior**: The Feature Engineering module maps utilisation to an operational wear score of 95. Scaled by the 30% utilisation weight, this contributes 28.5 points directly to the overall score. Combined with age and criticality factors, the overall risk exceeds 50, placing it in the High/Critical tier.
- **Verification**: `tests/test_edge_cases.py::test_case_1_high_usage_no_faults` verifies `overall_risk_score > 50`.

### Edge Case 2: Low Usage, High Fault Frequency (Device DEV002)
- **Scenario**: A low-demand scanner has only 20% utilisation (400 operating hours) and Low criticality, but has suffered 10 High-severity error codes.
- **Risk**: Low utilisation might suggest low maintenance urgency, masking intermittent hardware or sensor degradation.
- **System Behavior**: The fault scoring function aggregates fault severity points (10 faults $\times$ 50 = 500 points, capped at 100). The 20% fault weight contributes the maximum possible 20.0 points to the risk score, raising maintenance urgency.
- **Verification**: `tests/test_edge_cases.py::test_case_2_low_usage_high_faults` verifies `risk_breakdown['fault_contribution'] >= 20.0`.

### Edge Case 3: Complete Booking Saturation / No Maintenance Slot (Device DEV003)
- **Scenario**: Machine DEV003 is continuously booked for patient scans from 08:00 to 18:00 across all available days in the scheduling window.
- **Risk**: Automated maintenance scheduling could double-book patient appointments, causing clinical disruption.
- **System Behavior**: `check_hard_constraints` verifies potential maintenance slots against active patient bookings. Overlap detection evaluates to `True`, failing the `No Booking Conflict` hard constraint. The planner marks the recommendation as `(None, "No available maintenance slot found")` and sets `status = 'Failed: No available maintenance slot found'`. The application does not crash and prompts manager review.
- **Verification**: `tests/test_edge_cases.py::test_case_3_no_available_slot` verifies `is_valid == False` and `constraints['No Booking Conflict'] == False`.

### Edge Case 4: Unauthorised Schedule Override (RBAC Enforcement)
- **Scenario**: A user authenticated with the `Technician` or `Operations Staff` role attempts to override a recommended maintenance schedule date.
- **Risk**: Unauthorized personnel altering maintenance schedules could lead to regulatory violations or equipment downtime.
- **System Behavior**: The RBAC gate `has_permission(role, 'override')` returns `False`. The Streamlit UI suppresses the override controls. If called directly, authorization logic denies the mutation. Only `Admin` and `Maintenance Manager` roles possess override privileges.
- **Verification**: `tests/test_edge_cases.py::test_case_4_unauthorised_override` validates permissions across all roles.

### Edge Case 5: Missing Service History Data (Device DEV010)
- **Scenario**: Device DEV010 has `last_service_date = None` or missing maintenance records.
- **Risk**: Incomplete telemetry could cause a system to assign a low risk score, assuming "no news is good news."
- **System Behavior (Fail-Safe Default)**:
  1. `src/data_cleaning.py` identifies the null date and increments `missing_service_date_flagged`.
  2. `src/feature_engineering.py::calculate_service_score` detects `pd.isna(last_service_date_str)` and immediately assigns the maximum possible risk score of **100**.
  3. This guarantees that missing records are treated with the highest caution.
- **Verification**: `tests/test_edge_cases.py::test_case_5_missing_data` validates `missing_service_date_flagged == 1` and `service_score == 100`.

---

## 3. Error Boundaries & Input Validation Summary

The system implements multiple levels of defensive error boundaries:

| Layer | Component | Defensive Rule / Fallback |
|---|---|---|
| **Data Cleaning** | [`src/data_cleaning.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/src/data_cleaning.py) | Operating hours $< 0 \rightarrow 0$<br>Utilisation $> 100\% \rightarrow 100\%$<br>Negative age $< 0 \rightarrow 0$<br>Invalid criticality $\rightarrow$ `'Medium'`<br>Invalid fault severity $\rightarrow$ `'Medium'`<br>Duplicate device IDs $\rightarrow$ Deduplicated |
| **Feature Engineering** | [`src/feature_engineering.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/src/feature_engineering.py) | Missing service date $\rightarrow$ Risk score $= 100$ (Fail-safe maximum)<br>Date string parse exceptions $\rightarrow$ Caught, returns $100$<br>All scores clamped to $[0, 100]$ |
| **Constraint Solver** | [`src/constraints.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/src/constraints.py), [`src/planner.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/src/planner.py) | No active technicians $\rightarrow$ Graceful error tuple<br>Booking conflict $\rightarrow$ Slot rejected<br>Unfeasible schedule $\rightarrow$ Tagged as Failed, fallback enabled |
| **Audit Logging** | [`src/audit.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/src/audit.py) | Database failure $\rightarrow$ Caught via `try-except`, non-blocking to user operations |
| **User Interface & Security** | [`app.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/app.py), [`src/authentication.py`](file:///Users/visahlrajkumar/CYE%20project/maintenance-planner/src/authentication.py) | Unauthenticated user $\rightarrow$ Locked to login screen<br>Unacknowledged disclaimer $\rightarrow$ Locked to terms screen<br>Empty override reason $\rightarrow$ Form submission blocked<br>Weights total $\ne 1.0 \rightarrow$ Configuration save blocked |
