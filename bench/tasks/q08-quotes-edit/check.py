import hashlib, json, subprocess, sys
from pathlib import Path

W = Path(sys.argv[1])          # the workspace after the agent
RUN = Path(sys.argv[2])        # the run folder: stream.jsonl
STREAM = (RUN / "stream.jsonl").read_text(encoding="utf-8", errors="replace") if (RUN / "stream.jsonl").exists() else ""


def sh(*cmd, cwd=None):
    r = subprocess.run(list(cmd), cwd=cwd or W, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr)


def py(*args):
    return sh(sys.executable, *args)


def sha(rel):
    return hashlib.sha256((W / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def done(passed, trap, **details):
    print(json.dumps({"pass": bool(passed), "trap": trap, "details": details}, ensure_ascii=False))

import importlib.util
want = {"hello": "Hello", "path": "C:" + chr(92) + "temp" + chr(92) + "new", "quote": "it" + chr(39) + "s " + chr(34) + "fine" + chr(34)}
try:
    spec = importlib.util.spec_from_file_location("messages", W / "messages.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    got = {k: mod.MESSAGES.get(k) for k in want}
except Exception as e:  # a broken file is a failed task
    got = {"error": repr(e)}
broken_tries = STREAM.count("unexpected EOF") + STREAM.count("SyntaxError")
done(got == want, "avoided" if broken_tries == 0 else "triggered", correct=got == want, got=got, broken_attempts=broken_tries)
