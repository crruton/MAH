#!/usr/bin/env python3
"""Add or remove the self-harness hooks in a Claude Code settings.json.

  claude_settings.py add    <settings.json> <guard.sh> [<collect-tool-errors.sh>]
  claude_settings.py remove <settings.json>
  claude_settings.py show   <settings.json>

Other hooks and keys of the file stay as they are. Our entries are the hook commands
that contain "/harness/hooks/". `add` writes a backup next to the file first and does
nothing when our entries are already there.
"""
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

MARK = "/harness/hooks/"


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() and p.stat().st_size else {}


def save(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def ours(entry: dict) -> bool:
    return any(MARK in (h.get("command") or "").replace("\\", "/") for h in entry.get("hooks", []))


def add(p: Path, guard: str, collector: str = "") -> int:
    data = load(p)
    if p.exists():
        shutil.copy2(p, p.with_name(f"{p.name}.bak-harness-{dt.datetime.now():%Y%m%d-%H%M%S}"))
    hooks = data.setdefault("hooks", {})
    want = [("PreToolUse", "Bash|Read|Edit|Write", guard)]
    if collector:
        want.append(("PostToolUse", "*", collector))
    added = 0
    for event, matcher, script in want:
        lst = hooks.setdefault(event, [])
        if any(ours(e) and script.split("/")[-1] in json.dumps(e) for e in lst):
            continue
        lst.append({"matcher": matcher, "hooks": [{"type": "command", "command": f'bash "{script}"', "timeout": 10}]})
        added += 1
    save(p, data)
    print(f"{p}: {added} hook entries added")
    return 0


def remove(p: Path) -> int:
    data = load(p)
    hooks = data.get("hooks", {})
    removed = 0
    for event in list(hooks):
        keep = [e for e in hooks[event] if not ours(e)]
        removed += len(hooks[event]) - len(keep)
        if keep:
            hooks[event] = keep
        else:
            del hooks[event]
    if not hooks and "hooks" in data:
        del data["hooks"]
    if removed:
        save(p, data)
    print(f"{p}: {removed} hook entries removed")
    return 0


def show(p: Path) -> int:
    for event, lst in load(p).get("hooks", {}).items():
        for e in lst:
            if ours(e):
                print(event, e.get("matcher"), e["hooks"][0]["command"])
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("add", "remove", "show"):
        sys.exit(__doc__)
    cmd, path = sys.argv[1], Path(sys.argv[2])
    sys.exit({"add": lambda: add(path, *sys.argv[3:5]), "remove": lambda: remove(path), "show": lambda: show(path)}[cmd]())
