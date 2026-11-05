"""Shared helpers for diff-based gates.

Changed files and added lines come from, in order:
  1. HARNESS_BASE env (CI: the target branch, for example origin/main): diff BASE...HEAD
  2. staged changes (local pre-commit use)
  3. the last commit (HEAD~1..HEAD)
  4. all tracked files (a repository with one commit)
"""
import os
import subprocess
import sys

TEXT_LIMIT = 2_000_000


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def _range() -> list:
    base = os.environ.get("HARNESS_BASE", "").strip()
    if base and git("rev-parse", "--verify", base):
        return [f"{base}...HEAD"]
    if git("diff", "--cached", "--name-only").strip():
        return ["--cached"]
    if git("rev-parse", "--verify", "HEAD~1"):
        return ["HEAD~1", "HEAD"]
    return []


def changed_files() -> list:
    rng = _range()
    if not rng:
        return [f for f in git("ls-files").splitlines() if f]
    out = git("diff", "--name-only", "--diff-filter=ACMR", *rng)
    return [f for f in out.splitlines() if f]


def added_and_removed(path: str):
    """Return (added_lines, removed_lines) of a file in the current range."""
    rng = _range()
    if not rng:
        try:
            return read_text(path).splitlines(), []
        except OSError:
            return [], []
    diff = git("diff", "--unified=0", *rng, "--", path)
    added, removed = [], []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
    return added, removed


def read_text(path: str) -> str:
    with open(path, "rb") as fh:
        data = fh.read(TEXT_LIMIT)
    if b"\0" in data[:8000]:
        raise OSError("binary")
    return data.decode("utf-8", errors="replace")


def report(gate: str, problems: list, ok_note: str = "") -> int:
    if problems:
        print(f"FAIL {gate}:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"{gate}: OK{(' — ' + ok_note) if ok_note else ''}")
    return 0
