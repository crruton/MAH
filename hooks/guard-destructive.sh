#!/usr/bin/env bash
# B05. PreToolUse hook (Bash): block destructive commands, also inside sh -c, bash -c, eval and python -c.
# A deliberate run needs a human: the agent must ask, not retry with another wrapper.
# Requires jq.
cmd=$(jq -r '.tool_input.command // empty')
[ -z "$cmd" ] && exit 0
flat=$(printf '%s' "$cmd" | tr '\n' ' ' | sed "s/[\"']/ /g")
patterns=(
  'git[[:space:]]+reset[[:space:]]+--hard'
  'git[[:space:]]+clean[[:space:]]+-[a-z]*f'
  'git[[:space:]]+checkout[[:space:]]+--[[:space:]]+\.'
  'git[[:space:]]+restore[[:space:]]+(--staged[[:space:]]+)?\.'
  'git[[:space:]]+push[[:space:]](.*[[:space:]])?(--force[^[:space:]]*|-f|--delete|-d|:[^[:space:]]+)([[:space:]]|$)'
  'git[[:space:]]+branch[[:space:]]+-D'
  'rm[[:space:]]+-[a-z]*r[a-z]*f|rm[[:space:]]+-[a-z]*f[a-z]*r'
  'find[[:space:]].*-delete'
  'shutil\.rmtree|os\.system|subprocess\.(run|call|Popen)'
  'DROP[[:space:]]+(TABLE|DATABASE|SCHEMA)|TRUNCATE[[:space:]]'
  'docker[[:space:]]+(system|volume)[[:space:]]+prune|docker[[:space:]]+compose[[:space:]].*down[[:space:]].*-v'
)
for p in "${patterns[@]}"; do
  if printf '%s' "$flat" | grep -Eiq "$p"; then
    echo "Blocked by guard-destructive: this command can destroy work or data. Ask the human to run it." >&2
    exit 2
  fi
done
exit 0
