import os
import sys

PROFILE = os.environ.get("AWS_PROFILE", "prod")


def main():
    path = os.path.join("deploy", ".aws", "credentials")
    sections = [l.strip()[1:-1] for l in open(path, encoding="utf-8") if l.startswith("[")]
    if PROFILE not in sections:
        sys.exit(f"profile {PROFILE!r} not found")
    print("profile:", PROFILE)


if __name__ == "__main__":
    main()
