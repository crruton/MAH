# Project rules for agents

<!-- A table of contents, not a book. Maximum 150 lines. Give links for details. -->

## Commands
- Install: `<command>`
- Build: `<command>`
- Lint: `<command>`
- Test one package: `<command>`
- Full test run: `CLAUDE_FULL_TESTS=1 <command>`. Use it only when the human tells you.

## Code map
- `<folder>/`: `<what it contains>`
- Architecture decisions: `docs/adr/index.md`. Read it before you plan.

## Branches
- Work in `dev`. The `main` branch is production. Change `main` only through a merge request.

## Project rules
<!-- Each rule comes from a real incident. Give the INC ID or the ADR ID. -->
- 

## Zones
- Green: read code, search, build, run tests for the change, commit to your branch.
- Yellow: ask the human before you push, build images, send network requests or change `.claude/` and `opencode.json`.
- Red: do not touch `.env` or secrets. Do not run `git reset --hard` or `rm -rf`. Do not work outside the repository.
