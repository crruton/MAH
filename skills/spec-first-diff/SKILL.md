---
name: spec-first-diff
description: Use before you change behavior. Links each change to a spec or an ADR.
---
# Spec-first diff

A change without a spec is a guess about what the human wants.

## Rules
- Before you change behavior, find the spec (`openspec/`, `docs/specs/`) or the ADR for it.
- When no spec exists, write a short proposal first. Wait for approval.
- Put the spec ID or ADR ID in the commit body: `Spec: SPEC-0012` or `ADR: 0007`.
- Do not change code outside the scope of the spec.

## Check before you finish
1. The diff touches only the paths of the spec.
2. The commit body has the spec ID.

## Origin
The agent changed code with no link to a spec. Reviews then had no criteria.
