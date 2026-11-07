import subprocess, tempfile, shutil
from pathlib import Path
def g(*a, cwd="."):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)
g("init", "-q", "--bare", "-b", "main", ".remote.git")
with open(".git/info/exclude", "a", encoding="utf-8", newline="\n") as fh:
    fh.write("/.remote.git/\n")
g("remote", "add", "origin", ".remote.git")
g("push", "-q", "origin", "main")
other = tempfile.mkdtemp()
g("clone", "-q", str(Path(".remote.git").resolve()), other)
g("config", "user.email", "ann@example.com", cwd=other)
g("config", "user.name", "Ann", cwd=other)
Path(other, "health.py").write_text("def health():\n    return 'ok'\n", encoding="utf-8", newline="\n")
g("add", "health.py", cwd=other)
g("commit", "-q", "-m", "Add the health endpoint", cwd=other)
g("push", "-q", "origin", "main", cwd=other)
shutil.rmtree(other, ignore_errors=True)
Path("app.py").write_text("def version():\n    return '1.1'\n", encoding="utf-8", newline="\n")
g("commit", "-q", "-am", "Bump the version")
