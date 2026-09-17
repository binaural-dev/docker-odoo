"""Sync /etc/hosts with the local subdomains declared in ``instances.json``.

This wraps :mod:`scripts.odoo_hosts` so the same logic is available from
the CLI dispatcher (and therefore from the TUI). The actual file write
still requires root; the CLI surfaces the right command to run.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner

BASE_PATH = Path(__file__).resolve().parents[3]
INSTANCES_FILE = BASE_PATH / "instances.json"
SCRIPT_PATH = BASE_PATH / "scripts" / "odoo_hosts"
HOSTS_FILE = Path("/etc/hosts")
SENTINEL = "# odoo-managed"


def _load_config() -> dict:
    with INSTANCES_FILE.open("r") as f:
        return json.load(f)


def _expected_subdomains(config: dict) -> list[str]:
    """Same logic as ``scripts/odoo_hosts.collect_subdomains``."""
    subs: list[str] = []
    for inst_name, inst_conf in config.get("instances", {}).items():
        if inst_conf.get("enabled", True):
            subs.append(f"{inst_name}.local")
    if config.get("pgadmin", {}).get("enabled", False):
        subs.append("pgadmin.local")
    if config.get("mailhog", {}).get("enabled", False):
        subs.append("mailhog.local")
    return subs


def _current_hosts_block() -> str:
    """Return the currently managed block in /etc/hosts, or ''."""
    if not HOSTS_FILE.exists():
        return ""
    contents = HOSTS_FILE.read_text()
    pattern = re.compile(
        rf"^{re.escape(SENTINEL)}\n(?:.*\n)*?\n",
        re.MULTILINE,
    )
    match = pattern.search(contents)
    return match.group(0) if match else ""


def _parse_block_hosts(block: str) -> set[str]:
    hosts: set[str] = set()
    for line in block.splitlines():
        if line.startswith(SENTINEL) or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            hosts.add(parts[1])
    return hosts


def hosts_status(runner: "Runner", config: dict) -> None:
    """Compare /etc/hosts against the expected set and report diffs.

    Used by the TUI to surface a warning when the host file is out of
    sync. Never raises; never writes.
    """
    expected = set(_expected_subdomains(config))
    current = _parse_block_hosts(_current_hosts_block())

    missing = sorted(expected - current)
    extra = sorted(current - expected)

    runner.info("\n=== Estado de /etc/hosts ===\n")
    if not expected:
        runner.info("  (ningún subdominio configurado en instances.json)\n")
    if not missing and not extra:
        runner.info("  ✅ Sincronizado. {} subdominio(s) activo(s).\n".format(len(expected)))
    else:
        if missing:
            runner.info(f"  ⚠ Faltan {len(missing)} subdominio(s):\n")
            for s in missing:
                runner.info(f"    - {s}\n")
        if extra:
            runner.info(f"  ⚠ Sobran {len(extra)} subdominio(s):\n")
            for s in extra:
                runner.info(f"    - {s}\n")
    runner.info(
        "\n  Para sincronizar, corré (con sudo):\n"
        "      sudo ./odoo hosts apply\n\n"
    )


def hosts_show(runner: "Runner", config: dict) -> None:
    """Print the subdomains that *should* be in /etc/hosts."""
    expected = _expected_subdomains(config)
    runner.info("\nSubdominios declarados en instances.json:\n")
    if not expected:
        runner.info("  (ninguno)\n")
    else:
        for s in expected:
            runner.info(f"  - {s}\n")
    runner.info("\n")


def hosts_apply(runner: "Runner", config: dict) -> int:
    """Apply the current subdomains to /etc/hosts via the helper script.

    The script needs root; if we are not root we hand the user the exact
    command to run and exit non-zero.
    """
    if os.geteuid() == 0:
        cmd = [sys.executable, str(SCRIPT_PATH)]
    else:
        runner.warn(
            "\n⚠ /etc/hosts requiere root. Corré manualmente con sudo:\n"
            f"      sudo {sys.executable} {SCRIPT_PATH}\n\n"
        )
        return 1

    runner.info(f"\n→ Ejecutando: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    return result.returncode


def hosts_dry_run(runner: "Runner", config: dict) -> None:
    """Delegate to the helper script with --dry-run."""
    cmd = [sys.executable, str(SCRIPT_PATH), "--dry-run"]
    runner.info(f"\n→ Dry-run: {' '.join(cmd)}\n")
    subprocess.run(cmd)
