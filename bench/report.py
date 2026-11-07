#!/usr/bin/env python3
"""Bench report: pass rate, traps, cost in rubles, time; arm against base with 95% intervals.

  python bench/run.py report --out <results dir> [--base none] [--arm self]

Statistics (stdlib only, fixed seed, so the same results give the same report):
  pass rate      Wilson 95% interval
  differences    paired by (task, repeat): arm minus base; bootstrap 95% interval, 4000 resamples
  verdict        "лучше" / "хуже" only when the interval does not cross 0, else "не доказано"
"""
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "metrics"))
import dashboard  # noqa: E402 -- reason: the import needs sys.path set above

fmt = dashboard.fmt


def wilson(k: int, n: int):
    if not n:
        return (0.0, 0.0, 0.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def boot(diffs, seed=7, n=4000):
    if not diffs:
        return None, None, None
    rnd = random.Random(seed)
    means = sorted(statistics.fmean(rnd.choices(diffs, k=len(diffs))) for _ in range(n))
    return statistics.fmean(diffs), means[int(0.025 * n)], means[int(0.975 * n) - 1]


def verdict(lo, hi, lower_better):
    if lo is None:
        return "нет данных"
    if lo > 0:
        return "хуже" if lower_better else "лучше"
    if hi < 0:
        return "лучше" if lower_better else "хуже"
    return "не доказано"


def load(out: Path):
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(out.glob("runs/*/*/*/result.json"))]
    cfg = json.loads((out / "config.json").read_text(encoding="utf-8")) if (out / "config.json").exists() else {}
    return rows, cfg


def arm_stats(rows, rate):
    n = len(rows)
    k = sum(r["pass"] for r in rows)
    traps = [r for r in rows if r["trap"] in ("avoided", "triggered")]
    p, lo, hi = wilson(k, n)
    med = lambda key: statistics.median(r[key] for r in rows) if rows else None  # noqa: E731 -- reason: a one-line helper inside the function
    return {"n": n, "pass": p, "lo": lo, "hi": hi, "trap_hit": sum(r["trap"] == "triggered" for r in traps), "traps": len(traps),
            "rub": (med("cost_usd") or 0) * rate, "wall": med("wall_s"), "turns": med("turns"),
            "tokens": med("tokens_in") + med("tokens_out") if rows else None, "tool_errors": statistics.fmean(r["tool_errors"] for r in rows) if rows else None,
            "blocked": sum(r["blocked"] + r["barrier_events"] for r in rows)}


def paired(base, arm, key, scale=1.0):
    b = {(r["task"], r["rep"]): r for r in base}
    return [(a[key] - b[(a["task"], a["rep"])][key]) * scale for a in arm if (a["task"], a["rep"]) in b]


def main(out: Path, base_name: str, arm_name: str, fail_if_worse: bool = False) -> int:
    rows, cfg = load(out)
    rate = cfg.get("usd_rub") or dashboard.usd_rub()[0] or 0
    base = [r for r in rows if r["arm"] == base_name]
    arm = [r for r in rows if r["arm"] == arm_name]
    if not base or not arm:
        print(f"нет прогонов для {base_name!r} или {arm_name!r} в {out}")
        return 1
    L = [f"# Бенч харнеса: {arm_name} против {base_name}", "",
         f"Модель исполнителя: `{cfg.get('model', '?')}`, повторов: {cfg.get('reps', '?')}, задач: {len(cfg.get('tasks', []))}, "
         f"коммит кита: `{cfg.get('kit_commit', '?')}`, {cfg.get('claude', '')}.",
         f"Изоляция: {'полная (ANTHROPIC_API_KEY, пустой CLAUDE_CONFIG_DIR)' if cfg.get('isolated') else 'по логину: пользовательский CLAUDE.md одинаково загружен во всех вариантах'}.",
         f"Рубли: {cfg.get('rate_source', '')}, {fmt(round(rate, 2))} ₽ за $.", ""]
    for split in ("all", "train", "heldout"):
        b = [r for r in base if split == "all" or r["split"] == split]
        a = [r for r in arm if split == "all" or r["split"] == split]
        if not b or not a:
            continue
        sb, sa = arm_stats(b, rate), arm_stats(a, rate)
        title = {"all": "Все задачи", "train": "Обучающие задачи (на них настраивали харнес)", "heldout": "Отложенные задачи (харнес их не видел)"}[split]
        L += [f"## {title}", "",
              "| | " + base_name + " | " + arm_name + " |", "|---|---|---|",
              f"| Решено | {sb['pass']:.0%} [{sb['lo']:.0%}–{sb['hi']:.0%}] из {sb['n']} | {sa['pass']:.0%} [{sa['lo']:.0%}–{sa['hi']:.0%}] из {sa['n']} |",
              f"| Попал в ловушку | {sb['trap_hit']} из {sb['traps']} | {sa['trap_hit']} из {sa['traps']} |",
              f"| ₽ за прогон, медиана | {fmt(round(sb['rub'], 1))} | {fmt(round(sa['rub'], 1))} |",
              f"| Время, с, медиана | {fmt(sb['wall'])} | {fmt(sa['wall'])} |",
              f"| Ходов, медиана | {fmt(sb['turns'])} | {fmt(sa['turns'])} |",
              f"| Токенов (без чтения кэша), медиана | {fmt(sb['tokens'])} | {fmt(sa['tokens'])} |",
              f"| Упавших вызовов на прогон | {fmt(round(sb['tool_errors'], 2))} | {fmt(round(sa['tool_errors'], 2))} |",
              f"| Срабатываний барьеров | {sb['blocked']} | {sa['blocked']} |", ""]
        L += ["| Разница (" + arm_name + " − " + base_name + ") | среднее | 95% интервал | вывод |", "|---|---|---|---|"]
        for label, key, scale, lower in (("Решено, п.п.", "pass", 100, False), ("₽ за прогон", "cost_usd", rate, True),
                                          ("Время, с", "wall_s", 1, True), ("Ходов", "turns", 1, True),
                                          ("Упавших вызовов", "tool_errors", 1, True)):
            m, lo, hi = boot([float(x) for x in paired(b, a, key, scale)])
            L.append(f"| {label} | {fmt(round(m, 1)) if m is not None else '—'} | "
                     f"{(fmt(round(lo, 1)) + ' … ' + fmt(round(hi, 1))) if lo is not None else '—'} | {verdict(lo, hi, lower)} |")
        L.append("")
    L += ["## По задачам", "", "| Задача | Выборка | " + base_name + ": решено | " + arm_name + ": решено | ловушка " + base_name + " → " + arm_name + " |", "|---|---|---|---|---|"]
    for t in sorted({r["task"] for r in rows}):
        b = [r for r in base if r["task"] == t]
        a = [r for r in arm if r["task"] == t]
        tr = lambda rs: sum(r["trap"] == "triggered" for r in rs)  # noqa: E731 -- reason: a one-line helper inside the function
        L.append(f"| {t} | {(b or a)[0]['split']} | {sum(r['pass'] for r in b)}/{len(b)} | {sum(r['pass'] for r in a)}/{len(a)} | {tr(b)} → {tr(a)} |")
    L += ["", "Интервал «не доказано» — данных не хватает, чтобы отличить эффект от разброса. Больше повторов: `--reps 5`.", ""]
    text = "\n".join(L)
    (out / f"report-{arm_name}-vs-{base_name}.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    if fail_if_worse:  # the CI gate of a harness change: not proven worse, no new trap
        _, lo, hi = boot([float(x) for x in paired(base, arm, "pass", 100)])
        traps = sum(r["trap"] == "triggered" for r in arm) - sum(r["trap"] == "triggered" for r in base)
        if (hi is not None and hi < 0) or traps > 0:
            print(f"\nFAIL: {arm_name} is worse than {base_name}: solved interval {lo} … {hi}, traps {traps:+d}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), *(sys.argv[2:4] or ["none", "self"])))
