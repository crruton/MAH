#!/usr/bin/env python3
"""Barrier B39: mask secret values in the output of a test run before the output reaches the agent.

guard.sh changes a test command into  { <command> ; } 2>&1 | python mask-output.py <repo root>
A failed assert can print a dict of headers or a connection string with the secret in it. B06 stops
the agent from reading the secret file, but the test reads it, and the output goes to the model
(INC-2026-11-09-04). This filter replaces each secret value with *** and keeps the rest of the line.

Secret values come from the secret files of the repository (the same names as B06): .env and
.env.*, *.local.json, settings.local.*, credentials.json, secrets.json|yaml|yml|toml, secrets/.
Known token formats are masked too. The filter never fails: on an error it prints the line as is.
"""
import json
import os
import re
import sys
from pathlib import Path

SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", "dist", "build", ".remote.git"}
EXAMPLE = re.compile(r"\.(example|sample|template)$")
SECRET_FILE = re.compile(r"^(\.env(\..+)?|.+\.local\.json|settings\.local\..+|credentials\.json|secrets\.(json|ya?ml|toml))$")
SECRET_KEY = re.compile(r"pass|secret|token|key|auth|credential|dsn|private|cookie|session", re.I)
TOKENS = re.compile(r"(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}|gl(pat|dt|rt|ptt|cbt|soat)-[A-Za-z0-9_.-]{20,}"
                    r"|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|xox[abpr]-[A-Za-z0-9-]{10,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})")
MIN = 6  # shorter values ("dev", "1234") are too common to mask


def secret_files(root: Path, depth: int = 5):
    for dirpath, dirs, files in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        dirs[:] = [d for d in dirs if d not in SKIP] if len(rel.parts) < depth else []
        in_secrets = "secrets" in rel.parts
        for f in files:
            if (in_secrets or SECRET_FILE.match(f)) and not EXAMPLE.search(f):
                yield Path(dirpath, f)


def json_values(node, key=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from json_values(v, k)
    elif isinstance(node, list):
        for v in node:
            yield from json_values(v, key)
    elif isinstance(node, str) and SECRET_KEY.search(key):
        yield node


def values(root: Path) -> list:
    found = set()
    for p in secret_files(root):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if p.suffix == ".json":
            try:
                found.update(json_values(json.loads(text)))
                continue
            except ValueError:
                pass
        for line in text.splitlines():
            m = re.match(r"\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_.-]*\s*[=:]\s*(.*?)\s*$", line)
            if m:
                found.add(m.group(1).strip("'\""))
    return sorted((v for v in found if len(v) >= MIN), key=len, reverse=True)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    try:
        secrets = values(root)
    except Exception:  # noqa: BLE001 - the filter must never break the test run
        secrets = []
    rx = re.compile("|".join(re.escape(s) for s in secrets)) if secrets else None
    out = sys.stdout.buffer
    for raw in sys.stdin.buffer:
        try:
            line = raw.decode("utf-8", errors="surrogateescape")
            if rx:
                line = rx.sub("***", line)
            line = TOKENS.sub("***", line)
            out.write(line.encode("utf-8", errors="surrogateescape"))
        except Exception:  # noqa: BLE001
            out.write(raw)
        out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
