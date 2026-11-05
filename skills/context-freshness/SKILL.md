---
name: context-freshness
description: Use at the start of a task and before a large change. Stops work on an old copy of the repository.
---
# Context freshness

The agent can plan from an old snapshot. The plan then conflicts with new commits.

## Rules
- At the start of a task, call `is_context_fresh` in the `context-freshness` MCP server.
- When the context is old, call `refresh_context`. Read the changed files again.
- Before you push, get the latest `dev`. Do the task again on the new base if necessary.

## Check before you finish
1. `is_context_fresh` gives `true`.

## Origin
Solo stage: a skill. Team stage: a separate MCP server, because many agents need one source of truth.
