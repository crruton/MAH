#!/usr/bin/env python3
"""Count tokens in agent-facing files: the cost that agents pay on each task.

Uses tiktoken (pip install tiktoken) as a proxy. Claude has its own tokenizer, so give
the numbers as an estimate and compare files with the same tokenizer only.

Usage: token_count.py [--encoding o200k_base] files...
Default files: AGENTS.md CLAUDE.md .claude/skills/**/SKILL.md
"""
import glob
import re
import sys

try:
    import tiktoken
except ImportError:
    sys.exit("pip install tiktoken")

args = sys.argv[1:]
name = "o200k_base"
if args[:1] == ["--encoding"]:
    name, args = args[1], args[2:]
enc = tiktoken.get_encoding(name)
files = []
for pattern in args or ["AGENTS.md", "CLAUDE.md", ".claude/skills/**/SKILL.md"]:
    files += glob.glob(pattern, recursive=True)

total = 0
print(f"{'tokens':>7} {'rules':>6} {'per rule':>9}  file   ({name})")
for f in sorted(set(files)):
    text = open(f, encoding="utf-8").read()
    t = len(enc.encode(text))
    rules = len(re.findall(r"^[ \t]*(-|\d+\.)[ \t]", text, re.M)) or 1
    total += t
    print(f"{t:>7} {rules:>6} {t / rules:>9.1f}  {f}")
print(f"{total:>7} total")
