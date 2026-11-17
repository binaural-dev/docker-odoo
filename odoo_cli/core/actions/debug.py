"""``./odoo debug-setup``: prepare remote debugging of Odoo instances.

For every instance with ``debug: true`` it

1. extracts the Odoo core that the instance REALLY runs (read from the
   instance's own ``<inst>-py:/usr/lib/`` volume via an ephemeral
   ``docker compose run --entrypoint sh``; Odoo itself is never started)
   into ``src/debug/core-<ver>-<hash>/`` (only ``*.py``, read-only, shared by
   instances whose core has identical content);
2. writes the editor's debug configuration (``--editor``, only ``zed`` for
   now) pointing at ``127.0.0.1:<port>`` with path mappings core -> container.

Why a copy of the core: Odoo runs from the ``.deb`` at
``/usr/lib/python3/dist-packages/odoo`` (possibly an older/newer nightly than
``src/odoo<ver>``), so breakpoints only line up against the container's own
files. Zed can only link breakpoints to files inside the worktree.

Adding an editor: write a function ``(base_path, targets, prune, active) ->
(config_path, referenced_core_dirs)`` and register it in :data:`EDITORS`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from typing import TYPE_CHECKING

from generators.compose_generator import _project_slug
from generators.config_loader import (
    DEBUG_INTERNAL_PORT,
    _strip_json_comments,
    get_debug_instances,
    get_odoo_minor,
)
from generators.debug_ports import prune_debug_ports, resolve_debug_ports

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner

COMPOSE_FILE = "docker-compose.generated.yml"
CORE_REMOTE_ROOT = "/usr/lib/python3/dist-packages/odoo"
SRC_REMOTE_ROOT = "/home/odoo/src"
DEFAULT_DEST = os.path.join("src", "debug")
CORE_DIR_PREFIX = "core-"
COMPLETE_MARKER = ".complete"

# Runs inside the ephemeral container: stream only the *.py of the core.
_TAR_CMD = (
    f"cd {CORE_REMOTE_ROOT} && "
    "find . -name '*.py' -not -path '*/__pycache__/*' | tar -cf - -T -"
)


class DebugSetupError(Exception):
    """User-facing failure (message printed, exit code 1)."""


# ============================================================
# Core extraction
# ============================================================


def _within(base_path: str, path: str) -> bool:
    base = os.path.realpath(base_path)
    real = os.path.realpath(path)
    return os.path.commonpath([base, real]) == base


def _safe_member_path(name: str) -> str | None:
    name = name[2:] if name.startswith("./") else name
    parts = name.split("/")
    if not name or name.startswith("/") or ".." in parts or "__pycache__" in parts:
        return None
    return name if name.endswith(".py") else None


def _make_read_only(root: str) -> None:
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for f in filenames:
            os.chmod(os.path.join(dirpath, f), 0o444)
        os.chmod(dirpath, 0o555)


def _rmtree_force(path: str) -> None:
    def _fix(func, p, _exc):
        os.chmod(os.path.dirname(p), stat.S_IRWXU)
        os.chmod(p, stat.S_IRWXU)
        func(p)

    for dirpath, dirnames, _ in os.walk(path):
        os.chmod(dirpath, stat.S_IRWXU)
    shutil.rmtree(path, onerror=_fix)


def _image_tag(base_path: str, config: dict, inst: str) -> str:
    version = config["instances"][inst]["odoo_version"]
    return f"local_odoo_{_project_slug(base_path)}_{inst}:{get_odoo_minor(version)}"


def extract_core(base_path: str, config: dict, inst: str, dest_parent: str) -> str:
    """Extract the core of ``inst`` under ``dest_parent``; return the final
    directory (``core-<major>-<hash>``). Idempotent: identical content is
    reused, never re-written."""
    image = _image_tag(base_path, config, inst)
    probe = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True, text=True, cwd=base_path,
    )
    if probe.returncode != 0:
        raise DebugSetupError(
            f"La imagen '{image}' no existe. Corre './odoo build' primero "
            f"(debug-setup no construye ni arranca nada)."
        )

    os.makedirs(dest_parent, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix=".tmp-core-", dir=dest_parent)
    try:
        entries: list[tuple[str, str]] = []
        with tempfile.TemporaryFile() as err:
            proc = subprocess.Popen(
                ["docker", "compose", "-f", COMPOSE_FILE, "run", "--rm",
                 "--no-deps", "-T", "--entrypoint", "sh", f"odoo-{inst}",
                 "-c", _TAR_CMD],
                stdout=subprocess.PIPE, stderr=err, cwd=base_path,
            )
            try:
                with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
                    for member in tar:
                        rel = _safe_member_path(member.name) if member.isreg() else None
                        if rel is None:
                            continue
                        target = os.path.join(tmp, rel)
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        data = tar.extractfile(member).read()
                        with open(target, "wb") as out:
                            out.write(data)
                        entries.append((rel, hashlib.sha256(data).hexdigest()))
            except tarfile.TarError as exc:
                proc.kill()
                proc.wait()
                raise DebugSetupError(f"Salida de tar inválida desde '{inst}': {exc}")
            rc = proc.wait()
            if rc != 0 or not entries:
                err.seek(0)
                detail = err.read().decode(errors="replace").strip()[-600:]
                raise DebugSetupError(
                    f"No se pudo extraer el core de '{inst}' (código {rc}, "
                    f"{len(entries)} archivos).\n{detail}"
                )

        digest = hashlib.sha256()
        for rel, h in sorted(entries):
            digest.update(f"{rel}\0{h}\n".encode())
        major = get_odoo_minor(config["instances"][inst]["odoo_version"])
        final = os.path.join(dest_parent, f"{CORE_DIR_PREFIX}{major}-{digest.hexdigest()[:8]}")

        if os.path.exists(os.path.join(final, COMPLETE_MARKER)):
            _rmtree_force(tmp)
            return final
        if os.path.exists(final):  # leftover from an interrupted run
            _rmtree_force(final)
        open(os.path.join(tmp, COMPLETE_MARKER), "w").close()
        _make_read_only(tmp)
        os.chmod(dest_parent, os.stat(dest_parent).st_mode | stat.S_IWUSR)
        os.replace(tmp, final)
        return final
    except BaseException:
        if os.path.exists(tmp):
            _rmtree_force(tmp)
        raise


# ============================================================
# Editors (registry: name -> writer)
# ============================================================


def _zed_scenario(inst: str, port: int, core_rel: str) -> dict:
    return {
        "label": f"Odoo {inst} (attach)",
        "adapter": "Debugpy",
        "request": "attach",
        "connect": {"host": "127.0.0.1", "port": port},
        "justMyCode": False,
        "pathMappings": [
            # Core FIRST: src/debug lives inside src, first match wins.
            {"localRoot": "${ZED_WORKTREE_ROOT}/" + core_rel, "remoteRoot": CORE_REMOTE_ROOT},
            {"localRoot": "${ZED_WORKTREE_ROOT}/src", "remoteRoot": SRC_REMOTE_ROOT},
        ],
    }


_ZED_LABEL_RE = re.compile(r"^Odoo (.+?) \(attach\)")


def write_zed_config(base_path: str, targets: list[dict], prune: bool = False,
                     active: set[str] | None = None):  # EDITORS signature
    """Merge managed scenarios into ``.zed/debug.json``.

    ``targets``: [{"instance", "port", "core_rel"}]. Only scenarios whose
    label starts with ``Odoo <inst> (attach)`` are managed; everything else
    is preserved. With ``prune``, managed-looking scenarios of instances not
    in ``active`` (current debug instances) are dropped too.
    Returns ``(path, referenced_core_dirs)``.
    """
    path = os.path.join(base_path, ".zed", "debug.json")
    scenarios: list = []
    original = None
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            original = f.read()
        if original.strip():
            try:
                scenarios = json.loads(_strip_json_comments(original))
            except ValueError as exc:
                raise DebugSetupError(
                    f"No pude leer {path} ({exc}). Solo entiendo JSON con "
                    f"comentarios '//' (sin '/* */' ni comas finales). No lo "
                    f"modifiqué: corrígelo a mano o quítalo y vuelve a correr."
                )
            if not isinstance(scenarios, list):
                raise DebugSetupError(f"{path} debe contener una lista de escenarios.")

    def _managed_by(label, inst):
        return isinstance(label, str) and (
            label == f"Odoo {inst} (attach)"
            or label.startswith(f"Odoo {inst} (attach) ")
        )

    names = {t["instance"] for t in targets}
    fresh = {t["instance"]: _zed_scenario(t["instance"], t["port"], t["core_rel"]) for t in targets}
    result: list = []
    placed: set[str] = set()
    for sc in scenarios:
        label = sc.get("label") if isinstance(sc, dict) else None
        owner = next((n for n in names if _managed_by(label, n)), None)
        if owner:
            if owner not in placed:
                result.append(fresh[owner])
                placed.add(owner)
            continue
        if prune and isinstance(label, str):
            m = _ZED_LABEL_RE.match(label)
            if m and m.group(1) not in (active or names):
                continue
        result.append(sc)
    result += [fresh[t["instance"]] for t in targets if t["instance"] not in placed]

    new_text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if original is not None and original != new_text:
        shutil.copyfile(path, path + ".bak")
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)

    referenced = set()
    for sc in result:
        for pm in (sc.get("pathMappings", []) if isinstance(sc, dict) else []):
            root = pm.get("localRoot", "") if isinstance(pm, dict) else ""
            base = os.path.basename(root.rstrip("/"))
            if base.startswith(CORE_DIR_PREFIX):
                referenced.add(base)
    return path, referenced


EDITORS = {
    "zed": write_zed_config,
}


# ============================================================
# Entry point
# ============================================================


def debug_setup(
    runner: "Runner",
    config: dict,
    base_path: str,
    instance: str | None = None,
    dest: str | None = None,
    editor: str = "zed",
    prune: bool = False,
) -> int:
    try:
        return _debug_setup(runner, config, base_path, instance, dest, editor, prune)
    except DebugSetupError as exc:
        runner.error(f"Error: {exc}")
        return 1


def _debug_setup(runner, config, base_path, instance, dest, editor, prune) -> int:
    if editor not in EDITORS:
        raise DebugSetupError(
            f"Editor '{editor}' no soportado. Disponibles: {', '.join(sorted(EDITORS))}"
        )

    debug_names = get_debug_instances(config)
    if instance:
        if instance not in config["instances"]:
            raise DebugSetupError(
                f"La instancia '{instance}' no existe (o está deshabilitada) en instances.json"
            )
        if instance not in debug_names:
            raise DebugSetupError(
                f"La instancia '{instance}' no tiene \"debug\": true en instances.json"
            )
        targets_names = [instance]
    else:
        targets_names = debug_names
    if not targets_names and not prune:
        raise DebugSetupError(
            "Ninguna instancia tiene \"debug\": true en instances.json."
        )

    dest_parent = os.path.abspath(
        os.path.join(base_path, dest if dest else DEFAULT_DEST)
    )
    if not _within(base_path, dest_parent):
        raise DebugSetupError(
            f"--dest debe quedar dentro del proyecto ({base_path}): el editor "
            f"solo enlaza breakpoints a archivos del worktree. Recibí: {dest_parent}"
        )

    ports = resolve_debug_ports(base_path, config)
    compose_path = os.path.join(base_path, COMPOSE_FILE)
    compose_text = ""
    if os.path.exists(compose_path):
        with open(compose_path, "r", encoding="utf-8") as f:
            compose_text = f.read()

    targets = []
    for name in targets_names:
        port = ports[name]
        runner.info(f"→ {name}: extrayendo el core real desde su contenedor...")
        core_dir = extract_core(base_path, config, name, dest_parent)
        core_rel = os.path.relpath(core_dir, base_path)
        runner.info(f"  core: {core_rel}")
        if f"127.0.0.1:{port}:{DEBUG_INTERNAL_PORT}" not in compose_text:
            runner.warn(
                f"  '{name}' aún no publica el puerto {port} en el compose "
                f"generado: corre './odoo build' y recrea el contenedor."
            )
        targets.append({"instance": name, "port": port, "core_rel": core_rel})

    config_path, referenced = EDITORS[editor](
        base_path, targets, prune, set(debug_names)
    )
    runner.info(f"✓ {editor}: {os.path.relpath(config_path, base_path)} actualizado")

    if prune:
        for p in prune_debug_ports(base_path, config):
            runner.info(f"  puerto de '{p}' olvidado (ya no es debug)")
        if os.path.isdir(dest_parent):
            for entry in sorted(os.listdir(dest_parent)):
                if entry.startswith(CORE_DIR_PREFIX) and entry not in referenced:
                    _rmtree_force(os.path.join(dest_parent, entry))
                    runner.info(f"  core huérfano eliminado: {entry}")

    for t in targets:
        runner.info(f"  Odoo {t['instance']} (attach) → 127.0.0.1:{t['port']}")
    runner.info(
        "Recuerda: usa Detach (no Stop/Rerun) y no abras conexiones vacías al "
        "puerto de debug. Ver scripts/README.md."
    )
    return 0
