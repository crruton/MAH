import sys

cfg = dict(line.strip().split("=", 1) for line in open("build.cfg", encoding="utf-8") if "=" in line)
if cfg.get("mode") not in ("debug", "release"):
    sys.exit(f"build failed: unknown mode {cfg.get('mode')!r}")
print("build ok:", cfg["mode"])
