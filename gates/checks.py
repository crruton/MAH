#!/usr/bin/env python3
"""Harness gates B08-B15, B19, B20, B34-B37. Usage: checks.py <gate> [args].

Gates:
  forbidden-files   B08  secret files are tracked (.env, keys, certificates)
  large-files       B09  a changed file is larger than HARNESS_MAX_FILE_KB (default 1024). Optional
  conflict-markers  B10  merge conflict markers in changed files
  test-weakening    B11  a test was skipped or lost assertions
  adr-fields        B14  an ADR has no Status, Applies To or Reconsider When
  adr-links         B15  an ADR refers to an ADR that does not exist
  zones             B19  a project setting opens a Red Zone action or turns off the hooks
  integrity         B20  harness files differ from harness.lock
  test-deletion     B34  a test file or a test function was deleted
  suppressions      B35  a new linter or type check suppression without a reason
  leftovers         B36  cut code ("// ... rest of the code"), stubs, debugger calls
  lockfile-sync     B37  a manifest changed its dependencies, the lock file did not
  lock                   write harness.lock (run after a reviewed harness change)

Any line with "harness-allow" is not checked by B35 and B36.
"""
import fnmatch
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _lib  # noqa: E402
from _lib import added_and_removed, changed_files, git, read_text, report  # noqa: E402

ADR_DIR = os.environ.get("HARNESS_ADR_DIR", "docs/adr")
ADR_FILE = re.compile(r"^(ADR-)?(\d{3,4})")


# ---------- B08
FORBIDDEN = [".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa", "id_ed25519", "secrets/*", "*.kdbx"]
ALLOWED = [".env.example", ".env.sample", ".env.template"]


def forbidden_files() -> int:
    problems = []
    for f in git("ls-files").splitlines():
        name = f.rsplit("/", 1)[-1]
        if any(fnmatch.fnmatch(name, a) for a in ALLOWED):
            continue
        if any(fnmatch.fnmatch(name, p) or fnmatch.fnmatch(f, p) for p in FORBIDDEN):
            problems.append(f"{f}: secret file is tracked. Run 'git rm --cached {f}', add it to .gitignore, rotate the secret.")
    return report("check-forbidden-files", problems)


# ---------- B09
def large_files() -> int:
    limit = int(os.environ.get("HARNESS_MAX_FILE_KB", "1024")) * 1024
    problems = []
    for f in changed_files():
        try:
            size = os.path.getsize(f)
        except OSError:
            continue
        if size > limit:
            problems.append(f"{f}: {size // 1024} KB > {limit // 1024} KB. Use Git LFS or an artifact store.")
    return report("check-large-files", problems)


# ---------- B10
MARKER = re.compile(r"^(<{7}|>{7})( |$)|^={7}$")


def conflict_markers() -> int:
    problems = []
    for f in changed_files():
        try:
            lines = read_text(f).splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            if MARKER.match(line):
                problems.append(f"{f}:{n}: merge conflict marker. Resolve the conflict.")
                break
    return report("check-conflict-markers", problems)


# ---------- B11
TEST_FILE = _lib.TEST_FILE
SKIP = re.compile(r"\bt\.Skip(Now)?\(|@pytest\.mark\.(skip|xfail)|pytest\.skip\(|\b(it|test|describe|context)\.(skip|only|todo)\(|"
                  r"\b[xf](it|describe|context|test)\(|@Disabled\b|@Ignore\b|\[Ignore\]|Skip\s*=\s*\"|unittest\.skip|#\[ignore\]|"
                  r"^\s*(skip|pending)\b|markTestSkipped|XCTSkip|@tag\s+:skip|\bskip:\s*true")
ASSERT = re.compile(r"\bassert|\bexpect\(|\bexpect\b.*\bto\b|\brequire\.|\bt\.(Error|Fatal)|\bShould\(|\bshould\b|Assert\.|XCTAssert|\brefute\b")


def test_weakening() -> int:
    problems = []
    for f in changed_files():
        if not TEST_FILE.search(f):
            continue
        added, removed = added_and_removed(f)
        if any(SKIP.search(line) for line in added):
            problems.append(f"{f}: a test is skipped or focused. Fix the code, not the test.")
        lost = sum(1 for line in removed if ASSERT.search(line)) - sum(1 for line in added if ASSERT.search(line))
        if lost > 0:
            problems.append(f"{f}: {lost} assertion(s) removed. A human must approve this change.")
    return report("check-test-weakening", problems)


# ---------- B34
TEST_DEF = re.compile(r"^\s*(func\s+Test\w*\(|(async\s+)?def\s+test_\w*\(|(it|test|specify)\s*\(\s*['\"`]|@Test\b|\[(Fact|Test|TestMethod|Theory)\]|"
                      r"#\[test\]|test\s+['\"]|func\s+test\w*\(\)|public function test\w*\()")


def test_deletion() -> int:
    problems = []
    for f in _lib.deleted_files():
        if TEST_FILE.search(f):
            problems.append(f"{f}: test file deleted. A human must approve this change.")
    for f in changed_files():
        if not TEST_FILE.search(f):
            continue
        added, removed = added_and_removed(f)
        lost = sum(1 for line in removed if TEST_DEF.search(line)) - sum(1 for line in added if TEST_DEF.search(line))
        if lost > 0:
            problems.append(f"{f}: {lost} test(s) removed. Fix the code, not the tests, or ask a human to approve.")
    return report("check-test-deletion", problems)


# ---------- B35
SUPPRESS = re.compile(r"eslint-disable|@ts-ignore|@ts-nocheck|@ts-expect-error|#\s*type:\s*ignore|#\s*noqa|pylint:\s*disable|//\s*nolint|"
                      r"@SuppressWarnings|#\[allow\(|rubocop:disable|#pragma warning disable|NOSONAR|istanbul ignore|c8 ignore|"
                      r"pragma:\s*no cover|@phpstan-ignore|phpcs:ignore|swiftlint:disable|detekt|ktlint-disable|biome-ignore|deno-lint-ignore")
REASON = re.compile(r"\s--\s+\S|reason:|because|harness-allow|\bsee\s+(https?:|#|[A-Z]+-\d+)|#\d+|[A-Z]{2,}-\d+")


def suppressions() -> int:
    problems = []
    for f in changed_files():
        if f.endswith((".md", ".txt", ".rst", ".json", ".yml", ".yaml")):  # text and data name a suppression, they do not use it
            continue
        added, _ = added_and_removed(f)
        n = sum(1 for line in added if SUPPRESS.search(line) and not REASON.search(line))
        if n:
            problems.append(f"{f}: {n} new linter or type check suppression(s) without a reason. "
                            "Fix the warning, or add the reason on the same line ('-- reason', 'reason:', a ticket ID).")
    return report("check-suppressions", problems)


# ---------- B36
LEFTOVER = [
    ("cut code", re.compile(r"(?i)(//|#|/\*|<!--|--)\s*(\.\.\.|…)?\s*(rest|remainder|remaining|existing|other|previous|same)\s+(of\s+(the\s+)?)?"
                            r"(code|implementation|methods?|functions?|logic|file|content|tests?)\b.*(here|unchanged|as before|remains?|omitted|goes here|\.\.\.|…)")),
    ("cut code", re.compile(r"(?i)^\s*(//|#)\s*\.\.\.\s*(code|implementation)\s*\.\.\.\s*$")),
    ("stub", re.compile(r"\b(todo|unimplemented)!\(\)|throw\s+new\s+(Error|NotImplementedException|UnsupportedOperationException)\(\s*['\"]?(not\s+implemented|TODO)|"
                        r"(?i:raise\s+NotImplementedError\(['\"](todo|implement))")),
    ("debugger", re.compile(r"^\s*debugger;?\s*$|\bbreakpoint\(\)|\bpdb\.set_trace\(\)|^\s*import\s+i?pdb\b|\bbinding\.(pry|irb)\b|^\s*byebug\b|"
                            r"\bdbg!\(|\bvar_dump\(|\bdd\(\$|\bconsole\.trace\(|runtime\.Breakpoint\(\)")),
]
NO_LEFTOVER_CHECK = (".md", ".txt", ".rst", ".snap", ".lock")


def leftovers() -> int:
    problems = []
    for f in changed_files():
        if f.endswith(NO_LEFTOVER_CHECK) or f.startswith("gates/"):
            continue
        added, _ = added_and_removed(f)
        for line in added:
            if "harness-allow" in line:
                continue
            hit = next((name for name, rx in LEFTOVER if rx.search(line)), "")
            if hit:
                problems.append(f"{f}: {hit} left in the code: `{line.strip()[:70]}`. "
                                + ("Write the full code: a cut comment deletes the real code." if hit == "cut code" else "Remove it before the merge."))
                break
    return report("check-leftovers", problems)


# ---------- B37
# manifest -> lock files; dependency lines -> regex that a dependency change matches
MANIFESTS = {
    "package.json": (("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb", "npm-shrinkwrap.json"),
                     re.compile(r"^\s*\"(?!version\"|name\"|description\"|main\"|types\"|module\"|node\"|npm\"|pnpm\"|yarn\")[@\w./-]+\"\s*:\s*\"(\^|~|[<>=]|\*|\d|workspace:|npm:|file:|link:|git|https?:|latest)")),
    "composer.json": (("composer.lock",), re.compile(r"^\s*\"[\w.-]+/[\w.-]+\"\s*:\s*\"")),
    "pyproject.toml": (("poetry.lock", "uv.lock", "pdm.lock"),
                       re.compile(r"^\s*\"[A-Za-z0-9_.\[\]-]+\s*([<>=!~]=?|@|;|\")|^\s*(?!name|version|description|readme|requires-python|license|python)[A-Za-z0-9_.-]+\s*=\s*(\"[\^~<>=*\d]|\{)")),
    "Pipfile": (("Pipfile.lock",), re.compile(r"^\s*[A-Za-z0-9_.-]+\s*=\s*(\"|\{)")),
    "Cargo.toml": (("Cargo.lock",), re.compile(r"^\s*(?!name|version|edition|description|license|authors|readme|rust-version)[A-Za-z0-9_-]+\s*=\s*(\"[\^~<>=*\d]|\{)")),
    "go.mod": (("go.sum",), re.compile(r"^\s*(require\s+)?[\w.-]+\.[\w.-]+/\S*\s+v\d")),
    "Gemfile": (("Gemfile.lock",), re.compile(r"^\s*gem\s+['\"]")),
    "mix.exs": (("mix.lock",), re.compile(r"\{:\w+,\s*\"")),
    "pubspec.yaml": (("pubspec.lock",), re.compile(r"^\s+[a-z0-9_]+:\s*[\^><=\d]")),
}


def lockfile_sync() -> int:
    changed = set(changed_files())
    tracked = set(git("ls-files").splitlines())
    problems = []
    for f in sorted(changed):
        d, _, name = f.rpartition("/")
        if name not in MANIFESTS:
            continue
        locks, dep = MANIFESTS[name]
        here = [f"{d}/{x}" if d else x for x in locks]
        have = [x for x in here if x in tracked]
        if not have or any(x in changed for x in have):
            continue  # the project does not commit a lock file, or the lock changed too
        added, removed = added_and_removed(f)
        if any(dep.search(line) for line in added + removed):
            problems.append(f"{f}: dependencies changed, {have[0]} did not. Run the package manager and commit the lock file.")
    return report("check-lockfile-sync", problems)


# ---------- B14, B15
def adr_files():
    d = Path(ADR_DIR)
    if not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("*.md")):
        m = ADR_FILE.match(p.name)
        if m and m.group(2).strip("0"):
            out.append((m.group(2), p))
    return out


def field(text: str, name: str) -> str:
    m = re.search(rf"^[ \t]*-?[ \t]*\**{name}:?\**:?[ \t]*(.*)$", text, re.M | re.I)
    return m.group(1).strip(" *`") if m else ""


def adr_fields() -> int:
    problems = []
    for num, p in adr_files():
        t = p.read_text(encoding="utf-8")
        for name in ("Status", "Applies To", "Reconsider When"):
            v = field(t, name)
            if not v or v.startswith("<") or "PROPOSED | APPROVED" in v:
                problems.append(f"{p.name}: field '{name}' is empty.")
    return report("check-adr-fields", problems, f"{len(adr_files())} ADR")


def adr_links() -> int:
    nums = {n.lstrip("0") for n, _ in adr_files()}
    problems = []
    for num, p in adr_files():
        for ref in re.findall(r"ADR-(\d{3,4})", p.read_text(encoding="utf-8")):
            if ref.lstrip("0") and ref.lstrip("0") not in nums:
                problems.append(f"{p.name}: refers to ADR-{ref}, which does not exist.")
    return report("check-adr-links", problems)


# ---------- B19
# A project setting must not open what the global guard closes.
RISKY_ALLOW = ["git reset", "git clean", "git push --force", "git push -f", "rm -rf", ".env", "secrets/", "*.pem", "*.key"]


def zones() -> int:
    problems = []
    for p in (Path(".claude/settings.json"), Path(".claude/settings.local.json")):
        if not p.exists() or (p.name.endswith("local.json") and not git("ls-files", str(p)).strip()):
            continue
        cfg = json.loads(p.read_text(encoding="utf-8"))
        for rule in cfg.get("permissions", {}).get("allow", []):
            if any(r in rule for r in RISKY_ALLOW):
                problems.append(f"{p}: allow rule \"{rule}\" opens a Red Zone action. Remove it.")
        if cfg.get("disableAllHooks"):
            problems.append(f"{p}: disableAllHooks turns off the guard. Remove it.")
        if cfg.get("permissions", {}).get("defaultMode") == "bypassPermissions":
            problems.append(f"{p}: defaultMode bypassPermissions in a shared file. Remove it.")
    o = Path("opencode.json")
    if o.exists():
        bash = json.loads(o.read_text(encoding="utf-8")).get("permission", {}).get("bash", {})
        if isinstance(bash, dict):
            for pattern, value in bash.items():
                if value == "allow" and any(r in pattern for r in ("git reset", "rm -rf", "git push --force")):
                    problems.append(f"opencode.json: bash \"{pattern}\" is allow. Use deny or ask.")
    return report("check-zones", problems)


# ---------- B20
LOCK = Path("harness.lock")
GUARDED = [".githooks", ".claude/hooks", ".claude/settings.json", "opencode.json", "gates"]


def guarded_files():
    out = []
    for g in GUARDED:
        p = Path(g)
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out += sorted(x for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts)
    return out


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def lock() -> int:
    data = {str(p).replace("\\", "/"): digest(p) for p in guarded_files()}
    LOCK.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"harness.lock: {len(data)} files")
    return 0


def integrity() -> int:
    if not LOCK.exists():
        return report("check-harness-integrity", [], "no harness.lock, skipped (install --project --lock to use it)")
    want = json.loads(LOCK.read_text(encoding="utf-8"))
    have = {str(p).replace("\\", "/"): digest(p) for p in guarded_files()}
    problems = [f"{f}: changed without review (harness.lock differs)." for f in sorted(set(want) | set(have))
                if want.get(f) != have.get(f)]
    return report("check-harness-integrity", problems, f"{len(have)} files")


GATES = {
    "forbidden-files": forbidden_files, "large-files": large_files, "conflict-markers": conflict_markers,
    "test-weakening": test_weakening, "adr-fields": adr_fields, "adr-links": adr_links,
    "zones": zones, "integrity": integrity, "lock": lock,
    "test-deletion": test_deletion, "suppressions": suppressions, "leftovers": leftovers, "lockfile-sync": lockfile_sync,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in GATES:
        print(__doc__)
        sys.exit(2)
    sys.exit(GATES[sys.argv[1]]())
