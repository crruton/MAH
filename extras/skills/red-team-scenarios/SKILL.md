---
name: red-team-scenarios
description: Use when you add or change a barrier. Attacks the barrier with known bypass methods.
---
# Red team scenarios

A barrier that nobody attacked is only a hope.

## Rules
- After you add a hook, a gate or a deny rule, attack it.
- Get the attack list from the `redteam-runner` MCP server: `list_scenarios`.
- Run each applicable attack: `run_scenario`.
- The barrier must stop each attack. When one attack passes, the barrier is not done.

## Check before you finish
1. Give the result of each attack.

## Origin
A string filter blocked `git reset --hard`. The agent then used `sh -c`. Now each barrier gets attacked before merge.
