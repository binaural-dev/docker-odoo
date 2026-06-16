"""Maintenance actions: init addons, sync repos.

These are the "I just want to set up / refresh the local source tree"
actions. They don't talk to the docker daemon directly; they touch
the filesystem (the ``src/`` directory tree) and the local git
remotes of each custom repo.

``BASE_PATH`` is taken from ``os.getcwd()`` (the ``./odoo`` launcher
does ``os.chdir(BASE_PATH)`` at the top of ``main()``).
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner

from generators.config_loader import resolve_instance_config


# ============================================================
# init: discover / report the addons state
# ============================================================


def init_addons(runner: "Runner", config: dict, instance: str | None) -> None:
    """Inspect the addons state for ``instance`` (or all instances).

    Reports which addon paths already exist locally and which ones
    need to be cloned. This is a *report* action: it does not clone
    anything (the legacy ``./odoo init`` behavior).
    """
    if instance:
        runner.info(
            f"\n=== 📦 INICIALIZANDO ADDONS EN: {instance.upper()} ===\n"
        )
    else:
        runner.info(
            "\n=== 📦 INICIALIZANDO ADDONS EN TODAS LAS INSTANCIAS ===\n"
        )

    instances_to_init = (
        [instance] if instance else list(config["instances"].keys())
    )
    base_path = os.getcwd()

    for inst_name in instances_to_init:
        inst_conf = config["instances"][inst_name]
        odoo_conf = resolve_instance_config(inst_conf, config)
        addons = odoo_conf.get("addons", [])
        odoo_version = inst_conf["odoo_version"]

        runner.info(
            f"\n=== Init para instancia: {inst_name} (Odoo {odoo_version}) ==="
        )
        for addon_path in addons:
            # addon_path is like "src/enterprise" or "src/custom/<instance-name>"
            local_path = os.path.join(base_path, addon_path)
            if os.path.isdir(local_path):
                runner.info(f"  ✓ {addon_path} ya existe")
            else:
                runner.info(
                    f"  → {addon_path} no encontrado. Créalo manualmente "
                    f"o clona el repositorio correspondiente en {local_path}"
                )

    runner.info("")


# ============================================================
# sync: refresh custom repos and their submodules
# ============================================================


def sync(
    runner: "Runner",
    repo_names: str | list[str],
    branch: str,
    show: bool = False,
) -> None:
    """Sync the named custom repos to ``branch``.

    For each repo we:
      1. ``git stash`` any local changes (so the checkout doesn't
         fail on dirty trees).
      2. ``git checkout <branch>``.
      3. ``git pull origin <branch>``.
      4. ``git submodule update --init --recursive``.

    With ``show=True`` the git output is left visible; otherwise it
    is silenced (``subprocess.DEVNULL``) so the user only sees our
    progress messages.
    """
    runner.info(
        f"\n=== 🔄 SINCRONIZANDO REPOSITORIOS (Rama: {branch}) ===\n"
    )
    if isinstance(repo_names, str):
        repo_names = [repo_names]

    base_path = os.getcwd()

    for repo_name in repo_names:
        repo_path = os.path.join(base_path, "src", "custom", repo_name)
        if not os.path.isdir(repo_path):
            runner.error(
                f"Error: Repositorio '{repo_name}' no encontrado en src/custom/"
            )
            continue

        runner.info(f"\n=== Sincronizando {repo_name} (Rama: {branch}) ===")
        os.chdir(repo_path)

        stdout = subprocess.DEVNULL if not show else None

        try:
            runner.info("→ Guardando cambios locales (stash)...")
            subprocess.run(["git", "stash"], stdout=stdout)

            runner.info(f"→ Cambiando a rama {branch}...")
            subprocess.run(["git", "checkout", branch], stdout=stdout)

            runner.info("→ Trayendo últimos cambios (pull)...")
            subprocess.run(["git", "pull", "origin", branch], stdout=stdout)

            runner.info("→ Actualizando submódulos (init --recursive)...")
            # Using --init --recursive to ensure all levels are updated
            subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"],
                stdout=stdout,
            )

            runner.info(f"✅ {repo_name} sincronizado.")
        except Exception as e:
            runner.error(f"❌ Error sincronizando {repo_name}: {e}")
        finally:
            os.chdir(base_path)


__all__ = [
    "init_addons",
    "sync",
]
