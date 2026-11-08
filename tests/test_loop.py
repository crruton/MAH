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
                      ("cat > patch.py <<'PYEOF'\nx = 'a\\\\nb'\nPYEOF", 2), ("cat > notes.md <<'EOF'\nuse \\\\n in docs\nEOF", 0),
                      ("python -I -c \"s = s.replace('a', 'b\\\\n')\"", 2), ("python -c \"print('a\\nb')\"", 0)):  # INC-2026-11-09-03
        r = subprocess.run([bash, str(ROOT / "hooks" / "guard.sh")], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                           capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == want, (cmd, r.returncode, r.stderr)


def test_secret_glob_is_denied():  # INC-2026-11-09-01
    import json
    bash = shutil.which("bash") or "bash"
    for cmd, want in (("cat .env* 2>/dev/null", 2), ("ls .env?", 2), ("cat .env.example", 0), ("ls src/*.py", 0)):
        r = subprocess.run([bash, str(ROOT / "hooks" / "guard.sh")], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                           capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == want, (cmd, r.returncode, r.stderr)


def _guard(payload: dict, cwd=None):
    import json
    bash = shutil.which("bash") or "bash"
    return subprocess.run([bash, str(ROOT / "hooks" / "guard.sh")], input=json.dumps(payload), cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8")


def test_secret_config_is_denied():  # INC-2026-11-09-05
    for tool, key, value, want in (("Read", "file_path", "config/settings.local.json", 2), ("Bash", "command", "cat credentials.json", 2),
                                   ("Bash", "command", "type config\\secrets.yaml", 2), ("Read", "file_path", ".claude/settings.local.json", 0),
                                   ("Read", "file_path", "src/settings.json", 0), ("Read", "file_path", "config/settings.local.json.example", 0)):
        r = _guard({"tool_name": tool, "tool_input": {key: value}})
        assert r.returncode == want, (value, r.returncode, r.stderr)


def test_test_output_is_masked():  # INC-2026-11-09-04
    import json
    secret = "bench-api-key-" + "7c21"  # harness:allow-secret: the fake key of bench task q27
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git", "init", "-q"], cwd=d, check=True)
        Path(d, "test_x.py").write_text("import sys\nprint({'Authorization': 'Bearer %s'})\nsys.exit(1)\n" % secret, encoding="utf-8", newline="\n")
        plain = _guard({"tool_name": "Bash", "tool_input": {"command": "python test_x.py"}}, cwd=d)
        assert plain.returncode == 0 and not plain.stdout.strip(), ("no secret file: the command stays", plain.stdout)
        Path(d, "api").mkdir()
        Path(d, "api", ".env").write_text("API_KEY=%s\n" % secret, encoding="utf-8", newline="\n")
        r = _guard({"tool_name": "Bash", "tool_input": {"command": "python test_x.py", "description": "run"}}, cwd=d)
        upd = json.loads(r.stdout)["hookSpecificOutput"]["updatedInput"]
        assert upd["description"] == "run" and "mask-output.py" in upd["command"], upd
        bash = shutil.which("bash") or "bash"
        run = subprocess.run([bash, "-c", upd["command"]], cwd=d, capture_output=True, text=True, encoding="utf-8")
        assert secret not in run.stdout and "Bearer ***" in run.stdout, run.stdout
        assert run.returncode == 1, ("the exit code of the test stays", run.returncode)
        # the form agents use in the bench (q27): cd, the runner, 2>&1, a filter, git status. The hook runs elsewhere.
        agent = f'cd "{Path(d).as_posix()}" && python test_x.py 2>&1 | tail -15; git status --short'
        r = _guard({"tool_name": "Bash", "tool_input": {"command": agent}}, cwd=tempfile.gettempdir())
        upd = json.loads(r.stdout)["hookSpecificOutput"]["updatedInput"]
        run = subprocess.run([bash, "-c", upd["command"]], capture_output=True, text=True, encoding="utf-8")
        assert secret not in run.stdout and "Bearer ***" in run.stdout, run.stdout
        joined = f'cd "{Path(d).as_posix()}" && cat test_x.py && echo --- && python test_x.py 2>&1 | tail -20'
        r = _guard({"tool_name": "Bash", "tool_input": {"command": joined}}, cwd=d)
        assert "mask-output.py" in r.stdout, ("reads joined with a test run are masked too", joined)
        joined = f'cd "{Path(d).as_posix()}" && git ls-files && git log --oneline | head -3 && python test_x.py 2>&1 | tail -15'
        r = _guard({"tool_name": "Bash", "tool_input": {"command": joined}}, cwd=d)
        assert "mask-output.py" in r.stdout, ("git reads joined with a test run are masked too", joined)
        for other in ("python test_x.py && rm -rf out", "python test_x.py > out.txt", "python test_x.py $(cat x)",
                      "find . -name '*.pyc' -delete && pytest", "cat test_x.py", "python app.py"):
            r = _guard({"tool_name": "Bash", "tool_input": {"command": other}}, cwd=d)
            assert "updatedInput" not in r.stdout, ("only a test command is changed", other)


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
