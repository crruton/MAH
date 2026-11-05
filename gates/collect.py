#!/usr/bin/env python3
"""Error collector: append one event to the error store.

Store: <repo>/.harness/errors/events-YYYY-MM-<author>.jsonl
  One JSON object per line. One file per author and month, so files merge in git
  without conflicts and the team gets shared statistics. Commit the folder.
Sources: hook (agent hooks), git-hook, gate (local or CI), tool (failed agent tool call), manual.
Secrets and personal data in `detail` are masked before the write.
The collector never fails the caller: errors in the collector are ignored.

Usage:
  collect.py --source hook --barrier B05 --name guard-destructive --outcome blocked \
             [--session ID] [--detail TEXT | --detail-stdin]
Env: HARNESS_ERRORS=0 turns the collector off. HARNESS_ERRORS_DIR changes the folder.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MASKS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "<private-key>"),
    (re.compile(r"\b(AKIA[0-9A-Z]{16}|gh[posu]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_\-]{20}|xox[abposr]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_\-]{20,})"), "<token>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "<jwt>"),
    (re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b(\s*[:=]\s*)\S+"), r"\1\2<secret>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<email>"),
    (re.compile(r"(?<!\w)\+?\d[\d ()-]{8,}\d"), "<phone>"),
]


def _git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def mask(text: str) -> str:
    for rx, sub in MASKS:
        text = rx.sub(sub, text)
    return text


def runtime() -> str:
    if os.environ.get("CLAUDECODE"):
        return "claude-code"
    if os.environ.get("OPENCODE"):
        return "opencode"
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS") or os.environ.get("GITLAB_CI"):
        return "ci"
    return "local"


def store_dir() -> Path:
    if os.environ.get("HARNESS_ERRORS_DIR"):
        return Path(os.environ["HARNESS_ERRORS_DIR"])
    root = _git("rev-parse", "--show-toplevel") or os.getcwd()
    return Path(root) / ".harness" / "errors"


def author() -> str:
    # user.name, not the email: the store is committed and can be public
    who = _git("config", "user.name") or os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    return re.sub(r"[^a-z0-9]+", "-", who.lower()).strip("-") or "unknown"


def record(source: str, barrier: str = "", name: str = "", outcome: str = "blocked",
           detail: str = "", session: str = "", actor: str = "") -> None:
    """Append one event. Never raises."""
    if os.environ.get("HARNESS_ERRORS") == "0":
        return
    try:
        now = dt.datetime.now(dt.timezone.utc)
        rt = runtime()
        event = {
            "v": 1,
            "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": source,
            "barrier": barrier,
            "name": name,
            "outcome": outcome,
            "actor": actor or ("agent" if source in ("hook", "tool") or rt in ("claude-code", "opencode") else "human"),
            "runtime": rt,
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "commit": _git("rev-parse", "--short", "HEAD"),
            "session": session[:64],
            "detail": mask(" ".join(detail.split()))[:300],
        }
        d = store_dir()
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"events-{now:%Y-%m}-{author()}.jsonl"
        with f.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:  # the collector must never break a hook or a gate
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=["hook", "git-hook", "gate", "tool", "manual"])
    ap.add_argument("--barrier", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--outcome", default="blocked", choices=["blocked", "failed", "tool-error", "incident"])
    ap.add_argument("--session", default="")
    ap.add_argument("--actor", default="")
    ap.add_argument("--detail", default="")
    ap.add_argument("--detail-stdin", action="store_true")
    a = ap.parse_args()
    detail = sys.stdin.read() if a.detail_stdin else a.detail
    record(a.source, a.barrier, a.name, a.outcome, detail, a.session, a.actor)
    return 0


if __name__ == "__main__":
    sys.exit(main())
