#!/usr/bin/env bash
# PreToolUse hook for Bash, Read, Edit, MultiEdit, Write, NotebookEdit. Barriers B04-B06, B28-B33 in one process.
#
# Three levels, so the agent asks the human only when it matters:
#   deny  (exit 2)  the action destroys work that git cannot bring back, hides a problem, or leaks a secret:
#                   B05 git reset --hard, git clean -f, git checkout -- ., force push, rm -rf of /, ~, ., .git
#                   B06 secret files   B28 --no-verify, HUSKY=0   B31 credential stores (~/.aws, ~/.kube, ...)
#                   B32 hand edit of lock files and installed packages   B38 a heredoc with a syntax error
#   ask             the action can be correct but needs a human:
#                   B04 a full test run   B05 git branch -D, DROP/TRUNCATE, docker prune
#                   B29 curl | sh   B30 publish, deploy, terraform apply, kubectl delete
#                   B31 env dump    B33 change of hooks and agent settings
#   allow           all other actions, for example rm -rf build, docker compose down -v
#
# Speed: one jq call and bash regex. About 70-130 ms on Windows, see ./harness.sh budget.
# Requires jq. Without jq the hook allows all actions (it never breaks the agent).

command -v jq >/dev/null 2>&1 || exit 0
# Unit separator, not a tab: read collapses empty fields when IFS is whitespace. Windows paths get "/".
input=$(cat)
IFS=$'\x1f' read -r tool cmd path session < <(jq -r '[.tool_name // "", (.tool_input.command // "" | gsub("[\n\u001f]"; " ")),
  (.tool_input.file_path // .tool_input.notebook_path // .tool_input.path // "" | gsub("\\\\"; "/")), .session_id // ""] | join("\u001f")' <<< "$input")

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

# B31 deny: credential stores of tools (cloud, registries, git, kube, ssh keys)
CRED='(\.aws/credentials|(^|[/[:space:]])[._]netrc|\.git-credentials|\.docker/config\.json|\.kube/config|\.config/gh/hosts\.yml|\.ssh/id_[a-z0-9]+([^.a-z0-9]|$)|\.pgpass|\.vault-token|credentials\.tfrc\.json|\.config/gcloud/(credentials|application_default))'
for target in "${path//\\//}" "${cmd//\\//}"; do
  [ -n "$target" ] && [[ $target =~ $CRED ]] && deny B31 guard-credentials "${BASH_REMATCH[1]} is a credential store. Agents do not read tokens. Ask the human for a scoped token in an environment variable." "$tool $target"
done

case "$tool" in Edit|MultiEdit|Write|NotebookEdit)
  p="${path//\\//}"
  # B32 deny: lock files and installed packages are generated. A hand edit makes the build differ from the lock.
  LOCKF='(^|/)(package-lock\.json|npm-shrinkwrap\.json|yarn\.lock|pnpm-lock\.yaml|bun\.lockb?|poetry\.lock|uv\.lock|Pipfile\.lock|pdm\.lock|Cargo\.lock|go\.sum|composer\.lock|Gemfile\.lock|mix\.lock|pubspec\.lock|Podfile\.lock|packages\.lock\.json|gradle\.lockfile)$'
  GEN='(^|/)(node_modules|\.venv|venv|site-packages|__pycache__|Pods|\.gradle)/'
  [[ $p =~ $LOCKF || $p =~ $GEN ]] && deny B32 guard-generated "${p##*/} is generated. Change the manifest and run the package manager (npm install, poetry lock, go mod tidy, cargo update)." "$tool $p"
  # B33 ask: the agent changes its own guard: hooks, agent settings, the harness lock
  SELF='(^|/)\.claude/settings(\.local)?\.json$|/harness/hooks/|(^|/)\.githooks/|(^|/)\.git/hooks/|(^|/)\.husky/|(^|/)\.git/config$|(^|/)harness\.lock$|(^|/)opencode\.json$|(^|/)lefthook\.ya?ml$|(^|/)\.pre-commit-config\.yaml$'
  [[ $p =~ $SELF ]] && ask B33 guard-self "this file controls the guards of the agent. Confirm that you asked for this change" "$tool $p"
  exit 0 ;;
esac

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

# B28 deny: skip of the git hooks. The hook found a problem: fix it, do not go around it.
BYPASS="git$S+(-c$S+[^[:space:]]+$S+)*(commit|push|merge|rebase|am)$S(.*$S)?(--no-verify|-n)($S|$)|(^|$S)(HUSKY=0|HUSKY_SKIP_HOOKS=1|LEFTHOOK=0|SKIP_HOOKS=1)$S"
DRYRUN="git$S+push$S(.*$S)?-n($S|$)"   # git push -n is a dry run, not a skip of hooks
if [[ $flat =~ $BYPASS ]]; then
  m=${BASH_REMATCH[0]# }; m=${m% }
  [[ $flat =~ $DRYRUN && ! $flat =~ --no-verify ]] || deny B28 guard-bypass "\"$m\" skips the git hooks. Fix the problem that the hook reports." "$cmd"
fi

# B38 deny: a heredoc or a multi-line command with a shell syntax error. The shell runs the first part
# and fails in the middle, or a quote inside the script ends the heredoc early (INC-2026-11-06-03, -08).
if [[ $cmd == *"<<"* || ${#cmd} -gt 400 ]]; then
  raw=$(jq -r '.tool_input.command // ""' <<< "$input")
  if [[ $raw == *$'\n'* ]] && ! syn=$(bash -n -c "$raw" 2>&1); then
    deny B38 guard-syntax "the command has a shell syntax error (${syn##*: }). Write the script to a file with the Write tool, then run the file." "$syn"
  fi
  # a heredoc into an interpreter with a double escape: "\\n" in the patch becomes a real line break in the code
  INTERP="(python3?|py|node|ruby|perl)([[:space:]][^<]*)?<<|[>][[:space:]]*[^[:space:]]+\.(py|js|mjs|cjs|ts|rb|pl)[[:space:]]*<<|<<-?[[:space:]]*['\"]?[A-Za-z_]+['\"]?[[:space:]]*[>][[:space:]]*[^[:space:]]+\.(py|js|mjs|cjs|ts|rb|pl)([[:space:]]|$)"
  if [[ $raw =~ $INTERP && $raw == *'\\n'* || $raw =~ $INTERP && $raw == *'\\t'* ]]; then
    deny B38 guard-syntax "a heredoc script for an interpreter has a double escape (\\\\n or \\\\t). One level of escapes is lost on the way into the code (INC-2026-11-07-01). Write the script to a file with the Write tool, then run the file." "$raw"
  fi
fi
# B38 deny: sed -i with escapes in a code file. Two shells change \n into a real line break (INC-2026-11-06-13).
SEDCODE="(^|[;&|][[:space:]]*)sed[[:space:]]([^;&|]*[[:space:]])?-[a-zA-Z]*i[^;&|]*\\\\[nt\\\\][^;&|]*\.(py|js|mjs|cjs|ts|tsx|jsx|go|java|kt|rb|php|rs|cs|c|cc|cpp|h|swift)([[:space:]]|$|[;&|])"
if [[ $cmd =~ $SEDCODE ]]; then
  deny B38 guard-syntax "sed -i with \\n, \\t or \\\\ in a code file. The escapes pass through two shells and break the code. Use the Edit tool." "$cmd"
fi

# B32 deny: a lock file changed by a text tool
WRITE="(sed$S+-i|perl$S+-pi|[>]|tee$S)"
LOCKB="$WRITE[^;&|]*(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|Cargo\.lock|go\.sum|composer\.lock|Gemfile\.lock)($S|$)"
if [[ $flat =~ $LOCKB ]]; then
  deny B32 guard-generated "${BASH_REMATCH[2]} is generated. Run the package manager." "$cmd"
fi

# B29 ask: a script from the network goes straight into an interpreter
REMOTE="(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)$S[^|]*\|$S*(sudo$S+)?(ba|z|da|k)?sh|(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)$S[^|]*\|$S*(sudo$S+)?(python3?|node|perl|ruby|iex|Invoke-Expression)($S|$)"
REMOTE+="|(ba|z)?sh$S+<\($S*(curl|wget)|\\\$\($S*(curl|wget)$S"
if [[ $flat =~ $REMOTE ]]; then
  ask B29 guard-remote-exec "a script from the network runs with no review. Download it, read it, then run it" "$cmd"
fi

# B30 ask: the action leaves the machine: publish a package or an image, change real infrastructure
PUB="(npm|pnpm|yarn|bun)$S+publish|cargo$S+publish|twine$S+upload|gem$S+push|(poetry|uv|flit|hatch)$S+publish|dotnet$S+nuget$S+push|mvn$S+([^[:space:]]+$S+)*deploy($S|$)"
PUB+="|(\./)?gradlew?$S+([^[:space:]]+$S+)*publish|docker$S+(image$S+)?push|gh$S+release$S+create|git$S+push$S(.*$S)?--tags"
PUB+="|(terraform|tofu)$S+(apply|destroy)|pulumi$S+(up|destroy)|kubectl$S+(delete|apply|replace|scale|drain|patch|rollout$S+restart)|helm$S+(install|upgrade|uninstall|delete|rollback)"
PUB+="|(vercel|netlify)$S+(.*$S)?--prod|(fly|flyctl|firebase|serverless|sls|wrangler)$S+deploy|aws$S+[a-z0-9-]+$S+(delete|terminate|remove)-"
if [[ $flat =~ $PUB ]]; then
  ask B30 guard-publish "\"${BASH_REMATCH[0]# }\" changes a system outside this machine. Confirm the target" "$cmd"
fi

# B31 ask: a dump of the environment puts every token of the session into the context
ENVDUMP="(^|[;&|]$S*)(env|printenv|set|export$S+-p|Get-ChildItem$S+env:)$S*($|[;&|])"
ENVSECRET="(echo|printf|printenv)[^;&|]*(TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|PRIVATE_KEY)"
if [[ $cmd =~ $ENVDUMP || $cmd =~ $ENVSECRET ]]; then
  ask B31 guard-credentials "the command prints secrets from the environment into the context. Print only the variable names" "$cmd"
fi

# B33 ask: the agent changes its own guard from the shell
SELFB="(\.claude/settings(\.local)?\.json|/harness/hooks/|\.githooks/|\.git/hooks/|\.husky/|harness\.lock)"
SELFW="(sed$S+-i|[>]|tee$S|(^|$S)(rm|mv|cp|chmod|truncate)$S)"
HOOKCFG="core\.hooksPath|disableAllHooks"
if [[ $flat =~ $HOOKCFG ]] || { [[ $flat =~ $SELFB ]] && [[ $flat =~ $SELFW ]]; }; then
  ask B33 guard-self "the command changes the guards of the agent. Confirm that you asked for this change" "$cmd"
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
  FULL='(^|&&|;|\|\||\|)[[:space:]]*((npm|pnpm|yarn|bun)( run)? test|npx (jest|vitest|mocha)( run)?|(jest|vitest|mocha)( run)?|pytest|python3? -m (pytest|unittest)|tox|nox|go test \./\.\.\.|cargo test|cargo nextest run|(mvn|\./mvnw) (clean )?(test|verify)|(\./)?gradlew? (clean )?(test|check)|dotnet test|(bundle exec )?(rspec|rake test|rails test)|(vendor/bin/|\./vendor/bin/)?(phpunit|pest)|mix test|swift test|flutter test|dart test|deno test|ctest|make (test|check))[[:space:]]*($|&&|;|\|)'
  [[ $cmd =~ $FULL ]] && ask B04 guard-tests "full test suite. Run the tests of the changed files, or confirm the full run" "$cmd"
fi
exit 0
