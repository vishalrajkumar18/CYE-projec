# Evaluation Report

## Baseline vs Proposed Strategy
The traditional Calendar-Based approach assumes maintenance happens rigidly (e.g., every 180 days) regardless of equipment usage. This leads to high unplanned downtime as heavily used or aging equipment fails before the scheduled date.

Our Usage-Based strategy ranks equipment based on:
- Utilisation (30%)
- Age (20%)
- Fault History (20%)
- Service History (15%)
- Criticality (15%)

## Primary Objective
The primary success metric is the **Reduction in Unplanned Downtime**. 

**Target:** >20% reduction.

### Results
*Results are dynamically generated in the Streamlit application's Evaluation tab based on simulated metric calculations.*
In the typical simulation run:
- Baseline Unplanned Downtime: ~400-500 hours
- Usage-Based Unplanned Downtime: ~200-250 hours
- **Reduction**: ~40-50% (Target Achieved)

## Error Analysis & Limitations
1. **Missing Data Flagging**: When service history is entirely missing, the system conservatively assigns it maximum risk (100) instead of throwing a fatal error.
2. **Scheduling Bottlenecks**: If all active technicians are unavailable, the planner properly fails the task and surfaces it to the Manager for manual override.
3. **Model Limitations**: The risk weights are assumptions. A real deployment requires tuning with historical operational data and validation by maintenance engineers.

## Stakeholder Validation (Simulated)
| Metric | Result |
|--------|--------|
| Dashboard usability | 4.2/5 |
| Recommendation usefulness | 4.0/5 |
| Override workflow | 4.4/5 |
| Role clarity | 4.5/5 |
| Overall satisfaction | 4.2/5 |
*Note: This is simulated/demo validation as real users were not available.*
