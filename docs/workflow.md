# Workflow Map

## Actors & Roles
- **Admin**: Configures risk weights, manages users, has full access.
- **Maintenance Manager**: Views recommendations, approves schedules, overrides schedules, reviews logs.
- **Technician**: Performs actual maintenance, views assigned tasks, updates task status.
- **Operations Staff**: Views equipment availability and scheduling to coordinate patient care.

## Expected Workflow
1. **Data Ingestion**: System periodically reads equipment, booking, and fault data.
2. **Analysis**: Risk engine calculates a score (0-100) for every machine based on utilisation, age, and faults.
3. **Recommendation**: Planner finds feasible slots considering Technician availability and patient bookings.
4. **Approval**: Maintenance Manager logs in, reviews the dashboard.
   - Manager can **Approve** the slot.
   - Manager can **Override** the slot (must provide a reason).
5. **Execution**: Technician logs in to see the final scheduled task.
6. **Evaluation**: System continuously measures unplanned downtime reduction against the calendar baseline.
