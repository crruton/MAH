#!/usr/bin/env bash
# PostToolUse hook: send failed agent tool calls to the error store (source: tool).
# Best effort: the fields of tool_response depend on the runtime version.
# An event is written when the response has is_error=true, a non-empty error, or a non-zero exit code.
# Requires jq. Never blocks: exit 0 always.
input=$(cat)
# Fast path: most calls succeed. Skip jq when the response has no error marker.
[[ $input == *'"is_error":true'* || $input == *'"is_error": true'* || $input == *'"error":'* || $input == *'"exit_code"'* || $input == *'"exitCode"'* ]] || exit 0
fail=$(printf '%s' "$input" | jq -r '
  (.tool_response // {}) as $r
  | if ($r|type) != "object" then empty
    elif ($r.is_error == true) or (($r.error // "") != "") or ((($r.exit_code // $r.exitCode // 0)|tonumber? // 0) != 0)
    then "yes" else empty end' 2>/dev/null)
[ "$fail" = "yes" ] || exit 0
tool=$(printf '%s' "$input" | jq -r '.tool_name // "tool"')
detail=$(printf '%s' "$input" | jq -r '[(.tool_input.command // .tool_input.file_path // ""), ((.tool_response.error // .tool_response.stderr // "")|tostring)] | join(" => ")' 2>/dev/null)
session=$(printf '%s' "$input" | jq -r '.session_id // empty')
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
py=$(command -v python3 || command -v python) || exit 0
[ -f "$root/gates/collect.py" ] && "$py" "$root/gates/collect.py" --source tool --name "$tool" --outcome tool-error \
  --session "$session" --detail "$detail" >/dev/null 2>&1
exit 0
