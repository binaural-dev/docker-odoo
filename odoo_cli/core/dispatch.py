"""Dispatch: maps argparse args to action functions.

The same dispatch table is used by both ``./odoo`` and ``./odoo tui``.
The function takes a :class:`odoo_cli.core.Runner`, a parsed argparse
namespace, and the loaded config; it returns the process exit code.

Why a separate dispatch module?
-------------------------------
The dispatch is the "wiring" between argparse (which subcommand did
the user pick?) and the action functions in
:mod:`odoo_cli.core.actions`. Keeping it in its own module:

  * Makes the same dispatch reusable from the TUI (when the TUI
    invokes an action through a ``TextualRunner`` instead of the
    CLI's argparse flow).
  * Makes the test surface small: a test can call
    ``dispatch(runner, args, config)`` and assert on the runner's
    recorded calls.

Note on the special ``tui`` action
---------------------------------
The ``tui`` action does NOT call into :mod:`odoo_cli.core.actions`.
It launches the Textual app directly via :mod:`tui.__main__`. This
is a deliberate split: the TUI is its own program; the ``./odoo tui``
subcommand is a thin entry point.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

    from odoo_cli.core.runner import Runner

from odoo_cli.core.actions.access import (
    list_containers,
    psql_connect,
    run_bash,
    show_logs,
)
from odoo_cli.core.actions.hosts import (
    hosts_apply,
    hosts_dry_run,
    hosts_show,
    hosts_status,
)
from odoo_cli.core.actions.lifecycle import (
    build_odoo,
    fix_filestore,
    remove_odoo,
    restart_odoo,
    start_odoo,
    stop_odoo,
)
from odoo_cli.core.actions.maintenance import init_addons, sync
from odoo_cli.core.actions.modules import reset_password, update
from odoo_cli.core.prompts import (
    prompt_for_branch,
    prompt_for_database,
    prompt_for_instance,
    prompt_for_modules,
    prompt_for_repos,
    prompt_for_user,
)


# ============================================================
# Subcommand table
# ============================================================


# Subcommands that accept a positional instance argument (with the
# usual "leave it empty to mean all instances" semantics). The
# dispatch resolves ``args.instance`` to a concrete name before
# calling the action.
_INSTANCE_AWARE_ACTIONS = {
    "start", "stop", "restart", "logs", "remove",
    "fix-files", "init", "bash", "psql", "pw", "update",
}


def _resolve_instance(runner: "Runner", config: dict, args: "Namespace") -> str | None:
    """Pick the instance for ``args.action``.

    Mirrors the legacy CLI's behaviour:

      * If the user already passed ``args.instance``, use it.
      * For ``pw -d <dbname>``, search the instances whose container
        has that DB; with one match, use it silently; with multiple,
        ask the user which one.
      * Otherwise, prompt for an instance (using the action's
        ``allow_all`` set inside :func:`prompt_for_instance`).
    """
    if getattr(args, "instance", None) is not None:
        return args.instance

    if args.action == "pw" and getattr(args, "d", None):
        from odoo_cli.core.instance import find_instances_with_db

        candidatas = find_instances_with_db(config, args.d)
        if len(candidatas) == 1:
            runner.info(
                f"\nℹ La base de datos '{args.d}' solo existe en "
                f"la instancia '{candidatas[0]}'. Usando esa.\n"
            )
            return candidatas[0]
        if len(candidatas) > 1:
            from odoo_cli.core.prompts import prompt_selection

            options = [(name, name) for name in candidatas]
            runner.info(
                f"\nLa base de datos '{args.d}' existe en varias "
                f"instancias. Selecciona una:"
            )
            return prompt_selection(
                runner,
                options,
                f"Selecciona instancia que contiene '{args.d}'",
            )

    return prompt_for_instance(runner, config, args.action)


# ============================================================
# Public entry point
# ============================================================


def dispatch(
    runner: "Runner", args: "Namespace", config: dict, base_path: str
) -> int:
    """Run the action selected by ``args.action``.

    Returns the process exit code. ``0`` means success; any non-zero
    return is the action's own signal (mostly via
    :func:`sys.exit` for the failure-summary cases).

    ``base_path`` is the project root (``./odoo``'s ``BASE_PATH``).
    It's used for the few actions that need to chdir into a custom
    repo (``sync``) or run a sibling script (``new``).
    """
    # Special: the TUI launches a different program entirely.
    if args.action == "tui":
        from tui.__main__ import main as tui_main

        # ``tui_main()`` reads ``sys.argv`` itself. We're being called
        # from inside ``./odoo``'s ``main()``, so ``sys.argv`` is
        # ``["./odoo", "tui", ...]`` — we must strip the leading
        # ``["./odoo", "tui"]`` before handing control over, otherwise
        # the TUI's argparse will reject the positional ``tui``.
        import sys as _sys
        saved_argv = _sys.argv
        _sys.argv = [saved_argv[0]] + [
            a for a in saved_argv[1:] if a != "tui"
        ]
        try:
            return tui_main()
        finally:
            _sys.argv = saved_argv

    # Subcommands that need an instance resolved first.
    if args.action in _INSTANCE_AWARE_ACTIONS:
        args.instance = _resolve_instance(runner, config, args)

    if args.action == "build":
        build_odoo(runner, config, args.no_cache)

    elif args.action == "start":
        start_odoo(runner, config, args.instance)

    elif args.action == "stop":
        stop_odoo(runner, config, args.instance)

    elif args.action == "restart":
        restart_odoo(runner, config, args.instance)

    elif args.action == "bash":
        run_bash(runner, config, args.instance)

    elif args.action == "logs":
        show_logs(runner, config, args.instance)

    elif args.action == "list":
        list_containers(runner, config)

    elif args.action == "remove":
        remove_odoo(runner, config, args.instance)

    elif args.action == "fix-files":
        fix_filestore(runner, config, args.instance)

    elif args.action == "psql":
        if getattr(args, "d", None) is None:
            args.d = prompt_for_database(runner, config, args.instance)
        psql_connect(runner, config, args.instance, args.d)

    elif args.action == "pw":
        if getattr(args, "d", None) is None:
            args.d = prompt_for_database(runner, config, args.instance)
        if getattr(args, "l", None) is None:
            args.l = prompt_for_user(runner, config, args.instance, args.d)
        reset_password(
            runner, config, args.instance, args.d, args.l, args.password
        )

    elif args.action == "update":
        if args.instance is None:
            args.instance = prompt_for_instance(runner, config, "update")
        if getattr(args, "d", None) is None:
            args.d = prompt_for_database(
                runner, config, args.instance, allow_all=True
            )
        if getattr(args, "m", None) is None:
            args.m = prompt_for_modules(runner, config, args.instance)
        update(runner, config, args.instance, args.d, args.m)

    elif args.action == "init":
        init_addons(runner, config, args.instance)

    elif args.action == "sync":
        if getattr(args, "r", None) is None:
            args.r = prompt_for_repos(runner)
        if getattr(args, "b", None) is None:
            args.b = prompt_for_branch(
                runner, args.r if isinstance(args.r, str) else None
            )
        sync(runner, args.r, args.b, show=args.v)

    elif args.action == "validate-instances":
        runner.info("\n✅ El archivo instances.json es válido.\n")

    elif args.action == "hosts":
        hosts_mode = getattr(args, "hosts_mode", "status")
        if hosts_mode == "status":
            hosts_status(runner, config)
        elif hosts_mode == "show":
            hosts_show(runner, config)
        elif hosts_mode == "apply":
            return hosts_apply(runner, config)
        elif hosts_mode == "dry-run":
            hosts_dry_run(runner, config)
        else:
            runner.error(f"Modo de hosts desconocido: {hosts_mode!r}")
            return 2

    elif args.action == "new":
        cmd = [
            sys.executable,
            os.path.join(base_path, "scripts", "create_instance.py"),
        ]
        if getattr(args, "name", None):
            cmd.append(args.name)
        if getattr(args, "repo", None):
            cmd.append(args.repo)
        if getattr(args, "branch", None):
            cmd.append(args.branch)
        if getattr(args, "version", None):
            cmd.append(args.version)
        subprocess.run(cmd)

    else:
        runner.error(f"Acción desconocida: {args.action!r}")
        return 2

    return 0


__all__ = ["dispatch", "_INSTANCE_AWARE_ACTIONS"]
