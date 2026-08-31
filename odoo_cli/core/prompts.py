"""Interactive prompts for the CLI.

The prompts here are the "ask the user" surface: which instance,
which database, which modules to update, etc. They consume a
:class:`odoo_cli.core.Runner` for the simpler messages (the
"no se encontraron modulos" notice, the free-form branch prompt),
and the big interactive grid menu (:func:`prompt_selection`) keeps
its ``tty.setraw`` reading and ``sys.stdout.write`` rendering
verbatim — abstracting that across runners is out of scope for this
batch.

Why ``runner`` if the menu bypasses it?
---------------------------------------
Two reasons:

  1. The fallback path (non-TTY stdin, e.g. CI / piped input) and
     the helper prompts (branch, user, modules) do go through the
     runner, so they can be tested with a ``FakeRunner``.
  2. The next refactor will swap the tty loop for a Textual widget
     by adding a parallel implementation of the same prompts in a
     future ``TextualPrompts`` class that uses the runner's
     ``select_one``/``select_many`` methods.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo_cli.core.runner import Runner

from odoo_cli.core.instance import (
    get_custom_modules,
    get_custom_repos,
    get_databases,
    get_users,
)


# ============================================================
# Interactive grid menu (verbatim from the legacy ./odoo)
# ============================================================


def prompt_selection(
    runner: "Runner",
    options: list[tuple[str, str]],
    title: str,
    multi: bool = False,
):
    """Generic interactive selection menu.

    ``options`` is a list of ``(label, value)`` tuples. ``title`` is
    shown above the menu. ``multi=True`` enables multi-select (Space
    to toggle, Enter to confirm).

    Returns the selected value (or list of values if multi).

    Why we keep tty.setraw here
    ---------------------------
    The grid menu reads individual key presses (arrow keys, Space,
    'A' for all) directly from stdin with termios in raw mode. That's
    hard to do through a Runner abstraction without changing the UX.
    The verbatim code is preserved for now; the fallback path (no
    TTY) goes through the runner (``runner.prompt_text``) so the
    code is at least testable end-to-end.
    """
    if not options:
        return [] if multi else None

    def fallback_prompt():
        runner.info(f"\n{title}:")
        for i, (text, _) in enumerate(options, 1):
            runner.info(f"  {i}. {text}")
        if multi:
            runner.info(
                "  (Ingresa números separados por coma, "
                "ej: 1,3,4 o 'all' para todos)"
            )
        while True:
            try:
                choice = runner.prompt_text("Selección").strip().lower()
                if not choice:
                    if multi:
                        return []
                    continue
                if multi and choice == "all":
                    runner.info(f"✔ {title}: todos")
                    return [val for _, val in options]
                if multi:
                    indices = [
                        int(x.strip())
                        for x in choice.replace(",", " ").split()
                        if x.strip()
                    ]
                    selected = []
                    for idx in indices:
                        if 1 <= idx <= len(options):
                            selected.append(options[idx - 1][1])
                    labels = ", ".join(
                        options[idx - 1][0] for idx in indices
                        if 1 <= idx <= len(options)
                    )
                    runner.info(f"✔ {title}: {labels or '(ninguna)'}")
                    return selected
                idx = int(choice)
                if 1 <= idx <= len(options):
                    runner.info(f"✔ {title}: {options[idx - 1][0]}")
                    return options[idx - 1][1]
                runner.info("Selección inválida.")
            except ValueError:
                runner.info("Por favor ingresa un valor válido.")
            except (KeyboardInterrupt, EOFError):
                runner.info("\nOperación cancelada.")
                sys.exit(0)

    if not sys.stdin.isatty():
        return fallback_prompt()

    try:
        import tty
        import termios
    except ImportError:
        return fallback_prompt()

    def getch():
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
        except Exception:
            return sys.stdin.read(1)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch += sys.stdin.read(2)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    current_idx = 0
    selected_indices = set()
    input_buffer = ""

    # Grid settings
    try:
        term_width = os.get_terminal_size().columns
    except Exception:
        term_width = 80

    max_text_len = max(len(text) for text, _ in options)
    item_width = max_text_len + 10  # prefix + num + text + spacing
    num_cols = max(1, term_width // item_width)
    num_rows = (len(options) + num_cols - 1) // num_cols
    lines_to_clear = num_rows + 1

    # The interactive grid below reads from stdin in raw mode and
    # writes ANSI escape codes directly to stdout. We deliberately
    # do NOT route these through ``runner.info`` because:
    #   * the menu is redrawn tens of times per second;
    #   * the renderer uses cursor positioning that assumes it
    #     owns stdout;
    #   * wrapping the per-frame output in ``runner.info`` would
    #     prefix every frame with an ANSI color code and break the
    #     cursor math.
    # The non-TTY fallback above is the runner-aware path.
    print(f"\n{title}:")

    def render_menu():
        sys.stdout.write("\r")
        for row in range(num_rows):
            line_content = ""
            for col in range(num_cols):
                idx = row + col * num_rows
                if idx < len(options):
                    text, _ = options[idx]
                    num = f"{idx + 1:2d}. "
                    prefix = "❯ " if idx == current_idx else "  "
                    if multi:
                        mark = "[x] " if idx in selected_indices else "[ ] "
                        prefix += mark

                    item = f"{prefix}{num}{text}"
                    # Padding to maintain columns
                    padding = " " * (item_width - len(item))

                    if idx == current_idx:
                        line_content += f"\033[92m{item}\033[0m{padding}"
                    else:
                        line_content += f"{item}{padding}"

            sys.stdout.write(f"{line_content}\033[K\n")

        if multi:
            sys.stdout.write(
                f"\033[90m(Espacio: sel, Enter: ok, A: todos, N: ninguno)\033[0m\033[K"
            )
        else:
            sys.stdout.write(
                f"Opción (Número o flechas) [ {input_buffer} ]: \033[K"
            )
        sys.stdout.flush()

    sys.stdout.write("\033[?25l")  # Ocultar cursor
    try:
        render_menu()
        while True:
            ch = getch()
            if ch == "\x03":  # Ctrl+C
                raise KeyboardInterrupt
            elif ch in ("\r", "\n"):
                # Typing digits only moves the cursor (see the digit
                # branch below) — it never marks the item, unlike the
                # non-TTY fallback where typing a number selects it
                # outright. That mismatch is confusing in multi-select:
                # someone who types "54" and hits Enter expects item 54
                # marked, not silently skipped for lack of a Space. If
                # there's a pending typed number, treat confirming on it
                # as marking that item too.
                if multi and input_buffer:
                    try:
                        typed_idx = int(input_buffer)
                        if 1 <= typed_idx <= len(options):
                            selected_indices.add(typed_idx - 1)
                    except ValueError:
                        pass
                sys.stdout.write("\n")
                break
            elif ch == " ":  # Espacio
                if multi:
                    if current_idx in selected_indices:
                        selected_indices.remove(current_idx)
                    else:
                        selected_indices.add(current_idx)
            elif ch in ("a", "A"):
                if multi:
                    selected_indices = set(range(len(options)))
            elif ch in ("n", "N"):
                if multi:
                    selected_indices.clear()
            elif ch == "\x1b[A":  # Arriba
                current_idx = (current_idx - 1) % len(options)
                input_buffer = ""
            elif ch == "\x1b[B":  # Abajo
                current_idx = (current_idx + 1) % len(options)
                input_buffer = ""
            elif ch == "\x1b[C":  # Derecha
                current_idx = (current_idx + num_rows) % len(options)
                input_buffer = ""
            elif ch == "\x1b[D":  # Izquierda
                current_idx = (current_idx - num_rows) % len(options)
                input_buffer = ""
            elif ch in ("\x7f", "\b"):  # Backspace
                input_buffer = input_buffer[:-1]
                if input_buffer:
                    try:
                        num_val = int(input_buffer)
                        if 1 <= num_val <= len(options):
                            current_idx = num_val - 1
                    except ValueError:
                        pass
            elif len(ch) == 1 and ch.isdigit():
                new_buffer = input_buffer + ch
                try:
                    num_val = int(new_buffer)
                    if 1 <= num_val <= len(options):
                        input_buffer = new_buffer
                        current_idx = num_val - 1
                    else:
                        # Si el número completo no es válido,
                        # intentar solo con el último dígito
                        num_val = int(ch)
                        if 1 <= num_val <= len(options):
                            input_buffer = ch
                            current_idx = num_val - 1
                except ValueError:
                    pass

            # Regresar cursor arriba
            sys.stdout.write(f"\033[{lines_to_clear}F")
            render_menu()

        # Al salir, limpiar el menú de la pantalla para no ensuciar el log
        sys.stdout.write(f"\033[{lines_to_clear}A")  # Subir al inicio del menú
        for _ in range(lines_to_clear + 1):
            sys.stdout.write("\033[K\n")  # Limpiar línea y bajar
        sys.stdout.write(f"\033[{lines_to_clear + 1}F")  # Regresar arriba de todo

    except (Exception, KeyboardInterrupt):
        sys.stdout.write("\n\033[?25hOperación cancelada.\n")
        sys.exit(0)
    finally:
        sys.stdout.write("\033[?25h")  # Mostrar cursor

    if multi:
        chosen = [options[i] for i in sorted(selected_indices)]
    else:
        chosen = [options[current_idx]]

    # Dejar constancia en consola de lo elegido: el menú de arriba se
    # borra (para no ensuciar el log con el grid completo), pero sin
    # esta línea no quedaba ningún rastro de la selección tomada.
    labels = ", ".join(text for text, _ in chosen) if chosen else "(ninguna)"
    print(f"✔ {title}: {labels}")

    if multi:
        return [value for _, value in chosen]
    return chosen[0][1]


# ============================================================
# Domain-specific prompts
# ============================================================


# Actions where the prompt offers a "Todas las instancias" shortcut.
# Kept in sync with the legacy CLI (the dispatch elsewhere in this
# file relies on the same set).
_ALLOW_ALL_ACTIONS = {
    "start", "stop", "restart", "logs", "remove",
    "fix-files", "init",
}


def prompt_for_instance(
    runner: "Runner", config: dict, action: str
) -> str | None:
    """Ask the user which instance to act on.

    Returns the chosen instance name, or ``None`` if the user picked
    "Todas las instancias" (only offered for actions in
    :data:`_ALLOW_ALL_ACTIONS`).
    """
    instances = list(config.get("instances", {}).keys())
    if not instances:
        runner.info("No hay instancias configuradas.")
        sys.exit(1)

    allow_all = action in _ALLOW_ALL_ACTIONS

    options: list[tuple[str, str | None]] = []
    if allow_all:
        options.append(("Todas las instancias", None))
    for name in instances:
        options.append((name, name))

    return prompt_selection(
        runner,
        options,
        "Selecciona una instancia (Usa las flechas, números y Enter para confirmar)",
    )


def prompt_for_bulk_instances(
    runner: "Runner", full_config: dict, action: str
) -> list[str]:
    """Ask which instances to enable/disable, with multi-select.

    ``full_config`` must be the UNFILTERED config (``load_full_config``),
    not the ``enabled``-filtered one — otherwise a disabled instance
    could never be picked for ``./odoo enable``.
    """
    instances = list(full_config.get("instances", {}).keys())
    if not instances:
        runner.info("No hay instancias configuradas.")
        sys.exit(1)

    options = [(f"Todas ({len(instances)})", "__all__")] + [
        (name, name) for name in instances
    ]
    selected = prompt_selection(
        runner,
        options,
        f"Selecciona instancia(s) a {action} "
        "(Espacio para marcar, Enter para confirmar)",
        multi=True,
    )
    if not selected:
        runner.info(f"No se seleccionó ninguna instancia para {action}.")
        sys.exit(0)
    if "__all__" in selected:
        return instances
    return selected


def prompt_for_database(
    runner: "Runner", config: dict, instance: str, allow_all: bool = False
) -> str:
    """Ask the user which database to act on for ``instance``.

    With ``allow_all=True`` the menu also offers a special
    ``"all"`` option that the ``update`` action uses to fan out
    over every database.
    """
    databases = get_databases(config, instance)
    if not databases:
        all_hint = " (o 'all')" if allow_all else ""
        return runner.prompt_text(
            f"\nNo se pudieron auto-detectar bases de datos. "
            f"Ingresa el nombre de la base de datos para '{instance}'{all_hint}"
        ).strip()

    options: list[tuple[str, str]] = []
    if allow_all:
        options.append(("all (todas las bases de datos)", "all"))
    options.extend((db, db) for db in databases)
    return prompt_selection(
        runner,
        options,
        f"Selecciona base de datos para '{instance}'",
    )


def prompt_for_modules(
    runner: "Runner", config: dict, instance: str
) -> str:
    """Ask the user which modules to update.

    Returns a comma-joined list of module names. If the user picks
    nothing, falls back to ``"all"`` (the legacy CLI behavior).
    """
    modules = get_custom_modules(config, instance)
    if not modules:
        runner.info(
            f"\nNo se encontraron módulos custom en los addons de '{instance}'."
        )
        return "all"

    options = [(mod, mod) for mod in modules]
    selected = prompt_selection(
        runner,
        options,
        f"Selecciona módulos a actualizar para '{instance}' "
        "(Espacio para marcar, Enter para confirmar)",
        multi=True,
    )
    if not selected:
        return "all"
    return ",".join(selected)


def prompt_for_test_modules(
    runner: "Runner", config: dict, instance: str
) -> str:
    """Ask the user which modules to test.

    Unlike :func:`prompt_for_modules`, there's no valid "all" fallback
    for testing — if nothing gets selected, this exits with an error.
    """
    modules = get_custom_modules(config, instance)
    if not modules:
        runner.error(
            f"\nNo se encontraron módulos custom en los addons de '{instance}'."
        )
        sys.exit(1)

    options = [(mod, mod) for mod in modules]
    selected = prompt_selection(
        runner,
        options,
        f"Selecciona modulo(s) a testear para '{instance}' "
        "(Espacio para marcar, Enter para confirmar)",
        multi=True,
    )
    if not selected:
        runner.error("Debes seleccionar al menos un módulo.")
        sys.exit(1)
    return ",".join(selected)


def prompt_for_user(
    runner: "Runner", config: dict, instance: str, dbname: str
) -> str:
    """Ask the user which user login to reset the password for.

    Auto-detects the list of active users via
    :func:`odoo_cli.core.instance.get_users`. If that fails (no
    container, no DB, no users) falls back to free-form input.
    """
    users = get_users(config, instance, dbname)
    if not users:
        return runner.prompt_text(
            "\nNo se pudieron auto-detectar usuarios. "
            "Ingresa el login del usuario"
        ).strip()

    options = [(u, u) for u in users]
    return prompt_selection(
        runner, options, f"Selecciona usuario en '{dbname}'"
    )


def prompt_for_repos(runner: "Runner") -> list[str]:
    """Ask the user which custom repos to sync.

    Returns an empty list if there are no custom repos. The caller
    (the ``sync`` dispatch) is responsible for treating the empty
    list as a hard error or a no-op.
    """
    repos = get_custom_repos()
    if not repos:
        runner.info("\nNo se encontraron repositorios en src/custom/.")
        sys.exit(1)

    options = [(r, r) for r in repos]
    selected = prompt_selection(
        runner,
        options,
        "Selecciona repositorios para sincronizar "
        "(Espacio para marcar, Enter para confirmar)",
        multi=True,
    )
    if not selected:
        runner.info("No se seleccionó ningún repositorio.")
        sys.exit(0)
    return selected


def prompt_for_odoo_version(runner: "Runner", config: dict) -> str:
    """Ask which Odoo version to bulk-update projects for.

    Options come straight from ``instances.json`` (via
    :func:`generators.config_loader.get_unique_odoo_versions`) — no
    hardcoded version list to keep in sync.
    """
    from generators.config_loader import get_unique_odoo_versions

    versions = sorted(get_unique_odoo_versions(config))
    if not versions:
        runner.info("No hay versiones de Odoo configuradas en instances.json.")
        sys.exit(1)

    options = [(v, v) for v in versions]
    selected = prompt_selection(runner, options, "Selecciona la versión de Odoo")
    if not selected:
        runner.info("No se seleccionó ninguna versión.")
        sys.exit(0)
    return selected


def prompt_for_bulk_projects(
    runner: "Runner", config: dict, odoo_version: str
) -> list[str]:
    """Ask which projects on ``odoo_version`` to bulk-update.

    Multi-select over :func:`odoo_cli.core.instance.get_projects_for_version`,
    with an "Todos" shortcut prepended (mirrors the "Todas las instancias"
    entry in :func:`prompt_for_instance`) on top of the grid menu's own
    ``A``/``"all"`` shortcut.
    """
    from odoo_cli.core.instance import get_projects_for_version

    projects = get_projects_for_version(config, odoo_version)
    if not projects:
        runner.info(
            f"\nNo se encontraron proyectos en src/custom/ para Odoo {odoo_version}."
        )
        sys.exit(1)

    options = [(f"Todos ({len(projects)})", "__all__")] + [
        (p, p) for p in projects
    ]
    selected = prompt_selection(
        runner,
        options,
        f"Selecciona proyectos en Odoo {odoo_version} "
        "(Espacio para marcar, Enter para confirmar)",
        multi=True,
    )
    if not selected:
        runner.info("No se seleccionó ningún proyecto.")
        sys.exit(0)
    if "__all__" in selected:
        return projects
    return selected


def prompt_for_bulk_branch_origin(runner: "Runner") -> str | None:
    """Ask which base branch to move every project onto for a bulk update.

    Unlike :func:`prompt_for_branch_origin` (used by the single-project
    ``update-tags``, which always resolves to *some* branch and treats
    an empty answer as an error), an empty answer here is a valid,
    deliberate choice: it means every project keeps whatever branch
    it's already on instead of all being forced onto the same one —
    the N projects in a bulk batch may not even share a common branch
    name across different clients. Always asked explicitly (never
    silently defaulted) so leaving it blank is something the user
    chose, not something that happened without them noticing.
    """
    branch = runner.prompt_text(
        "\n¿Rama base para mover CADA proyecto antes de ramificar "
        "(checkout + pull)? Dejá vacío para que cada proyecto se quede "
        "en la rama en la que ya está (no se lo mueve)",
        default="",
    ).strip()
    return branch or None


def prompt_for_project(runner: "Runner") -> str:
    """Ask the user which project (``src/custom/<proyecto>``) to target.

    Single-select, unlike :func:`prompt_for_repos` (multi-select for
    ``sync``) — ``update-tags`` operates on one project at a time.
    """
    repos = get_custom_repos()
    if not repos:
        runner.info("\nNo se encontraron proyectos en src/custom/.")
        sys.exit(1)

    options = [(r, r) for r in repos]
    selected = prompt_selection(runner, options, "Selecciona el proyecto")
    if not selected:
        runner.info("No se seleccionó ningún proyecto.")
        sys.exit(0)
    return selected


def prompt_for_branch_origin(runner: "Runner", project_path: str) -> str:
    """Ask for the base branch to pull from and branch off of.

    Defaults to the project repo's current branch (best guess for
    "where we are already working"), but the user can type a
    different one.
    """
    current = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=project_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ).stdout.strip()
    default = current if current and current != "HEAD" else ""

    branch = runner.prompt_text(
        "\nRama base (branch_origin) para el pull y para crear la rama nueva",
        default=default,
    ).strip()
    if not branch:
        runner.info("La rama base es requerida.")
        sys.exit(1)
    return branch


def prompt_for_submodule(runner: "Runner", project_path: str) -> str:
    """Ask which submodule of the project to bump."""
    from odoo_cli.core.actions.maintenance import _discover_submodules

    submodulos = _discover_submodules(project_path)
    if not submodulos:
        runner.info(f"\nNo se encontraron submódulos en {project_path}.")
        sys.exit(1)

    options = [(s, s) for s in submodulos]
    selected = prompt_selection(runner, options, "Selecciona el submódulo a actualizar")
    if not selected:
        runner.info("No se seleccionó ningún submódulo.")
        sys.exit(0)
    return selected


def prompt_for_tag(runner: "Runner", submodule_path: str) -> str:
    """Ask which tag to check out, with an optional text filter.

    Lists tags sorted newest-first by semantic version
    (``--sort=-v:refname``, not the alphabetical default of plain
    ``git tag``) so the user picks from an already-correct order —
    this is what avoids the alphabetical-sort bug of the old
    ``grep ... | tail -n 1`` workflow.
    """
    from odoo_cli.core.actions.maintenance import _filter_tags

    tags = subprocess.run(
        ["git", "tag", "--sort=-v:refname"],
        cwd=submodule_path,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.splitlines()
    tags = [t for t in tags if t.strip()]
    if not tags:
        runner.info(f"\nNo se encontraron tags en {submodule_path}.")
        sys.exit(1)

    # A filter with zero matches only re-asks for the filter — it must
    # NOT sys.exit(1) here: that would kill the whole update-tags run
    # (including any submodule bumps already checked out earlier in
    # the same loop) just because one filter typo/too-narrow term
    # didn't match, instead of just letting the user try again.
    while True:
        text_filter = runner.prompt_text(
            "\nFiltro opcional para los tags (ej: beta, ve, 17, alpha) "
            "— Enter para ver todos"
        ).strip()
        filtered = _filter_tags(tags, text_filter)
        if filtered:
            break
        runner.info(
            f"Ningún tag coincide con el filtro '{text_filter}'. "
            "Probá con otro filtro, o Enter para ver todos los tags."
        )

    options = [(t, t) for t in filtered]
    selected = prompt_selection(runner, options, "Selecciona el tag exacto")
    if not selected:
        runner.info("No se seleccionó ningún tag.")
        sys.exit(0)
    return selected


def prompt_for_branch(runner: "Runner", repo_name: str | None = None) -> str:
    """Ask the user for the branch name to sync to.

    The branch is required: an empty answer exits the process (the
    legacy CLI behavior — a sync without a branch makes no sense).
    """
    title = (
        f"Ingresa la rama para '{repo_name}'"
        if repo_name
        else "Ingresa la rama para sincronizar"
    )
    branch = runner.prompt_text(f"\n{title}").strip()
    if not branch:
        runner.info("La rama es requerida.")
        sys.exit(1)
    return branch


__all__ = [
    "prompt_selection",
    "prompt_for_instance",
    "prompt_for_database",
    "prompt_for_modules",
    "prompt_for_user",
    "prompt_for_repos",
    "prompt_for_branch",
    "prompt_for_project",
    "prompt_for_branch_origin",
    "prompt_for_submodule",
    "prompt_for_tag",
    "prompt_for_odoo_version",
    "prompt_for_bulk_projects",
    "prompt_for_bulk_branch_origin",
]
