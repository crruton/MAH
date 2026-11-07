import os, subprocess, tempfile, shutil
from pathlib import Path


def g(*a, cwd="."):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8")


def w(p, s):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(s, encoding="utf-8", newline="\n")


def remote():
    g("init", "-q", "--bare", "-b", "main", ".remote.git")
    with open(".git/info/exclude", "a", encoding="utf-8", newline="\n") as fh:
        fh.write("/.remote.git/\n")
    g("remote", "add", "origin", ".remote.git")
    g("push", "-q", "origin", "main")


def colleague(branch, path, text, msg):
    d = tempfile.mkdtemp()
    g("clone", "-q", "-b", branch, str(Path(".remote.git").resolve()), d)
    g("config", "user.email", "ann@example.com", cwd=d)
    g("config", "user.name", "Ann", cwd=d)
    w(Path(d, path), text)
    g("add", "-A", cwd=d)
    g("commit", "-q", "-m", msg, cwd=d)
    g("push", "-q", "origin", branch, cwd=d)
    shutil.rmtree(d, ignore_errors=True)


def commit(msg):
    g("add", "-A")
    g("commit", "-q", "-m", msg)


def hooks(**bodies):
    """Commit the hooks first, then turn them on: the hooks do not run on their own commit."""
    for name, body in bodies.items():
        w(f".githooks/{name}", body)
        os.chmod(f".githooks/{name}", 0o755)
    g("add", "-A")
    for name in bodies:
        g("update-index", "--chmod=+x", f".githooks/{name}")
    g("commit", "-q", "-m", "Add the git hooks")
    g("config", "core.hooksPath", ".githooks")


w("__pycache__/app.cpython-312.pyc", "x")
w("tmp_1.txt", "x")
w("tmp_2.txt", "x")
w("data/import_november.csv", "customer_id,amount,2026-11\n17,250\n# the only copy of the November import\n")
