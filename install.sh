#!/usr/bin/env bash
# Installs the harness into a target git repository without overwriting existing files.
# Usage: bash install.sh /path/to/repo
set -euo pipefail

kit="$(cd "$(dirname "$0")" && pwd)"
repo="${1:?usage: install.sh /path/to/repo}"
git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 || { echo "$repo is not a git repository" >&2; exit 1; }
repo="$(cd "$repo" && pwd)"

copied=() skipped=()
put() { # put <source in kit> <destination in repo>
  local dst="$repo/$2"
  mkdir -p "$(dirname "$dst")"
  if [ -e "$dst" ]; then skipped+=("$2"); else cp "$kit/$1" "$dst"; copied+=("$2"); fi
}

# context and records
put templates/AGENTS.project.md         AGENTS.md
put templates/error.md                  error.md
put templates/adr/index.md              docs/adr/index.md
put templates/adr/ADR-0000.md           docs/adr/ADR-0000-template.md
put templates/pull_request_template.md  .github/pull_request_template.md
put templates/CHANGELOG.md              CHANGELOG.md
put review/harness-review.md            docs/harness/harness-review.md
put review/arbitration.md               docs/harness/arbitration.md
# zones and agent hooks
put zones/claude-settings.json          .claude/settings.json
put zones/opencode.json                 opencode.json
for h in guard-tests.sh guard-destructive.sh guard-secrets.sh; do put "hooks/$h" ".claude/hooks/$h"; done
# git hooks
put hooks/pre-push                      .githooks/pre-push
put hooks/commit-msg                    .githooks/commit-msg
# gates and metrics
for f in _lib.py checks.py check-secrets.py check-ste.py ste-wordlist.tsv check-adr-numbers.sh check-rules-size.sh check-error-log.py run-all.sh; do
  put "gates/$f" "gates/$f"
done
put metrics/convergence.py              metrics/convergence.py
# skills
for d in "$kit"/skills/*/; do n=$(basename "$d"); put "skills/$n/SKILL.md" ".claude/skills/$n/SKILL.md"; done
# MCP servers
for f in "$kit"/mcp/servers/*.py; do n=$(basename "$f"); put "mcp/servers/$n" ".harness/mcp/$n"; done
put mcp/requirements.txt                .harness/mcp/requirements.txt
if [ ! -e "$repo/.mcp.json" ]; then
  kitpath="$kit"; command -v cygpath >/dev/null && kitpath="$(cygpath -m "$kit")"
  sed "s#\"HARNESS_KIT\": \"\"#\"HARNESS_KIT\": \"$kitpath\"#" "$kit/mcp/mcp.json" > "$repo/.mcp.json"
  copied+=(".mcp.json")
else
  skipped+=(".mcp.json")
fi

[ -e "$repo/CLAUDE.md" ] || { printf '@AGENTS.md\n' > "$repo/CLAUDE.md"; copied+=("CLAUDE.md"); }
chmod +x "$repo"/.githooks/* "$repo"/.claude/hooks/*.sh "$repo"/gates/*.sh "$repo"/gates/*.py 2>/dev/null || true
git -C "$repo" config core.hooksPath .githooks
for ig in .claude/settings.local.json .harness/state/ __pycache__/; do
  grep -qxF "$ig" "$repo/.gitignore" 2>/dev/null || echo "$ig" >> "$repo/.gitignore"
done
[ -e "$repo/harness.lock" ] || (cd "$repo" && "$(command -v python3 || command -v python)" gates/checks.py lock >/dev/null && copied+=("harness.lock"))

echo "Installed into $repo: ${#copied[@]} files, kept ${#skipped[@]} existing"
[ ${#skipped[@]} -gt 0 ] && printf '  = kept existing %s\n' "${skipped[@]}"
cat <<'NEXT'

Next steps (PROCESS.md, step 1):
  1. Fill in AGENTS.md: commands, code map, rules. Maximum 150 lines.
  2. Copy templates/AGENTS.global.md to ~/.claude/CLAUDE.md and ~/.config/opencode/AGENTS.md.
  3. Protect main on the server (push: nobody). Work in dev.
  4. Add the gates to CI: see ci/ in the kit.
  5. MCP servers: pip install -r .harness/mcp/requirements.txt
  6. After a reviewed harness change: ./harness.sh lock <repo>
NEXT
