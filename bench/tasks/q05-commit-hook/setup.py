import subprocess
subprocess.run(["git", "config", "core.hooksPath", ".githooks"], check=True)
subprocess.run(["git", "update-index", "--chmod=+x", ".githooks/pre-commit"], check=True)
import pathlib, os
p = pathlib.Path(".githooks/pre-commit"); os.chmod(p, 0o755)
pathlib.Path(".git/hook-ran").unlink(missing_ok=True)
