#!/usr/bin/env bash
# PreToolUse hook (Bash): block full-suite test runs to save time/tokens.
# Allow with CLAUDE_FULL_TESTS=1 in the environment or as a prefix of the command.
# Requires jq.
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')
[ -z "$cmd" ] && exit 0

# Explicitly allowed
[ "${CLAUDE_FULL_TESTS:-}" = "1" ] && exit 0
printf '%s' "$cmd" | grep -q 'CLAUDE_FULL_TESTS=1' && exit 0

# Bare full-suite commands (each segment of && ; || | chains)
sep='(^|&&|;|\|\||\|)[[:space:]]*'
end='[[:space:]]*($|&&|;|\|)'
patterns=(
  "(npm|pnpm|yarn|bun)( run)? test"
  "npx (jest|vitest)( run)?"
  "(jest|vitest)( run)?"
  "pytest"
  "python3? -m pytest"
  "go test \./\.\.\."
  "cargo test"
  "mvn test"
  "(\./)?gradlew test"
)
for p in "${patterns[@]}"; do
  if printf '%s' "$cmd" | grep -Eq "${sep}${p}${end}"; then
    echo "Blocked: full test suite. Run tests for the changed files or pass specific files/filters. For a deliberate full run, prefix the command with CLAUDE_FULL_TESTS=1." >&2
    exit 2
  fi
done
exit 0
