#!/usr/bin/env bash
# MAH installer.
#
# Global (default): once per machine, works in every project. Nothing goes into repositories.
#   bash install.sh [--rules] [--no-tool-errors]
#     ~/.claude/harness/hooks/   guard.sh (B04-B06), collect-tool-errors.sh
#     ~/.claude/harness/bin/     collect.py, errors.py, budget.py, dashboard.py
#     ~/.claude/skills/          5 process skills (existing skills with the same name stay)
#     ~/.claude/settings.json    2 hook entries are added; other keys and hooks stay; backup first
#     --rules                    also import templates/AGENTS.global.md into ~/.claude/CLAUDE.md
#     --no-tool-errors           no PostToolUse collector (saves ~50 ms on each tool call)
#     --auto-evolve              SessionEnd runs evolve in repositories with error.md; SessionStart tells the agent
#
# Project (optional, for a team): git hooks and CI gates in one repository.
#   bash install.sh --project <repo> [--team-store] [--lock]
#     .githooks/ (pre-push, commit-msg), gates/, error.md, docs/adr/, PR template
#     --team-store   .harness/errors/ in the repository: the team commits one shared store
#     --lock         harness.lock: a change of hooks or gates fails CI until a human runs lock
#
# Remove:  bash install.sh --uninstall [--purge]      (--purge also deletes the error store)
# Target folder: CLAUDE_CONFIG_DIR, else ~/.claude.
set -euo pipefail

kit="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3 || command -v python)"
H="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
HH="$H/harness"
win() { command -v cygpath >/dev/null 2>&1 && cygpath -m "$1" || printf '%s' "$1"; }
SKILLS="error-to-rule adr-decision harness-review ste-writing change-pipeline"

mode=global repo="" rules=0 tool_errors=1 team=0 lock=0 purge=0 auto=0
while [ $# -gt 0 ]; do
  case "$1" in
    --project) mode=project; repo="${2:?--project needs a path}"; shift 2 ;;
    --uninstall) mode=uninstall; shift ;;
    --rules) rules=1; shift ;;
    --no-tool-errors) tool_errors=0; shift ;;
    --auto-evolve) auto=1; shift ;;
    --team-store) team=1; shift ;;
    --lock) lock=1; shift ;;
    --purge) purge=1; shift ;;
    -h|--help) sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option $1 (see --help)" >&2; exit 2 ;;
  esac
done

global_install() {
  mkdir -p "$HH/hooks" "$HH/bin" "$HH/errors" "$H/skills"
  cp "$kit/hooks/guard.sh" "$kit/hooks/collect-tool-errors.sh" "$kit/hooks/session-end.sh" "$kit/hooks/session-start.sh" "$HH/hooks/"
  cp "$kit/gates/collect.py" "$kit/metrics/errors.py" "$kit/metrics/budget.py" "$kit/metrics/dashboard.py" "$HH/bin/"
  chmod +x "$HH"/hooks/*.sh
  touch "$HH/installed-skills.txt"
  local n kept=()
  for n in $SKILLS; do
    # a skill folder that we did not install belongs to the user: keep it
    if [ -e "$H/skills/$n" ] && ! grep -qxF "$n" "$HH/installed-skills.txt"; then kept+=("$n"); continue; fi
    mkdir -p "$H/skills/$n" && cp "$kit/skills/$n/SKILL.md" "$H/skills/$n/"
    grep -qxF "$n" "$HH/installed-skills.txt" || echo "$n" >> "$HH/installed-skills.txt"
  done
  local collector="-" loop=()
  [ $tool_errors = 1 ] && collector="$(win "$HH/hooks/collect-tool-errors.sh")"
  [ $auto = 1 ] && loop=("$(win "$HH/hooks/session-end.sh")" "$(win "$HH/hooks/session-start.sh")")
  "$PY" "$kit/lib/claude_settings.py" add "$H/settings.json" "$(win "$HH/hooks/guard.sh")" "$collector" "${loop[@]}"
  if [ $rules = 1 ]; then
    cp "$kit/templates/AGENTS.global.md" "$HH/AGENTS.md"
    local line="@$(win "$HH/AGENTS.md")"
    grep -qF "$line" "$H/CLAUDE.md" 2>/dev/null || printf '\n%s\n' "$line" >> "$H/CLAUDE.md"
  fi
  git -C "$kit" rev-parse --short HEAD > "$HH/VERSION" 2>/dev/null || echo dev > "$HH/VERSION"
  command -v jq >/dev/null || echo "WARNING: jq is not installed. The hooks allow all actions until you install jq." >&2
  echo "Installed MAH into $H"
  echo "  hooks: guard.sh$([ $tool_errors = 1 ] && echo ', collect-tool-errors.sh')   skills: $(tr '\n' ' ' < "$HH/installed-skills.txt")"
  [ ${#kept[@]} -gt 0 ] && echo "  kept your existing skills: ${kept[*]}"
  echo "  errors go to $HH/errors/ — see: ./harness.sh errors"
  echo "  cost for the agent: ./harness.sh budget"
}

global_uninstall() {
  [ -f "$H/settings.json" ] && "$PY" "$kit/lib/claude_settings.py" remove "$H/settings.json"
  if [ -f "$HH/installed-skills.txt" ]; then
    while read -r n; do [ -n "$n" ] && rm -r "${H:?}/skills/$n"; done < "$HH/installed-skills.txt"
  fi
  if [ -f "$H/CLAUDE.md" ]; then
    "$PY" -c "import sys,io;p=sys.argv[1];m=sys.argv[2];L=io.open(p,encoding='utf-8').read().splitlines(True);io.open(p,'w',encoding='utf-8',newline='').writelines(l for l in L if m not in l.replace(chr(92),'/'))" "$H/CLAUDE.md" "harness/AGENTS.md"   # no leading slash: Git Bash rewrites "/x" arguments to "C:/Program Files/Git/x"
  fi
  rm -rf "${HH:?}/hooks" "$HH/bin" "$HH/AGENTS.md" "$HH/installed-skills.txt" "$HH/VERSION"
  if [ $purge = 1 ]; then rm -rf "${HH:?}"; echo "Removed MAH and the error store"; else echo "Removed MAH. The error store stays in $HH/errors (--purge deletes it)"; fi
}

project_install() {
  git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 || { echo "$repo is not a git repository" >&2; exit 1; }
  repo="$(cd "$repo" && pwd)"
  local copied=() skipped=()
  put() { local dst="$repo/$2"; mkdir -p "$(dirname "$dst")"; if [ -e "$dst" ]; then skipped+=("$2"); else cp "$kit/$1" "$dst"; copied+=("$2"); fi; }
  put templates/error.md                  error.md
  put templates/adr/index.md              docs/adr/index.md
  put templates/adr/ADR-0000.md           docs/adr/ADR-0000-template.md
  put templates/pull_request_template.md  .github/pull_request_template.md
  put hooks/pre-push                      .githooks/pre-push
  put hooks/commit-msg                    .githooks/commit-msg
  local f
  for f in _lib.py collect.py checks.py check-secrets.py check-ste.py check-portability.py ste-wordlist.tsv \
           check-adr-numbers.sh check-rules-size.sh check-error-log.py run-all.sh; do
    put "gates/$f" "gates/$f"
  done
  chmod +x "$repo"/.githooks/* "$repo"/gates/*.sh "$repo"/gates/*.py 2>/dev/null || true
  git -C "$repo" config core.hooksPath .githooks
  grep -qE '^\*\.sh[[:space:]].*eol=lf' "$repo/.gitattributes" 2>/dev/null || echo '*.sh text eol=lf' >> "$repo/.gitattributes"
  [ $team = 1 ] && { mkdir -p "$repo/.harness/errors"; touch "$repo/.harness/errors/.keep"; copied+=(".harness/errors/"); }
  [ $lock = 1 ] && [ ! -e "$repo/harness.lock" ] && (cd "$repo" && "$PY" gates/checks.py lock >/dev/null) && copied+=("harness.lock")
  echo "Project install into $repo: ${#copied[@]} files, kept ${#skipped[@]} existing"
  [ ${#skipped[@]} -gt 0 ] && printf '  = kept existing %s\n' "${skipped[@]}"
  echo "  CI: bash gates/run-all.sh   (examples: $kit/ci/)"
}

case "$mode" in
  global) global_install ;;
  uninstall) global_uninstall ;;
  project) project_install ;;
esac
