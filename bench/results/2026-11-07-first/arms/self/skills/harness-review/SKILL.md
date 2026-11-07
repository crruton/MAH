---
name: harness-review
description: Use when a change touches the harness: AGENTS.md, rules, hooks, gates, skills, MCP permissions.
---
# Harness review

A harness change changes the behavior of all agents. Review it as an experiment.

## Procedure
1. Run the task of the incident two times: with the change and without it. Compare the behavior.
2. Run the same task set on the base harness and on the new harness.
3. Change only the harness. Keep the tasks, the model and the runtime the same.
4. Test the change on tasks that you did not use to write it.
5. Make sure that the agent cannot see the test criteria.
6. Mark an infrastructure failure as "not scored", not as zero.
7. Write the conditions in the report: model, runtime, tasks, network limits.
8. Do the quarantine arbitration in `docs/harness/arbitration.md`.
9. Run `./harness.sh lock` after approval.

## Source
Methods 1-8 come from harness2 (Google Research).
