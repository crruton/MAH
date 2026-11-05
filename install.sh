#!/usr/bin/env bash
# Installs the harness into a target git repository without overwriting existing files.
# Usage: bash install.sh /path/to/repo
set -euo pipefail

kit="$(cd "$(dirname "$0")" && pwd)"
repo="${1:?usage: install.sh /path/to/repo}"
git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 || { echo "$repo is not a git repository" >&2; exit 1; }
repo="$(cd "$repo" && pwd)"

copied=() skipped=()
put() { # put <source> <destination relative to repo>
  local dst="$repo/$2"
  mkdir -p "$(dirname "$dst")"
  if [ -e "$dst" ]; then skipped+=("$2"); else cp "$kit/$1" "$dst"; copied+=("$2"); fi
}

put templates/AGENTS.project.md         AGENTS.md
put templates/error.md                  error.md
put templates/adr/index.md              docs/adr/index.md
put templates/adr/ADR-0000.md           docs/adr/ADR-0000-template.md
put templates/pull_request_template.md  .github/pull_request_template.md
put templates/CHANGELOG.md              CHANGELOG.md
put zones/claude-settings.json          .claude/settings.json
put zones/opencode.json                 opencode.json
put hooks/guard-tests.sh                .claude/hooks/guard-tests.sh
put hooks/pre-push                      .githooks/pre-push
put gates/check-adr-numbers.sh          gates/check-adr-numbers.sh
put gates/check-rules-size.sh           gates/check-rules-size.sh
put gates/check-error-log.py            gates/check-error-log.py
put gates/run-all.sh                    gates/run-all.sh
put metrics/convergence.py              metrics/convergence.py
put review/harness-review.md            docs/harness/harness-review.md
put review/arbitration.md               docs/harness/arbitration.md

[ -e "$repo/CLAUDE.md" ] || { printf '@AGENTS.md\n' > "$repo/CLAUDE.md"; copied+=("CLAUDE.md"); }
chmod +x "$repo/.githooks/pre-push" "$repo/.claude/hooks/guard-tests.sh" "$repo"/gates/*.sh 2>/dev/null || true
git -C "$repo" config core.hooksPath .githooks
grep -qxF '.claude/settings.local.json' "$repo/.gitignore" 2>/dev/null || echo '.claude/settings.local.json' >> "$repo/.gitignore"

echo "Installed into $repo"
printf '  + %s\n' "${copied[@]}"
[ ${#skipped[@]} -gt 0 ] && printf '  = kept existing %s\n' "${skipped[@]}"
cat <<'NEXT'

Next steps (PROCESS.md, step 1):
  1. Fill AGENTS.md: commands, code map, rules. Keep it under 150 lines.
  2. Put templates/AGENTS.global.md into ~/.claude/CLAUDE.md and ~/.config/opencode/AGENTS.md.
  3. Protect main on the server (push: no one), work in dev.
  4. Run gates in CI: bash gates/run-all.sh
  5. Baseline metrics: python metrics/convergence.py
NEXT
