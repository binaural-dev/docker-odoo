#!/usr/bin/env bash
# opencode_model_switch.sh — alterna el modelo de TODOS los agentes de OpenCode
# entre el plan de pago (opencode-go/mimo-v2.5) y el gratuito
# (opencode/nemotron-3-ultra-free), para cuando se agota el límite mensual.
#
# Usage:
#   bash scripts/opencode_model_switch.sh status
#   bash scripts/opencode_model_switch.sh free    [--dry-run] [--scope repo|global|all]
#   bash scripts/opencode_model_switch.sh paid    [--dry-run] [--scope repo|global|all]
#   bash scripts/opencode_model_switch.sh restore [--dry-run]
#   bash scripts/opencode_model_switch.sh set <model-id> [--dry-run]
#
# Opciones:
#   --dry-run      muestra qué cambiaría, sin escribir nada
#   --scope        repo = src/.opencode ; global = ~/.config/opencode ; all (default)
#   --no-validate  no comprueba el modelo destino con `opencode models`
#
# Archivos gestionados (se reescribe SOLO el valor de `model`, en texto, para
# preservar comentarios y formato del JSONC):
#   repo:   src/.opencode/opencode.json, src/.opencode/agents/*.md
#   global: ~/.config/opencode/opencode.jsonc, ~/.config/opencode/agents/*.md,
#           ~/.config/opencode/agent/*.md
#
# `free`/`paid` cambian el modelo de todos los agentes gestionados (incluidos los
# que hoy usan otro modelo, p. ej. sdd-spec/pm/qc con deepseek-v4-flash). La
# primera vez guarda los valores originales en
# ~/.config/opencode/.model-switch-state.json; `restore` los devuelve exactos
# y borra el estado. Backups en ~/.config/opencode/model-switch-backups/<ts>/.
#
# Nota: un job OpenCode ya en ejecución conserva el modelo con el que arrancó;
# el cambio aplica a dispatches nuevos. No hace commits.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export REPO_ROOT
export OC_GLOBAL_DIR="${OPENCODE_GLOBAL_DIR:-$HOME/.config/opencode}"
export OC_REPO_DIR="${OPENCODE_REPO_DIR:-$REPO_ROOT/src/.opencode}"

FREE_MODEL="${OPENCODE_FREE_MODEL:-opencode/minimax-m3.1-flash-free}"
PAID_MODEL="${OPENCODE_PAID_MODEL:-opencode-go/deepseek-v4.1-flash}"

usage() { sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

[[ $# -ge 1 ]] || usage 1
CMD="$1"; shift
TARGET=""
DRY_RUN=0
SCOPE="all"
VALIDATE=1

case "$CMD" in
  free) TARGET="$FREE_MODEL" ;;
  paid) TARGET="$PAID_MODEL" ;;
  set)
    [[ $# -ge 1 ]] || { echo "error: set requiere <model-id>"; exit 1; }
    TARGET="$1"; shift ;;
  status|restore) ;;
  -h|--help|help) usage 0 ;;
  *) echo "error: subcomando desconocido: $CMD"; usage 1 ;;
esac

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --no-validate) VALIDATE=0 ;;
    --scope)
      [[ $# -ge 2 ]] || { echo "error: --scope requiere valor"; exit 1; }
      SCOPE="$2"; shift ;;
    *) echo "error: opción desconocida: $1"; exit 1 ;;
  esac
  shift
done

case "$SCOPE" in repo|global|all) ;; *) echo "error: --scope debe ser repo|global|all"; exit 1 ;; esac

if [[ -n "$TARGET" && $VALIDATE -eq 1 && $DRY_RUN -eq 0 ]]; then
  if command -v opencode >/dev/null 2>&1; then
    if ! opencode models 2>/dev/null | grep -Fxq -- "$TARGET"; then
      echo "error: el modelo '$TARGET' no aparece en 'opencode models' (usa --no-validate para omitir)"
      exit 1
    fi
  else
    echo "aviso: 'opencode' no está en PATH; se omite la validación del modelo"
  fi
fi

export OC_CMD="$CMD" OC_TARGET="$TARGET" OC_DRY_RUN="$DRY_RUN" OC_SCOPE="$SCOPE"

python3 - <<'PY'
import glob
import json
import os
import re
import shutil
import sys
import time

cmd = os.environ["OC_CMD"]
target = os.environ["OC_TARGET"]
dry = os.environ["OC_DRY_RUN"] == "1"
scope = os.environ["OC_SCOPE"]
gdir = os.environ["OC_GLOBAL_DIR"]
rdir = os.environ["OC_REPO_DIR"]
repo_root = os.environ["REPO_ROOT"]

state_path = os.path.join(gdir, ".model-switch-state.json")
backup_root = os.path.join(gdir, "model-switch-backups")


def managed_files():
    files = []
    if scope in ("repo", "all"):
        files.append(os.path.join(rdir, "opencode.json"))
        files += sorted(glob.glob(os.path.join(rdir, "agents", "*.md")))
    if scope in ("global", "all"):
        files.append(os.path.join(gdir, "opencode.jsonc"))
        files += sorted(glob.glob(os.path.join(gdir, "agents", "*.md")))
        files += sorted(glob.glob(os.path.join(gdir, "agent", "*.md")))
    return [f for f in files if os.path.isfile(f)]


JSON_RE = re.compile(r'("model"\s*:\s*")([^"]+)(")')
MD_RE = re.compile(r'^(model:[ \t]*)(\S+)([ \t]*)$', re.M)


def is_json(path):
    return path.endswith((".json", ".jsonc"))


def split_md(text):
    """(frontmatter, rest) — el `model:` solo cuenta dentro del frontmatter."""
    m = re.match(r'\A(---\r?\n.*?\r?\n---\r?\n?)', text, re.S)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def read_models(path):
    text = open(path, encoding="utf-8").read()
    if is_json(path):
        return [m.group(2) for m in JSON_RE.finditer(text)]
    fm, _ = split_md(text)
    return [m.group(2) for m in MD_RE.finditer(fm)]


def rewrite(path, new_values):
    """Sustituye, en orden, cada valor de `model` por new_values[i]."""
    text = open(path, encoding="utf-8").read()
    it = iter(new_values)

    def sub(m):
        return m.group(1) + next(it) + m.group(3)

    if is_json(path):
        return JSON_RE.sub(sub, text)
    fm, rest = split_md(text)
    return MD_RE.sub(sub, fm) + rest


def display(path):
    for base, label in ((rdir, "repo"), (gdir, "global")):
        if path.startswith(base + os.sep):
            return f"[{label}] {os.path.relpath(path, base)}"
    return path


def load_state():
    if os.path.isfile(state_path):
        with open(state_path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def write_files(changes):
    """changes: {path: new_text}. Hace backup antes de escribir."""
    if not changes:
        return
    ts = time.strftime("%Y%m%d-%H%M%S")
    bdir = os.path.join(backup_root, ts)
    os.makedirs(bdir, mode=0o700, exist_ok=True)
    os.chmod(backup_root, 0o700)
    for path, new_text in changes.items():
        dest = os.path.join(bdir, path.lstrip(os.sep).replace(os.sep, "__"))
        shutil.copy2(path, dest)
        os.chmod(dest, 0o600)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_text)
    print(f"Backup: {bdir}")


files = managed_files()
if not files:
    print("error: no se encontró ningún archivo gestionado")
    sys.exit(1)

if cmd == "status":
    by_model = {}
    for f in files:
        for v in read_models(f):
            by_model.setdefault(v, []).append(display(f))
            print(f"  {v:<34} {display(f)}")
    print()
    for model, where in sorted(by_model.items()):
        print(f"{model}: {len(where)} entrada(s)")
    if len(by_model) > 1:
        print("Aviso: hay más de un modelo en uso (puede ser intencional).")
    st = load_state()
    print("Estado de switch guardado: " + ("sí (usa 'restore' para volver al original)" if st else "no"))
    sys.exit(0)

if cmd == "restore":
    st = load_state()
    if not st:
        print("No hay estado guardado; nada que restaurar.")
        sys.exit(0)
    changes = {}
    for path, originals in st.items():
        if not os.path.isfile(path):
            print(f"aviso: {path} ya no existe, se omite")
            continue
        current = read_models(path)
        if len(current) != len(originals):
            print(f"aviso: {display(path)} cambió de estructura ({len(current)} vs {len(originals)} entradas); se omite")
            continue
        if current != originals:
            changes[path] = rewrite(path, originals)
            print(f"  restaurar {display(path)}: {sorted(set(current))} -> {sorted(set(originals))}")
    if not changes:
        print("Los archivos ya coinciden con el estado original.")
    elif dry:
        print("(dry-run) no se escribió nada")
        sys.exit(0)
    else:
        write_files(changes)
    if not dry:
        os.remove(state_path)
        print("Estado de switch eliminado.")
    sys.exit(0)

# free / paid / set
state = load_state()
new_state = dict(state)
changes = {}
unchanged = 0
for f in files:
    cur = read_models(f)
    if not cur:
        continue
    if all(v == target for v in cur):
        unchanged += 1
        continue
    if f not in new_state:
        new_state[f] = cur  # valores originales, solo la primera vez
    changes[f] = rewrite(f, [target] * len(cur))
    print(f"  {display(f)}: {sorted(set(cur))} -> {target}")

if not changes:
    print(f"Sin cambios: todo ya usa {target} ({unchanged} archivo(s)).")
elif dry:
    print(f"(dry-run) {len(changes)} archivo(s) cambiarían a {target}; no se escribió nada")
else:
    write_files(changes)
    os.makedirs(gdir, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(new_state, fh, indent=2)
    os.chmod(state_path, 0o600)
    print(f"{len(changes)} archivo(s) cambiados a {target}. Usa 'restore' para volver a los valores originales.")
    print("Nota: jobs OpenCode ya en ejecución conservan su modelo; aplica a dispatches nuevos.")
PY

# Verificación de alineación entre ambos configs (solo si se escribió algo).
if [[ "$CMD" =~ ^(free|paid|set|restore)$ && $DRY_RUN -eq 0 && "$SCOPE" == "all" ]]; then
  SYNC="$REPO_ROOT/scripts/sdd_opencode_config_sync_check.sh"
  if [[ -x "$SYNC" || -f "$SYNC" ]]; then
    echo "--- sync check ---"
    bash "$SYNC" || { echo "aviso: los configs repo/global divergen (ver arriba)"; exit 1; }
  fi
fi
