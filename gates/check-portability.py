#!/usr/bin/env python3
"""B21-B27. Portability gate: mistakes that work on Linux and break on Windows, or break later.

Each rule comes from a real agent error (see error.md of MAH):
  B21  re.M / re.MULTILINE pattern with \\s: an empty field captures the next line. Use [ \\t].
  B22  subprocess with a bare "bash" or "sh": Windows starts WSL from System32, not Git Bash.
       Use shutil.which("bash").
  B23  stdio protocol test: communicate() with JSON-RPC input closes stdin before the server
       answers. Read each reply before you send the next message.
  B24  dependency with a lower bound only (pkg>=1): the next major version breaks imports.
       Add an upper bound (<N) and test both majors in CI.
  B25  text I/O without encoding: open(), read_text(), write_text(), subprocess text=True.
       Windows uses cp1251/cp866 by default and breaks Cyrillic.
  B26  shell script with CRLF, or .gitattributes without "*.sh text eol=lf".
  B27  shell script or hook in git without the exec bit (100644 instead of 100755).

Python checks use the ast module. Files: changed files (see _lib), or all files with HARNESS_ALL=1.
"""
import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import changed_files, git, read_text, report  # noqa: E402

RE_FUNCS = {"compile", "search", "match", "fullmatch", "findall", "finditer", "sub", "subn", "split"}
FLAG_POS = {"compile": 1, "search": 2, "match": 2, "fullmatch": 2, "findall": 2, "finditer": 2, "split": 3, "sub": 4, "subn": 4}
SUBPROC = {"run", "call", "check_call", "check_output", "Popen"}
SCRIPT = re.compile(r"(\.sh|(^|/)(pre-push|pre-commit|commit-msg|post-commit|prepare-commit-msg))$")


def has_multiline(node) -> bool:
    return any(isinstance(n, ast.Attribute) and n.attr in ("M", "MULTILINE") for n in ast.walk(node))


def const_str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def kw(call, name):
    return next((k.value for k in call.keywords if k.arg == name), None)


def is_true(node) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def check_python(path: str, src: str, problems: list):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    jsonrpc = "jsonrpc" in src
    # names bound to a string constant: bash = "bash"; subprocess.run([bash, ...]) is the same error (INC-2026-11-06-12)
    names = {t.id: n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
             and isinstance(n.value.value, str) for t in n.targets if isinstance(t, ast.Name)}

    def head_of(node):
        return names.get(node.id) if isinstance(node, ast.Name) else const_str(node)

    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
        f = call.func
        name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
        owner = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
        loc = f"{path}:{call.lineno}"
        # B21
        if owner == "re" and name in RE_FUNCS and call.args:
            pat = const_str(call.args[0])
            pos = FLAG_POS.get(name, 2)
            flags = kw(call, "flags") or (call.args[pos] if len(call.args) > pos else None)
            if pat and "\\s" in pat and flags is not None and has_multiline(flags):
                problems.append(("B21", f"{loc}: re.M pattern with \\s can match the next line. Use [ \\t]."))
        # B22
        if owner == "subprocess" and name in SUBPROC and call.args:
            first = call.args[0]
            head = head_of(first.elts[0]) if isinstance(first, (ast.List, ast.Tuple)) and first.elts else head_of(first)
            if head and head.split()[0] in ("bash", "sh"):
                problems.append(("B22", f"{loc}: bare \"{head.split()[0]}\" starts WSL on Windows. Use shutil.which(\"bash\")."))
        # B23
        if name == "communicate" and jsonrpc and (call.args or kw(call, "input") is not None):
            problems.append(("B23", f"{loc}: communicate() sends all JSON-RPC messages and closes stdin. Read each reply first."))
        # B25
        if name == "open" and not owner and kw(call, "encoding") is None:
            mode = const_str(call.args[1]) if len(call.args) > 1 else const_str(kw(call, "mode")) or "r"
            if mode is not None and "b" not in mode:
                problems.append(("B25", f"{loc}: open() in text mode without encoding. Add encoding=\"utf-8\"."))
        if name in ("read_text", "write_text") and isinstance(f, ast.Attribute) and kw(call, "encoding") is None:
            n_pos = 0 if name == "read_text" else 1
            if len(call.args) <= n_pos:
                problems.append(("B25", f"{loc}: {name}() without encoding. Add encoding=\"utf-8\"."))
        # B25: text writes translate "\n" to "\r\n" on Windows unless newline= is set
        if name == "write_text" and isinstance(f, ast.Attribute) and kw(call, "newline") is None and len(call.args) < 4:
            problems.append(("B25", f"{loc}: write_text() without newline=. Windows writes CRLF. Add newline=\"\\n\"."))
        if name == "open" and not owner and kw(call, "newline") is None:
            mode = const_str(call.args[1]) if len(call.args) > 1 else const_str(kw(call, "mode"))
            if mode and "b" not in mode and any(c in mode for c in "wax"):
                problems.append(("B25", f"{loc}: open(..., \"{mode}\") without newline=. Windows writes CRLF. Add newline=\"\\n\"."))
        if owner == "subprocess" and name in SUBPROC and kw(call, "encoding") is None and \
                (is_true(kw(call, "text")) or is_true(kw(call, "universal_newlines"))):
            problems.append(("B25", f"{loc}: subprocess text=True without encoding. Add encoding=\"utf-8\"."))


REQ = re.compile(r"^\s*([A-Za-z0-9_.\-\[\]]+)\s*>=\s*[\w.]+\s*(?:;.*)?$")


def check_requirements(path: str, src: str, problems: list):
    for n, line in enumerate(src.splitlines(), 1):
        line = line.split("#")[0].strip().strip('",')
        m = REQ.match(line)
        if m and "<" not in line:
            problems.append(("B24", f"{path}:{n}: \"{line}\" has no upper bound. Add <NEXT_MAJOR and test both majors."))


def main() -> int:
    problems = []
    # bench/tasks/*/repo/ is the start state of a task for the agent: a fixture, not code of this kit
    files = [f for f in changed_files() if Path(f).is_file() and not (f.startswith("bench/tasks/") and "/repo/" in f)]
    for f in files:
        try:
            src = read_text(f)
        except OSError:
            continue
        if f.endswith(".py"):
            check_python(f, src, problems)
        name = f.rsplit("/", 1)[-1]
        if re.match(r"requirements.*\.txt$", name) or name == "pyproject.toml":
            check_requirements(f, src, problems)
        if SCRIPT.search(f) or src.startswith("#!/usr/bin/env bash") or src.startswith("#!/bin/sh"):
            if "\r\n" in src:
                problems.append(("B26", f"{f}: CRLF line endings in a shell script. Convert to LF."))
            mode = git("ls-files", "-s", "--", f).split(" ")[0]
            if mode and mode != "100755":
                problems.append(("B27", f"{f}: mode {mode}. Run: git update-index --chmod=+x {f}"))
    if any(SCRIPT.search(f) for f in files):
        ga = Path(".gitattributes")
        text = ga.read_text(encoding="utf-8") if ga.exists() else ""
        if not re.search(r"^\*\.sh[ \t]+.*eol=lf", text, re.M):
            problems.append(("B26", ".gitattributes: add \"*.sh text eol=lf\" so Windows checkouts keep LF."))
    rc = 0
    for bid in sorted({b for b, _ in problems}):
        rc |= report(f"check-portability {bid}", [p for b, p in problems if b == bid], barrier=bid)
    if not problems:
        report("check-portability", [], f"{len(files)} files, B21-B27")
    return rc


if __name__ == "__main__":
    sys.exit(main())
