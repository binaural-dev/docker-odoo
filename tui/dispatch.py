"""Dispatch logic for the TUI: action -> modal/worker pipeline.

This is a mixin: methods on ``DispatchMixin`` expect ``self`` to be a
``DockerOdooApp`` (or any class that provides the same surface). It
centralises everything that decides WHICH modal to push and HOW to
build the argv, without owning the UI widgets themselves.

The split exists for two reasons:

  1. The 906-line ``tui/app.py`` was mixing composition, dispatch,
     keybindings, and execution in one place. Splitting them makes
     each module readable in isolation and easier to test.
  2. Dispatch logic and keybinding logic evolve independently. Putting
     them in separate modules means a new keybinding doesn't touch
     the dispatch code (and vice versa).

Why a mixin and not free functions
----------------------------------
Most dispatch methods need access to ``self`` (e.g. ``self._log``,
``self._raw_config``, ``self.config``, ``self.query_one``, ...). Two
options were considered:

  * Free functions that take ``app: DockerOdooApp`` as first arg.
  * A mixin class with instance methods.

The mixin is cleaner: methods read like normal methods on the app
(no ``app.`` prefix noise), and the type checker still sees them
as instance methods of the concrete class via MRO. The trade-off is
mixin MRO ordering, but Python handles that with a left-to-right
``class Foo(DispatchMixin, KeybindingsMixin, App)`` declaration.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import sys
from typing import Optional

from tui.actions import _odoo_cli_args, _script_args
from tui.config import BASE_PATH
from tui.models import (
    Action,
    ARG_DB,
    ARG_DEST_DB,
    ARG_INSTALL,
    ARG_LANG,
    ARG_MODULES,
    ARG_PASSWORD,
    ARG_PATH,
    ARG_REPO,
    ARG_BRANCH,
    ARG_TARGET_PG,
    ARG_TEST_TAGS,
    ARG_USER,
    ARG_ZIP,
)
from tui.runner import run_interactive
from tui.screens.confirm_modal import ConfirmModal
from tui.screens.input_modal import InputModal
from tui.screens.module_picker import ModulePicker
from tui.widgets.update_progress import UpdateProgress


class DispatchMixin:
    """Mixin providing the action-dispatch pipeline.

    Expected attributes on ``self`` (provided by ``DockerOdooApp``):
      - ``_raw_config: dict``
      - ``config: dict``
      - ``selected_instance: Optional[str]``
      - ``_log(message: str)`` and ``_log_bulk(message: str)``
      - ``_output_widget``, ``_update_widget`` (cached from on_mount)
      - ``_current_task``, ``_update_proc`` (cancel targets)
      - ``run_worker(coro, ...)`` (Textual App method)
      - ``query_one(selector, type)`` (Textual App method)
      - ``push_screen(screen, callback)`` (Textual App method)
      - ``_run_streamed(argv, label, ...)`` (in app.py)
      - ``_run_interactive(argv, action)`` (delegates to runner)
    """

    # The following attributes are provided by ``DockerOdooApp``; the
    # type annotations here are documentation only (not enforced).
    _raw_config: dict
    config: dict
    selected_instance: Optional[str]
    _output_widget: Optional[object]
    _update_widget: Optional[object]
    _current_task: Optional[asyncio.Task]
    _update_proc: Optional[object]
    _scan_instance_modules: callable

    # ---- dispatch entry point ----

    def _dispatch(self, action: Action) -> None:
        """Entry point: an action was selected in the UI.

        Decides whether to run immediately, push a confirmation modal,
        push an input modal, or scan modules and push the picker.
        """
        self._last_action = action
        if not self._raw_config.get("instances"):
            self._log("[red]No hay instancias configuradas en instances.json.[/red]")
            return
        # If an instance is needed and the user selected a disabled one, fail.
        from tui.models import ARG_INSTANCE
        if (
            ARG_INSTANCE in action.needs
            and self.selected_instance is not None
            and self.selected_instance not in self.config["instances"]
        ):
            self._log(
                f"[red]La instancia '{self.selected_instance}' está deshabilitada. "
                f"Reactivala con Space antes de correr acciones.[/red]"
            )
            return
        if ARG_INSTANCE in action.needs and self.selected_instance is None and not action.needs_all_option:
            self._log(f"[red]'{action.label}' requiere seleccionar una instancia.[/red]")
            return
        if (
            self.selected_instance is None
            and action.needs_all_option
            and not self.config.get("instances")
        ):
            self._log("[red]Todas las instancias están deshabilitadas.[/red]")
            return

        # Special-cased no-arg actions
        if not action.needs:
            self.run_worker(self._execute(action, {}), exclusive=False)
            return

        # ``hosts-status`` is special: it doesn't take args and doesn't
        # need a docker run, so we render the diff + suggested command
        # directly in the log panel.
        if action.action_id == "hosts-status":
            self.run_worker(self._hosts_status_async(), exclusive=False)
            return

        # The consolidated ``update`` action with an instance selected
        # can use the fzf-style module picker when addons paths are
        # available on disk. The text modal remains the fallback for
        # "all instances" or for instances whose addons paths produced
        # no modules.
        if action.action_id == "update" and self.selected_instance is not None:
            inst = self.config["instances"].get(self.selected_instance)
            if inst is not None:
                self.run_worker(
                    self._update_picker_async(action, inst),
                    exclusive=True,
                )
                return

        # Build the fields list for the input modal. ARG_INSTANCE is
        # pre-selected from the instance list and is NOT asked again.
        fields = []
        for arg in action.needs:
            if arg == ARG_INSTANCE:
                continue
            fields.append(self._arg_to_field(arg))

        # ``update`` exposes an optional --load-language field that
        # isn't in action.needs (the picker handles its own modal).
        if action.action_id == "update":
            fields.append(self._arg_to_field(ARG_LANG))

        # Confirm destructive actions before execution.
        if action.action_id == "remove":
            target = self.selected_instance or "TODAS las instancias"
            self.push_screen(
                ConfirmModal(
                    title="Eliminar instancia",
                    message=(
                        f"¿Eliminar contenedores y volúmenes de "
                        f"[b]{target}[/b]?"
                    ),
                ),
                lambda confirmed: (
                    self.run_worker(self._execute(action, {}), exclusive=False)
                    if confirmed
                    else self._log("[yellow]Eliminación cancelada.[/yellow]")
                ),
            )
            return

        # If the only thing the action needs was an instance (already
        # selected), skip the modal and run straight away.
        if not fields:
            self.run_worker(self._execute(action, {}), exclusive=False)
            return
        defaults = self._arg_defaults(action)
        modal = InputModal(
            title=f"{action.label} — completar datos",
            fields=fields,
            defaults=defaults,
        )
        self.push_screen(modal, lambda result: self._on_modal_result(action, result))

    def _dispatch_fallback_to_text_modal(self, action: Action) -> None:
        """Fallback cuando el scan no encontró addons: muestra el modal de texto."""
        from tui.models import ARG_INSTANCE
        fields = []
        for arg in action.needs:
            if arg == ARG_INSTANCE:
                continue
            fields.append(self._arg_to_field(arg))
        if action.action_id == "update":
            fields.append(self._arg_to_field(ARG_LANG))
        defaults = self._arg_defaults(action)
        modal = InputModal(
            title=f"{action.label} — completar datos",
            fields=fields,
            defaults=defaults,
        )
        self.push_screen(modal, lambda result: self._on_modal_result(action, result))

    # ---- picker / async dispatch helpers ----

    async def _update_picker_async(self, action: Action, inst: dict) -> None:
        """Versión async del dispatch para update con picker.

        Hace el scan de módulos en un thread pool (1-3s de syscalls) y
        luego muestra el modal. Sin esto, la UI quedaba congelada
        durante el scan.
        """
        from tui.models import ARG_INSTANCE
        from tui.app import _scan_instance_modules_pure

        inst_name = self.selected_instance
        if inst_name is None:
            return
        # Cache lookup happens on the main thread; the actual scan
        # (which can take 1-3s of syscalls) runs in the thread pool.
        # We write the cache result back on the main thread too, to
        # keep DOM-touching state mutations on a single thread.
        if inst_name in self.module_cache:
            available = self.module_cache[inst_name]
        else:
            available = await asyncio.to_thread(
                _scan_instance_modules_pure, inst_name, inst, self.config
            )
            self.module_cache[inst_name] = available
        if not available:
            self._log(
                "[yellow]No se detectaron addons locales; "
                "usando input de texto.[/yellow]"
            )
            # Re-dispatch recursivo pero ya con scan vacio -> cae al modal de texto
            self._dispatch_fallback_to_text_modal(action)
            return
        fields = [
            self._arg_to_field(ARG_DB),
            self._arg_to_field(ARG_LANG),
        ]
        defaults = self._arg_defaults(action)
        modal = InputModal(
            title=f"{action.label} — base de datos",
            fields=fields,
            defaults=defaults,
        )

        def _on_db_modal_result(db_result: Optional[dict]) -> None:
            if db_result is None:
                self._log("[yellow]Cancelado.[/yellow]")
                return
            selected_db = db_result.get(ARG_DB, "")
            selected_lang = db_result.get(ARG_LANG, "")
            self.push_screen(
                ModulePicker(
                    instance_name=inst_name,
                    available_modules=available,
                ),
                lambda picker_result: self._on_picker_result_with_db(
                    action, picker_result, selected_db, selected_lang
                ),
            )

        self.push_screen(modal, _on_db_modal_result)

    # ---- modal result handlers ----

    def _on_modal_result(self, action: Action, result: Optional[dict]) -> None:
        if result is None:
            self._log("[yellow]Cancelado.[/yellow]")
            return
        # Convert numeric fields where appropriate
        if ARG_TARGET_PG in result and result[ARG_TARGET_PG].isdigit():
            result[ARG_TARGET_PG] = int(result[ARG_TARGET_PG])
        # Soft-check that typed modules exist in any of the instance's
        # addons paths. This is only relevant for the text modal flow of
        # the ``update`` action; the fzf-style picker already filters
        # against the scanned module list.
        if action.action_id == "update" and result.get(ARG_MODULES):
            self._warn_unknown_modules(result[ARG_MODULES])
        self.run_worker(self._execute(action, result), exclusive=False)

    def _on_picker_result_with_db(
        self, action: Action, result: Optional[list], db: str, lang: Optional[str] = None
    ) -> None:
        """Handle the ModulePicker dismiss for the update action with a pre-selected database."""
        if result is None:
            self._log("[yellow]Cancelado.[/yellow]")
            return
        modules_str = ",".join(result) if result else "all"
        args = {ARG_DB: db, ARG_MODULES: modules_str}
        if lang:
            args[ARG_LANG] = lang
        self.run_worker(self._execute(action, args), exclusive=False)

    def _on_picker_result(
        self, action: Action, result: Optional[list]
    ) -> None:
        """Handle the ModulePicker dismiss for the update action.

        Empty selection means ``all``; a non-empty list is comma-joined
        for the ``-u`` flag. The DB default is auto-filled from
        ``overwrite_odoo_config.db_name`` exactly like the text modal
        flow does, so the picker path and the text modal path converge
        before reaching :meth:`_execute`.
        """
        if result is None:
            self._log("[yellow]Cancelado.[/yellow]")
            return
        modules_str = ",".join(result) if result else "all"
        if self.selected_instance:
            inst = self.config["instances"].get(self.selected_instance, {})
            db_default = inst.get("overwrite_odoo_config", {}).get(
                "db_name", self.selected_instance
            )
        else:
            db_default = ""
        args = {ARG_DB: db_default, ARG_MODULES: modules_str}
        self.run_worker(self._execute(action, args), exclusive=False)

    def _warn_unknown_modules(self, modules_str: str) -> None:
        """Log a yellow warning listing modules not found in addons paths."""
        if not modules_str or modules_str.strip().lower() == "all":
            return
        if self.selected_instance is None:
            return
        inst = self.config["instances"].get(self.selected_instance)
        if inst is None:
            return
        try:
            from generators.config_loader import resolve_instance_config
        except ImportError:
            return
        addons = resolve_instance_config(inst, self.config).get("addons", [])
        valid_paths = [
            a for a in addons
            if os.path.isdir(os.path.join(BASE_PATH, a))
        ]
        missing: list[str] = []
        for raw in modules_str.split(","):
            name = raw.strip()
            if not name:
                continue
            found = any(
                os.path.isfile(
                    os.path.join(BASE_PATH, a, name, "__manifest__.py")
                )
                for a in valid_paths
            )
            if not found:
                missing.append(name)
        if missing:
            self._log(
                f"[yellow]Aviso:[/yellow] módulo(s) no encontrado(s) en "
                f"addons: {', '.join(missing)}"
            )

    # ---- arg helpers ----

    def _arg_to_field(self, arg: str) -> dict:
        defaults = {
            ARG_DB: {"key": ARG_DB, "label": "Base de datos (-d)",
                     "placeholder": "ej: bananera_prod"},
            ARG_MODULES: {"key": ARG_MODULES, "label": "Módulos (-m)",
                          "placeholder": "sale,purchase o 'all'"},
            ARG_USER: {"key": ARG_USER, "label": "Login (-l)", "placeholder": "admin"},
            ARG_PASSWORD: {"key": ARG_PASSWORD, "label": "Nueva contraseña (-p)",
                           "placeholder": "admin", "password": True},
            ARG_REPO: {"key": ARG_REPO, "label": "Repo (carpeta bajo src/custom/)",
                       "placeholder": "ej: server-ux"},
            ARG_BRANCH: {"key": ARG_BRANCH, "label": "Branch", "placeholder": "19.0"},
            ARG_ZIP: {"key": ARG_ZIP, "label": "Archivo ZIP de backup",
                      "placeholder": "/ruta/al/backup.zip"},
            ARG_DEST_DB: {"key": ARG_DEST_DB, "label": "Nombre de la nueva DB",
                          "placeholder": "ej: restored_db"},
            ARG_TARGET_PG: {"key": ARG_TARGET_PG, "label": "Target pg major",
                            "placeholder": "16"},
            ARG_PATH: {"key": ARG_PATH, "label": "Ruta de salida del ZIP",
                       "placeholder": "/tmp/backup.zip"},
            ARG_TEST_TAGS: {"key": ARG_TEST_TAGS, "label": "Test tags (-t)",
                            "placeholder": "/binaural_accountant"},
            ARG_INSTALL: {"key": ARG_INSTALL, "label": "Módulos a instalar (-i)",
                          "placeholder": "account,sale"},
            ARG_LANG: {"key": ARG_LANG, "label": "Load language (opcional)",
                       "placeholder": "es_VE", "optional": True},
        }
        return defaults[arg]

    def _arg_defaults(self, action: Action) -> dict:
        defaults = {}
        if action.action_id == "pw":
            defaults[ARG_USER] = "admin"
            defaults[ARG_PASSWORD] = "admin"
        if action.action_id == "update":
            defaults[ARG_MODULES] = "all"
            if self.selected_instance:
                inst = self.config["instances"].get(self.selected_instance, {})
                defaults[ARG_DB] = inst.get(
                    "overwrite_odoo_config", {}
                ).get("db_name", self.selected_instance)
        if action.action_id == "script:test":
            defaults[ARG_DB] = "testing"
            defaults[ARG_TEST_TAGS] = "/binaural_accountant"
            defaults[ARG_INSTALL] = "l10n_ve,binaural_rate,account,binaural_accountant"
        if action.action_id == "script:backup":
            defaults[ARG_TARGET_PG] = "16"
        return defaults

    # ---- execution (called from worker) ----

    async def _execute(self, action: Action, args: dict) -> None:
        # If the action supports "all instances" and no instance was picked,
        # fan out across every enabled instance.
        if (
            action.needs_all_option
            and self.selected_instance is None
            and self.config.get("instances")
        ):
            await self._execute_all(action, args)
            return

        await self._execute_one(action, self.selected_instance, args)

    async def _execute_all(self, action: Action, args: dict) -> None:
        from tui.config import is_instance_enabled
        instances = list(self.config["instances"].keys())
        disabled = [
            name for name, inst in self._raw_config.get("instances", {}).items()
            if not is_instance_enabled(inst)
        ]
        if disabled:
            self._log(
                f"[dim]Saltando instancia(s) deshabilitada(s): "
                f"{', '.join(disabled)}[/dim]"
            )
        self._log(f"[cyan]→ {action.label} para {len(instances)} instancia(s): "
                  f"{', '.join(instances) or '(ninguna habilitada)'}[/cyan]")
        rc_total = 0
        for name in instances:
            self._log(f"[dim]-- {name} --[/dim]")
            rc = await self._execute_one(action, name, args, echo_cmd=False)
            rc_total = rc_total or rc
        if rc_total == 0:
            self._log(f"[green]✓ {action.label} OK en todas las instancias[/green]")
        else:
            self._log(f"[red]✗ {action.label} salió con código {rc_total} en al menos una instancia[/red]")

    async def _execute_one(self, action: Action, instance: Optional[str], args: dict, *, echo_cmd: bool = True) -> int:
        # The consolidated ``update`` action routes through scripts/odoo-update
        # just like the legacy ``script:update`` did.
        if action.action_id == "update" or action.action_id.startswith("script:"):
            argv = _script_args(action, instance, args)
        else:
            argv = _odoo_cli_args(action, instance, args)
        if not shutil.which("docker") and action.action_id != "list":
            self._log("[yellow]Aviso:[/yellow] 'docker' no está en PATH; el comando va a fallar.")
        if action.interactive:
            await self._run_interactive(argv, action)
            return 0
        use_progress = self._is_update_with_modules(action, args)
        if use_progress:
            self._progress_label = action.label
        return await self._run_streamed(argv, action.label, echo_cmd=echo_cmd, use_progress_widget=use_progress)

    async def _run_interactive(self, argv: list, action: Action) -> None:
        """Suspende la TUI y corre un comando interactivo (bash, logs, psql).

        Delega en `tui.runner.run_interactive` para que el subprocess
        corre en asyncio (no en un thread aparte). El `self.suspend()`
        cede el control del terminal al comando hasta que termine.
        """
        self._log(f"[cyan]→ {' '.join(shlex.quote(a) for a in argv)}[/cyan]")
        self._log("[dim]Suspendiendo TUI para comando interactivo. Volvé cuando termine.[/dim]")
        with self.suspend():
            try:
                await run_interactive(argv, BASE_PATH)
            except FileNotFoundError as exc:
                print(f"\n[ERROR] No se pudo ejecutar: {exc}", file=sys.stderr)
            except KeyboardInterrupt:
                print("\n[interrumpido]", file=sys.stderr)
        self._log(f"[green]✓ {action.label} finalizado.[/green]")

    def _is_update_with_modules(self, action: Action, args: dict) -> bool:
        """Determina si podemos mostrar el widget de progreso.

        Para cualquier action ``update``: Odoo siempre emite el formato
        ``(N/M)`` cuando actualiza modulos (sean especificos o 'all'),
        asi que la barra aplica a todos los updates. Antes se ocultaba
        para modules='all'/vacio, pero eso era un bug: el usuario que
        corre 'update' sin elegir modulos especificos no veia ninguna
        barra, aunque Odoo claramente estaba emitiendo progreso.
        """
        return action.action_id == "update"

    async def _hosts_status_async(self) -> None:
        """Render the hosts status directly into the log panel.

        Runs the diff in a worker thread (the /etc/hosts read is cheap,
        but going through ``odoo_cli`` keeps us aligned with the CLI's
        logic) and emits a clear "ready to paste" sudo command.
        """
        from odoo_cli.core.actions.hosts import hosts_status

        def _runner_info(msg: str) -> None:
            self._log(msg)

        def _runner_warn(msg: str) -> None:
            self._log(msg)

        class _InlineRunner:
            def info(self, msg: str) -> None:
                _runner_info(msg)

            def warn(self, msg: str) -> None:
                _runner_warn(msg)

            def error(self, msg: str) -> None:
                self._log(f"[red]{msg}[/red]")

        await asyncio.to_thread(hosts_status, _InlineRunner(), self._raw_config)
