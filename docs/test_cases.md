# Test Cases & Edge Cases

The system enforces automated tests (via `pytest tests/`) covering the following edge cases:

1. **High Usage, No Faults (DEV001)**
   - **Scenario**: Utilisation is 95%, but fault count is 0.
   - **Expected Behavior**: High utilisation heavily influences risk, bumping the score up sufficiently to classify as High risk, despite zero faults.

2. **Low Usage, High Fault Frequency (DEV002)**
   - **Scenario**: Utilisation is 20%, but the machine has 10 high-severity faults.
   - **Expected Behavior**: Fault history heavily punishes the score.

3. **No Available Maintenance Slot (DEV003)**
   - **Scenario**: The machine is booked constantly across the technician's availability window.
   - **Expected Behavior**: Hard constraint fails, planner returns "No available maintenance slot found", requiring manual intervention.

4. **Unauthorised Override**
   - **Scenario**: User with 'Technician' role tries to override a schedule.
   - **Expected Behavior**: Access is denied, button does not appear.

5. **Missing Data (DEV010)**
   - **Scenario**: Device has completely missing service history.
   - **Expected Behavior**: Data cleaning flags it but retains it. Feature engineering assigns a maximum service risk score (100) safely.
