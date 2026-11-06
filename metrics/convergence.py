#!/usr/bin/env python3
"""Weekly convergence metrics of an agent harness, computed from git history.

Per ISO week of the chosen branch:
  commits, merges, fix share   — how much work goes into repairs;
  ADR total                    — are decisions being recorded;
  rule bullets in AGENTS.md    — is the harness bloating;
  test files                   — is behaviour covered.

A converging harness shows a falling fix share while rules plateau and code grows.
Fix commits are detected by keywords in the subject, so the share is an estimate.

Usage: convergence.py [--repo PATH] [--branch REF] [--rules AGENTS.md] [--adr docs/adr] [--csv out.csv]
"""
import argparse
import collections
import csv
import datetime as dt
import re
import subprocess
import sys

FIX_RE = re.compile(r"(?i)\bfix|\bhotfix|\bbug|\brevert|исправ|почин|чиним|откат")
# the same list as gates/_lib.py TEST_FILE
TEST_RE = re.compile(
    r"(_test\.(go|py|rb|exs|dart|cpp|cc|c)|\.(test|spec)\.[cm]?[jt]sx?|(^|/)test_[^/]+\.py|_spec\.rb|"
    r"(Test|Tests|IT|Spec)\.(java|kt|scala|cs|php|swift)|(^|/)tests/[^/]+\.rs)$")
ADR_RE = re.compile(r"^(ADR-)?\d{3,4}")
BULLET_RE = re.compile(r"^\s*([-*]|\d+\.)\s+\S")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--branch", default="HEAD")
    ap.add_argument("--rules", default="AGENTS.md")
    ap.add_argument("--adr", default="docs/adr")
    ap.add_argument("--csv")
    a = ap.parse_args()

    log = git(a.repo, "log", a.branch, "--reverse", "--format=%H|%ad|%P|%s", "--date=short")
    if not log.strip():
        sys.exit("no commits found")
    weeks = collections.OrderedDict()
    for line in log.splitlines():
        sha, day, parents, subject = line.split("|", 3)
        y, w, _ = dt.date.fromisoformat(day).isocalendar()
        k = f"{y}-W{w:02d}"
        rec = weeks.setdefault(k, {"week": k, "start": day, "commits": 0, "merges": 0, "fixes": 0})
        rec["commits"] += 1
        rec["merges"] += len(parents.split()) > 1
        rec["fixes"] += bool(FIX_RE.search(subject))
        rec["last"] = sha

    rows = []
    for rec in weeks.values():
        files = git(a.repo, "ls-tree", "-r", "--name-only", rec["last"]).splitlines()
        adr = {ADR_RE.match(f.rsplit("/", 1)[1]).group(0).replace("ADR-", "")
               for f in files if f.startswith(a.adr.rstrip("/") + "/") and ADR_RE.match(f.rsplit("/", 1)[1])}
        # projects keep agent rules in AGENTS.md or CLAUDE.md; count the first one that exists
        rules_txt = next((t for t in (git(a.repo, "show", f"{rec['last']}:{r}") for r in (a.rules, "CLAUDE.md")) if t), "")
        rows.append({
            "week": rec["week"], "start": rec["start"], "commits": rec["commits"], "merges": rec["merges"],
            "fix_share_pct": round(100 * rec["fixes"] / rec["commits"]),
            "adr_total": len(adr),
            "rule_bullets": sum(1 for l in rules_txt.splitlines() if BULLET_RE.match(l)),
            "rules_lines": len(rules_txt.splitlines()),
            "test_files": sum(1 for f in files if TEST_RE.search(f)),
        })

    cols = list(rows[0].keys())
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=cols)
            wr.writeheader()
            wr.writerows(rows)
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")


if __name__ == "__main__":
    main()
