#!/usr/bin/env python3
"""Fail when a closed incident in error.md has no barrier, level or repro test.

An incident is a '## INC-...' section. 'Статус: закрыт' (or 'Status: closed') requires
non-empty 'Барьер', 'Уровень' and 'Репро-тест' fields (or Barrier, Level, Repro).
Usage: check-error-log.py [path]   (default: error.md)
"""
import re
import sys
from pathlib import Path

REQUIRED = {"Барьер": "Barrier", "Уровень": "Level", "Репро-тест": "Repro"}
LEVELS = {"текст", "хук", "сервер", "ос", "text", "hook", "server", "os"}


def fields(body: str) -> dict:
    out = {}
    for m in re.finditer(r"^[ \t]*-[ \t]*([^:\n]+):[ \t]*(.*)$", body, re.M):
        out[m.group(1).strip()] = m.group(2).strip()
    return out


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "error.md")
    if not path.exists():
        print(f"check-error-log: no {path}, skipped")
        return 0
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"^##\s+", text, flags=re.M)[1:]
    problems = []
    for sec in sections:
        title = sec.splitlines()[0].strip()
        if not title.startswith("INC-"):
            continue
        f = fields(sec)
        status = (f.get("Статус") or f.get("Status") or "").lower()
        if status not in ("закрыт", "closed"):
            continue
        for ru, en in REQUIRED.items():
            val = (f.get(ru) or f.get(en) or "").strip(" —-")
            if not val:
                problems.append(f"{title}: closed without '{ru}'")
        level = (f.get("Уровень") or f.get("Level") or "").lower()
        if level and level not in LEVELS:
            problems.append(f"{title}: unknown level '{level}' (use: текст | хук | сервер | ОС)")
    if problems:
        print("FAIL: error log:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    print(f"check-error-log: {len(sections)} incidents OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
