#!/usr/bin/env bash
# Fails when two ADR files share a number (the ADR-044 incident: parallel agents picked numbers from memory).
# Usage: check-adr-numbers.sh [adr_dir]   (default: docs/adr)
set -euo pipefail
dir="${1:-docs/adr}"
[ -d "$dir" ] || { echo "check-adr-numbers: no $dir, skipped"; exit 0; }
dups=$(ls "$dir" | grep -Eo '^(ADR-)?[0-9]{3,4}' | sed 's/^ADR-//' | sort | uniq -d || true)
if [ -n "$dups" ]; then
  py=$(command -v python3 || command -v python)
  "$py" "$(dirname "$0")/collect.py" --source gate --barrier B13 --name check-adr-numbers --outcome failed --detail "duplicate ADR numbers: $(echo $dups)" >/dev/null 2>&1 || true
  echo "FAIL: duplicate ADR numbers in $dir:" >&2
  for n in $dups; do ls "$dir" | grep -E "^(ADR-)?$n" | sed 's/^/  /' >&2; done
  next=$(ls "$dir" | grep -Eo '^(ADR-)?[0-9]{3,4}' | sed 's/^ADR-//' | sort -n | tail -1)
  echo "Next free number: $(printf '%0*d' ${#next} $((10#$next + 1)))" >&2
  exit 1
fi
echo "check-adr-numbers: OK"
