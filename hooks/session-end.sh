#!/usr/bin/env bash
# SessionEnd hook (install --auto-evolve): one turn of the loop with no human.
# In a repository with error.md: draft incidents for new repeats and save the tasks for the agent.
# The next session gets one line about them (session-start.sh). Never blocks: exit 0 always.
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -f "$root/error.md" ] || exit 0
HH="${HARNESS_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/harness}"
py=$(command -v python3 || command -v python) || exit 0
mkdir -p "$HH/evolve"
"$py" "$HH/bin/dashboard.py" --evolve "$root" --tasks-file "$HH/evolve/$(basename "$root").md" >/dev/null 2>&1
exit 0
