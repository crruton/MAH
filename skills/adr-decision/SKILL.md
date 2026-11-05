---
name: adr-decision
description: Use before you plan a change and when you make an architecture decision. Reads, cites and records ADRs.
---
# ADR decision

A clean diff that silently cancels an accepted decision is a defect.

## Before you plan
1. Open `docs/adr/index.md`.
2. Compare the paths that you will change with `Applies To`.
3. Read each accepted ADR that applies.
4. Write the ADR IDs in your plan, or write "no applicable ADRs".

## When your change conflicts with an accepted ADR
- Stop. Tell the human.
- When a `Reconsider When` trigger occurred, propose a new ADR with `Supersedes`.

## To record a decision
1. Run `./harness.sh adr . "decision in one sentence"`.
2. Fill in `Applies To` and `Reconsider When` with measurable triggers.
3. Do not change old ADRs. Mark them `SUPERSEDED by ADR-NNNN`.
