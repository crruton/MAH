---
name: invariants-guard
description: Use when you change core logic that has invariants. Stops silent changes to rules that must not change.
---
# Invariants guard

Some behavior must not change without a human decision.

## Rules
- Read the invariants list of the module (`docs/invariants.md` or the ADR).
- When your change touches an invariant, stop. Tell the human. This is Red Zone.
- Do not change an invariant test to make your change pass.
- Write a test for each new invariant.

## Check before you finish
1. All invariant tests pass.
2. The diff does not change invariant tests.

## Origin
The agent broke barge-in handling in the dialog logic. The invariants list now stops this class of error.
