#!/usr/bin/env python3
"""Normalize ``instances.json`` to the flat schema expected by ``load_config``.

Background
----------
``load_config`` (``.resources/generators/config_loader.py``) requires the
top-level sections ``odoo_configs``, ``databases`` and ``instances`` to live
at the **root** of the JSON document:

    {
        "odoo_configs": { ... },
        "databases":    { ... },
        "instances":    { ... },
        "pgadmin":      { ... },   # optional
        "mailhog":      { ... }    # optional
    }

Some teams (rightly) want to keep their config in a single nested block
during development, ending up with a structure like:

    {
        "odoo_configs": {
            "19.0_full": { ... },
            "databases": { ... },
            "instances": { ... },
            "pgadmin":   { ... },
            "mailhog":   { ... }
        }
    }

That nested layout makes ``load_config`` raise:

    ValueError: Sección 'databases' requerida en instances.json

This script detects the nested layout and rewrites the file with the
sections hoisted to the root.

What it does
------------
1. Reads ``instances.json`` (tolerating ``//`` line comments via the same
   helper used by ``config_loader``).
2. If a required section is found **inside** ``odoo_configs``, it is moved
   to the root.
3. Writes the result back as a clean, indented JSON (no ``//`` comments).
4. **Always** creates a timestamped backup at
   ``instances.json.bak.YYYYMMDD-HHMMSS`` before writing.

Usage
-----
::

    python3 scripts/fix_instances_json.py            # auto-detect path
    python3 scripts/fix_instances_json.py --dry-run  # print result, no writes
    python3 scripts/fix_instances_json.py --path /custom/path/instances.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure the local ``generators`` package is importable so we can reuse
# ``_strip_json_comments``. The script is designed to be runnable from
# anywhere, so we anchor the path to the repo root.
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / ".resources"))

from generators.config_loader import _strip_json_comments  # noqa: E402


REQUIRED_SECTIONS = ("odoo_configs", "databases", "instances")
OPTIONAL_SECTIONS = ("pgadmin", "mailhog")
HOISTABLE_SECTIONS = REQUIRED_SECTIONS + OPTIONAL_SECTIONS


def _load_raw(path: Path) -> dict:
    """Read JSON (with // comment tolerance) and return the parsed dict."""
    raw = path.read_text(encoding="utf-8")
    return json.loads(_strip_json_comments(raw))


def _is_nested(data: dict) -> bool:
    """Return True if any hoistable section lives inside ``odoo_configs``."""
    odoo_configs = data.get("odoo_configs")
    if not isinstance(odoo_configs, dict):
        return False
    return any(section in odoo_configs for section in HOISTABLE_SECTIONS)


def _hoist(data: dict) -> tuple[dict, list[str]]:
    """Move nested sections to the root. Returns (new_data, moved_sections)."""
    new_data = dict(data)
    odoo_configs = dict(new_data.get("odoo_configs", {}))
    moved: list[str] = []

    for section in HOISTABLE_SECTIONS:
        if section in odoo_configs:
            new_data[section] = odoo_configs.pop(section)
            moved.append(section)

    new_data["odoo_configs"] = odoo_configs
    return new_data, moved


def _backup(path: Path) -> Path:
    """Copy the file to a timestamped sibling. Returns the backup path."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".bak.{ts}")
    backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize instances.json to the flat schema.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=REPO_ROOT / "instances.json",
        help="Path to instances.json (default: <repo>/instances.json).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the would-be result without writing anything.",
    )
    args = parser.parse_args()

    path: Path = args.path
    if not path.exists():
        print(f"❌ Error: {path} no existe.")
        return 1

    print(f"📂 Leyendo {path} ...")
    try:
        data = _load_raw(path)
    except json.JSONDecodeError as e:
        print(f"❌ Error de JSON en línea {e.lineno}, columna {e.colno}: {e.msg}")
        print("   (Quita los // de la línea problemática o corrige la sintaxis.)")
        return 2

    if not _is_nested(data):
        print("✅ El archivo ya tiene la estructura plana correcta. Nada que hacer.")
        return 0

    new_data, moved = _hoist(data)

    print("🔍 Secciones anidadas detectadas dentro de 'odoo_configs':")
    for section in moved:
        print(f"   • {section}")

    if args.dry_run:
        print("\n--- DRY RUN: resultado que se escribiría ---")
        print(json.dumps(new_data, indent=2, ensure_ascii=False))
        return 0

    backup = _backup(path)
    print(f"💾 Backup creado: {backup}")

    path.write_text(
        json.dumps(new_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"✅ Archivo normalizado: {path}")
    print("   (Los // comentarios se perdieron al re-escribir; el archivo ahora es JSON estándar.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
