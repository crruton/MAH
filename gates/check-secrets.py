#!/usr/bin/env python3
"""B07. Fail when added lines contain a secret.

Patterns: private keys, cloud and SaaS tokens, JWT, and assignments of long literals
to names like password, secret, token, api_key. Allow one line with the marker
'harness:allow-secret' (use it only for test fixtures).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import added_and_removed, changed_files, report  # noqa: E402

PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(ghp|gho|ghs|ghu)_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{60,}")),
    # 20 characters in old tokens; new tokens are longer and have dots (INC-2026-11-06-11)
    ("GitLab token", re.compile(r"\bgl(pat|dt|rt|ptt|cbt|soat)-[A-Za-z0-9_\-.]{20,}")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_\-]{32,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("hardcoded credential", re.compile(
        r"(?i)\b(password|passwd|secret|token|api[_-]?key|access[_-]?key)\b\s*[:=]\s*['\"][^'\"\s$]{12,}['\"]")),
]
SKIP_SUFFIX = (".lock", ".svg", ".min.js")


def main() -> int:
    problems = []
    for f in changed_files():
        if f.endswith(SKIP_SUFFIX):
            continue
        added, _ = added_and_removed(f)
        for line in added:
            if "harness:allow-secret" in line:
                continue
            for name, rx in PATTERNS:
                if rx.search(line):
                    problems.append(f"{f}: {name} in an added line. Move it to an environment variable or a secret store.")
                    break
    return report("check-secrets", problems)


if __name__ == "__main__":
    sys.exit(main())
