#!/usr/bin/env bash
# PreToolUse hook for Bash, Read, Edit, Write. Barriers B04, B05, B06 in one process.
#
# Three levels, so the agent asks the human only when it matters:
#   deny  (exit 2)  the action destroys work that git cannot bring back:
#                   git reset --hard, git clean -f, git checkout -- ., force push,
#                   rm -rf of /, ~, $HOME, ., .., *, .git; read or change of secret files
#   ask             the action can be correct but needs a human:
#                   git branch -D, DROP/TRUNCATE, docker system|volume prune, a full test run
#   allow           all other actions, for example rm -rf build, docker compose down -v
#
# Speed: one jq call and bash regex. About 70-130 ms on Windows, see ./harness.sh budget.
# Requires jq. Without jq the hook allows all actions (it never breaks the agent).

command -v jq >/dev/null 2>&1 || exit 0
IFS=$'\t' read -r tool cmd path session < <(jq -r '[.tool_name // "", .tool_input.command // "",
  (.tool_input.file_path // .tool_input.path // ""), .session_id // ""] | @tsv')

HH="${HARNESS_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/harness}"
log() { # log <barrier> <name> <outcome> <detail>
  local py c
  py=$(command -v python3 || command -v python) || return 0
  for c in "$HH/bin/collect.py" "$(git rev-parse --show-toplevel 2>/dev/null)/gates/collect.py"; do
    [ -f "$c" ] && { "$py" "$c" --source hook --barrier "$1" --name "$2" --outcome "$3" --session "$session" --detail "$4" >/dev/null 2>&1; return 0; }
  done
}
deny() { log "$1" "$2" blocked "$4"; echo "Blocked by $2: $3" >&2; exit 2; }
ask() {
  log "$1" "$2" asked "$4"
  local reason=${3//\"/\'}
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s (%s)"}}\n' "$reason" "$2"
  exit 0
}

# B06: secret files, by path or inside a command
SECRET='(^|[[:space:]/"'"'"'=<>])(\.env(\.[A-Za-z0-9_-]+)?|[^[:space:]/"'"'"']*\.(pem|key|p12|pfx|kdbx)|id_rsa|id_ed25519|secrets/[^[:space:]"'"'"']*)([[:space:]"'"'"';|&)]|$)'
ALLOWED='\.env\.(example|sample|template)$'
for target in "$path" "$cmd"; do
  [ -n "$target" ] || continue
  rest=" $target "
  while [[ $rest =~ $SECRET ]]; do
    hit=${BASH_REMATCH[2]}
    [[ $hit =~ $ALLOWED ]] || deny B06 guard-secrets "$hit is a secret file. Agents do not read or change secrets." "$tool $target"
    rest=${rest#*"$hit"}
  done
done

[ "$tool" = "Bash" ] && [ -n "$cmd" ] || exit 0
flat=" ${cmd//[\"\']/ } "
S='[[:space:]]'

# B05 deny: work that git cannot bring back
DENY="git$S+reset$S+--hard|git$S+clean$S+-[a-z]*f|git$S+checkout$S+--$S+\.($S|$)|git$S+restore$S+(--staged$S+)?\.($S|$)"
DENY+="|git$S+push$S(.*$S)?(--force[^[:space:]]*|-f|--delete|-d|:[^[:space:]]+)($S|$)"
DENY+="|rm$S+(-[a-zA-Z]*$S+)*-[a-zA-Z]*(rf|fr|Rf|fR)[a-zA-Z]*$S+(-[a-zA-Z]+$S+)*(/|/\*|~|~/|\\\$HOME|\.|\./|\.\.|\.\./?\*?|\*|\.git/?)($S|;|&|$)"
if [[ $flat =~ $DENY ]]; then
  deny B05 guard-destructive "\"${BASH_REMATCH[0]# }\" destroys work that git cannot bring back. Ask the human to run it." "$cmd"
fi

# B05 ask: correct in some tasks, dangerous in others
shopt -s nocasematch
ASK="git$S+branch$S+-D$S|DROP$S+(TABLE|DATABASE|SCHEMA)|TRUNCATE$S+TABLE|docker$S+(system|volume)$S+prune"
if [[ $flat =~ $ASK ]]; then
  shopt -u nocasematch
  ask B05 guard-destructive "\"${BASH_REMATCH[0]}\" deletes data. Confirm that this is a test environment" "$cmd"
fi
shopt -u nocasematch

# B04 ask: full test suite (each segment of && ; || | chains). CLAUDE_FULL_TESTS=1 allows it.
if [ "${CLAUDE_FULL_TESTS:-}" != "1" ] && ! [[ $cmd == *CLAUDE_FULL_TESTS=1* ]]; then
  FULL='(^|&&|;|\|\||\|)[[:space:]]*((npm|pnpm|yarn|bun)( run)? test|npx (jest|vitest)( run)?|(jest|vitest)( run)?|pytest|python3? -m pytest|go test \./\.\.\.|cargo test|mvn test|(\./)?gradlew test)[[:space:]]*($|&&|;|\|)'
  [[ $cmd =~ $FULL ]] && ask B04 guard-tests "full test suite. Run the tests of the changed files, or confirm the full run" "$cmd"
fi
exit 0
