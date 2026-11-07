#!/usr/bin/env bash
# MAH launcher.
#
#   ./harness.sh                       menu
#   ./harness.sh install [--rules]     global install: once per machine, all projects
#   ./harness.sh uninstall [--purge]   remove the global install
#   ./harness.sh demo [Bnn]            36 attacks and 17 normal actions on throwaway folders
#   ./harness.sh errors [--project NAME] [--suggest]   error statistics of all projects
#   ./harness.sh budget [--repo PATH]  tokens and hook latency that the harness costs
#   ./harness.sh dashboard [--repo PATH]  HTML: does the agent make fewer errors, faster, cheaper
#   ./harness.sh evolve <repo> [--dry-run]  one turn of the loop: draft incidents, tasks for the agent
#   ./harness.sh bench run|report ...  A/B of harnesses on dev tasks with hidden checks (see docs/BENCH.md)
#   ./harness.sh h2 step|gate|adopt ...  Harness²: the harness proposes, probes and composes its own edit
#   ./harness.sh doctor                check the machine and the install
#   ./harness.sh project <repo> [--team-store] [--lock]   optional: git hooks and CI gates
#   ./harness.sh check <repo>          run the CI gates of a project
#   ./harness.sh incident <repo> "what happened"          new error.md entry
#   ./harness.sh adr <repo> "decision"                    new ADR with the next free number
#   ./harness.sh lock <repo>           accept a reviewed change of hooks or gates
#   ./harness.sh metrics <repo>        weekly convergence from git history
set -uo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$(command -v python3 || command -v python || true)"
H="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
if [ -t 1 ]; then B=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; N=$'\e[0m'; else B= G= Y= R= N=; fi
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; }
err()  { printf '  %s✗%s %s\n' "$R" "$N" "$*" >&2; }
help_() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; }

need_repo() {
  [ -n "${1:-}" ] || { err "give the path to a repository"; return 1; }
  git -C "$1" rev-parse --git-dir >/dev/null 2>&1 || { err "$1 is not a git repository"; return 1; }
  (cd "$1" && pwd)
}

slug() {
  "$PY" -c 'import re,sys
t=dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",["a","b","v","g","d","e","e","zh","z","i","y","k","l","m","n","o","p","r","s","t","u","f","h","ts","ch","sh","sch","","y","","e","yu","ya"]))
s="".join(t.get(c,c) for c in sys.argv[1].lower())
print(re.sub(r"[^a-z0-9]+","-",s).strip("-")[:48])' "$1"
}

cmd_doctor() {
  printf '%sEnvironment%s\n' "$B" "$N"
  for t in git bash; do command -v "$t" >/dev/null && ok "$t" || err "$t not found"; done
  [ -n "$PY" ] && ok "python: $("$PY" --version 2>&1)" || err "python 3 not found"
  command -v jq >/dev/null && ok "jq" || warn "jq not found: the hooks allow all actions until you install it"
  printf '%sInstall%s (%s)\n' "$B" "$N" "$H"
  [ -f "$H/harness/hooks/guard.sh" ] && ok "guard.sh $(cat "$H/harness/VERSION" 2>/dev/null)" || warn "not installed: ./harness.sh install"
  "$PY" "$KIT/lib/claude_settings.py" show "$H/settings.json" 2>/dev/null | sed 's/^/    /'
  [ -s "$H/harness/installed-skills.txt" ] && ok "skills: $(tr '\n' ' ' < "$H/harness/installed-skills.txt")"
  local n; n=$(cat "$H"/harness/errors/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
  ok "error store: $n events in $H/harness/errors"
}

cmd_incident() {
  local repo; repo="$(need_repo "${1:-}")" || return 1
  local title="${2:-}"; [ -n "$title" ] || read -r -p "What happened (one line): " title
  local log="$repo/error.md" day n id
  [ -f "$log" ] || cp "$KIT/templates/error.md" "$log"
  day="$(date +%F)"; n=$(grep -c "^## INC-$day-" "$log" || true); id="INC-$day-$(printf '%02d' $((n + 1)))"
  printf '\n## %s: %s\n- Date: %s\n- Agent:\n- Found by: barrier | gate | ci | review | human | prod\n- Where:\n- Symptom:\n- Cause:\n- Class:\n- Barrier:\n- Level: text | hook | server | OS\n- Repro:\n- ADR: -\n- Status: open\n- Closed:\n' \
    "$id" "$title" "$day" >> "$log"
  (cd "$repo" && "$PY" "$KIT/gates/collect.py" --source manual --outcome incident --name "$id" --detail "$title") >/dev/null 2>&1 || true
  ok "$id added to error.md. Fill in Barrier and Repro in 24 hours"
}

cmd_adr() {
  local repo; repo="$(need_repo "${1:-}")" || return 1
  local title="${2:-}"; [ -n "$title" ] || read -r -p "Decision in one sentence: " title
  local dir="$repo/docs/adr" last next s file
  mkdir -p "$dir"
  last=$(ls "$dir" | grep -Eo '^(ADR-)?[0-9]{4}' | sed 's/^ADR-//' | grep -v '^0000$' | sort -n | tail -1)
  next=$(printf '%04d' $((10#${last:-0} + 1))); s=$(slug "$title")
  file="$dir/$next${s:+-$s}.md"
  sed -e "s/ADR-NNNN: <decision in one sentence>/ADR-$next: $title/" -e "s/YYYY-MM-DD/$(date +%F)/" \
      -e "s/PROPOSED | APPROVED | LOCKED | SUPERSEDED by ADR-XXXX/PROPOSED/" "$KIT/templates/adr/ADR-0000.md" > "$file"
  [ -f "$dir/index.md" ] || cp "$KIT/templates/adr/index.md" "$dir/index.md"
  printf '| %s | %s | PROPOSED | `<paths>` |\n' "$next" "$title" >> "$dir/index.md"
  ok "created $(basename "$file"). Fill in Applies To and Reconsider When"
}

run() { # run <command> <args...>
  local r
  case "$1" in
    install)   shift; bash "$KIT/install.sh" "$@" ;;
    uninstall) shift; bash "$KIT/install.sh" --uninstall "$@" ;;
    project)   r="$(need_repo "${2:-}")" || return 1; shift 2; bash "$KIT/install.sh" --project "$r" "$@" ;;
    demo)      if [ -n "${2:-}" ]; then bash "$KIT/try-it.sh" --only "$2"; else bash "$KIT/try-it.sh"; fi ;;
    errors)    shift; "$PY" "$KIT/metrics/errors.py" --repo "$PWD" "$@" ;;
    budget)    shift; "$PY" "$KIT/metrics/budget.py" "$@" ;;
    dashboard) shift; "$PY" "$KIT/metrics/dashboard.py" --repo "$PWD" "$@" ;;
    bench)     shift; "$PY" "$KIT/bench/run.py" "$@" ;;
    h2)        shift; "$PY" "$KIT/h2/h2.py" "$@" ;;
    evolve)    r="$(need_repo "${2:-$PWD}")" || return 1; shift; [ $# -gt 0 ] && shift; "$PY" "$KIT/metrics/dashboard.py" --evolve "$r" "$@" ;;
    doctor)    cmd_doctor ;;
    check)     r="$(need_repo "${2:-}")" || return 1; (cd "$r" && bash gates/run-all.sh) ;;
    lock)      r="$(need_repo "${2:-}")" || return 1; (cd "$r" && "$PY" gates/checks.py lock) && ok "commit harness.lock with the change" ;;
    metrics)   r="$(need_repo "${2:-}")" || return 1; "$PY" "$KIT/metrics/convergence.py" --repo "$r" ;;
    incident)  shift; cmd_incident "$@" ;;
    adr)       shift; cmd_adr "$@" ;;
    help|-h|--help) help_ ;;
    *) err "unknown command: $1"; help_; return 2 ;;
  esac
}

menu() {
  while true; do
    printf '\n%sMAH%s\n' "$B" "$N"
    cat <<'M'
  1) Install for all projects (global)
  2) Demo: 36 attacks, 17 normal actions
  3) Error statistics
  4) Cost for the agent (budget)
  8) Learning dashboard (HTML)
  5) Check the install (doctor)
  6) Add git hooks and CI gates to a project
  7) Uninstall
  0) Exit
M
    read -r -p "> " c || return 0
    case "$c" in
      1) run install ;;
      2) run demo ;;
      3) run errors ;;
      4) run budget ;;
      8) run dashboard ;;
      5) run doctor ;;
      6) read -r -p "Path to the repository: " r; run project "$r" ;;
      7) run uninstall ;;
      0|q|Q) return 0 ;;
      *) warn "no such item" ;;
    esac
  done
}

if [ $# -eq 0 ]; then menu; else run "$@"; fi
