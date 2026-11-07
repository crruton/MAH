---
name: latency-budget
description: Use when a change touches a hot path or an external call. Compares latency with the baseline.
---
# Latency budget

Each feature uses part of the latency budget. Nobody sees this until production.

## Rules
- Find the latency baseline of the endpoint (`docs/perf/` or the load test report).
- After the change, run the load test or the benchmark for this endpoint.
- When p95 increases by more than 10 percent, stop. Tell the human the numbers.
- Do not increase timeouts to make a slow call pass.

## Check before you finish
1. Give the p95 before and after.
2. Give the command that you used.

## Origin
Solo stage: the agent added features with no latency check. Team stage: the result goes to a shared dashboard.
