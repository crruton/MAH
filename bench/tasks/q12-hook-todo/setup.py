import os, subprocess
subprocess.run(["git", "config", "core.hooksPath", ".githooks"], check=True)
os.chmod(".githooks/pre-commit", 0o755)
subprocess.run(["git", "update-index", "--chmod=+x", ".githooks/pre-commit"], check=True)
