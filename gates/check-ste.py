#!/usr/bin/env python3
"""B18. Check agent-facing English text against measurable ASD-STE100 Issue 9 rules.

Agents read AGENTS.md, CLAUDE.md, skills and rules on every task. Short, plain English
uses fewer tokens and gives fewer ways to misread an instruction.

Checked rules (ASD-STE100 Issue 9, Part 1):
  5.1  Procedural sentence (list item, numbered step): max 20 words.     -> error
  6.3  Descriptive sentence: max 25 words.                               -> error
  6.6  Paragraph: max 6 sentences.                                       -> error
  4.2  No contractions (don't, it's, can't).                             -> error
  8.1  No semicolons.                                                    -> error
  1.1  Words that are not approved in the STE dictionary (subset in ste-wordlist.tsv),
       with the approved alternative.                                    -> error
  5.2  One instruction in each sentence ("and then", ", then").          -> warning
  3.6  Passive voice ("is/are/was/were/be/been + -ed").                  -> warning

Not checked: code blocks, inline code, tables, headings, YAML front matter, URLs,
sentences with Cyrillic text (STE applies to English only).
Word count follows rules 8.5-8.7: text in parentheses, numbers with units and
hyphenated words count as one word.

Usage: check-ste.py [--strict] [files...]
Default files: AGENTS.md CLAUDE.md .claude/skills/**/SKILL.md rules/*.md
"""
import glob
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import collect  # noqa: E402

HERE = Path(__file__).parent
PROC_MAX, DESC_MAX, PARA_MAX = 20, 25, 6
DEFAULT = ["AGENTS.md", "CLAUDE.md", ".claude/skills/**/SKILL.md", "rules/*.md"]

CONTRACTION = re.compile(r"\b\w+(n't|'re|'ve|'ll|'d|'m)\b|\b(it|that|there|what|he|she)'s\b", re.I)
PASSIVE = re.compile(r"\b(is|are|was|were|be|been|being)\s+((?-i:[a-z]{2,}ed)|done|made|given|taken|written|shown|known|seen|set|put|kept|built|run)\b", re.I)
SEQUENCE = re.compile(r"\band then\b|,\s*then\b", re.I)
CYR = re.compile(r"[А-Яа-яЁё]")


def wordlist():
    out = {}
    for line in (HERE / "ste-wordlist.tsv").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            word, alt = line.split("\t")[:2]
            out[word.lower()] = alt
    return out


def words(sentence: str) -> int:
    s = re.sub(r"\([^)]*\)", " P ", sentence)                         # 8.5
    s = re.sub(r"\b\d+([.,]\d+)?\s?(%|ms|s|kb|mb|gb|rps|min|h)\b", " N ", s, flags=re.I)  # 8.6
    return len([w for w in re.split(r"\s+", s) if re.search(r"\w", w)])  # 8.7: a-b is one token


def clean(line: str) -> str:
    line = re.sub(r"`[^`]*`", "X", line)
    line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
    line = re.sub(r"https?://\S+", "URL", line)
    return re.sub(r"[*_]{1,2}", "", line)


def sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.!?:])\s+(?=[A-Z0-9\"(])", text) if s.strip()]


def blocks(text: str):
    """Yield (line_no, kind, text). kind: proc (list item) or desc (paragraph)."""
    in_code = in_front = False
    para, start = [], 0
    lines = text.splitlines()
    for n, raw in enumerate(lines, 1):
        s = raw.strip()
        if n == 1 and s == "---":
            in_front = True
            continue
        if in_front:
            in_front = s != "---"
            continue
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        item = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", raw)
        if not s or s.startswith(("#", "|", ">")) or item:
            if para:
                yield start, "desc", " ".join(para)
                para = []
            if item:
                yield n, "proc", item.group(3)
            continue
        if not para:
            start = n
        para.append(s)
    if para:
        yield start, "desc", " ".join(para)


def check(path: str, words_bad: dict):
    errors, warns = [], []
    for n, kind, raw in blocks(Path(path).read_text(encoding="utf-8")):
        text = clean(raw)
        sents = [s for s in sentences(text) if not CYR.search(s)]
        if kind == "desc" and len(sents) > PARA_MAX:
            errors.append(f"{path}:{n}: 6.6 paragraph has {len(sents)} sentences (max {PARA_MAX}).")
        for s in sents:
            limit = PROC_MAX if kind == "proc" else DESC_MAX
            rule = "5.1" if kind == "proc" else "6.3"
            w = words(s)
            if w > limit:
                errors.append(f"{path}:{n}: {rule} sentence has {w} words (max {limit}): \"{s[:70]}...\"")
            if CONTRACTION.search(s):
                errors.append(f"{path}:{n}: 4.2 contraction \"{CONTRACTION.search(s).group(0)}\". Write the full form.")
            if ";" in s:
                errors.append(f"{path}:{n}: 8.1 semicolon. Write two sentences.")
            for tok in re.findall(r"[A-Za-z]+", s):
                alt = words_bad.get(tok.lower())
                if alt:
                    errors.append(f"{path}:{n}: 1.1 \"{tok}\" is not approved. Use \"{alt}\".")
            if kind == "proc" and SEQUENCE.search(s):
                warns.append(f"{path}:{n}: 5.2 two instructions in one sentence. Write one step for each action.")
            if PASSIVE.search(s):
                warns.append(f"{path}:{n}: 3.6 passive voice \"{PASSIVE.search(s).group(0)}\". Use the active voice.")
    return errors, warns


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    files = []
    for pattern in args or DEFAULT:
        files += [f for f in glob.glob(pattern, recursive=True) if Path(f).is_file()]
    bad = wordlist()
    errors, warns = [], []
    for f in sorted(set(files)):
        e, w = check(f, bad)
        errors += e
        warns += w
    for w in warns:
        print(f"  warn {w}")
    if errors or (strict and warns):
        collect.record("gate", "B18", "check-ste", "failed", " | ".join((errors or warns)[:3]))
        print("FAIL check-ste (ASD-STE100 Issue 9):", *errors, sep="\n  ", file=sys.stderr)
        return 1
    print(f"check-ste: OK — {len(set(files))} files, {len(warns)} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
