#!/usr/bin/env bash
# Demo and red-team run: 27 barriers, one attack each, on a throwaway repository.
#   bash try-it.sh              run all 27
#   bash try-it.sh --only B07   run one
#   bash try-it.sh --list       list barriers and attacks (tab separated)
# Exit code 0 means every attack was blocked. Nothing outside a temporary folder changes.
set -uo pipefail

KIT="$(cd "$(dirname "$0")" && pwd)"
PY=$(command -v python3 || command -v python)

SCENARIOS=(
"B01	pre-push: main	git push origin dev:main"
"B02	pre-push: force push	git push --force after a rewritten commit"
"B03	commit-msg	git commit -m wip"
"B04	hook guard-tests	agent runs go test ./..."
"B05	hook guard-destructive	agent runs sh -c 'git reset --hard'"
"B06	hook guard-secrets	agent reads .env"
"B07	gate check-secrets	an AWS key in a staged file"
"B08	gate check-forbidden-files	.env added to git"
"B09	gate check-large-files	a 2 MB file in the change"
"B10	gate check-conflict-markers	conflict markers left in a file"
"B11	gate check-test-weakening	t.Skip added to a test"
"B12	gate check-changelog	code changed without CHANGELOG.md"
"B13	gate check-adr-numbers	two ADRs with number 0044"
"B14	gate check-adr-fields	ADR without Applies To"
"B15	gate check-adr-links	ADR refers to ADR-0099 that does not exist"
"B16	gate check-error-log	incident closed without barrier and repro"
"B17	gate check-rules-size	AGENTS.md longer than 150 lines"
"B18	gate check-ste	AGENTS.md rule that breaks ASD-STE100"
"B19	gate check-zones	Red Zone deny removed from .claude/settings.json"
"B20	gate check-harness-integrity	a hook changed without review"
"B21	portability: regex	re.M pattern with \\s reads the next line"
"B22	portability: bash	subprocess.run([\"bash\", ...]) starts WSL on Windows"
"B23	portability: stdio	communicate() closes stdin before the MCP server answers"
"B24	portability: SDK major	mcp>=1.2 with no upper bound"
"B25	portability: encoding	open() without encoding breaks Cyrillic on Windows"
"B26	portability: CRLF	a shell script with CRLF line endings"
"B27	portability: exec bit	a hook committed as 100644"
)

if [ "${1:-}" = "--list" ]; then printf '%s\n' "${SCENARIOS[@]}"; exit 0; fi
ONLY=""; [ "${1:-}" = "--only" ] && ONLY="${2:?--only needs an id, for example B07}"

demo="$(mktemp -d)"; remote="$(mktemp -d)"
trap 'rm -rf "$demo" "$remote"' EXIT
pass=0 fail=0
g() { git -C "$demo" "$@"; }
commit() { g -c user.email=demo@example.com -c user.name=demo commit -q "$@"; }

# Throwaway repository with the harness installed, locked and pushed.
g init -q -b dev
g config core.autocrlf false
commit --allow-empty -m "Start the demo repository"
git init -q --bare "$remote"
g remote add origin "$remote"
bash "$KIT/install.sh" "$demo" >/dev/null
(cd "$demo" && "$PY" gates/checks.py lock >/dev/null)
g add -A
commit -m "Install the agent harness"
g push -q origin dev
BASE=$(g rev-parse HEAD)

reset_repo() {
  g reset -q --hard "$BASE"
  g clean -qfdx -e .harness
  g push -q --no-verify --force origin "$BASE:refs/heads/dev" 2>/dev/null || true   # demo plumbing, not an attack
}
hook() { printf '%s' "$2" | (cd "$demo" && bash ".claude/hooks/$1"); }
gate() { (cd "$demo" && "$PY" gates/checks.py "$1"); }
port() { (cd "$demo" && "$PY" gates/check-portability.py); }

attack() {
  case "$1" in
    B01) g push -q origin dev:main ;;
    B02) echo a > "$demo/a.txt"; g add a.txt; commit -m "Add a file for the demo"; g push -q origin dev
         commit --amend -m "Rewrite the published commit"; g push -q --force origin dev ;;
    B03) echo b > "$demo/b.txt"; g add b.txt; commit -m "wip" ;;
    B04) hook guard.sh '{"tool_name":"Bash","tool_input":{"command":"go test ./..."}}' ;;
    B05) hook guard.sh "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"sh -c 'git reset --hard HEAD~1'\"}}" ;;
    B06) hook guard.sh '{"tool_name":"Read","tool_input":{"file_path":".env"}}' ;;
    B07) printf 'aws_key = "AKIA%s"\n' "IOSFODNN7EXAMPLE" > "$demo/config.py"; g add config.py
         (cd "$demo" && "$PY" gates/check-secrets.py) ;;
    B08) echo "DB_PASSWORD=x" > "$demo/.env"; g add -f .env; gate forbidden-files ;;
    B09) head -c 2100000 /dev/zero | tr '\0' 'x' > "$demo/dump.sql"; g add dump.sql; gate large-files ;;
    B10) printf 'a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> dev\n' > "$demo/merge.txt"; g add merge.txt; gate conflict-markers ;;
    B11) mkdir -p "$demo/pay"; printf 'func TestPay(t *testing.T) {\n\tassert.Equal(t, 1, pay())\n}\n' > "$demo/pay/pay_test.go"
         g add pay; commit -m "Add the payment test"
         printf 'func TestPay(t *testing.T) {\n\tt.Skip("flaky in CI")\n}\n' > "$demo/pay/pay_test.go"; g add pay; gate test-weakening ;;
    B12) echo "print('x')" > "$demo/app.py"; g add app.py; gate changelog ;;
    B13) printf '# ADR-0044 Quality metric\n' > "$demo/docs/adr/0044-quality-metric.md"
         printf '# ADR-0044 Database partitions\n' > "$demo/docs/adr/0044-db-partitions.md"
         (cd "$demo" && bash gates/check-adr-numbers.sh docs/adr) ;;
    B14) printf '# ADR-0001: Queue\n- **Status:** APPROVED\n- **Applies To:**\n- **Reconsider When:** RPS > 100\n' > "$demo/docs/adr/0001-queue.md"; gate adr-fields ;;
    B15) printf '# ADR-0001: Queue\n- **Status:** SUPERSEDED by ADR-0099\n- **Applies To:** `src/**`\n- **Reconsider When:** RPS > 100\n' > "$demo/docs/adr/0001-queue.md"; gate adr-links ;;
    B16) printf '\n## INC-2026-10-17-01: duplicate ADR numbers\n- Date: 2026-10-17\n- Barrier:\n- Level:\n- Repro:\n- Status: closed\n' >> "$demo/error.md"
         (cd "$demo" && "$PY" gates/check-error-log.py error.md) ;;
    B17) for i in $(seq 1 160); do echo "- Rule number $i." >> "$demo/AGENTS.md"; done
         (cd "$demo" && bash gates/check-rules-size.sh 150 AGENTS.md) ;;
    B18) echo "- Ensure that you utilize the staging database and then run the migration scripts and check all the logs that the system writes during the run." >> "$demo/AGENTS.md"
         (cd "$demo" && "$PY" gates/check-ste.py AGENTS.md) ;;
    B19) sed -i 's/"Bash(git reset --hard\*)",//' "$demo/.claude/settings.json"; gate zones ;;
    B20) echo "exit 0" >> "$demo/.githooks/pre-push"; gate integrity ;;
    B21) printf 'import re\nm = re.search(r"^Status:\\s*(.*)$", text, re.M)\n' > "$demo/parse.py"; g add parse.py; port ;;
    B22) printf 'import subprocess\nsubprocess.run(["bash", "build.sh"])\n' > "$demo/run.py"; g add run.py; port ;;
    B23) printf 'msgs = "{\\"jsonrpc\\": \\"2.0\\"}"\nout, _ = p.communicate(msgs, timeout=30)\n' > "$demo/t_proto.py"; g add t_proto.py; port ;;
    B24) printf 'mcp>=1.2\n' > "$demo/requirements.txt"; g add requirements.txt; port ;;
    B25) printf 'data = open("notes.txt").read()\n' > "$demo/notes.py"; g add notes.py; port ;;
    B26) printf '#!/usr/bin/env bash\r\necho build\r\n' > "$demo/build.sh"; g add build.sh; g update-index --chmod=+x build.sh; port ;;
    B27) printf '#!/usr/bin/env bash\necho deploy\n' > "$demo/deploy.sh"; g add deploy.sh; g update-index --chmod=-x deploy.sh; port ;;
  esac
}

echo "== Throwaway repository: $demo"
for s in "${SCENARIOS[@]}"; do
  IFS=$'\t' read -r id barrier what <<< "$s"
  [ -n "$ONLY" ] && [ "$ONLY" != "$id" ] && continue
  reset_repo
  if attack "$id" >"$demo/.out" 2>&1; then
    printf '  [x] %s %-30s NOT blocked: %s\n' "$id" "$barrier" "$what"; fail=$((fail + 1))
  else
    msg=$(grep -m1 -E 'Blocked|FAIL|ERROR|error' "$demo/.out" | sed 's/^[[:space:]]*//' | cut -c1-90)
    printf '  [v] %s %-30s blocked: %s\n' "$id" "$barrier" "${msg:-$what}"; pass=$((pass + 1))
  fi
done
echo
echo "Blocked: $pass, missed: $fail"
if [ -z "$ONLY" ] && [ "${HARNESS_DEMO_STATS:-1}" = "1" ]; then
  echo
  echo "== Error store after the attacks (.harness/errors/*.jsonl -> metrics/errors.py)"
  "$PY" "$KIT/metrics/errors.py" --repo "$demo" | sed -n "/^## Барьеры/,/^## По неделям/p" | grep "^| B" | head -30
fi
[ "$fail" -eq 0 ] && [ "$pass" -gt 0 ]
