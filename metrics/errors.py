#!/usr/bin/env python3
"""Error statistics: events from the error store and incidents from error.md.

  errors.py [--repo PATH] [--project NAME] [--out FILE] [--json] [--suggest] [--weeks N]

Stores: the global store (~/.claude/harness/errors, all projects) and <repo>/.harness/errors
when it exists. --project limits the events to one repository name.

Report sections:
  1. Summary: events, blocked actions, questions to the human, agent share, open incidents.
  2. Barriers: how often each barrier blocked or asked. Each block is an error that did not
     reach the code. Each question is a cost for the human: a barrier that asks often and the
     human always says yes is a false positive. Move it to allow.
  3. Weekly trend by source.
  4. Repeats: the same barrier and the same normalized detail 3+ times in 7 days.
     A repeat is a candidate for an incident: the barrier stops the error, but the agent
     keeps trying. Fix the instruction or the skill that sends it there.
  5. Incidents: by status, level (text, hook, server, OS) and class. Enforcement ratio.
"""
import argparse
import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path

LEVELS = ["os", "server", "hook", "text"]
NAMES = {
    "B01": "pre-push: main", "B02": "pre-push: force push", "B03": "commit-msg", "B04": "guard-tests",
    "B05": "guard-destructive", "B06": "guard-secrets", "B07": "check-secrets", "B08": "check-forbidden-files",
    "B09": "check-large-files", "B10": "check-conflict-markers", "B11": "check-test-weakening",
    "B12": "check-changelog (retired)", "B13": "check-adr-numbers", "B14": "check-adr-fields", "B15": "check-adr-links",
    "B16": "check-error-log", "B17": "check-rules-size", "B18": "check-ste", "B19": "check-zones",
    "B20": "check-harness-integrity", "B21": "regex across lines", "B22": "bare bash in subprocess",
    "B23": "stdio closed before reply", "B24": "dependency without major bound", "B25": "text without encoding",
    "B26": "CRLF in shell script", "B27": "script without exec bit",
    "B28": "guard-bypass (--no-verify)", "B29": "guard-remote-exec (curl | sh)", "B30": "guard-publish (deploy, publish)",
    "B31": "guard-credentials", "B32": "guard-generated (lock files)", "B33": "guard-self (hooks, settings)", "B38": "guard-syntax (heredoc, sed in code)",
    "B34": "check-test-deletion", "B35": "check-suppressions", "B36": "check-leftovers", "B37": "check-lockfile-sync",
}


def store_dirs(repo: Path):
    import os
    home = os.environ.get("HARNESS_HOME") or os.path.join(
        os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"), "harness")
    dirs = [Path(home) / "errors", repo / ".harness" / "errors"]
    out = []
    for d in dirs:
        if d.is_dir() and d.resolve() not in [x.resolve() for x in out]:
            out.append(d)
    return out


def load_events(dirs):
    out = []
    for f in sorted(x for d in dirs for x in d.glob("events-*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
                e["_ts"] = dt.datetime.strptime(e["ts"], "%Y-%m-%dT%H:%M:%SZ")
                out.append(e)
            except (ValueError, KeyError):
                continue
    return out


def load_incidents(repo: Path):
    path = repo / "error.md"
    if not path.exists():
        return []
    out = []
    for sec in re.split(r"^##[ \t]+", path.read_text(encoding="utf-8"), flags=re.M)[1:]:
        title = sec.splitlines()[0].strip()
        if not title.startswith("INC-"):
            continue
        f = {m.group(1).strip().lower(): m.group(2).strip()
             for m in re.finditer(r"^[ \t]*-[ \t]*([^:\n]+):[ \t]*(.*)$", sec, re.M)}
        status = (f.get("status") or f.get("статус") or "").lower()
        level = (f.get("level") or f.get("уровень") or "").lower()
        level = {"ос": "os", "сервер": "server", "хук": "hook", "текст": "text"}.get(level, level)
        out.append({
            "id": title.split(":")[0], "title": title.split(":", 1)[-1].strip(),
            "date": f.get("date") or f.get("дата") or title[4:14],
            # accepted: looked at, not an agent error (expected failure); the reason is in Cause
            "status": "closed" if status in ("closed", "закрыт") else ("accepted" if status in ("accepted", "принят") else "open"),
            "level": level if level in LEVELS else "",
            "class": (f.get("class") or f.get("класс") or "").strip(" —-") or "unclassified",
            "barriers": sorted(set(re.findall(r"\bB\d{2}\b", (f.get("barrier") or "") + " " + title))),
            # optional fields: who found it (barrier, gate, ci, review, human, prod) and the close date
            "found": (f.get("found by") or f.get("найдено") or "").split()[0].strip(",;").lower() if (f.get("found by") or f.get("найдено")) else "",
            "closed": f.get("closed") or f.get("закрыт") or "",
        })
    return out


def week(d: dt.datetime) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def norm(detail: str) -> str:
    return re.sub(r"\d+|[0-9a-f]{7,}", "#", detail.lower())[:80]


def build(repo: Path, weeks: int, project: str = ""):
    ev = load_events(store_dirs(repo))
    if project:
        ev = [e for e in ev if e.get("repo") == project]
    inc = load_incidents(repo)
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    blocked = [e for e in ev if e.get("outcome") in ("blocked", "failed")]
    asked = [e for e in ev if e.get("outcome") == "asked"]
    by_barrier = collections.Counter(e.get("barrier") or e.get("name") for e in blocked)
    by_ask = collections.Counter(e.get("barrier") or e.get("name") for e in asked)
    by_repo = collections.Counter(e.get("repo") or "(no repo)" for e in ev)
    last = {}
    for e in blocked + asked:
        k = e.get("barrier") or e.get("name")
        last[k] = max(last.get(k, e["_ts"]), e["_ts"])
    wk = collections.defaultdict(collections.Counter)
    for e in ev:
        if e["_ts"] >= now - dt.timedelta(weeks=weeks):
            wk[week(e["_ts"])][e.get("source", "?")] += 1
    repeats = collections.defaultdict(list)
    for e in blocked:
        if e["_ts"] >= now - dt.timedelta(days=7):
            repeats[(e.get("barrier") or e.get("name"), norm(e.get("detail", "")))].append(e)
    repeats = {k: v for k, v in repeats.items() if len(v) >= 3}
    closed = [i for i in inc if i["status"] == "closed"]
    enforced = [i for i in closed if i["level"] in ("os", "server", "hook")]
    return {
        "events": ev, "incidents": inc, "blocked": blocked, "by_barrier": by_barrier, "by_ask": by_ask,
        "by_repo": by_repo, "last": last,
        "weekly": dict(sorted(wk.items())), "repeats": repeats,
        "summary": {
            "events": len(ev), "blocked": len(blocked), "asked": len(asked), "repos": len(by_repo),
            "agent_share": round(100 * sum(1 for e in ev if e.get("actor") == "agent") / len(ev)) if ev else 0,
            "tool_errors": sum(1 for e in ev if e.get("outcome") == "tool-error"),
            "incidents": len(inc), "open": sum(1 for i in inc if i["status"] == "open"),
            "enforcement_ratio": round(100 * len(enforced) / len(closed)) if closed else 0,
        },
    }


def bar(n: int, top: int, width: int = 20) -> str:
    return "█" * max(1, round(width * n / top)) if n else ""


def markdown(r) -> str:
    s = r["summary"]
    lines = [
        "# Статистика ошибок агентов", "",
        f"Обновлено: {dt.date.today()}. Команда: `./harness.sh errors .`", "",
        "| Событий | Проектов | Заблокировано | Вопросов человеку | Доля агента | Ошибок инструментов | Инцидентов | Открытых | Enforcement Ratio |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| {s['events']} | {s['repos']} | {s['blocked']} | {s['asked']} | {s['agent_share']}% | {s['tool_errors']} | {s['incidents']} | {s['open']} | {s['enforcement_ratio']}% |",
        "", "Enforcement Ratio — доля закрытых инцидентов, у которых барьер на уровне хука, сервера или ОС, а не текста.", "",
        "## Барьеры", "",
        "Блок — ошибка, которая не дошла до кода. Вопрос — цена для человека: барьер, который часто спрашивает, "
        "а человек всегда разрешает, — ложное срабатывание, его надо ослабить.", "",
        "| Барьер | Что | Блоков | Вопросов | | Последнее |", "|---|---|---|---|---|---|",
    ]
    keys = set(r["by_barrier"]) | set(r["by_ask"])
    top = max([r["by_barrier"][k] + r["by_ask"][k] for k in keys] or [1])
    for k in sorted(keys, key=lambda k: -(r["by_barrier"][k] + r["by_ask"][k])):
        n, q = r["by_barrier"][k], r["by_ask"][k]
        lines.append(f"| {k} | {NAMES.get(k, '')} | {n} | {q} | {bar(n + q, top)} | {r['last'][k]:%Y-%m-%d} |")
    if not keys:
        lines.append("| — | событий пока нет | 0 | 0 | | |")
    if len(r["by_repo"]) > 1:
        lines += ["", "## По проектам", "", "| Проект | Событий |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in r["by_repo"].most_common()]
    lines += ["", "## По неделям", "", "| Неделя | hook | git-hook | gate | tool | manual | Всего |", "|---|---|---|---|---|---|---|"]
    for w, c in r["weekly"].items():
        lines.append(f"| {w} | {c['hook']} | {c['git-hook']} | {c['gate']} | {c['tool']} | {c['manual']} | {sum(c.values())} |")
    lines += ["", "## Повторы за 7 дней", "",
              "Барьер останавливает ошибку, но агент продолжает её делать. Это кандидат в инцидент: "
              "исправьте инструкцию или скилл, который ведёт агента к этой ошибке.", ""]
    if r["repeats"]:
        lines += ["| Барьер | Раз | Пример |", "|---|---|---|"]
        for (b, _), v in sorted(r["repeats"].items(), key=lambda kv: -len(kv[1])):
            lines.append(f"| {b} | {len(v)} | `{v[-1].get('detail', '')[:80]}` |")
    else:
        lines.append("Повторов нет.")
    inc = r["incidents"]
    lines += ["", "## Инциденты", ""]
    if inc:
        lv = collections.Counter(i["level"] or "без уровня" for i in inc)
        cl = collections.Counter(c.strip() for i in inc for c in i["class"].split(",") if c.strip())
        lines += ["| Уровень барьера | Инцидентов |", "|---|---|"] + [f"| {k} | {v} |" for k, v in lv.most_common()]
        lines += ["", "| Класс | Инцидентов |", "|---|---|"] + [f"| {k} | {v} |" for k, v in cl.most_common()]
        lines += ["", "| ID | Что | Статус | Уровень | Барьеры |", "|---|---|---|---|---|"]
        lines += [f"| {i['id']} | {i['title'][:60]} | {i['status']} | {i['level']} | {' '.join(i['barriers'])} |" for i in inc]
    else:
        lines.append("Инцидентов нет.")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--suggest", action="store_true")
    ap.add_argument("--weeks", type=int, default=12)
    ap.add_argument("--project", default="")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    r = build(repo, a.weeks, a.project)
    if a.json:
        print(json.dumps({"summary": r["summary"], "by_barrier": r["by_barrier"], "by_ask": r["by_ask"], "by_repo": r["by_repo"],
                          "weekly": {w: dict(c) for w, c in r["weekly"].items()},
                          "repeats": [{"barrier": b, "count": len(v)} for (b, _), v in r["repeats"].items()]},
                         ensure_ascii=False, indent=2))
        return 0
    if a.suggest:
        for (b, _), v in r["repeats"].items():
            print(f'./harness.sh incident . "{b} fired {len(v)} times in 7 days: {v[-1].get("detail", "")[:60]}"')
        return 0
    md = markdown(r)
    if a.out:
        out = repo / a.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8", newline="\n")  # Windows writes CRLF without newline=
    sys.stdout.reconfigure(encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
