#!/usr/bin/env python3
"""Carriles de review semanticos con fingerprint (P1-5).

Un carril es una frontera semantica del cambio. Cada carril declara:

    {
      "lanes": {
        "<id>": {
          "paths": ["<glob>", ...],
          "dependsOn": ["<id>", ...],
          "obligations": ["data-integrity", ...]
        }
      },
      "excluded": {"<obligacion>": "<razon concreta>"}
    }

El plan vive en src/.sdd/plans/<branch con "/" -> "_">/REVIEW_PLAN.json y el estado
(generaciones persistentes) en <repo>/.git/sdd-lanes.json.

Fingerprint de un carril:

    sha256(json_estable({
        lane, obligations, inputs: [[path, blob_id] ...],
        deps: [[id, fingerprint] ...], generation
    }))

Consecuencia: cambiar el contenido de un carril reabre ese carril y su cierre de
dependencias, y solo esos. Cada carril tiene una generacion {epoch, revision}; el
comando `invalidate` incrementa la revision del carril y la de sus dependientes.

Reglas:
  - las dependencias forman un DAG (no se admiten ciclos)
  - todo path cambiado entre la base y el worktree tiene que estar cubierto por >=1 carril
  - un carril NUNCA se ensancha solo: validate solo reporta los paths sin cubrir
  - las obligaciones estandar de Odoo tienen que estar cubiertas por al menos un carril
    o excluidas con una razon concreta

Uso:
  python3 scripts/sdd_lane_fingerprint.py validate [--base REF] [--plan PATH] [--repo DIR]
  python3 scripts/sdd_lane_fingerprint.py fingerprint [--lane ID] [--plan PATH] [--repo DIR]
  python3 scripts/sdd_lane_fingerprint.py invalidate <lane> [--plan PATH] [--repo DIR]
"""

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid

PLAN_SCHEMA = "sdd-lanes/v1"
PLAN_REL = os.path.join("src", ".sdd", "plans")
STATE_NAME = "sdd-lanes.json"
MAX_REVISION = 2 ** 53 - 1

USAGE = """usage:
  sdd_lane_fingerprint.py validate [--base REF] [--plan PATH] [--repo DIR] [--no-untracked]
  sdd_lane_fingerprint.py fingerprint [--lane ID] [--plan PATH] [--repo DIR]
  sdd_lane_fingerprint.py invalidate <lane> [--plan PATH] [--repo DIR]"""

# Obligaciones estandar para cambios en Odoo.
OBLIGATIONS = [
    "data-integrity",
    "security-permissions",
    "migrations",
    "i18n",
    "performance",
    "ui-ux",
]


def git(repo, *args, check=True):
    """Ejecuta git en `repo` y devuelve el stdout (sin el salto de linea final)."""
    proc = subprocess.run(
        ["git"] + list(args),
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError("git %s fallo en %s" % (" ".join(args), repo))
    return proc.stdout.strip()


def repo_root(repo=None):
    repo = repo or os.getcwd()
    return git(repo, "rev-parse", "--show-toplevel")


def current_branch(repo):
    try:
        return git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    except RuntimeError:
        return ""


def branch_slug(repo):
    """Rama actual con "/" reemplazado por "_" (nombre del directorio del plan)."""
    return current_branch(repo).replace("/", "_")


def default_plan_path(repo):
    return os.path.join(repo, PLAN_REL, branch_slug(repo), "REVIEW_PLAN.json")


def state_path(repo):
    """Ruta del estado persistente: <repo>/.git/sdd-lanes.json."""
    try:
        git_dir = git(repo, "rev-parse", "--git-dir")
    except RuntimeError:
        git_dir = os.path.join(repo, ".git")
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(repo, git_dir)
    return os.path.join(git_dir, STATE_NAME)


def load_plan(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_state(repo):
    path = state_path(repo)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"schema": PLAN_SCHEMA, "lanes": {}}


def save_state(repo, state):
    path = state_path(repo)
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    return path


def generation(state, lane_id):
    """Generacion persistida de un carril; se crea si todavia no existe."""
    lanes = state.setdefault("lanes", {})
    gen = lanes.get(lane_id)
    if not gen:
        gen = {"epoch": str(uuid.uuid4()), "revision": 1}
        lanes[lane_id] = gen
    return gen


def _glob_regex(pattern):
    """Traduce un glob tipo gitignore a regex: `*` no cruza "/", `**` si."""
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        char = pattern[i]
        if char == "*":
            if pattern[i:i + 3] == "**/":
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern[i:i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
            i += 1
            continue
        if char == "?":
            out.append("[^/]")
            i += 1
            continue
        out.append(re.escape(char))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def match_path(path, pattern):
    """True si `path` (relativo al repo, posix) cae dentro del glob del carril."""
    pattern = pattern.strip()
    if not pattern:
        return False
    if not any(ch in pattern for ch in "*?["):
        # Sin comodines: ruta exacta o directorio contenedor.
        return path == pattern or path.startswith(pattern.rstrip("/") + "/")
    if fnmatch.fnmatchcase(path, pattern):
        return True
    if pattern.endswith("/**"):
        base = pattern[:-3].rstrip("/")
        if path == base or path.startswith(base + "/"):
            return True
    return bool(_glob_regex(pattern).match(path))


def match_any(path, patterns):
    return any(match_path(path, pattern) for pattern in patterns or [])


def tracked_files(repo):
    out = git(repo, "ls-files", "-z")
    return [p for p in out.split("\0") if p]


def untracked_files(repo):
    proc = subprocess.run(
        ["git", "ls-files", "-o", "--exclude-standard", "-z"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if proc.returncode != 0:
        return []
    return [p for p in proc.stdout.split("\0") if p]


def index_blobs(repo):
    """Mapa path -> blob id del indice de git (identidad de la entrada versionada)."""
    out = git(repo, "ls-files", "-s", "-z")
    blobs = {}
    for entry in out.split("\0"):
        if not entry:
            continue
        parts = entry.split(None, 3)
        if len(parts) < 4:
            continue
        sha, path = parts[1], parts[3]
        blobs[path] = sha
    return blobs


def modified_paths(repo):
    """Paths tracked modificados en el worktree respecto al indice."""
    proc = subprocess.run(
        ["git", "diff", "--name-only", "-z"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if proc.returncode != 0:
        return set()
    return {p for p in proc.stdout.split("\0") if p}


def blob_id(repo, path, blobs, modified):
    """Blob id efectivo del path: el del worktree si cambio, el del indice si no."""
    sha = blobs.get(path)
    absolute = os.path.join(repo, path)
    if os.path.exists(absolute):
        if sha is None or path in modified:
            try:
                return git(repo, "hash-object", "--", path)
            except RuntimeError:
                return sha or ""
        return sha
    return sha or ""


def lane_inputs(repo, lane, blobs=None, modified=None):
    """Entradas del carril: [[path, blob_id]] ordenado por path."""
    blobs = blobs if blobs is not None else index_blobs(repo)
    modified = modified if modified is not None else modified_paths(repo)
    candidates = set(tracked_files(repo)) | set(untracked_files(repo))
    patterns = lane.get("paths") or []
    inputs = []
    for path in sorted(candidates):
        if not match_any(path, patterns):
            continue
        sha = blob_id(repo, path, blobs, modified)
        if not sha:
            continue
        inputs.append([path, sha])
    inputs.sort()
    return inputs


def _stable_json(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(repo, plan, lane_id, state, cache=None, blobs=None, modified=None):
    """Fingerprint de un carril (incluye el de sus dependencias)."""
    cache = cache if cache is not None else {}
    if lane_id in cache:
        return cache[lane_id]
    lanes = plan.get("lanes", {})
    if lane_id not in lanes:
        raise KeyError(lane_id)
    lane = lanes[lane_id]
    deps = []
    for dep in sorted(lane.get("dependsOn") or []):
        deps.append([dep, fingerprint(repo, plan, dep, state, cache, blobs, modified)])
    deps.sort()
    payload = {
        "lane": lane_id,
        "obligations": sorted(lane.get("obligations") or []),
        "inputs": lane_inputs(repo, lane, blobs, modified),
        "deps": deps,
        "generation": generation(state, lane_id),
    }
    digest = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()
    cache[lane_id] = digest
    return digest


def dependents(plan, lane_id):
    """Cierre de dependientes (transitivo) de un carril."""
    lanes = plan.get("lanes", {})
    result = set()
    frontier = [lane_id]
    while frontier:
        current = frontier.pop()
        for other, lane in lanes.items():
            if current in (lane.get("dependsOn") or []):
                if other not in result:
                    result.add(other)
                    frontier.append(other)
    return result


def find_cycle(plan):
    """Devuelve el primer ciclo encontrado (lista de ids) o None."""
    lanes = plan.get("lanes", {})
    state = {}
    stack = []

    def visit(node):
        state[node] = 1
        stack.append(node)
        for dep in sorted(lanes.get(node, {}).get("dependsOn") or []):
            if dep not in lanes:
                continue
            if state.get(dep) == 1:
                return stack[stack.index(dep):] + [dep]
            if state.get(dep, 0) == 0:
                found = visit(dep)
                if found:
                    return found
        stack.pop()
        state[node] = 2
        return None

    for lane_id in sorted(lanes):
        if state.get(lane_id, 0) == 0:
            found = visit(lane_id)
            if found:
                return found
    return None


def default_base(repo):
    """Base por defecto: merge-base de HEAD con HEAD~."""
    for args in (("merge-base", "HEAD", "HEAD~"), ("rev-parse", "HEAD~"), ("rev-parse", "HEAD")):
        try:
            value = git(repo, *args)
        except RuntimeError:
            continue
        if value:
            return value
    return ""


def changed_paths(repo, base, include_untracked=True):
    """Paths cambiados entre `base` y el worktree."""
    paths = set()
    if base:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "-z", base],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if proc.returncode == 0:
            paths = {p for p in proc.stdout.split("\0") if p}
    else:
        paths = set(modified_paths(repo))
    if include_untracked:
        paths |= set(untracked_files(repo))
    return paths


def cmd_validate(args):
    repo = repo_root(args.repo)
    plan_file = args.plan or default_plan_path(repo)
    errs = []
    if not os.path.exists(plan_file):
        print("FAIL no existe el plan %s" % plan_file)
        return 1
    try:
        plan = load_plan(plan_file)
    except ValueError as exc:
        print("FAIL plan ilegible: %s" % exc)
        return 1
    lanes = plan.get("lanes")
    if not isinstance(lanes, dict) or not lanes:
        print("FAIL el plan no declara carriles")
        return 1
    excluded = plan.get("excluded") or {}
    for lane_id, lane in lanes.items():
        for key in ("paths", "obligations"):
            if not isinstance(lane.get(key), list):
                errs.append("carril %s: '%s' debe ser una lista" % (lane_id, key))
        if not isinstance(lane.get("dependsOn", []), list):
            errs.append("carril %s: 'dependsOn' debe ser una lista" % lane_id)
        for dep in lane.get("dependsOn") or []:
            if dep not in lanes:
                errs.append("carril %s: depende de '%s' que no existe" % (lane_id, dep))
    cycle = find_cycle(plan)
    if cycle:
        errs.append("ciclo de dependencias: %s" % " -> ".join(cycle))
    for obligation in OBLIGATIONS:
        if obligation in excluded:
            reason = (excluded[obligation] or "").strip()
            if not reason:
                errs.append("obligacion '%s' excluida sin razon" % obligation)
            continue
        covered = [
            lane_id
            for lane_id, lane in lanes.items()
            if obligation in (lane.get("obligations") or [])
        ]
        if not covered:
            errs.append("obligacion '%s' no esta cubierta por ningun carril" % obligation)
    base = args.base or default_base(repo)
    paths = changed_paths(repo, base, not args.no_untracked)
    # El propio plan es metadata del gate, no un entregable del cambio.
    plan_rel = os.path.relpath(plan_file, repo)
    uncovered = []
    for path in sorted(paths):
        if path == plan_rel:
            continue
        if not any(match_any(path, lane.get("paths") or []) for lane in lanes.values()):
            uncovered.append(path)
    for path in uncovered:
        errs.append("path cambiado sin carril: %s" % path)
    for err in errs:
        print("FAIL %s" % err)
    print("plan: %s" % plan_file)
    print("lanes: %d" % len(lanes))
    print("base: %s" % (base or "(ninguna)"))
    print("changed paths: %d" % len(paths))
    print("uncovered: %d" % len(uncovered))
    return 1 if errs else 0


def cmd_fingerprint(args):
    repo = repo_root(args.repo)
    plan_file = args.plan or default_plan_path(repo)
    if not os.path.exists(plan_file):
        print("FAIL no existe el plan %s" % plan_file)
        return 1
    plan = load_plan(plan_file)
    lanes = plan.get("lanes", {})
    state = load_state(repo)
    cache = {}
    blobs = index_blobs(repo)
    modified = modified_paths(repo)
    wanted = [args.lane] if args.lane else sorted(lanes)
    result = {}
    for lane_id in wanted:
        if lane_id not in lanes:
            print("FAIL carril desconocido: %s" % lane_id)
            return 1
        result[lane_id] = fingerprint(repo, plan, lane_id, state, cache, blobs, modified)
    save_state(repo, state)
    for lane_id in wanted:
        print("%s %s" % (result[lane_id], lane_id))
    return 0


def cmd_invalidate(args):
    repo = repo_root(args.repo)
    plan_file = args.plan or default_plan_path(repo)
    if not os.path.exists(plan_file):
        print("FAIL no existe el plan %s" % plan_file)
        return 1
    plan = load_plan(plan_file)
    lanes = plan.get("lanes", {})
    if args.lane not in lanes:
        print("FAIL carril desconocido: %s" % args.lane)
        return 1
    state = load_state(repo)
    targets = [args.lane] + sorted(dependents(plan, args.lane))
    for lane_id in targets:
        gen = generation(state, lane_id)
        if gen["revision"] >= MAX_REVISION:
            gen["epoch"] = str(uuid.uuid4())
            gen["revision"] = 1
        else:
            gen["revision"] += 1
    path = save_state(repo, state)
    for lane_id in targets:
        gen = state["lanes"][lane_id]
        print("%s revision=%d epoch=%s" % (lane_id, gen["revision"], gen["epoch"]))
    print("wrote %s" % path)
    return 0


def build_parser():
    """CLI: validate | fingerprint | invalidate."""
    parser = argparse.ArgumentParser(prog="sdd_lane_fingerprint.py", description=USAGE)
    parser.add_argument("--repo", dest="repo_global", default=None, help="raiz del repo git")
    parser.add_argument("--plan", dest="plan_global", default=None, help="ruta del REVIEW_PLAN.json")
    sub = parser.add_subparsers(dest="command")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", dest="repo", default=None, help="raiz del repo git")
    common.add_argument("--plan", dest="plan", default=None, help="ruta del REVIEW_PLAN.json")

    p_validate = sub.add_parser("validate", parents=[common], help="valida el plan del carril")
    p_validate.add_argument("--base", default=None, help="ref base del diff (default: merge-base)")
    p_validate.add_argument("--no-untracked", dest="no_untracked", action="store_true",
                            help="no contar los archivos untracked entre los paths cambiados")

    p_fingerprint = sub.add_parser("fingerprint", parents=[common], help="fingerprint de los carriles")
    p_fingerprint.add_argument("--lane", default=None, help="un solo carril (default: todos)")

    p_invalidate = sub.add_parser("invalidate", parents=[common], help="invalida un carril")
    p_invalidate.add_argument("lane", help="id del carril a invalidar")

    return parser


def parse_args(argv):
    """Parsea los argumentos y devuelve (comando, Namespace) o (None, None)."""
    parser = build_parser()
    opts = parser.parse_args(argv)
    if not opts.command:
        parser.print_help()
        return None, None
    if not opts.repo:
        opts.repo = opts.repo_global
    if not opts.plan:
        opts.plan = opts.plan_global
    return opts.command, opts


if __name__ == "__main__":
    cmd, opts = parse_args(sys.argv[1:])
    if cmd is None:
        sys.exit(2)
    handlers = {"validate": cmd_validate, "fingerprint": cmd_fingerprint, "invalidate": cmd_invalidate}
    handler = handlers.get(cmd)
    if handler is None:
        print("FAIL comando desconocido: %s" % cmd)
        sys.exit(2)
    sys.exit(handler(opts))
