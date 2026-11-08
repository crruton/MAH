#!/usr/bin/env bash
# SessionStart hook (install --auto-evolve): tell the agent that the loop left tasks for this repository.
# Costs tokens only when tasks wait. The agent tells the human and does them only when asked.
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
HH="${HARNESS_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/harness}"
f="$HH/evolve/$(basename "$root").md"
[ -s "$f" ] || exit 0
n=$(grep -c '^- ' "$f")
[ "$n" -gt 0 ] || exit 0
echo "MAH: $n harness task(s) from ./harness.sh evolve wait for this repository, list in $f. Tell the user in one line at the start. Do them only when the user asks."
exit 0
