#!/usr/bin/env python3
"""Aggregate Claude Code token/cache usage from local session transcripts.

Read-only. Source: ~/.claude/projects/<project-slug>/*.jsonl (main sessions)
and <session>/subagents/*.jsonl (subagent calls, attributed to the parent
session). Each API response is counted once (dedup by message.id — a single
response is written as several transcript lines, one per content block).

Used by sdd-metrics-reporter for the "Consumo y caché" section. Complements
`opencode stats`, which only covers the OpenCode side of the delegation.

"ieq" (input-equivalent tokens) weights each bucket by its price relative to
base input on the same model: input 1, cache write 5m 1.25, cache write 1h 2,
cache read 0.1, output 5. It is a trend metric, not dollars — compare it
across days, not across models.

Usage:
  scripts/sdd_token_usage.py [--since YYYY-MM-DD] [--until YYYY-MM-DD]
                             [--project-dir DIR] [--top N] [--format md|json]
"""
import argparse
import collections
import datetime
import glob
import json
import os
import sys

WEIGHTS = {"in": 1.0, "cw5m": 1.25, "cw1h": 2.0, "cr": 0.1, "out": 5.0}

# Alert thresholds (documented in sdd-metrics-reporter-agent).
MAX_SESSION_CTX = 400_000
MAX_AVG_READ_PER_CALL = 250_000
MIN_HIT_RATE = 95.0
MAX_WEEK_GROWTH_PCT = 30.0
MAX_BASELINE_CTX = 60_000


def default_project_dir():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    slug = root.replace("/", "-")
    return os.path.expanduser(f"~/.claude/projects/{slug}")


def iter_usage(path):
    seen = set()
    with open(path, errors="ignore") as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            msg = entry.get("message")
            if not isinstance(msg, dict) or "usage" not in msg:
                continue
            mid = msg.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            yield entry.get("timestamp") or "", msg.get("model") or "?", msg["usage"]


def buckets(usage):
    cc = usage.get("cache_creation") or {}
    cw = usage.get("cache_creation_input_tokens", 0) or 0
    cw1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
    cw5m = cc.get("ephemeral_5m_input_tokens", cw - cw1h) or 0
    return {
        "in": usage.get("input_tokens", 0) or 0,
        "cw5m": cw5m,
        "cw1h": cw1h,
        "cr": usage.get("cache_read_input_tokens", 0) or 0,
        "out": usage.get("output_tokens", 0) or 0,
    }


def ieq(c):
    return sum(c[k] * w for k, w in WEIGHTS.items())


def hit_rate(c):
    total = c["in"] + c["cw5m"] + c["cw1h"] + c["cr"]
    return round(100.0 * c["cr"] / total, 1) if total else 0.0


def collect(project_dir, since, until):
    days = collections.defaultdict(collections.Counter)
    models = collections.defaultdict(collections.Counter)
    sessions = {}
    for main in glob.glob(os.path.join(project_dir, "*.jsonl")):
        sid = os.path.basename(main)[:-6]
        sess = {"id": sid, "calls": 0, "sub_calls": 0, "first_ctx": None, "max_ctx": 0,
                "cr": 0, "ieq": 0.0, "day": None, "models": collections.Counter()}
        files = [(main, False)] + [(p, True) for p in glob.glob(os.path.join(project_dir, sid, "subagents", "*.jsonl"))]
        for path, is_sub in files:
            for ts, model, usage in iter_usage(path):
                day = ts[:10]
                if not day or day < since or day > until:
                    continue
                b = buckets(usage)
                ctx = b["in"] + b["cw5m"] + b["cw1h"] + b["cr"]
                d = days[day]
                d.update(b)
                d["calls"] += 1
                d["sub_calls"] += is_sub
                models[model].update(b)
                models[model]["calls"] += 1
                sess["calls"] += 1
                sess["sub_calls"] += is_sub
                sess["cr"] += b["cr"]
                sess["ieq"] += ieq(b)
                sess["models"][model] += 1
                if not is_sub:
                    if sess["first_ctx"] is None:
                        sess["first_ctx"] = ctx
                        sess["day"] = day
                    sess["max_ctx"] = max(sess["max_ctx"], ctx)
        if sess["calls"]:
            sessions[sid] = sess
    return days, models, sessions


def summarize(days, models, sessions, top, until):
    day_rows = []
    for day in sorted(days):
        c = days[day]
        day_rows.append({
            "day": day, "calls": c["calls"], "sub_calls": c["sub_calls"],
            "input": c["in"], "cache_write_5m": c["cw5m"], "cache_write_1h": c["cw1h"],
            "cache_read": c["cr"], "output": c["out"], "hit_pct": hit_rate(c),
            "avg_read_per_call": c["cr"] // max(c["calls"], 1), "ieq": int(ieq(c)),
        })
    model_rows = [{"model": m, "calls": c["calls"], "cache_read": c["cr"], "output": c["out"],
                   "ieq": int(ieq(c))} for m, c in sorted(models.items(), key=lambda kv: -ieq(kv[1]))]
    sess_rows = sorted(({
        "session": s["id"][:8], "day": s["day"], "calls": s["calls"], "sub_calls": s["sub_calls"],
        "first_ctx": s["first_ctx"] or 0, "max_ctx": s["max_ctx"],
        "avg_read_per_call": s["cr"] // max(s["calls"], 1), "ieq": int(s["ieq"]),
        "model": s["models"].most_common(1)[0][0],
    } for s in sessions.values()), key=lambda r: -r["ieq"])

    end = datetime.date.fromisoformat(until) if until != "9999-12-31" else datetime.date.today()
    week = lambda lo, hi: sum(r["ieq"] for r in day_rows if lo <= r["day"] <= hi)
    d = lambda n: (end - datetime.timedelta(days=n)).isoformat()
    this_week, prev_week = week(d(6), end.isoformat()), week(d(13), d(7))
    growth = round(100.0 * (this_week - prev_week) / prev_week, 1) if prev_week else None

    alerts = []
    big = [r for r in sess_rows if r["max_ctx"] > MAX_SESSION_CTX]
    if big:
        worst = ", ".join(f"{r['session']} {k(r['max_ctx'])}" for r in sorted(big, key=lambda r: -r["max_ctx"])[:5])
        alerts.append(f"{len(big)} of {len(sess_rows)} sessions exceeded {k(MAX_SESSION_CTX)} context (worst: {worst})")
    firsts = sorted(r["first_ctx"] for r in sess_rows if r["first_ctx"])
    baseline = firsts[len(firsts) // 2] if firsts else 0
    if baseline > MAX_BASELINE_CTX:
        alerts.append(f"median session baseline is {k(baseline)} tokens before any work (> {k(MAX_BASELINE_CTX)})")
    heavy_days = [r for r in day_rows if r["avg_read_per_call"] > MAX_AVG_READ_PER_CALL]
    if heavy_days:
        alerts.append(f"{len(heavy_days)} days with avg cache read per call > {k(MAX_AVG_READ_PER_CALL)}: "
                      + ", ".join(f"{r['day']} {k(r['avg_read_per_call'])}" for r in heavy_days))
    for r in day_rows:
        if r["calls"] >= 50 and r["hit_pct"] < MIN_HIT_RATE:
            alerts.append(f"{r['day']}: cache hit {r['hit_pct']}% (< {MIN_HIT_RATE}%)")
    if growth is not None and growth > MAX_WEEK_GROWTH_PCT:
        alerts.append(f"week-over-week ieq growth {growth}% (> {MAX_WEEK_GROWTH_PCT}%)")

    return {"days": day_rows, "models": model_rows, "top_sessions": sess_rows[:top],
            "sessions_total": len(sess_rows),
            "week": {"this": this_week, "previous": prev_week, "growth_pct": growth},
            "baseline_median": baseline, "alerts": alerts}


def k(n):
    return f"{n / 1000:,.0f}k" if n < 10_000_000 else f"{n / 1_000_000:,.1f}M"


def render_md(s):
    out = ["### Por día", "",
           "| Día | Llamadas | Subagente | Cache write 5m | Cache write 1h | Cache read | Output | Hit % | Read/llamada | ieq |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in s["days"]:
        out.append(f"| {r['day']} | {r['calls']} | {r['sub_calls']} | {k(r['cache_write_5m'])} | {k(r['cache_write_1h'])} | "
                   f"{k(r['cache_read'])} | {k(r['output'])} | {r['hit_pct']} | {k(r['avg_read_per_call'])} | {k(r['ieq'])} |")
    out += ["", "### Por modelo", "", "| Modelo | Llamadas | Cache read | Output | ieq |", "|---|---|---|---|---|"]
    for r in s["models"]:
        out.append(f"| {r['model']} | {r['calls']} | {k(r['cache_read'])} | {k(r['output'])} | {k(r['ieq'])} |")
    out += ["", f"**Contexto inicial mediano por sesión:** {k(s['baseline_median'])}"]
    out += ["", f"### Sesiones más costosas (top {len(s['top_sessions'])} de {s['sessions_total']})", "",
            "| Sesión | Día | Llamadas | Subagente | Contexto inicial | Contexto máx | Read/llamada | ieq | Modelo |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in s["top_sessions"]:
        out.append(f"| {r['session']} | {r['day']} | {r['calls']} | {r['sub_calls']} | {k(r['first_ctx'])} | "
                   f"{k(r['max_ctx'])} | {k(r['avg_read_per_call'])} | {k(r['ieq'])} | {r['model']} |")
    w = s["week"]
    out += ["", f"**Semana actual vs anterior (ieq):** {k(w['this'])} vs {k(w['previous'])}"
            + (f" ({w['growth_pct']:+}%)" if w["growth_pct"] is not None else ""), "", "### Alertas", ""]
    out += [f"- {a}" for a in s["alerts"]] or ["- ninguna"]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default=(datetime.date.today() - datetime.timedelta(days=14)).isoformat())
    ap.add_argument("--until", default="9999-12-31")
    ap.add_argument("--project-dir", default=default_project_dir())
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--format", choices=("md", "json"), default="md")
    args = ap.parse_args()
    if not os.path.isdir(args.project_dir):
        sys.exit(f"project dir not found: {args.project_dir}")
    summary = summarize(*collect(args.project_dir, args.since, args.until), args.top, args.until)
    print(json.dumps(summary, indent=2) if args.format == "json" else render_md(summary))


if __name__ == "__main__":
    main()
