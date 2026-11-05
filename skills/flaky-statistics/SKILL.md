---
name: flaky-statistics
description: Use when a test passes and fails with no code change. Decides with statistics, not with one rerun.
---
# Flaky statistics

One green rerun does not prove that you fixed a flaky test.

## Rules
- Do not mark a flaky test as passed after one rerun.
- Run the test N times (default 20). Record the failure rate.
- Compare the rate with the baseline flaky rate of the suite.
- When the rate is above the baseline, the change is not done. Find the cause.
- Do not add `skip`, retries or longer sleeps to hide the failure.

## Check before you finish
1. Give the failure rate before and after.

## Origin
Solo stage: the rule was three runs in a row. Team stage: three runs were not sufficient. The skill now uses a statistical test.
