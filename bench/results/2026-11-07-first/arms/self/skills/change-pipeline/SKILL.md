---
name: change-pipeline
description: Use before each commit and push. Runs the gates and the tests for the change only.
---
# Change pipeline

The environment must stop a bad change before a human sees it.

## Before you commit
1. Run the tests for the changed files only. Do not run the full suite.
2. Run `bash gates/run-all.sh`.
3. When a gate fails, fix the cause. Do not skip the gate.
4. Add an entry to `CHANGELOG.md` when code changed.

## Before you push
1. Push to `dev` only. Do not push to `main`.
2. Do not force push.
3. Open a merge request to `main` only when the human tells you.

## When you must skip a gate
- Use `HARNESS_SKIP="<gate>"` only with human approval.
- Write the reason in the merge request.
