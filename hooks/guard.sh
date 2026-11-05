#!/usr/bin/env bash
# PreToolUse hook for Bash, Read, Edit, Write: barriers B04, B05, B06 in one process.
#   B04 guard-tests        full test suite on each change (allow: CLAUDE_FULL_TESTS=1)
#   B05 guard-destructive  commands that destroy work or data, also inside sh -c, bash -c, python -c
#   B06 guard-secrets      read or change of .env, keys, certificates, secrets/
# Speed: one jq call and bash regex matching, no grep per pattern. A tool call costs one
# bash start and one jq start (see ./harness.sh budget). Exit 2 blocks the call. Requires jq.

IFS=$'\t' read -r tool cmd path session < <(jq -r '[.tool_name // "", .tool_input.command // "",
  (.tool_input.file_path // .tool_input.path // ""), .session_id // ""] | @tsv')

block() { # block <barrier> <name> <message> <detail>
  local root py
  if root=$(git rev-parse --show-toplevel 2>/dev/null) && py=$(command -v python3 || command -v python) \
     && [ -f "$root/gates/collect.py" ]; then
    "$py" "$root/gates/collect.py" --source hook --barrier "$1" --name "$2" --outcome blocked \
      --session "$session" --detail "$4" >/dev/null 2>&1
  fi
  echo "Blocked by $2: $3" >&2
  exit 2
}

# B06: secret files, by path or inside a command
SECRET='(^|[[:space:]/"'"'"'=<>])(\.env(\.[A-Za-z0-9_-]+)?|[^[:space:]/"'"'"']*\.(pem|key|p12|pfx|kdbx)|id_rsa|id_ed25519|secrets/[^[:space:]"'"'"']*)([[:space:]"'"'"';|&)]|$)'
ALLOWED='\.env\.(example|sample|template)$'
for target in "$path" "$cmd"; do
  [ -n "$target" ] || continue
  rest=" $target "
  while [[ $rest =~ $SECRET ]]; do
    hit=${BASH_REMATCH[2]}
    if ! [[ $hit =~ $ALLOWED ]]; then
      block B06 guard-secrets "$hit is a secret file. Agents do not read or change secrets." "$tool $target"
    fi
    rest=${rest#*"$hit"}
  done
done

[ "$tool" = "Bash" ] && [ -n "$cmd" ] || exit 0
flat=${cmd//[\"\']/ }

# B05: destructive commands
DESTRUCTIVE='git[[:space:]]+reset[[:space:]]+--hard|git[[:space:]]+clean[[:space:]]+-[a-z]*f|git[[:space:]]+checkout[[:space:]]+--[[:space:]]+\.|git[[:space:]]+restore[[:space:]]+(--staged[[:space:]]+)?\.([[:space:]]|$)|git[[:space:]]+push[[:space:]](.*[[:space:]])?(--force[^[:space:]]*|-f|--delete|-d|:[^[:space:]]+)([[:space:]]|$)|git[[:space:]]+branch[[:space:]]+-D|rm[[:space:]]+-[a-z]*(rf|fr)|find[[:space:]].*-delete|shutil\.rmtree|DROP[[:space:]]+(TABLE|DATABASE|SCHEMA)|TRUNCATE[[:space:]]+TABLE|docker[[:space:]]+(system|volume)[[:space:]]+prune'
shopt -s nocasematch
if [[ $flat =~ $DESTRUCTIVE ]]; then
  block B05 guard-destructive "\"${BASH_REMATCH[0]}\" can destroy work or data. Ask the human to run it." "$cmd"
fi
shopt -u nocasematch

# B04: full test suite (each segment of && ; || | chains)
if [ "${CLAUDE_FULL_TESTS:-}" != "1" ] && ! [[ $cmd == *CLAUDE_FULL_TESTS=1* ]]; then
  FULL='(^|&&|;|\|\||\|)[[:space:]]*((npm|pnpm|yarn|bun)( run)? test|npx (jest|vitest)( run)?|(jest|vitest)( run)?|pytest|python3? -m pytest|go test \./\.\.\.|cargo test|mvn test|(\./)?gradlew test)[[:space:]]*($|&&|;|\|)'
  if [[ $cmd =~ $FULL ]]; then
    block B04 guard-tests "full test suite. Run the tests of the changed files. For a full run, prefix CLAUDE_FULL_TESTS=1." "$cmd"
  fi
fi
exit 0
