#!/usr/bin/env python3
"""Repro tests of the barriers that the loop made from its own incidents. Plain Python, no pytest.

  python tests/test_loop.py

Each test names the incident it closes. It must fail without the barrier and pass with it.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "gates"), str(ROOT / "metrics")]
os.environ["HARNESS_ERRORS"] = "0"
import collect  # noqa: E402
import dashboard  # noqa: E402

# a fake token in the new GitLab format, built at run time so that no gate sees a token in this file
FAKE = "gl" + "pat-" + "x" * 27 + ".01." + "y" * 9


def test_signature_skips_node_stack_header():  # INC-2026-11-06-07
    msg = "Exit code 1\nnode:internal/process/promises:394\n    triggerUncaughtException(err, true);\n    ^\n\n[TypeError: Headers.append: invalid header value.]"
    assert "TypeError" in dashboard.signature("Bash", msg), dashboard.signature("Bash", msg)


def test_signature_skips_success_line():  # INC-2026-11-06-10
    msg = "Exit code 1\n✓ check-syntax: 12 файлов, 3 inline-скриптов\nError: lint failed in app.js"
    assert "lint failed" in dashboard.signature("PowerShell", msg), dashboard.signature("PowerShell", msg)


def test_new_gitlab_token_is_masked():  # INC-2026-11-06-11
    out = collect.mask(f'[TypeError: "GITLAB_TOKEN={FAKE}" is an invalid header value.]')
    assert FAKE not in out and ".01." not in out, out


def test_new_gitlab_token_fails_the_gate():  # INC-2026-11-06-11
    src = (ROOT / "gates" / "check-secrets.py").read_text(encoding="utf-8")
    rx = re.search(r'\("GitLab token", re\.compile\(r"(.+?)"\)\)', src).group(1)
    assert re.search(rx, f"token = {FAKE}"), rx


def test_shell_patching_of_code_is_denied():  # INC-2026-11-06-03, -08, -13
    import json
    bash = shutil.which("bash") or "bash"  # a bare "bash" starts WSL on Windows (B22)
    for cmd, want in (("python - <<'PY'\nprint('x')\nPY\necho 'unclosed", 2), ("python - <<'PY'\nprint(\"it's ok\")\nPY", 0),
                      ("sed -i 's/x/newline=\"\\n\")/' tests/t.py", 2), ("sed -i 's/old/new/' src/app.py", 0),  # INC-2026-11-06-13
                      ("python - x.py <<'PY'\nlow = '\\\\n'.join(a)\nPY", 2), ("python - <<'PY'\nprint('a\\nb')\nPY", 0),  # INC-2026-11-07-01
                      ("cat > patch.py <<'PYEOF'\nx = 'a\\\\nb'\nPYEOF", 2), ("cat > notes.md <<'EOF'\nuse \\\\n in docs\nEOF", 0)):
        r = subprocess.run([bash, str(ROOT / "hooks" / "guard.sh")], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                           capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == want, (cmd, r.returncode, r.stderr)


def test_accepted_incident_needs_a_cause():  # gate B16, status accepted
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "error.md"
        p.write_text("## INC-2026-01-01-01: x\n- Cause:\n- Status: accepted\n", encoding="utf-8", newline="\n")
        gate = [sys.executable, str(ROOT / "gates" / "check-error-log.py"), str(p)]
        assert subprocess.run(gate, capture_output=True).returncode == 1
        p.write_text("## INC-2026-01-01-01: x\n- Cause: expected failure\n- Status: accepted\n", encoding="utf-8", newline="\n")
        assert subprocess.run(gate, capture_output=True).returncode == 0


def test_bare_bash_through_a_variable_fails_the_gate():  # INC-2026-11-06-12
    with tempfile.TemporaryDirectory() as d:
        Path(d, "run.py").write_text('import subprocess\nb = "bash"\nsubprocess.run([b, "x.sh"])\n', encoding="utf-8", newline="\n")
        subprocess.run(["git", "init", "-q", d], check=True)
        env = dict(os.environ, HARNESS_ALL="1", HARNESS_ERRORS="0")
        subprocess.run(["git", "-C", d, "add", "run.py"], check=True, capture_output=True)
        r = subprocess.run([sys.executable, str(ROOT / "gates" / "check-portability.py")], cwd=d, env=env, capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 1 and "B22" in r.stderr, (r.returncode, r.stderr)


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_")]
    failed = 0
    for n, f in tests:
        try:
            f()
            print(f"ok   {n}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {n}: {e}")
    print(f"{len(tests) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
