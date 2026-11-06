#!/usr/bin/env python3
"""Learning dashboard: does the agent with this harness make fewer errors, faster and cheaper?

  dashboard.py [--repo PATH ...] [--weeks N] [--out FILE] [--json]

Sources (all local, read only):
  sessions   Claude Code transcripts in CLAUDE_CONFIG_DIR/projects/**.jsonl: each tool call,
             each failed call, tokens, cost (USD in the file, rubles in the report), human prompts. This is the denominator:
             the hooks do not count successful calls, so they cost nothing.
  events     the error store (blocks and questions of the barriers), see errors.py.
  incidents  error.md of each repository: from --repo and from the session folders.

Output: one HTML file with no external files (default: <harness home>/dashboard.html).

The loop that the dashboard checks:
  1. capture   a barrier, a gate or a failed tool call writes an event
  2. detect    repeats and rising error signatures become candidates
  3. incident  an entry in error.md with a class and a barrier ID
  4. barrier   the deepest level that can stop it; a repro attack goes into the demo
  5. teach     the block message tells the agent what to do; a rule line for the next sessions
  6. verify    attempts of the barrier after the incident: 0 = learned, >0 = the barrier holds,
               a new incident of the same class = leaked
"""
import argparse
import collections
import datetime as dt
import html
import json
import os
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent / "gates"):
    sys.path.insert(0, str(p))
import errors as E  # noqa: E402
try:
    from collect import mask  # noqa: E402
except ImportError:
    def mask(t): return t

H = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
HH = Path(os.environ.get("HARNESS_HOME") or H / "harness")
REJECT = re.compile(r"doesn't want to proceed|user rejected|Permission to use .* has been denied|was blocked by|denied by", re.I)
BLOCKED = re.compile(r"Blocked by [\w-]+|hook (error|blocked)", re.I)


def usd_rub():
    """USD -> RUB rate and its source. Order: HARNESS_USD_RUB, today's cache, the Bank of Russia
    daily rates (one GET, nothing is sent), an old cache. HARNESS_OFFLINE=1 skips the network."""
    if os.environ.get("HARNESS_USD_RUB"):
        try:
            return float(os.environ["HARNESS_USD_RUB"].replace(",", ".")), "HARNESS_USD_RUB"
        except ValueError:
            pass
    cache = HH / "usd_rub.json"
    old = {}
    try:
        old = json.loads(cache.read_text(encoding="utf-8"))
        if old.get("date") == dt.date.today().isoformat():
            return float(old["rate"]), f"курс ЦБ РФ на {old['date']}"
    except (OSError, ValueError, KeyError):
        pass
    if os.environ.get("HARNESS_OFFLINE") != "1":
        try:
            import urllib.request
            with urllib.request.urlopen("https://www.cbr.ru/scripts/XML_daily.asp", timeout=4) as r:
                xml = r.read().decode("windows-1251", errors="replace")
            m = re.search(r"<CharCode>USD</CharCode>\s*<Nominal>(\d+)</Nominal>.*?<Value>([\d,]+)</Value>", xml, re.S)
            if m:
                rate = float(m.group(2).replace(",", ".")) / int(m.group(1))
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps({"date": dt.date.today().isoformat(), "rate": rate}), encoding="utf-8", newline="\n")
                return rate, f"курс ЦБ РФ на {dt.date.today().isoformat()}"
        except Exception:  # no network: use the old cache
            pass
    if old.get("rate"):
        return float(old["rate"]), f"курс ЦБ РФ на {old.get('date')}, сохранённый"
    return None, "курса нет: задайте HARNESS_USD_RUB"


def ts(s):
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


NOISE = re.compile(r"^\s*(Exit code \d+|</?\w+>|node:internal/\S+|\^+|at\s.+|throw\s.*|[✓✔]\s.*|OK\b.*|System\.Management\.Automation\.\w+)\s*$")
ERRWORD = re.compile(r"(?i)\b(error|errno|exception|fail(ed|ure)?|fatal|denied|not found|no such|cannot|can't|invalid|unexpected|refused|timed? ?out)\b|ошибк|не найден")


def signature(tool, msg):
    """The line that names the error, not a stack header or a success line before it (INC-2026-11-06-07, -10)."""
    lines = [l for l in msg.replace("\r", "").splitlines() if l.strip() and not NOISE.match(l)]
    first = next((l for l in lines if ERRWORD.search(l)), lines[0] if lines else msg.strip())[:200]
    first = re.sub(r"([A-Za-z]:)?[\\/][\w.\\/ -]+", "<path>", first)
    first = re.sub(r"\b[0-9a-f]{7,}\b|\d+", "#", first)
    return f"{tool}: {mask(first)[:90]}"


def load_sessions(root: Path):
    """One record per session id. Subagent files add to their parent session."""
    S = {}
    for f in root.rglob("*.jsonl"):
        msg_usage, tool_names, file_sids, last_t = {}, {}, collections.Counter(), None
        try:
            fh = f.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                sid = e.get("sessionId")
                if not sid:
                    continue
                file_sids[sid] += 1
                s = S.setdefault(sid, {"id": sid, "start": None, "end": None, "repo": "", "cwd": "", "calls": 0, "errors": 0,
                                       "rejected": 0, "blocked": 0, "prompts": 0, "tokens": 0, "cost": 0.0, "lines": 0, "active": 0.0, "sigs": []})
                t = ts(e.get("timestamp", ""))
                if t:
                    s["start"] = min(s["start"] or t, t)
                    s["end"] = max(s["end"] or t, t)
                    gap = (t - last_t).total_seconds() if last_t else 0
                    if 0 < gap < 300:  # active time: a pause of 5+ minutes is the human away, not the agent working
                        s["active"] += gap
                    last_t = t
                if e.get("cwd") and not s["cwd"]:
                    s["cwd"] = e["cwd"]
                    s["repo"] = Path(e["cwd"]).name
                typ, m = e.get("type"), e.get("message") or {}
                if typ == "cost-state":
                    s["cost"] = max(s["cost"], float(e.get("totalCostUSD") or 0))
                    s["lines"] = max(s["lines"], int(e.get("totalLinesAdded") or 0) + int(e.get("totalLinesRemoved") or 0))
                elif typ == "assistant":
                    u = m.get("usage") or {}
                    if m.get("id") and u:
                        # cache reads are cheap and repeat the same context; count the new work only
                        msg_usage[m["id"]] = sum(int(u.get(k) or 0) for k in
                                                 ("input_tokens", "output_tokens", "cache_creation_input_tokens"))
                    for b in m.get("content") or []:
                        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in tool_names:
                            tool_names[b["id"]] = b.get("name", "tool")
                            s["calls"] += 1
                elif typ == "user":
                    c = m.get("content")
                    results = [b for b in c if isinstance(b, dict) and b.get("type") == "tool_result"] if isinstance(c, list) else []
                    if not results and not e.get("isMeta") and not e.get("isSidechain") and text_of(c).strip():
                        s["prompts"] += 1
                    for b in results:
                        if not b.get("is_error"):
                            continue
                        msg = text_of(b.get("content"))
                        if REJECT.search(msg):
                            s["rejected"] += 1
                        elif BLOCKED.search(msg):
                            s["blocked"] += 1
                        else:
                            s["errors"] += 1
                            s["sigs"].append((t, signature(tool_names.get(b.get("tool_use_id"), "tool"), msg)))
        # one file is one session; a subagent file carries the id of its parent session
        if msg_usage and file_sids:
            S[file_sids.most_common(1)[0][0]]["tokens"] += sum(msg_usage.values())
    return [s for s in S.values() if s["start"] and (s["calls"] or s["prompts"])]


def week(d):
    return E.week(d)


def weeks_back(now, n):
    out, d = [], now - dt.timedelta(weeks=n - 1)
    while d <= now + dt.timedelta(days=1):
        w = week(d)
        if w not in out:
            out.append(w)
        d += dt.timedelta(days=7)
    if week(now) not in out:
        out.append(week(now))
    return out[-n:]


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def build(repos, n_weeks):
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    sessions = load_sessions(H / "projects")
    rate, rate_src = usd_rub()
    for s in sessions:
        s["week"] = week(s["start"])
        s["rub"] = s["cost"] * rate if rate else 0.0  # transcripts give USD; the report is in rubles
    events = E.load_events(E.store_dirs(Path.cwd()))
    for r in repos:
        events += [e for e in E.load_events(E.store_dirs(r)) if e not in events]
    # repositories: the ones given and the ones the sessions worked in
    roots = {Path(r).resolve() for r in repos}
    roots |= {Path(s["cwd"]) for s in sessions if s["cwd"] and (Path(s["cwd"]) / "error.md").exists()}
    incidents = []
    for r in sorted(roots):
        for i in E.load_incidents(r):
            i["repo"] = r.name
            i["_date"] = ts((i.get("closed") or i["date"])[:10] + "T00:00:00Z") or now
            incidents.append(i)
    W = weeks_back(now, n_weeks)

    # weekly series
    rows = []
    for w in W:
        ss = [s for s in sessions if s["week"] == w]
        ev = [e for e in events if week(e["_ts"]) == w]
        calls = sum(s["calls"] for s in ss)
        hard = [e for e in ev if e.get("outcome") in ("blocked", "failed")]
        asked = [e for e in ev if e.get("outcome") == "asked"]
        by_agent = [e for e in hard + asked if e.get("source") == "hook"]  # runtime barriers see each agent action
        rows.append({
            "week": w, "sessions": len(ss), "calls": calls,
            "tool_error_rate": pct(sum(s["errors"] for s in ss), calls),
            "attempts_rate": pct(len(by_agent), calls),
            "human_per_session": round((len(asked) + sum(s["rejected"] for s in ss)) / len(ss), 2) if ss else None,
            "tokens_per_session": round(statistics.median(s["tokens"] for s in ss) / 1000) if ss else None,
            "cost_per_session": round(statistics.median(s["rub"] for s in ss if s["rub"])) if any(s["rub"] for s in ss) else None,
            "cost_week": round(sum(s["rub"] for s in ss)) if any(s["rub"] for s in ss) else None,
            "minutes_per_session": round(statistics.median(s["active"] / 60 for s in ss)) if ss else None,
            "blocked": len(hard), "asked": len(asked),
            "incidents": sum(1 for i in incidents if week(i["_date"]) == w),
        })

    # learning per incident
    by_barrier = collections.defaultdict(list)
    for e in events:
        if e.get("outcome") in ("blocked", "failed", "asked"):
            by_barrier[e.get("barrier") or e.get("name")].append(e["_ts"])
    loop = []
    for i in sorted(incidents, key=lambda x: x["_date"]):
        ref = i["_date"]
        hits = [t for b in i["barriers"] for t in by_barrier.get(b, [])]
        # the date has no time: the events of that day are the catch that opened the incident, not repeats
        start = ref + dt.timedelta(days=1)
        before = sum(1 for t in hits if ref - dt.timedelta(days=28) <= t < start)
        after = sum(1 for t in hits if start <= t < start + dt.timedelta(days=28))
        # a leak: a later incident went through the same barrier, so the barrier did not hold
        same_class_later = [j["id"] for j in incidents if j is not i and j["_date"] >= ref and j["id"] > i["id"]
                            and set(j["barriers"]) & set(i["barriers"])]
        days = (now - start).days
        if i["status"] == "accepted":
            state, tone = "принято: не ошибка агента", "neutral"
        elif i["status"] == "open":
            state, tone = "открыт: нет барьера", "critical"
        elif not i["barriers"] and i["level"] == "text":
            state, tone = "только текст: машина не проверяет", "warning"
        elif same_class_later:
            state, tone = f"утечка: тот же барьер снова ({', '.join(same_class_later[:2])})", "serious"
        elif after:
            state, tone = f"барьер держит, агент пытается ({after}×): поправить инструкцию", "warning"
        elif days < 7:
            state, tone = "наблюдаем (< 7 дней)", "neutral"
        else:
            state, tone = "агент не пытается", "good"
        loop.append({**{k: i[k] for k in ("id", "title", "repo", "level", "class", "barriers")},
                     "date": ref.strftime("%Y-%m-%d"), "before": before, "after": after, "state": state, "tone": tone})

    # barriers that stopped errors before any incident: errors we did not have to live through
    linked = {b for i in incidents for b in i["barriers"]}
    proactive = collections.Counter(b for b, v in by_barrier.items() for _ in v if b and b not in linked)

    # new variants: a barrier stops a command it never saw before (generalisation, not a replay)
    seen, variants = set(), collections.Counter()
    for e in sorted(events, key=lambda x: x["_ts"]):
        if e.get("outcome") not in ("blocked", "failed", "asked"):
            continue
        k = (e.get("barrier") or e.get("name"), E.norm(e.get("detail", "")))
        if k not in seen:
            seen.add(k)
            variants[week(e["_ts"])] += 1
    for r in rows:
        r["new_variants"] = variants.get(r["week"], 0)

    # candidates: tool error signatures that repeat and no barrier covers yet
    recent = now - dt.timedelta(days=14)
    sig = collections.defaultdict(lambda: {"n": 0, "sessions": set(), "last7": 0, "prev7": 0, "repos": set()})
    for s in sessions:
        for t, g in s["sigs"]:
            if t and t >= recent:
                x = sig[g]
                x["n"] += 1
                x["sessions"].add(s["id"])
                x["repos"].add(s["repo"])
                x["last7" if t >= now - dt.timedelta(days=7) else "prev7"] += 1
    candidates = sorted(({"sig": g, "n": v["n"], "sessions": len(v["sessions"]), "last7": v["last7"], "prev7": v["prev7"],
                          "repos": ", ".join(sorted(v["repos"]))[:40]}
                         for g, v in sig.items() if v["n"] >= 3 and len(v["sessions"]) >= 2), key=lambda c: -c["n"])[:12]

    # new error classes per week: are new kinds of errors getting rare?
    first_class = {}
    for i in sorted(incidents, key=lambda x: x["_date"]):
        for c in (c.strip() for c in i["class"].split(",")):
            if c and c != "unclassified":
                first_class.setdefault(c, week(i["_date"]))
    for r in rows:
        r["new_classes"] = sum(1 for w in first_class.values() if w == r["week"])

    closed = [i for i in incidents if i["status"] == "closed"]
    found = collections.Counter((i.get("found") or "").lower() for i in incidents)
    machine = sum(v for k, v in found.items() if k in ("barrier", "gate", "hook", "ci", "test", "dashboard"))
    return {
        "now": now, "weeks": rows, "loop": loop, "proactive": proactive.most_common(), "candidates": candidates,
        "sessions": sessions, "events": events, "incidents": incidents,
        "totals": {
            "sessions": len(sessions), "calls": sum(s["calls"] for s in sessions), "events": len(events),
            "rub": round(sum(s["rub"] for s in sessions)), "rate": rate, "rate_src": rate_src,
            "incidents": len(incidents), "open": sum(1 for i in incidents if i["status"] == "open"), "repos": len({s["repo"] for s in sessions}),
            "enforcement": pct(sum(1 for i in closed if i["level"] in ("os", "server", "hook")), len(closed)),
            "found_by_machine": pct(machine, sum(found.values()) if any(found) else 0) if any(k for k in found) else None,
            "learned": sum(1 for l in loop if l["tone"] == "good"), "holding": sum(1 for l in loop if l["tone"] == "warning"),
            "leaked": sum(1 for l in loop if l["tone"] == "serious"),
        },
    }


# ---------- HTML

def window_delta(rows, key, n=4):
    vals = [r[key] for r in rows if r[key] is not None]
    if len(vals) < 2:
        return (vals[-1] if vals else None), None, None
    cur = vals[-n:] if len(vals) >= 2 * n else vals[len(vals) // 2:]
    prev = vals[-2 * n:-n] if len(vals) >= 2 * n else vals[:len(vals) // 2]
    c, p = statistics.mean(cur), statistics.mean(prev)
    return round(c, 2), round(p, 2), (round(100 * (c - p) / p) if p else None)


TILES = [  # key, title, unit, lower is better, what it answers
    ("tool_error_rate", "Ошибки инструментов", "на 100 вызовов", True, "качество: агент реже ошибается"),
    ("attempts_rate", "Попытки запрещённого", "на 100 вызовов", True, "агент перестаёт пытаться"),
    ("human_per_session", "Вопросы и отказы человека", "на сессию", True, "нагрузка на человека"),
    ("tokens_per_session", "Токены на сессию", "тыс., медиана", True, "дешевле"),
    ("cost_per_session", "Стоимость сессии", "₽, медиана", True, "дешевле"),
    ("minutes_per_session", "Длина сессии", "мин, медиана", True, "быстрее (смотреть вместе с объёмом)"),
]
CHARTS = [
    ("tool_error_rate", "Ошибки инструментов на 100 вызовов", "Падает: агент реже ошибается в незнакомых местах."),
    ("attempts_rate", "Срабатывания барьеров на 100 вызовов", "Падает: агент знает правило и не пытается."),
    ("tokens_per_session", "Токены на сессию, тыс. (медиана)", "Падает: меньше переделок и лишнего контекста."),
    ("new_variants", "Новые варианты, пойманные барьерами", "Барьер остановил команду, которую ещё не видел: обобщение, а не повтор."),
]


def esc(x):
    return html.escape(str(x))


def fmt(v):
    if v is None:
        return "—"
    # Russian number format: a space between thousands, a comma before decimals
    if isinstance(v, float):
        return f"{v:,.2f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",")
    return f"{v:,}".replace(",", " ")


def tile(rows, key, title, unit, lower, note):
    cur, prev, d = window_delta(rows, key)
    if d is None:
        badge = '<span class="delta neutral">мало данных</span>'
    else:
        good = (d < 0) == lower if d != 0 else None
        cls = "neutral" if good is None else ("good" if good else "critical")
        arrow = "▼" if d < 0 else ("▲" if d > 0 else "■")
        word = "" if good is None else (" лучше" if good else " хуже")
        badge = f'<span class="delta {cls}">{arrow} {abs(d)}%{word}</span>'
    return (f'<div class="tile"><div class="t-title">{esc(title)}</div><div class="t-value">{fmt(cur)}</div>'
            f'<div class="t-unit">{esc(unit)}</div>{badge}<div class="t-note">{esc(note)}</div></div>')


def line_chart(rows, key, title, note, cid):
    pts = [(r["week"], r[key]) for r in rows]
    vals = [v for _, v in pts if v is not None]
    W, Hh, L, R, T, B = 560, 180, 40, 12, 12, 26
    top = max(vals) if vals else 1
    top = top * 1.15 or 1
    n = max(len(pts) - 1, 1)
    x = lambda i: L + (W - L - R) * i / n  # noqa: E731
    y = lambda v: T + (Hh - T - B) * (1 - v / top)  # noqa: E731
    grid = "".join(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(top * f / 1.15):.1f}" y2="{y(top * f / 1.15):.1f}"/>'
                   f'<text class="axis" x="{L - 6}" y="{y(top * f / 1.15) + 4:.1f}" text-anchor="end">{fmt(round(top * f / 1.15, 1))}</text>'
                   for f in (0, 0.5, 1))
    path, dots, segs = [], [], []
    for i, (w, v) in enumerate(pts):
        if v is None:
            if path:
                segs.append(path)
            path = []
            continue
        path.append(f"{x(i):.1f},{y(v):.1f}")
        dots.append(f'<circle class="dot" cx="{x(i):.1f}" cy="{y(v):.1f}" r="4"/>')
    if path:
        segs.append(path)
    lines = "".join(f'<polyline class="line" points="{" ".join(s)}"/>' for s in segs)
    labels = "".join(f'<text class="axis" x="{x(i):.1f}" y="{Hh - 6}" text-anchor="middle">{esc(w[-3:])}</text>'
                     for i, (w, _) in enumerate(pts) if i % max(1, len(pts) // 6) == 0 or i == len(pts) - 1)
    hits = "".join(f'<rect class="hit" x="{x(i) - (W - L - R) / n / 2:.1f}" y="{T}" width="{(W - L - R) / n:.1f}" height="{Hh - T - B}" '
                   f'data-w="{esc(w)}" data-v="{esc(fmt(v))}"/>' for i, (w, v) in enumerate(pts))
    table = "".join(f"<tr><td>{esc(w)}</td><td>{fmt(v)}</td></tr>" for w, v in pts)
    return (f'<figure class="card chart" id="{cid}"><figcaption><b>{esc(title)}</b><span>{esc(note)}</span></figcaption>'
            f'<div class="plot"><svg viewBox="0 0 {W} {Hh}" role="img" aria-label="{esc(title)}">{grid}{lines}{dots}{labels}{hits}</svg>'
            f'<div class="tip" hidden></div></div>'
            f'<details><summary>Таблица</summary><table><tr><th>Неделя</th><th>Значение</th></tr>{table}</table></details></figure>')


def page(r):
    rows, t = r["weeks"], r["totals"]
    tiles = "".join(tile(rows, *x) for x in TILES)
    charts = "".join(line_chart(rows, k, ti, no, f"c{i}") for i, (k, ti, no) in enumerate(CHARTS))
    icon = {"good": "✓", "warning": "!", "serious": "↺", "critical": "✗", "neutral": "…"}
    loop_rows = "".join(
        f'<tr><td>{esc(l["date"])}</td><td><b>{esc(l["id"])}</b><br><span class="muted">{esc(l["title"][:70])}</span></td>'
        f'<td>{esc(l["repo"])}</td><td>{esc(" ".join(l["barriers"]) or "—")}</td><td>{esc(l["level"] or "—")}</td>'
        f'<td class="num">{l["before"]}</td><td class="num">{l["after"]}</td>'
        f'<td><span class="pill {l["tone"]}">{icon[l["tone"]]} {esc(l["state"])}</span></td></tr>'
        for l in reversed(r["loop"])) or '<tr><td colspan="8" class="muted">Инцидентов нет. Запишите первый: ./harness.sh incident . "что случилось"</td></tr>'
    pro = "".join(f'<tr><td><b>{esc(b)}</b></td><td>{esc(E.NAMES.get(b, ""))}</td><td class="num">{n}</td></tr>' for b, n in r["proactive"]) \
        or '<tr><td colspan="3" class="muted">Пока нет срабатываний.</td></tr>'
    cand = "".join(f'<tr><td><code>{esc(c["sig"])}</code></td><td class="num">{c["n"]}</td><td class="num">{c["sessions"]}</td>'
                   f'<td class="num">{c["prev7"]} → {c["last7"]}</td><td>{esc(c["repos"])}</td></tr>' for c in r["candidates"]) \
        or '<tr><td colspan="5" class="muted">Повторяющихся ошибок без барьера нет.</td></tr>'
    wk = "".join(f'<tr><td>{esc(w["week"])}</td><td class="num">{w["sessions"]}</td><td class="num">{fmt(w["calls"])}</td>'
                 f'<td class="num">{fmt(w["tool_error_rate"])}</td><td class="num">{w["blocked"]}</td><td class="num">{w["asked"]}</td>'
                 f'<td class="num">{fmt(w["tokens_per_session"])}</td><td class="num">{fmt(w["cost_per_session"])}</td><td class="num">{fmt(w["cost_week"])}</td>'
                 f'<td class="num">{w["incidents"]}</td><td class="num">{w["new_classes"]}</td></tr>' for w in rows)
    money = (f'{fmt(t["rub"])} ₽ ({t["rate_src"]}, {fmt(round(t["rate"], 2))} ₽ за $)' if t["rate"] else t["rate_src"])
    summary = (f'{t["sessions"]} сессий, {fmt(t["calls"])} вызовов инструментов, {t["repos"]} проектов, '
               f'{t["events"]} событий барьеров, {t["incidents"]} инцидентов ({t["open"]} открыто), потрачено {money}')
    return TEMPLATE.replace("{{SUMMARY}}", esc(summary)).replace("{{NOW}}", r["now"].strftime("%Y-%m-%d %H:%M UTC")) \
        .replace("{{TILES}}", tiles).replace("{{CHARTS}}", charts).replace("{{LOOP}}", loop_rows) \
        .replace("{{LEARNED}}", str(t["learned"])).replace("{{HOLDING}}", str(t["holding"])).replace("{{LEAKED}}", str(t["leaked"])) \
        .replace("{{ENF}}", fmt(t["enforcement"])).replace("{{MACHINE}}", fmt(t["found_by_machine"])) \
        .replace("{{PRO}}", pro).replace("{{CAND}}", cand).replace("{{WEEKS}}", wk)


TEMPLATE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Харнес: обучение агента</title>
<style>
:root{--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;--s1:#2a78d6;
--good:#006300;--good-bg:#e3f3e3;--warn:#8a5a00;--warn-bg:#fdf1d6;--serious:#a8431b;--serious-bg:#fbe7dd;--crit:#b02a2a;--crit-bg:#f8e1e1;--border:#e1e0d9}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;
--grid:#2c2c2a;--axis:#383835;--s1:#3987e5;--good:#0ca30c;--good-bg:#132a13;--warn:#fab219;--warn-bg:#2e2410;--serious:#ec835a;--serious-bg:#33201a;--crit:#e66767;--crit-bg:#341a1a;--border:#2c2c2a}}
:root[data-theme="dark"]{--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;--s1:#3987e5;
--good:#0ca30c;--good-bg:#132a13;--warn:#fab219;--warn-bg:#2e2410;--serious:#ec835a;--serious-bg:#33201a;--crit:#e66767;--crit-bg:#341a1a;--border:#2c2c2a}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 48px}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:32px 0 6px}
.lead,.muted,figcaption span,.t-note,.t-unit{color:var(--ink2)}.muted{color:var(--muted)}p.lead{margin:0 0 16px;max-width:860px}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px}
.tile,.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.t-title{font-size:12px;color:var(--ink2)}.t-value{font-size:26px;font-weight:650;margin-top:2px}.t-unit{font-size:12px}.t-note{font-size:12px;margin-top:6px}
.delta,.pill{display:inline-block;font-size:12px;border-radius:6px;padding:1px 7px;margin-top:6px}
.good{color:var(--good);background:var(--good-bg)}.critical{color:var(--crit);background:var(--crit-bg)}.warning{color:var(--warn);background:var(--warn-bg)}
.serious{color:var(--serious);background:var(--serious-bg)}.neutral{color:var(--ink2);background:var(--grid)}
.charts{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,520px),1fr));gap:10px}
figure{margin:0}figcaption{display:flex;flex-direction:column;gap:2px;margin-bottom:6px}
.plot{position:relative}svg{width:100%;height:auto;display:block}.grid{stroke:var(--grid);stroke-width:1}.axis{fill:var(--muted);font-size:11px}
.line{fill:none;stroke:var(--s1);stroke-width:2;stroke-linejoin:round}.dot{fill:var(--s1);stroke:var(--surface);stroke-width:2}
.hit{fill:transparent;cursor:crosshair}.hit:hover{fill:var(--grid);fill-opacity:.45}
.tip{position:absolute;pointer-events:none;background:var(--ink);color:var(--surface);font-size:12px;padding:4px 8px;border-radius:6px;white-space:nowrap;transform:translate(-50%,-110%)}
details{margin-top:6px}summary{cursor:pointer;color:var(--ink2);font-size:12px}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border);vertical-align:top}
th{font-weight:600;color:var(--ink2);font-size:12px}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}code{font-size:12px;word-break:break-all}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;counter-reset:s}
.flow div{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px 12px;font-size:13px}
.flow b{display:block;margin-bottom:2px}.flow b::before{counter-increment:s;content:counter(s) ". ";color:var(--s1)}
.kpis{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
</style></head><body><main>
<h1>Харнес: становится ли агент лучше</h1>
<p class="lead">Обновлено {{NOW}}. {{SUMMARY}}. Модель не учится между сессиями — учится среда: барьеры, правила и скиллы. Дашборд проверяет, что эта среда сходится: старые ошибки не повторяются, новые ловятся до человека, работа дешевеет.</p>

<h2>Последние 4 недели против 4 предыдущих</h2>
<div class="tiles">{{TILES}}</div>

<h2>Петля: что происходит с ошибкой</h2>
<div class="flow">
<div><b>Поймать</b>барьер, гейт или упавший вызов пишет событие в хранилище</div>
<div><b>Заметить</b>повтор 3+ раз за 7 дней или растущая сигнатура ошибки → кандидат</div>
<div><b>Записать</b>инцидент в error.md: класс, причина, ID барьера</div>
<div><b>Запретить</b>барьер на самом глубоком уровне + атака-репро в демо, CI не даст его сломать</div>
<div><b>Научить</b>сообщение барьера говорит агенту, что делать; строка правила — для следующих сессий</div>
<div><b>Проверить</b>попытки после инцидента: 0 — выучено, &gt;0 — держит, тот же класс снова — утечка</div>
</div>

<h2>Инциденты и что с ними стало</h2>
<div class="kpis"><span class="pill good">✓ выучено: {{LEARNED}}</span><span class="pill warning">! держит, агент пытается: {{HOLDING}}</span>
<span class="pill serious">↺ утечки: {{LEAKED}}</span><span class="pill neutral">барьер машинный (Enforcement Ratio): {{ENF}}%</span>
<span class="pill neutral">найдено машиной, а не человеком: {{MACHINE}}%</span></div>
<div class="card scroll"><table><tr><th>Дата</th><th>Инцидент</th><th>Проект</th><th>Барьер</th><th>Уровень</th>
<th class="num">Попыток за 28 дн. до</th><th class="num">после</th><th>Состояние</th></tr>{{LOOP}}</table></div>

<div class="charts" style="margin-top:10px">{{CHARTS}}</div>

<h2>Ошибки, которых не было: барьеры без инцидента</h2>
<p class="lead">Барьер поставлен заранее, по типовым ошибкам агентов, а не после своей. Каждое срабатывание — ошибка, которую не пришлось пережить.</p>
<div class="card scroll"><table><tr><th>Барьер</th><th>Что</th><th class="num">Остановлено</th></tr>{{PRO}}</table></div>

<h2>Следующие барьеры: повторяющиеся ошибки без защиты</h2>
<p class="lead">Сигнатуры упавших вызовов за 14 дней, 3+ раза и в 2+ сессиях. Растёт за последнюю неделю — первый кандидат в инцидент и барьер.</p>
<div class="card scroll"><table><tr><th>Сигнатура</th><th class="num">Раз</th><th class="num">Сессий</th><th class="num">Неделя до → последняя</th><th>Проекты</th></tr>{{CAND}}</table></div>

<h2>По неделям</h2>
<div class="card scroll"><table><tr><th>Неделя</th><th class="num">Сессий</th><th class="num">Вызовов</th><th class="num">Ошибок на 100</th>
<th class="num">Блоков</th><th class="num">Вопросов</th><th class="num">Токенов, тыс.</th><th class="num">₽ на сессию</th><th class="num">₽ за неделю</th><th class="num">Инцидентов</th><th class="num">Новых классов</th></tr>{{WEEKS}}</table></div>
<p class="muted">Источники: журналы сессий Claude Code, хранилище событий харнеса, error.md проектов. Данные не покидают машину. Команда: ./harness.sh dashboard</p>
</main>
<script>
document.querySelectorAll('.plot').forEach(function(p){var tip=p.querySelector('.tip');
p.querySelectorAll('.hit').forEach(function(h){h.addEventListener('mousemove',function(ev){var b=p.getBoundingClientRect();
tip.hidden=false;tip.textContent=h.dataset.w+': '+h.dataset.v;tip.style.left=(ev.clientX-b.left)+'px';tip.style.top=(ev.clientY-b.top)+'px';});
h.addEventListener('mouseleave',function(){tip.hidden=true;});});});
</script></body></html>
"""


def evolve(r, repo: Path, dry: bool = False) -> int:
    """One turn of the loop with no human: draft incidents for new candidates, tasks for the agent.
    The agent closes a draft with the error-to-rule skill; a human reviews the barrier in the MR."""
    log = repo / "error.md"
    text = log.read_text(encoding="utf-8") if log.exists() else ""
    now = dt.datetime.now(dt.timezone.utc)
    known = {b for i in r["incidents"] for b in i["barriers"]}
    drafts = []
    for c in r["candidates"]:  # failed calls that repeat and that no barrier covers
        if f"Signature: {c['sig']}" not in text:
            drafts.append((c["sig"][:60], f"{c['n']} failed calls in {c['sessions']} sessions in 14 days ({c['repos']})", c["sig"]))
    rep = collections.defaultdict(list)  # a barrier fires 3+ times in 7 days and no incident points at it
    for e in r["events"]:
        if e.get("outcome") in ("blocked", "failed", "asked") and e["_ts"] >= now.replace(tzinfo=None) - dt.timedelta(days=7):
            rep[(e.get("barrier") or e.get("name"), E.norm(e.get("detail", "")))].append(e)
    for (b, n), v in rep.items():
        sig = f"{b}: {n[:70]}"
        if len(v) >= 3 and b not in known and f"Signature: {sig}" not in text:
            drafts.append((f"{b} fired {len(v)} times in 7 days", f"the agent keeps trying: {v[-1].get('detail', '')[:100]}", sig))
    day = now.strftime("%Y-%m-%d")
    n0 = len(re.findall(rf"^## INC-{day}-", text, re.M))
    ids, body = [], ""
    for k, (title, symptom, sig) in enumerate(drafts, 1):
        iid = f"INC-{day}-{n0 + k:02d}"
        ids.append(iid)
        body += (f"\n## {iid}: {title}\n- Date: {day}\n- Agent:\n- Found by: dashboard\n- Where:\n- Symptom: {symptom}\n"
                 f"- Signature: {sig}\n- Cause:\n- Class:\n- Barrier:\n- Level: text | hook | server | OS\n- Repro:\n- ADR: -\n- Status: open\n- Closed:\n")
    if body and not dry:
        if not log.exists():
            body = "# Agent error log\n" + body
        with log.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
    print(f"evolve: {len(ids)} new draft incident(s){' (dry run)' if dry else ''} in {log}")
    tasks = [f"close {i} with the error-to-rule skill: find the class, make the barrier, add the repro" for i in ids]
    tasks += [f"{l['id']}: the barrier holds but the agent tries ({l['after']}x). Fix the rule line or the skill that leads it there"
              for l in r["loop"] if l["tone"] == "warning" and l["barriers"]]
    status = {i["id"]: i["status"] for i in r["incidents"]}
    later_open = lambda l: any(status.get(x) == "open" for x in re.findall(r"INC-[\d-]+", l["state"]))  # noqa: E731
    # a leak that a later closed incident fixed is history, not a task
    tasks += [f"{l['id']}: {l['state']}. Make the barrier stop the class, not the case"
              for l in r["loop"] if l["tone"] == "serious" and later_open(l)]
    tasks += [f"{l['id']}: only a text rule. Find a check that a machine can run" for l in r["loop"] if l["state"].startswith("только текст")]
    if tasks:
        print("Tasks for the agent (paste them into the agent session):")
        for t in tasks:
            print(f"  - {t}")
    else:
        print("Nothing to do: no new candidates, no barrier that leaks or that the agent keeps hitting.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", action="append", default=[])
    ap.add_argument("--weeks", type=int, default=12)
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--evolve", metavar="REPO", help="draft incidents in REPO/error.md and print tasks for the agent")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    r = build([Path(x) for x in a.repo + ([a.evolve] if a.evolve else [])], a.weeks)
    if a.evolve:
        return evolve(r, Path(a.evolve).resolve(), a.dry_run)
    if a.json:
        print(json.dumps({"totals": r["totals"], "weeks": r["weeks"], "loop": r["loop"], "candidates": r["candidates"],
                          "proactive": r["proactive"]}, ensure_ascii=False, indent=2))
        return 0
    out = Path(a.out) if a.out else HH / "dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(r), encoding="utf-8", newline="\n")
    t = r["totals"]
    print(f"{out}\n  {t['sessions']} sessions, {t['calls']} tool calls, {t['events']} barrier events, {t['incidents']} incidents"
          f" (learned {t['learned']}, holding {t['holding']}, leaked {t['leaked']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
