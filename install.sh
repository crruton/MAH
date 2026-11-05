#!/usr/bin/env bash
# Installs the harness into a target git repository without overwriting existing files.
#
#   bash install.sh <repo> [--profile core|full] [--mcp none|all|name,name] [--skills process|all]
#
# Profiles:
#   core (default)  27 barriers, error collector, 5 process skills, no MCP servers.
#                   check-changelog and check-large-files are off (HARNESS_SKIP in .harness/config).
#   full            everything: 15 skills, 10 MCP servers, all 16 gates on.
# Each MCP server and each skill puts text into the agent context. Add only what the project needs.
set -euo pipefail

kit="$(cd "$(dirname "$0")" && pwd)"
repo="${1:?usage: install.sh <repo> [--profile core|full] [--mcp none|all|a,b] [--skills process|all]}"; shift
profile=core mcp="" skills=""
while [ $# -gt 0 ]; do
  case "$1" in
    --profile) profile="$2"; shift 2 ;;
    --mcp) mcp="$2"; shift 2 ;;
    --skills) skills="$2"; shift 2 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done
case "$profile" in core|full) ;; *) echo "profile must be core or full" >&2; exit 2 ;; esac
[ -n "$mcp" ] || { [ "$profile" = full ] && mcp=all || mcp=none; }
[ -n "$skills" ] || { [ "$profile" = full ] && skills=all || skills=process; }
git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 || { echo "$repo is not a git repository" >&2; exit 1; }
repo="$(cd "$repo" && pwd)"
PY="$(command -v python3 || command -v python)"

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
for h in guard.sh collect-tool-errors.sh; do put "hooks/$h" ".claude/hooks/$h"; done
# git hooks
put hooks/pre-push                      .githooks/pre-push
put hooks/commit-msg                    .githooks/commit-msg
# gates, collector, metrics
for f in _lib.py collect.py checks.py check-secrets.py check-ste.py check-portability.py ste-wordlist.tsv \
         check-adr-numbers.sh check-rules-size.sh check-error-log.py run-all.sh; do
  put "gates/$f" "gates/$f"
done
put metrics/convergence.py              metrics/convergence.py
put metrics/errors.py                   metrics/errors.py
mkdir -p "$repo/.harness/errors"; touch "$repo/.harness/errors/.keep"
# skills
PROCESS="error-to-rule adr-decision harness-review ste-writing change-pipeline"
for d in "$kit"/skills/*/; do
  n=$(basename "$d")
  [ "$skills" = all ] || case " $PROCESS " in *" $n "*) ;; *) continue ;; esac
  put "skills/$n/SKILL.md" ".claude/skills/$n/SKILL.md"
done
# MCP servers
if [ "$mcp" != none ]; then
  put mcp/servers/_common.py ".harness/mcp/_common.py"
  put mcp/requirements.txt   ".harness/mcp/requirements.txt"
  kitpath="$kit"; command -v cygpath >/dev/null && kitpath="$(cygpath -m "$kit")"
  if [ ! -e "$repo/.mcp.json" ]; then
    "$PY" - "$kit/mcp/mcp.json" "$repo/.mcp.json" "$mcp" "$kitpath" <<'PYEOF'
import json, sys
src, dst, sel, kit = sys.argv[1:5]
cfg = json.load(open(src, encoding="utf-8"))
servers = cfg["mcpServers"]
keep = list(servers) if sel == "all" else [s.strip() for s in sel.split(",") if s.strip()]
unknown = [k for k in keep if k not in servers]
if unknown:
    sys.exit(f"unknown MCP servers: {unknown}. Known: {list(servers)}")
out = {k: servers[k] for k in keep}
if "redteam-runner" in out:
    out["redteam-runner"]["env"]["HARNESS_KIT"] = kit
json.dump({"mcpServers": out}, open(dst, "w", encoding="utf-8"), indent=2)
print(" ".join(f.split("/")[-1] for k in keep for f in out[k]["args"]))
PYEOF
    copied+=(".mcp.json")
  else
    skipped+=(".mcp.json")
  fi
  for f in $("$PY" -c "import json,sys;print(' '.join(a.split('/')[-1] for s in json.load(open(sys.argv[1],encoding='utf-8'))['mcpServers'].values() for a in s['args']))" "$repo/.mcp.json"); do
    [ -f "$kit/mcp/servers/$f" ] && put "mcp/servers/$f" ".harness/mcp/$f"
  done
fi
# profile config
if [ ! -e "$repo/.harness/config" ]; then
  { echo "# self-harness profile: $profile"
    [ "$profile" = core ] && echo 'HARNESS_SKIP="${HARNESS_SKIP-check-changelog check-large-files}"' || echo 'HARNESS_SKIP="${HARNESS_SKIP-}"'
  } > "$repo/.harness/config"
  copied+=(".harness/config")
fi

[ -e "$repo/CLAUDE.md" ] || { printf '@AGENTS.md\n' > "$repo/CLAUDE.md"; copied+=("CLAUDE.md"); }
chmod +x "$repo"/.githooks/* "$repo"/.claude/hooks/*.sh "$repo"/gates/*.sh "$repo"/gates/*.py 2>/dev/null || true
git -C "$repo" config core.hooksPath .githooks
grep -qE '^\*\.sh[[:space:]].*eol=lf' "$repo/.gitattributes" 2>/dev/null || echo '*.sh text eol=lf' >> "$repo/.gitattributes"
for ig in .claude/settings.local.json .harness/state/ __pycache__/; do
  grep -qxF "$ig" "$repo/.gitignore" 2>/dev/null || echo "$ig" >> "$repo/.gitignore"
done
[ -e "$repo/harness.lock" ] || { (cd "$repo" && "$PY" gates/checks.py lock >/dev/null) && copied+=("harness.lock"); }

echo "Installed into $repo (profile $profile, skills $skills, mcp $mcp): ${#copied[@]} files, kept ${#skipped[@]} existing"
[ ${#skipped[@]} -gt 0 ] && printf '  = kept existing %s\n' "${skipped[@]}"
cat <<'NEXT'

Next steps (PROCESS.md, step 1):
  1. Fill in AGENTS.md: commands, code map, rules. Maximum 150 lines.
  2. Copy templates/AGENTS.global.md to ~/.claude/CLAUDE.md and ~/.config/opencode/AGENTS.md.
  3. Protect main on the server (push: nobody). Work in dev.
  4. Add the gates to CI: see ci/ in the kit.
  5. Commit .harness/errors/ : the error store is shared through git.
  6. See the cost of the pack: ./harness.sh budget <repo>
NEXT
