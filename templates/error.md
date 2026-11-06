# Agent error log

One entry is one incident. Add the entry in 24 hours. You can set `Status: closed` only when `Barrier`, `Level` and `Repro` have values. The gate `gates/check-error-log.py` checks this. Give logs as a link and a short summary. Do not put secrets or personal data here.

## INC-2026-08-10-01: git reset --hard deleted uncommitted work
- Date: 2026-08-10
- Agent: backend-dev
- Found by: human
- Where: `<repository>`, task `<ID>`
- Symptom: uncommitted changes to .gitignore and constitution.md were lost
- Cause: the settings denied file writes, but the terminal stayed open
- Class: bypass of a rule
- Barrier: deny `git reset*` in the CLI settings, read-only repository root for the agent container
- Level: OS
- Repro: `sh -c 'git reset --hard'` in the agent container fails with "Read-only file system"
- ADR: -
- Status: closed
- Closed: 2026-08-10
