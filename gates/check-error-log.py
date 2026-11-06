#!/usr/bin/env python3
"""Fail when a closed incident in error.md has no barrier, level or repro test.

An incident is a '## INC-...' section. 'Статус: закрыт' (or 'Status: closed') requires
non-empty 'Барьер', 'Уровень' and 'Репро-тест' fields (or Barrier, Level, Repro).
'Статус: принят' (Status: accepted) means "not an agent error" and requires 'Причина' (Cause).
Usage: check-error-log.py [path]   (default: error.md)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import collect  # noqa: E402

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
    sections = re.split(r"^##[ \t]+", text, flags=re.M)[1:]
    problems = []
    for sec in sections:
        title = sec.splitlines()[0].strip()
        if not title.startswith("INC-"):
            continue
        f = fields(sec)
        status = (f.get("Статус") or f.get("Status") or "").lower()
        if status in ("принят", "accepted"):  # not an agent error: the reason must be written down
            if not (f.get("Причина") or f.get("Cause") or "").strip(" —-"):
                problems.append(f"{title}: accepted without 'Cause' (why this is not an agent error)")
            continue
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
        collect.record("gate", "B16", "check-error-log", "failed", " | ".join(problems[:3]))
        print("FAIL: error log:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    print(f"check-error-log: {len(sections)} incidents OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
