#!/usr/bin/env bash
# Context files are a table of contents, not a book: fail above the line limit.
# Usage: check-rules-size.sh [limit] [files...]   (default: 150 AGENTS.md CLAUDE.md)
set -euo pipefail
limit="${1:-150}"; shift || true
files=("$@"); [ ${#files[@]} -eq 0 ] && files=(AGENTS.md CLAUDE.md)
rc=0
for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  n=$(wc -l < "$f" | tr -d ' ')
  if [ "$n" -gt "$limit" ]; then
    echo "FAIL: $f has $n lines (limit $limit). Move details to linked docs." >&2; rc=1
  else
    echo "check-rules-size: $f $n/$limit OK"
  fi
done
exit $rc
