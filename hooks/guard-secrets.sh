#!/usr/bin/env bash
# B06. PreToolUse hook (Read, Edit, Write, Bash): block access to secret files.
# Requires jq.
input=$(cat)
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.path // empty')
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')
secret='(^|/)(\.env(\.[A-Za-z0-9_-]+)?|[^/]*\.(pem|key|p12|pfx|kdbx)|id_rsa|id_ed25519|secrets/[^[:space:]]*)([[:space:]]|$)'
allowed='\.env\.(example|sample|template)([[:space:]]|$)'
check() {
  printf '%s ' "$1" | grep -Eq "$secret" && ! printf '%s ' "$1" | grep -Eq "$allowed"
}
if [ -n "$path" ] && check "$path"; then
  echo "Blocked by guard-secrets: $path is a secret file. Agents do not read or change secrets." >&2
  exit 2
fi
if [ -n "$cmd" ]; then
  for tok in $cmd; do
    tok=${tok//\"/}; tok=${tok//\'/}
    if check "$tok"; then
      echo "Blocked by guard-secrets: the command touches a secret file ($tok)." >&2
      exit 2
    fi
  done
fi
exit 0
