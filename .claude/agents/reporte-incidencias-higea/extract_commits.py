#!/usr/bin/env python3
"""Extrae commits [FIX]/[FEAT] (u otros tags) de un repo git como JSON.

Uso:
  extract_commits.py --repo PATH --since YYYY-MM-DD --until YYYY-MM-DD [--branch NAME | --all-branches] [--tags FIX,FEAT]
  extract_commits.py --repo PATH --range REF1..REF2 [--tags FIX,FEAT]

Salida: JSON (lista de objetos) a stdout. No decide que incluir en el reporte
final ni redacta Resumen/Problema/Causa/Solucion -- eso es trabajo del modelo,
este script solo hace la extraccion mecanica de git log.
"""
import argparse
import json
import re
import subprocess
import sys

RS = "\x1e"  # separador de registro (entre commits)
FS = "\x1f"  # separador de campo (dentro de un commit)

REF_LINE_RE = re.compile(r"^-\s*(Ticket|Tarea|PR|Otros)\s*:\s*(.*)$", re.IGNORECASE)


def run_git(args, cwd):
    result = subprocess.run(
        ["git", "-C", cwd] + args, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    return result.stdout


def parse_subject(subject):
    """Separa '[TAG] modulo: resto' en (tag, modulo, resto). Best-effort: el
    modelo debe verificar contra el subject/body crudo si el modulo importa."""
    m = re.match(r"^\[(?P<tag>[A-Za-z_]+)\]\s*\(?(?P<modtxt>[^:)]*)\)?:?\s*(?P<rest>.*)$", subject)
    if not m:
        return None, None, subject
    tag = m.group("tag").upper()
    modtxt = m.group("modtxt").strip() or None
    rest = m.group("rest").strip()
    return tag, modtxt, rest


def parse_references(body):
    refs = {}
    for line in body.splitlines():
        m = REF_LINE_RE.match(line.strip())
        if m:
            key = m.group(1).capitalize()
            val = m.group(2).strip()
            refs[key] = val if val else None
    return refs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="Ruta al repositorio git (default: .)")
    ap.add_argument("--since", help="Fecha inicio YYYY-MM-DD (junto con --until)")
    ap.add_argument("--until", help="Fecha fin YYYY-MM-DD (junto con --until)")
    ap.add_argument("--range", help="Rango de refs, ej. abc123..def456")
    scope = ap.add_mutually_exclusive_group()
    scope.add_argument("--branch", help="Rama a inspeccionar (default: rama actual)")
    scope.add_argument("--all-branches", action="store_true", help="Buscar en todas las ramas (git log --all)")
    ap.add_argument("--tags", default="FIX,FEAT", help="Tags a incluir, separados por coma (default: FIX,FEAT)")
    args = ap.parse_args()

    if not args.range and not (args.since and args.until):
        ap.error("Especifica --range REF1..REF2, o --since y --until juntos.")

    wanted_tags = {t.strip().upper() for t in args.tags.split(",") if t.strip()}

    fmt = f"%H{FS}%h{FS}%ad{FS}%an{FS}%s{FS}%b{RS}"
    log_args = ["log", "--no-merges", "--date=short", f"--format={fmt}"]

    if args.range:
        log_args.append(args.range)
    else:
        if args.all_branches:
            log_args.append("--all")
        else:
            branch = args.branch
            if not branch:
                branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], args.repo).strip()
            log_args.append(branch)
        log_args += [f"--since={args.since} 00:00:00", f"--until={args.until} 23:59:59"]

    raw = run_git(log_args, args.repo)

    commits = []
    for record in raw.split(RS):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split(FS)
        if len(parts) != 6:
            continue
        full_hash, short_hash, date, author, subject, body = parts
        tag, module_guess, rest = parse_subject(subject)
        if wanted_tags and (tag is None or tag not in wanted_tags):
            continue
        commits.append({
            "hash": short_hash,
            "full_hash": full_hash,
            "date": date,
            "author": author,
            "subject": subject,
            "tag": tag,
            "module_guess": module_guess,
            "summary_guess": rest,
            "body": body,
            "references_guess": parse_references(body),
        })

    # git log ya devuelve del mas reciente al mas antiguo; el reporte queda
    # mas legible en orden cronologico ascendente.
    commits.reverse()

    print(json.dumps(commits, ensure_ascii=False, indent=2))
    if not commits:
        print(f"[extract_commits.py] Advertencia: 0 commits encontrados con tags {sorted(wanted_tags)} en el rango dado.", file=sys.stderr)


if __name__ == "__main__":
    main()
