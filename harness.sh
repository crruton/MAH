#!/usr/bin/env bash
# self-harness launcher: one entry point for the whole process.
#
#   ./harness.sh                     interactive menu
#   ./harness.sh start  <repo>       one button: doctor -> install -> check -> metrics -> next steps
#   ./harness.sh doctor              check prerequisites
#   ./harness.sh demo [Bnn]          20 barriers (or one) attacked on a throwaway repo
#   ./harness.sh barriers            list the 20 barriers
#   ./harness.sh install  <repo>     copy templates, hooks, gates into a repo (never overwrites)
#   ./harness.sh check    <repo>     run all gates
#   ./harness.sh metrics  <repo>     weekly convergence metrics -> <repo>/docs/metrics.md
#   ./harness.sh incident <repo> "title"   new error.md entry with the next INC id
#   ./harness.sh adr      <repo> "title"   new ADR with the next free number
#   ./harness.sh loadtest <url> [rps]      k6 ramp to <rps> (default 100) in Docker
#   ./harness.sh lock     <repo>     accept a reviewed harness change (write harness.lock)
set -uo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$(command -v python3 || command -v python || true)"
if [ -t 1 ]; then B=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; N=$'\e[0m'; else B= G= Y= R= N=; fi

say()  { printf '%s\n' "$*"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; }
err()  { printf '  %s✗%s %s\n' "$R" "$N" "$*" >&2; }
head_() { printf '\n%s== %s ==%s\n' "$B" "$*" "$N"; }

need_repo() {
  local repo="${1:-}"
  [ -n "$repo" ] || { err "укажите путь к репозиторию"; return 1; }
  git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 || { err "$repo — не git-репозиторий"; return 1; }
  (cd "$repo" && pwd)
}

slug() { # lowercase latin slug; Cyrillic is transliterated
  if [ -n "$PY" ]; then
    "$PY" -c 'import re,sys
t=dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",["a","b","v","g","d","e","e","zh","z","i","y","k","l","m","n","o","p","r","s","t","u","f","h","ts","ch","sh","sch","","y","","e","yu","ya"]))
s="".join(t.get(c,c) for c in sys.argv[1].lower())
print(re.sub(r"[^a-z0-9]+","-",s).strip("-")[:48])' "$1"
  else
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g' | cut -c1-48
  fi
}

cmd_doctor() {
  head_ "Проверка окружения"
  local rc=0
  for t in git bash; do command -v "$t" >/dev/null && ok "$t" || { err "$t не найден"; rc=1; }; done
  if [ -n "$PY" ]; then ok "python: $("$PY" --version 2>&1)"; else err "python 3 не найден"; rc=1; fi
  command -v jq >/dev/null && ok "jq (нужен хуку guard-tests для Claude Code)" || warn "jq не найден: хук guard-tests в Claude Code не сработает"
  command -v docker >/dev/null && ok "docker (для loadtest)" || warn "docker не найден: loadtest недоступен"
  command -v claude >/dev/null && ok "Claude Code" || warn "Claude Code не найден (необязательно)"
  command -v opencode >/dev/null && ok "OpenCode" || warn "OpenCode не найден (необязательно)"
  [ -f "$HOME/.claude/CLAUDE.md" ] && ok "глобальный слой: ~/.claude/CLAUDE.md" || warn "нет ~/.claude/CLAUDE.md — положите туда templates/AGENTS.global.md"
  return $rc
}

cmd_demo() {
  head_ "Демо: атаки на барьеры"
  if [ -n "${1:-}" ]; then bash "$KIT/try-it.sh" --only "$1"; else bash "$KIT/try-it.sh"; fi
}

cmd_barriers() { head_ "20 барьеров"; bash "$KIT/try-it.sh" --list | awk -F'\t' '{printf "  %-4s %-32s %s\n", $1, $2, $3}'; }

cmd_lock() {
  local repo; repo="$(need_repo "${1:-}")" || return 1
  head_ "Принять изменение харнеса: $repo"
  (cd "$repo" && "$PY" gates/checks.py lock) && ok "harness.lock обновлён — закоммитьте его вместе с изменением"
}

cmd_install() {
  local repo; repo="$(need_repo "${1:-}")" || return 1
  head_ "Установка в $repo"
  bash "$KIT/install.sh" "$repo"
}

cmd_check() {
  local repo; repo="$(need_repo "${1:-}")" || return 1
  head_ "Гейты в $repo"
  [ -f "$repo/gates/run-all.sh" ] || { err "гейты не установлены: ./harness.sh install $repo"; return 1; }
  (cd "$repo" && bash gates/run-all.sh)
}

cmd_metrics() {
  local repo; repo="$(need_repo "${1:-}")" || return 1
  head_ "Метрики сходимости: $repo"
  [ -n "$PY" ] || { err "нужен python 3"; return 1; }
  mkdir -p "$repo/docs"
  local out="$repo/docs/metrics.md"
  {
    printf '# Метрики сходимости харнеса\n\nОбновлено: %s. Команда: `./harness.sh metrics .`\n\n' "$(date +%F)"
    printf 'Хороший тренд: доля исправлений падает, пункты правил на плато, ADR и тесты растут.\n\n'
    "$PY" "$KIT/metrics/convergence.py" --repo "$repo"
  } > "$out" || { err "не удалось посчитать метрики"; return 1; }
  tail -n 6 "$out"
  ok "записано в docs/metrics.md"
}

cmd_incident() {
  local repo; repo="$(need_repo "${1:-}")" || return 1
  local title="${2:-}"
  [ -n "$title" ] || read -r -p "Что случилось (одной строкой): " title
  local log="$repo/error.md" day n id
  [ -f "$log" ] || cp "$KIT/templates/error.md" "$log"
  day="$(date +%F)"
  n=$(grep -c "^## INC-$day-" "$log" || true)
  id="INC-$day-$(printf '%02d' $((n + 1)))"
  cat >> "$log" <<EOF

## $id: $title
- Date: $day
- Agent:
- Where:
- Symptom:
- Cause:
- Class:
- Barrier:
- Level: text | hook | server | OS
- Repro:
- ADR: -
- Status: open
EOF
  ok "$id добавлен в error.md — заполните барьер и репро-тест в течение 24 часов"
}

cmd_adr() {
  local repo; repo="$(need_repo "${1:-}")" || return 1
  local title="${2:-}"
  [ -n "$title" ] || read -r -p "Решение одной фразой: " title
  local dir="$repo/docs/adr" last next file
  mkdir -p "$dir"
  last=$(ls "$dir" | grep -Eo '^(ADR-)?[0-9]{4}' | sed 's/^ADR-//' | grep -v '^0000$' | sort -n | tail -1)
  next=$(printf '%04d' $((10#${last:-0} + 1)))
  file="$dir/$next-$(slug "$title").md"
  [ "$(slug "$title")" ] || file="$dir/$next.md"
  sed -e "s/ADR-NNNN: <decision in one sentence>/ADR-$next: $title/" -e "s/YYYY-MM-DD/$(date +%F)/" -e "s/PROPOSED | APPROVED | LOCKED | SUPERSEDED by ADR-XXXX/PROPOSED/" \
    "$KIT/templates/adr/ADR-0000.md" > "$file"
  [ -f "$dir/index.md" ] || cp "$KIT/templates/adr/index.md" "$dir/index.md"
  printf '| %s | %s | PROPOSED | `<paths>` |\n' "$next" "$title" >> "$dir/index.md"
  ok "создан $(basename "$file") и строка в docs/adr/index.md — заполните Applies To и Reconsider When"
}

cmd_loadtest() {
  local url="${1:-}" rps="${2:-100}"
  [ -n "$url" ] || read -r -p "Адрес стенда (не прод!), например http://localhost:8080: " url
  command -v docker >/dev/null || { err "нужен docker"; return 1; }
  head_ "k6: ступени до $rps RPS на $url"
  local host_url="${url/localhost/host.docker.internal}"
  host_url="${host_url/127.0.0.1/host.docker.internal}"
  MSYS_NO_PATHCONV=1 docker run --rm -e BASE_URL="$host_url" -e PROFILE=ramp -e TARGET_RPS="$rps" \
    -v "$KIT/loadtest:/scripts:ro" grafana/k6:0.54.0 run /scripts/k6-template.js
}

cmd_start() {
  local repo; repo="$(need_repo "${1:-}")" || return 1
  say "${B}self-harness: шаг 1 процесса — базовая линия для $repo${N}"
  cmd_doctor || warn "есть недостающие инструменты, продолжаю"
  cmd_install "$repo" || return 1
  if [ -n "$(git -C "$repo" status --porcelain)" ]; then
    warn "харнес скопирован, но не закоммичен: проверьте файлы и сделайте коммит"
  fi
  cmd_check "$repo" || warn "гейты нашли нарушения — это нормально для первого запуска, разберите их"
  cmd_metrics "$repo" || true
  head_ "Дальше"
  say "  1. Заполните AGENTS.md: команды, карта кода, правила (до 150 строк)."
  say "  2. Глобальный слой: cp $KIT/templates/AGENTS.global.md ~/.claude/CLAUDE.md"
  say "  3. Защитите main на сервере (push: никто), работайте в dev."
  say "  4. Добавьте 'bash gates/run-all.sh' в CI — пример в $KIT/ci/."
  say "  5. Ошибка агента: ./harness.sh incident $repo \"что случилось\""
  say "  6. Раз в неделю: ./harness.sh metrics $repo"
  say "  Подробно: $KIT/PROCESS.md"
}

menu() {
  local repo="${HARNESS_REPO:-}"
  while true; do
    printf '\n%sself-harness%s — процесс, в котором агенты держат границы дрейфа\n' "$B" "$N"
    printf 'Репозиторий: %s\n\n' "${repo:-не выбран}"
    cat <<'M'
  1) Старт: базовая линия в репозитории (одна кнопка)
  2) Демо: 20 атак на барьеры на временном репозитории
  3) Проверить окружение
  4) Проверить гейты
  5) Метрики сходимости
  6) Записать ошибку агента (error.md)
  7) Новый ADR
  8) Нагрузочный тест (k6)
  l) Принять изменение харнеса (harness.lock)
  b) Список 20 барьеров
  9) Выбрать репозиторий
  0) Выход
M
    read -r -p "> " c || return 0
    case "$c" in
      1|4|5|6|7|l) [ -n "$repo" ] || { read -r -p "Путь к репозиторию: " repo; } ;;
    esac
    case "$c" in
      1) cmd_start "$repo" ;;
      2) cmd_demo ;;
      3) cmd_doctor ;;
      4) cmd_check "$repo" ;;
      5) cmd_metrics "$repo" ;;
      6) cmd_incident "$repo" ;;
      7) cmd_adr "$repo" ;;
      8) cmd_loadtest ;;
      l) cmd_lock "$repo" ;;
      b) cmd_barriers ;;
      9) read -r -p "Путь к репозиторию: " repo ;;
      0|q|Q) return 0 ;;
      *) warn "нет такого пункта" ;;
    esac
  done
}

case "${1:-menu}" in
  menu) menu ;;
  start|doctor|demo|barriers|install|check|metrics|incident|adr|loadtest|lock) c="$1"; shift; "cmd_$c" "$@" ;;
  -h|--help|help) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *) err "неизвестная команда: $1"; awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 2 ;;
esac
