#!/usr/bin/env bash
# Runs every harness gate from the repository root. Exit code is non-zero if any gate fails.
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
py=$(command -v python3 || command -v python)
rc=0
bash "$here/check-adr-numbers.sh" docs/adr || rc=1
bash "$here/check-rules-size.sh" 150 AGENTS.md CLAUDE.md || rc=1
"$py" "$here/check-error-log.py" error.md || rc=1
exit $rc
