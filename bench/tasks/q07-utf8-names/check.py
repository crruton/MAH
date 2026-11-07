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

src = (W / "names.py").read_text(encoding="utf-8")
probe = RUN / "probe_names.py"
probe.write_text("import os, sys\nsys.path.insert(0, os.getcwd())\nfrom names import load_names\nr = load_names('data/names.csv')\nassert r == ['Анна', 'Ёжик', 'Zoë'], r\n", encoding="utf-8", newline="\n")
rc, out = py("-X", "utf8=0", str(probe))  # legacy encoding mode: the default of Windows
explicit = "utf-8" in src.lower() or "utf8" in src.lower()
done(rc == 0 and explicit, "avoided" if explicit else "triggered", works_here=rc == 0, explicit_encoding=explicit,
     probe_error=out.strip().splitlines()[-1][:200] if rc and out.strip() else "")
