"""DockerOdooApp — main Textual application for the docker-odoo TUI."""

import asyncio
import json
import os
import shlex
import shutil
import subprocess
import sys
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    OptionList,
    ProgressBar,
    RichLog,
    Static,
)
from textual.widgets.option_list import Option

from tui.config import BASE_PATH, TCSS_PATH, is_instance_enabled, load_full_config
from tui.models import (
    Action,
    ACTIONS,
    CATEGORY_ORDER,
    ARG_INSTANCE,
    ARG_DB,
    ARG_MODULES,
    ARG_USER,
    ARG_PASSWORD,
    ARG_REPO,
    ARG_BRANCH,
    ARG_ZIP,
    ARG_DEST_DB,
    ARG_TARGET_PG,
    ARG_PATH,
    ARG_TEST_TAGS,
    ARG_INSTALL,
    ARG_LANG,
    LOG_LEVELS,
)
from tui.actions import get_action, _odoo_cli_args, _script_args
from tui.parser import parse_progress, classify_level
from tui.screens.input_modal import InputModal
from tui.screens.confirm_modal import ConfirmModal
from tui.screens.module_picker import ModulePicker
from tui.widgets.items import InstanceItem, AllInstancesItem, ActionItem, NoInstanceActionItem
from tui.widgets.update_progress import UpdateProgress


class DockerOdooApp(App):
    CSS_PATH = TCSS_PATH

    BINDINGS = [
        Binding("q", "quit", "Salir"),
        Binding("r", "refresh", "Refrescar"),
        Binding("tab", "focus_next", "Siguiente panel"),
        Binding("space", "toggle_instance", "Toggle enabled"),
        Binding("escape", "cancel_update", "Cancelar"),
        Binding("1", "toggle_level_info", "INFO"),
        Binding("2", "toggle_level_warning", "WARNING"),
        Binding("3", "toggle_level_error", "ERROR"),
        Binding("4", "toggle_level_critical", "CRITICAL"),
        Binding("0", "filter_all_levels", "Todos"),
        Binding("9", "filter_errors_only", "Solo error/warn"),
    ]

    selected_instance: reactive[Optional[str]] = reactive(None)

    def __init__(self, dev: bool | str = False):
        super().__init__()
        self.dev = dev                    # False / True / "all" (CLI --dev flag)
        self.config: dict = {}            # filtered (enabled-only) instances
        self._raw_config: dict = {}       # unfiltered, used for persistence
        self._last_action: Optional[Action] = None
        self.module_cache: dict = {}      # instance -> sorted module names
        self._update_proc: Optional[subprocess.Popen] = None  # current update proc
        self._progress_label: str = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Static("Instancias (instances.json)", id="subtitle")
                yield ListView(id="instances_list")
            with Vertical(id="right"):
                yield Static("Acciones disponibles", id="subtitle")
                yield ListView(id="actions_list")
        yield UpdateProgress(id="update_progress")
        yield RichLog(id="output", highlight=False, markup=True, wrap=True, max_lines=2000)
        yield Footer()

    def on_mount(self) -> None:
        self.title = "docker-odoo TUI"
        self.sub_title = "Launcher interactivo"
        if self.dev:
            self._log(f"[yellow]Dev mode activo:[/yellow] dev={self.dev!r}")
        self.refresh_instances()
        self.refresh_actions()
        self._log("[green]Listo.[/green] Elegí una instancia y luego una acción. "
                  "Atajos: [b]q[/b] salir, [b]r[/b] refrescar, [b]Tab[/b] cambiar panel.")

    # ---------- data loading ----------

    def refresh_instances(self) -> None:
        try:
            self._raw_config = load_full_config(BASE_PATH)
        except SystemExit:
            self._raw_config = {}
        except Exception as exc:
            self._log(f"[red]Error cargando instances.json:[/red] {exc}")
            self._raw_config = {}

        # Filtered view used by action dispatch (enabled-only).
        self.config = {
            "odoo_configs": self._raw_config.get("odoo_configs", {}),
            "databases": self._raw_config.get("databases", {}),
            "instances": {
                name: inst
                for name, inst in self._raw_config.get("instances", {}).items()
                if is_instance_enabled(inst)
            },
        }

        list_view = self.query_one("#instances_list", ListView)
        list_view.clear()
        enabled_count = len(self.config["instances"])
        list_view.append(AllInstancesItem(enabled_count=enabled_count))
        for name, inst in self._raw_config.get("instances", {}).items():
            list_view.append(InstanceItem(
                name=name,
                version=inst.get("odoo_version", "?"),
                port=inst.get("external_port", 0),
                database=inst.get("database", "?"),
                enabled=is_instance_enabled(inst),
            ))
        list_view.index = 0
        self.selected_instance = None

    def _scan_instance_modules(self, inst_name: str, inst_conf: dict) -> list:
        """Return the sorted list of module names found in the instance's addons paths.

        Results are memoised in ``self.module_cache``. The scan only
        happens lazily on first request for an instance, never on
        ``on_mount`` (which would scan every configured instance
        regardless of whether the user will ever use the picker).
        """
        if inst_name in self.module_cache:
            return self.module_cache[inst_name]
        try:
            from generators.config_loader import resolve_instance_config
        except ImportError:
            self.module_cache[inst_name] = []
            return []
        addons = resolve_instance_config(inst_conf, self.config).get("addons", [])
        modules: set[str] = set()
        for path in addons:
            abs_path = os.path.join(BASE_PATH, path)
            if not os.path.isdir(abs_path):
                continue
            for entry in os.listdir(abs_path):
                full = os.path.join(abs_path, entry)
                if (
                    os.path.isdir(full)
                    and os.path.isfile(os.path.join(full, "__manifest__.py"))
                ):
                    modules.add(entry)
        self.module_cache[inst_name] = sorted(modules)
        return self.module_cache[inst_name]

    def refresh_actions(self) -> None:
        list_view = self.query_one("#actions_list", ListView)
        list_view.clear()
        # Show all categories; user can pick a no-instance action directly
        for cat in CATEGORY_ORDER:
            for action in ACTIONS:
                if action.category != cat:
                    continue
                if ARG_INSTANCE in action.needs:
                    list_view.append(ActionItem(action))
                else:
                    list_view.append(NoInstanceActionItem(action))
        list_view.index = 0

    # ---------- toggle persistence ----------

    def action_toggle_instance(self) -> None:
        """Toggle the ``enabled`` flag of the highlighted instance and persist."""
        list_view = self.query_one("#instances_list", ListView)
        item = list_view.highlighted_child
        if item is None or not isinstance(item, InstanceItem):
            self._log("[yellow]Space no aplica a 'Todas las instancias'.[/yellow]")
            return
        name = item.instance_name
        if name not in self._raw_config.get("instances", {}):
            return
        new_value = not is_instance_enabled(self._raw_config["instances"][name])
        self._raw_config["instances"][name]["enabled"] = new_value
        if not self._save_instances_json(self._raw_config):
            # Revert in-memory change so UI and disk stay in sync.
            self._raw_config["instances"][name]["enabled"] = not new_value
            return
        self._log(
            f"[green]Instancia[/green] [b]{name}[/b] "
            f"{'habilitada' if new_value else 'deshabilitada'}."
        )
        # Repaint the list, preserving the current selection index.
        current_index = list_view.index
        self.refresh_instances()
        list_view.index = min(current_index, len(list_view.children) - 1)

    def _save_instances_json(self, raw_config: dict) -> bool:
        """Persist the full (unfiltered) instances.json. Returns True on success."""
        path = os.path.join(BASE_PATH, "instances.json")
        try:
            with open(path, "w") as f:
                json.dump(raw_config, f, indent=2, ensure_ascii=False)
                f.write("\n")
            return True
        except (OSError, PermissionError) as exc:
            self._log(
                f"[red]No se pudo guardar instances.json:[/red] {exc}"
            )
            return False

    # ---------- event wiring ----------

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "instances_list":
            item = event.item
            if isinstance(item, InstanceItem):
                self.selected_instance = item.instance_name
            else:
                self.selected_instance = None

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "instances_list":
            item = event.item
            if isinstance(item, InstanceItem):
                self.selected_instance = item.instance_name
                self._log(f"Instancia seleccionada: [b]{item.instance_name}[/b]")
            else:
                self.selected_instance = None
                self._log("Selección: [b]Todas las instancias[/b]")
            self.query_one("#actions_list", ListView).focus()
        elif event.list_view.id == "actions_list":
            item = event.item
            action = getattr(item, "action", None)
            if action is not None:
                self._dispatch(action)

    # ---------- dispatch ----------

    def _dispatch(self, action: Action) -> None:
        self._last_action = action
        if not self._raw_config.get("instances"):
            self._log("[red]No hay instancias configuradas en instances.json.[/red]")
            return
        # If an instance is needed and the user selected a disabled one, fail.
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

        # Special case: the consolidated ``update`` action with an
        # instance selected can use the fzf-style module picker when
        # addons paths are available on disk. The text modal remains
        # the fallback for "all instances" or for instances whose
        # addons paths did not produce any modules.
        if action.action_id == "update" and self.selected_instance is not None:
            inst = self.config["instances"].get(self.selected_instance)
            if inst is not None:
                available = self._scan_instance_modules(
                    self.selected_instance, inst
                )
                if available:
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
                                instance_name=self.selected_instance,
                                available_modules=available,
                            ),
                            lambda picker_result: self._on_picker_result_with_db(
                                action, picker_result, selected_db, selected_lang
                            ),
                        )

                    self.push_screen(modal, _on_db_modal_result)
                    return
                self._log(
                    "[yellow]No se detectaron addons locales; "
                    "usando input de texto.[/yellow]"
                )

        # Build the fields list and launch the input modal.
        # ARG_INSTANCE is pre-selected from the instance list and is NOT
        # asked again as a modal input.
        fields = []
        for arg in action.needs:
            if arg == ARG_INSTANCE:
                continue
            fields.append(self._arg_to_field(arg))

        # The consolidated ``update`` action exposes an optional
        # --load-language field on the text modal that is not part of
        # ``action.needs`` (the fzf-style picker handles its own modal).
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
                       "placeholder": "es_VE"},
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

    # ---------- execution ----------

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

    def _is_update_with_modules(self, action: Action, args: dict) -> bool:
        """Determina si podemos mostrar el widget de progreso.

        Solo para action ``update`` con módulos conocidos (no 'all').
        """
        if action.action_id != "update":
            return False
        modules = (args or {}).get("modules", "")
        if not modules or modules == "all":
            return False
        return True

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
        self._log(f"[cyan]→ {' '.join(shlex.quote(a) for a in argv)}[/cyan]")
        self._log("[dim]Suspendiendo TUI para comando interactivo. Volvé cuando termine.[/dim]")
        with self.suspend():
            try:
                await asyncio.to_thread(subprocess.run, argv, cwd=BASE_PATH)
            except FileNotFoundError as exc:
                print(f"\n[ERROR] No se pudo ejecutar: {exc}", file=sys.stderr)
            except KeyboardInterrupt:
                print("\n[interrumpido]", file=sys.stderr)
        self._log(f"[green]✓ {action.label} finalizado.[/green]")

    async def _run_streamed(
        self, argv: list, label: str, *,
        echo_cmd: bool = True, use_progress_widget: bool = False,
    ) -> int:
        if echo_cmd:
            self._log(f"[cyan]→ {' '.join(shlex.quote(a) for a in argv)}[/cyan]")
        self._log("[dim]Ejecutando... (Ctrl+C para abortar)[/dim]")

        # Mostrar widget de progreso si corresponde
        up: Optional[UpdateProgress] = None
        if use_progress_widget:
            up = self.query_one("#update_progress", UpdateProgress)
            up.display = True
            up.clear()
            up.filter_levels = set(LOG_LEVELS)

        def _run() -> int:
            try:
                proc = subprocess.Popen(
                    argv, cwd=BASE_PATH,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
            except FileNotFoundError as exc:
                self.call_from_thread(self._log, f"[red]No encontrado:[/red] {exc}")
                return 127
            # Guardar referencia para cancelacion con Esc
            self._update_proc = proc
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.rstrip()
                if up is not None:
                    parsed = parse_progress(line)
                    if parsed is not None:
                        self.call_from_thread(up.set_progress, parsed[0], parsed[1])
                    level = classify_level(line)
                    self.call_from_thread(up.add_line, level, line)
                    if level in up.filter_levels:
                        self.call_from_thread(self._log, line)
                else:
                    self.call_from_thread(self._log, line)
            rc = proc.wait()
            self._update_proc = None
            return rc

        rc = await asyncio.to_thread(_run)

        # Ocultar widget de progreso
        if up is not None:
            up.display = False

        if echo_cmd:
            if rc == 0:
                self._log(f"[green]✓ {label} OK[/green]")
            else:
                self._log(f"[red]✗ {label} salió con código {rc}[/red]")
        return rc

    def action_cancel_update(self) -> None:
        """Cancela la actualización en curso con Esc."""
        if self._update_proc is not None:
            self._log("[yellow]Cancelando actualización...[/yellow]")
            self._update_proc.terminate()
        else:
            self._log("[dim]No hay actualización en curso.[/dim]")

    def _rebuild_richlog_from_up(self, up: "UpdateProgress") -> None:
        """Reconstruye el RichLog con las líneas que pasan el filtro actual."""
        rl = self.query_one("#output", RichLog)
        rl.clear()
        for line in up.get_filtered_lines():
            rl.write(line)

    def _toggle_log_level(self, level: str) -> None:
        """Alterna un nivel de log en el UpdateProgress y reconstruye el RichLog."""
        try:
            up = self.query_one("#update_progress", UpdateProgress)
        except Exception:
            return
        if not up.display:
            return
        up._toggle_level(level)
        self._rebuild_richlog_from_up(up)

    def action_toggle_level_info(self) -> None:
        self._toggle_log_level("INFO")

    def action_toggle_level_warning(self) -> None:
        self._toggle_log_level("WARNING")

    def action_toggle_level_error(self) -> None:
        self._toggle_log_level("ERROR")

    def action_toggle_level_critical(self) -> None:
        self._toggle_log_level("CRITICAL")

    def action_filter_all_levels(self) -> None:
        """Activa todos los niveles [0]."""
        try:
            up = self.query_one("#update_progress", UpdateProgress)
        except Exception:
            return
        if not up.display:
            return
        up.set_all_levels(True)
        self._rebuild_richlog_from_up(up)
        self._log("[green]Filtro: todos los niveles activados[/green]")

    def action_filter_errors_only(self) -> None:
        """Activa solo ERROR y CRITICAL [9]."""
        try:
            up = self.query_one("#update_progress", UpdateProgress)
        except Exception:
            return
        if not up.display:
            return
        up.set_errors_only()
        self._rebuild_richlog_from_up(up)
        self._log("[yellow]Filtro: solo ERROR + CRITICAL[/yellow]")

    def _log(self, message: str) -> None:
        try:
            self.query_one("#output", RichLog).write(message)
        except Exception as exc:
            print(f"[TUI _log fallback] {message} (error: {exc})", file=sys.stderr)
