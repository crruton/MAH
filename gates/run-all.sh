#!/usr/bin/env bash
# Runs every harness gate from the repository root. Exit code is non-zero if any gate fails.
# CI: set HARNESS_BASE to the target branch (for example origin/main) to check only the change.
# Skip a gate: HARNESS_SKIP="check-ste" (write the reason in the merge request).
# Optional gates: HARNESS_EXTRA="check-large-files".
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
py=$(command -v python3 || command -v python)
skip=" ${HARNESS_SKIP:-} "
rc=0 n=0 failed=()
run() { # run <gate-name> <command...>
  local name="$1"; shift
  case "$skip" in *" $name "*) echo "$name: SKIPPED (HARNESS_SKIP)"; return ;; esac
  n=$((n + 1))
  if ! "$@"; then rc=1; failed+=("$name"); fi
}
run check-secrets           "$py" "$here/check-secrets.py"
run check-forbidden-files   "$py" "$here/checks.py" forbidden-files
run check-conflict-markers  "$py" "$here/checks.py" conflict-markers
run check-test-weakening    "$py" "$here/checks.py" test-weakening
run check-adr-numbers       bash  "$here/check-adr-numbers.sh" "${HARNESS_ADR_DIR:-docs/adr}"
run check-adr-fields        "$py" "$here/checks.py" adr-fields
run check-adr-links         "$py" "$here/checks.py" adr-links
run check-error-log         "$py" "$here/check-error-log.py" error.md
run check-rules-size        bash  "$here/check-rules-size.sh" 150 AGENTS.md CLAUDE.md
run check-ste               "$py" "$here/check-ste.py"
run check-portability       "$py" "$here/check-portability.py"
run check-test-deletion     "$py" "$here/checks.py" test-deletion
run check-suppressions      "$py" "$here/checks.py" suppressions
run check-leftovers         "$py" "$here/checks.py" leftovers
run check-lockfile-sync     "$py" "$here/checks.py" lockfile-sync
run check-zones             "$py" "$here/checks.py" zones
run check-harness-integrity "$py" "$here/checks.py" integrity
case " ${HARNESS_EXTRA:-} " in *" check-large-files "*) run check-large-files "$py" "$here/checks.py" large-files ;; esac
echo
if [ $rc -eq 0 ]; then echo "gates: $n passed"; else echo "gates: ${#failed[@]} of $n failed: ${failed[*]}" >&2; fi
exit $rc
