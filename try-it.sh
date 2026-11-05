#!/usr/bin/env bash
# Demo: creates a throwaway repo, installs the harness and shows five barriers in action.
# Nothing outside a temporary directory is touched.
set -uo pipefail

kit="$(cd "$(dirname "$0")" && pwd)"
py=$(command -v python3 || command -v python)
demo="$(mktemp -d)"
remote="$(mktemp -d)"
trap 'rm -rf "$demo" "$remote"' EXIT
pass=0 fail=0
expect_block() { # expect_block <title> <command...>
  local title="$1"; shift
  if "$@" >/dev/null 2>"$demo/err"; then
    echo "  [x] $title — NOT blocked"; fail=$((fail+1))
  else
    echo "  [v] $title — blocked: $(head -1 "$demo/err")"; pass=$((pass+1))
  fi
}

echo "== Throwaway repo: $demo"
git -C "$demo" init -q -b dev
git -C "$demo" config user.email demo@example.com
git -C "$demo" config user.name demo
git -C "$demo" commit -q --allow-empty -m "init"
git init -q --bare "$remote"
git -C "$demo" remote add origin "$remote"
bash "$kit/install.sh" "$demo" >/dev/null
git -C "$demo" add -A && git -C "$demo" commit -q -m "Install harness"
cd "$demo"

echo "== 1. pre-push: push to main"
expect_block "git push origin dev:main" git push -q origin dev:main

echo "== 2. guard-tests.sh: agent runs the full test suite"
if command -v jq >/dev/null; then
  expect_block "go test ./..." sh -c 'echo "{\"tool_input\":{\"command\":\"go test ./...\"}}" | bash .claude/hooks/guard-tests.sh'
else
  echo "  [-] skipped: jq is not installed"
fi

echo "== 3. check-adr-numbers.sh: two ADRs with one number (ADR-044 incident)"
printf '# ADR-044 quality metric\n' > docs/adr/044-quality-metric.md
printf '# ADR-044 db partitioning\n' > docs/adr/044-db-partitioning.md
expect_block "044-quality-metric + 044-db-partitioning" bash gates/check-adr-numbers.sh docs/adr

echo "== 4. check-error-log.py: incident closed without barrier and repro test"
cat >> error.md <<'INC'

## INC-2026-10-17-01: duplicate ADR numbers
- Дата: 2026-10-17
- Симптом: два ADR-044
- Барьер:
- Уровень:
- Репро-тест:
- Статус: закрыт
INC
expect_block "closed incident without barrier" "$py" gates/check-error-log.py error.md

echo "== 5. check-rules-size.sh: AGENTS.md grows past 150 lines"
for i in $(seq 1 160); do echo "- rule $i" >> AGENTS.md; done
expect_block "AGENTS.md > 150 lines" bash gates/check-rules-size.sh 150 AGENTS.md

echo
echo "Blocked: $pass, missed: $fail"
[ "$fail" -eq 0 ]
