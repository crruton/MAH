#!/usr/bin/env python3
"""Join the results of several bench runs into one folder for one report (result.json files only).

  python bench/merge.py --out bench/results/ALL RUN_DIR [RUN_DIR ...]

The same (arm, task, repeat) in two runs: the later folder on the command line wins.
All runs must use the same model; the merged config.json lists the sources.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("runs", nargs="+")
    a = ap.parse_args()
    out = Path(a.out)
    cfgs, n = [], 0
    for src in map(Path, a.runs):
        cfg = json.loads((src / "config.json").read_text(encoding="utf-8"))
        cfgs.append({"source": src.as_posix(), **cfg})
        for p in src.glob("runs/*/*/*/result.json"):
            dest = out / p.relative_to(src)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(p, dest)
            n += 1
    models = {c["model"] for c in cfgs}
    if len(models) > 1:
        raise SystemExit(f"different models: {models}")
    first = cfgs[0]
    merged = {**first, "tasks": sorted({t for c in cfgs for t in c["tasks"]}), "arms": sorted({Path(x).name for c in cfgs for x in c["arms"]}),
              "reps": "/".join(str(c["reps"]) for c in cfgs), "sources": cfgs}
    (out / "config.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    with (out / "results.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for p in sorted(out.glob("runs/*/*/*/result.json")):
            fh.write(p.read_text(encoding="utf-8").replace("\n", " ") + "\n")
    print(f"{out}: {len(list(out.glob('runs/*/*/*/result.json')))} runs from {len(cfgs)} sources ({n} copied)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
