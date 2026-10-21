#!/usr/bin/env python3
"""Registro de errores de subagentes/dispatch (causa raiz antes de redespachar).

Registro append-only en <logs>/errors.jsonl (v:1), un error por linea, con huella (fingerprint) para detectar
reincidencia. Dos fuentes: `add` (manual, tras diagnosticar la causa raiz) e `ingest` (automatico desde
metrics.jsonl: rejected, orphaned, result failed, needs_human, judge_verdict FAIL; idempotente por job+evento).

Honestidad: lo que no se puede clasificar queda como `unclassified` y se cuenta; nunca se oculta.

Uso:
  sdd_error_report.py add --job J --role R --class C --symptom S [--root-cause X --evidence E --fix F ...]
  sdd_error_report.py ingest            # metrics.jsonl -> errors.jsonl
  sdd_error_report.py top [--role R] [--class C] [--since YYYY-MM-DD] [--limit N]
  sdd_error_report.py lessons --role R  # top-3 errores conocidos con su fix (para citar en un dispatch)
Variable: SDD_LOG_ROOT (default src/.sdd/logs).
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = ("infra", "context", "guardrail", "spec", "code", "test", "tooling", "misread", "unclassified")
SCHEMA_V = 1


def log_root():
    return os.environ.get("SDD_LOG_ROOT") or os.path.join(ROOT, "src", ".sdd", "logs")


def errors_path():
    return os.path.join(log_root(), "errors.jsonl")


def read_jsonl(path):
    rows, corrupt = [], 0
    if not os.path.exists(path):
        return rows, corrupt
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                corrupt += 1
    return rows, corrupt


def normalize(symptom):
    s = (symptom or "").lower()
    s = re.sub(r"'[^']*'", "'<x>'", s)
    s = re.sub(r"/[\w./-]+", "<path>", s)
    s = re.sub(r"\b[0-9a-f]{7,}\b", "<hex>", s)
    s = re.sub(r"\d+", "N", s)
    return re.sub(r"\s+", " ", s).strip()[:120]


def fingerprint(error_class, symptom):
    return hashlib.sha1(("%s|%s" % (error_class, normalize(symptom))).encode()).hexdigest()[:12]


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append(rows):
    os.makedirs(log_root(), exist_ok=True)
    with open(errors_path(), "a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_row(existing, **kw):
    cls = kw["error_class"]
    fp = fingerprint(cls, kw["symptom"])
    prior = sum(1 for r in existing if r.get("fingerprint") == fp)
    row = {"v": SCHEMA_V, "ts": kw.get("ts") or now(), "job_id": kw.get("job_id", ""), "role": kw.get("role", ""),
           "phase": kw.get("phase", ""), "error_class": cls, "symptom": kw["symptom"],
           "root_cause": kw.get("root_cause", ""), "evidence": kw.get("evidence", ""), "fix": kw.get("fix", ""),
           "fingerprint": fp, "repeat_count": prior + 1, "odoo_version": kw.get("odoo_version", ""),
           "module": kw.get("module", ""), "resolved_in_job": kw.get("resolved_in_job", ""),
           "source_key": kw.get("source_key", "")}
    existing.append(row)
    return row


def classify_metric(d):
    """Devuelve (role, class, symptom) para un evento de metrics que representa un error, o None."""
    ev, reason = d.get("event"), d.get("reason", "") or ""
    if ev == "rejected":
        if re.search(r"duplicate dispatch|missing required context|cwd does not match|spec_path not found|"
                     r"spec_sha256 mismatch", reason):
            return "lead", "context", reason
        return "lead", "unclassified", reason or "rejected (sin motivo)"
    if ev == "orphaned":
        return "opencode", "infra", "orphaned job (sesion tmux murio sin result)"
    if ev == "result" and d.get("status") == "failed":
        if d.get("cause_kind"):
            return "opencode", "infra", d["cause_kind"]
        return "opencode", "unclassified", "result failed exit_code=%s" % d.get("exit_code")
    if ev == "needs_human":
        return "opencode", "context", "needs_human: %s" % (d.get("question") or "")[:100]
    if ev == "judge_verdict" and d.get("verdict") == "FAIL":
        cls = d.get("error_class") if d.get("error_class") in CLASSES else "unclassified"
        return "opencode", cls, d.get("reason") or "judge FAIL (sin motivo)"
    return None


def cmd_add(args):
    rows, _ = read_jsonl(errors_path())
    row = build_row(rows, job_id=args.job, role=args.role, phase=args.phase, error_class=args.error_class,
                    symptom=args.symptom, root_cause=args.root_cause, evidence=args.evidence, fix=args.fix,
                    odoo_version=args.odoo_version, module=args.module, resolved_in_job=args.resolved_in_job,
                    source_key="")
    append([row])
    print("registered %s class=%s repeat_count=%d" % (row["fingerprint"], row["error_class"], row["repeat_count"]))
    return 0


def cmd_ingest(_args):
    metrics, corrupt = read_jsonl(os.path.join(log_root(), "metrics.jsonl"))
    existing, _ = read_jsonl(errors_path())
    seen = {r.get("source_key") for r in existing if r.get("source_key")}
    new = []
    for d in metrics:
        hit = classify_metric(d)
        if not hit:
            continue
        key = "%s:%s" % (d.get("job", ""), d.get("event"))
        if key in seen:
            continue
        seen.add(key)
        role, cls, symptom = hit
        new.append(build_row(existing, ts=d.get("ts"), job_id=d.get("job", ""), role=role, phase=d.get("event"),
                             error_class=cls, symptom=symptom, source_key=key))
    append(new)
    print("ingested %d new, corrupt metrics lines: %d" % (len(new), corrupt))
    return 0


def filtered(args):
    rows, corrupt = read_jsonl(errors_path())
    out = [r for r in rows
           if (not getattr(args, "role", None) or r.get("role") == args.role)
           and (not getattr(args, "error_class", None) or r.get("error_class") == args.error_class)
           and (not getattr(args, "since", None) or (r.get("ts") or "") >= args.since)]
    return out, corrupt


def groups(rows):
    g = collections.OrderedDict()
    for r in rows:
        g.setdefault(r["fingerprint"], []).append(r)
    return sorted(g.values(), key=lambda v: -len(v))


def cmd_top(args):
    rows, corrupt = filtered(args)
    unc = sum(1 for r in rows if r.get("error_class") == "unclassified")
    print("errors: %d (unclassified: %d, corrupt lines: %d)" % (len(rows), unc, corrupt))
    for grp in groups(rows)[:args.limit]:
        last = grp[-1]
        print("%3d x [%s/%s] %s  fp=%s" % (len(grp), last["error_class"], last["role"], last["symptom"][:90],
                                          last["fingerprint"]))
        fix = next((r["fix"] for r in reversed(grp) if r.get("fix")), "")
        if fix:
            print("      fix: %s" % fix[:120])
    return 0


def cmd_lessons(args):
    rows, _ = filtered(args)
    shown = 0
    for grp in groups([r for r in rows if r.get("error_class") != "unclassified"]):
        fix = next((r["fix"] for r in reversed(grp) if r.get("fix")), "")
        cause = next((r["root_cause"] for r in reversed(grp) if r.get("root_cause")), "")
        if not (fix or cause):
            continue
        last = grp[-1]
        print("- [%s] %s (x%d): %s" % (last["error_class"], last["symptom"][:80], len(grp), fix or cause))
        shown += 1
        if shown == 3:
            break
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--job", default="")
    a.add_argument("--role", required=True)
    a.add_argument("--class", dest="error_class", required=True, choices=CLASSES)
    a.add_argument("--symptom", required=True)
    for opt in ("root-cause", "evidence", "fix", "phase", "odoo-version", "module", "resolved-in-job"):
        a.add_argument("--" + opt, default="")
    sub.add_parser("ingest")
    for name in ("top", "lessons"):
        s = sub.add_parser(name)
        s.add_argument("--role")
        s.add_argument("--class", dest="error_class", choices=CLASSES)
        s.add_argument("--since")
        s.add_argument("--limit", type=int, default=10)
    args = p.parse_args(argv)
    if args.cmd == "lessons" and not args.role:
        p.error("lessons requires --role")
    return {"add": cmd_add, "ingest": cmd_ingest, "top": cmd_top, "lessons": cmd_lessons}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
