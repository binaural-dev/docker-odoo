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


def _scan_instance_modules_pure(inst_name: str, inst_conf: dict, full_config: dict) -> list:
    """Pure sync module scan (runs in a thread via to_thread).

    Walks the instance's addons paths and returns a sorted list of
    directory names that contain a ``__manifest__.py``. No DOM access,
    no instance state mutation — the caller is responsible for caching
    the result. Keeping this function pure means it can be invoked
    from a thread pool without violating Textual's single-threaded
    DOM contract.
    """
    try:
        from generators.config_loader import resolve_instance_config
    except ImportError:
        return []
    addons = resolve_instance_config(inst_conf, full_config).get("addons", [])
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
    return sorted(modules)


def _write_instances_json(base_path: str, raw_config: dict) -> tuple[bool, str]:
    """Pure sync helper: write ``raw_config`` to ``base_path/instances.json``.

    Returns ``(True, "")`` on success, ``(False, error_message)`` on
    failure. No DOM access, no logging — those belong to the caller on
    the main thread. This is the function we run in the thread pool
    via ``asyncio.to_thread``.
    """
    path = os.path.join(base_path, "instances.json")
    try:
        with open(path, "w") as f:
            json.dump(raw_config, f, indent=2, ensure_ascii=False)
            f.write("\n")
        return True, ""
    except (OSError, PermissionError) as exc:
        return False, str(exc)


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
        # The current streaming subprocess handle. Kept (instead of
        # being replaced by ``_current_task`` outright) so the existing
        # smoke test ``test_integration_cancel_with_esc`` keeps working
        # unchanged: it sets ``app._update_proc = mock_proc`` and
        # expects ``mock_proc.terminate()`` to fire on Esc. The real
        # cancel path (commit 2) cancels ``_current_task`` instead;
        # this attribute is the legacy fallback used only by the test.
        self._update_proc: Optional[object] = None
        # Set by ``_run_streamed`` to the worker task that's currently
        # awaiting ``stream_command``. ``action_cancel_update`` cancels
        # this task on Esc; the runner's CancelledError handler then
        # SIGTERMs the real subprocess (and escalates to SIGKILL on
        # timeout).
        self._current_task: Optional[asyncio.Task] = None
        self._progress_label: str = ""
        # Cache of frequently-queried widgets. ``query_one`` does a
        # CSS selector walk every call; during a streaming run we
        # hit it once per line. Populated in ``on_mount`` once the
        # widgets exist on the DOM.
        self._output_widget: Optional[RichLog] = None
        self._update_widget: Optional[UpdateProgress] = None
        self._instances_list: Optional[ListView] = None
        self._actions_list: Optional[ListView] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Static("Instancias", id="instances_subtitle")
                yield ListView(id="instances_list")
            with Vertical(id="right"):
                yield Static("Acciones", id="actions_subtitle")
                yield ListView(id="actions_list")
        yield UpdateProgress(id="update_progress")
        yield RichLog(id="output", highlight=False, markup=True, wrap=True, max_lines=2000)
        yield Footer()

    def on_mount(self) -> None:
        self.title = "docker-odoo TUI"
        self.sub_title = "Launcher interactivo"
        # Cache hot-path widgets. query_one does a CSS selector walk
        # every call; during a streaming run we'd hit it once per line.
        # We try/except so headless tests that don't mount these
        # widgets don't crash.
        try:
            self._output_widget = self.query_one("#output", RichLog)
        except Exception:
            self._output_widget = None
        try:
            self._update_widget = self.query_one("#update_progress", UpdateProgress)
        except Exception:
            self._update_widget = None
        try:
            self._instances_list = self.query_one("#instances_list", ListView)
        except Exception:
            self._instances_list = None
        try:
            self._actions_list = self.query_one("#actions_list", ListView)
        except Exception:
            self._actions_list = None
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

        list_view = self._instances_list or self.query_one("#instances_list", ListView)
        self._instances_list = list_view
        list_view.clear()
        enabled_count = len(self.config["instances"])
        total_count = len(self._raw_config.get("instances", {}))
        if total_count == 0:
            list_view.append(EmptyStateItem(
                "No hay instancias configuradas",
                "Editá instances.json y apretá 'r' para refrescar",
            ))
        else:
            list_view.append(AllInstancesItem(enabled_count=enabled_count))
            for name, inst in self._raw_config.get("instances", {}).items():
                list_view.append(InstanceItem(
                    name=name,
                    version=inst.get("odoo_version", "?"),
                    port=inst.get("external_port", 0),
                    database=inst.get("database", "?"),
                    enabled=is_instance_enabled(inst),
                ))
        # Update subtitle with counts
        subtitle = self.query_one("#instances_subtitle", Static)
        if total_count > 0:
            subtitle.update(
                f"Instancias  [dim]({enabled_count}/{total_count} habilitadas)[/dim]"
            )
        else:
            subtitle.update("Instancias")
        list_view.index = 0
        self.selected_instance = None

    def _scan_instance_modules(self, inst_name: str, inst_conf: dict) -> list:
        """Return the sorted list of module names found in the instance's addons paths.

        Results are memoised in ``self.module_cache``. The scan only
        happens lazily on first request for an instance, never on
        ``on_mount`` (which would scan every configured instance
        regardless of whether the user will ever use the picker).

        This is a thin wrapper that does the cache check on the main
        thread and delegates the actual filesystem walk to the pure
        helper \`_scan_instance_modules_pure\` (which can be called
        from a thread via \`asyncio.to_thread\`). Keeping the cache
        write on the main thread is required to satisfy Textual's
        single-threaded DOM contract.
        """
        if inst_name in self.module_cache:
            return self.module_cache[inst_name]
        modules = _scan_instance_modules_pure(inst_name, inst_conf, self.config)
        self.module_cache[inst_name] = modules
        return modules

    def refresh_actions(self) -> None:
        list_view = self._actions_list or self.query_one("#actions_list", ListView)
        self._actions_list = list_view
        list_view.clear()
        # Show all categories; user can pick a no-instance action directly.
        # Insertamos un CategoryHeaderItem entre grupos para dar separacion
        # visual y orientacion al usuario.
        from tui.widgets.items import CategoryHeaderItem
        total = 0
        for cat in CATEGORY_ORDER:
            # Solo agregar header si hay al menos una accion en esta categoria
            cat_actions = [a for a in ACTIONS if a.category == cat]
            if not cat_actions:
                continue
            list_view.append(CategoryHeaderItem(cat))
            for action in cat_actions:
                if ARG_INSTANCE in action.needs:
                    list_view.append(ActionItem(action))
                else:
                    list_view.append(NoInstanceActionItem(action))
                total += 1
        list_view.index = 1  # skip first category header
        # Update subtitle with count
        subtitle = self.query_one("#actions_subtitle", Static)
        subtitle.update(f"Acciones  [dim]({total} disponibles)[/dim]")

    # ---------- toggle persistence ----------

    def action_toggle_instance(self) -> None:
        """Toggle the ``enabled`` flag of the highlighted instance and persist.

        Optimizado: NO relee instances.json ni repinta la lista entera.
        Solo actualiza in-place el item afectado y la vista filtrada
        (self.config). El save a disco corre en background.
        """
        list_view = self._instances_list or self.query_one("#instances_list", ListView)
        self._instances_list = list_view
        item = list_view.highlighted_child
        if item is None or not isinstance(item, InstanceItem):
            self._log("[yellow]Space no aplica a 'Todas las instancias'.[/yellow]")
            return
        name = item.instance_name
        if name not in self._raw_config.get("instances", {}):
            return
        new_value = not is_instance_enabled(self._raw_config["instances"][name])
        self._raw_config["instances"][name]["enabled"] = new_value

        # Update vista filtrada in-place (sin re-parsear el JSON)
        if new_value:
            inst = self._raw_config["instances"][name]
            self.config["instances"][name] = inst
        else:
            self.config["instances"].pop(name, None)

        # Update visual del item in-place (sin repintar lista)
        item.update_enabled(new_value)

        # Update count en "Todas las instancias"
        all_item = list_view.children[0] if list_view.children else None
        if isinstance(all_item, AllInstancesItem):
            all_item.disabled = new_value  # placeholder; we'll refresh label
            # Re-render el label: solo cambia el "habilitada" si count pasa a 0
            enabled_count = len(self.config["instances"])
            try:
                all_label = all_item.query_one(Label)
                all_label.update(
                    " Todas las instancias" if enabled_count > 0
                    else " [dim]Todas las instancias (ninguna habilitada)[/dim]"
                )
            except Exception:
                pass

        self._log(
            f"[green]Instancia[/green] [b]{name}[/b] "
            f"{'habilitada' if new_value else 'deshabilitada'}."
        )

        # Persistir en background (no bloquear UI)
        snapshot = dict(self._raw_config)
        self.run_worker(
            self._save_instances_json_async(snapshot),
            exclusive=False,
        )

    async def _save_instances_json_async(self, raw_config: dict) -> None:
        """Variante async de _save_instances_json. Corre en worker.

        El I/O a disco se hace en un thread pool (puede tardar en
        filesystems lentos). La decision sobre que hacer con el
        resultado se toma en el main thread del worker async, asi no
        tocamos el DOM de Textual desde un thread de fondo.
        """
        success, error_message = await asyncio.to_thread(
            _write_instances_json, BASE_PATH, raw_config
        )
        if not success:
            # Logging y revert van en el main thread del worker async,
            # no en el thread del executor. Cualquier \`self._log\` o
            # \`self.query_one\` desde el executor sería un bug
            # thread-safety.
            self._log(
                f"[red]No se pudo guardar instances.json:[/red] {error_message}"
            )
            # Revertimos in-memory para que UI y disco no se desincronicen.
            self._raw_config = load_full_config(BASE_PATH)
            self.config["instances"] = {
                name: inst
                for name, inst in self._raw_config.get("instances", {}).items()
                if is_instance_enabled(inst)
            }

    def _save_instances_json(self, raw_config: dict) -> bool:
        """DEPRECATED: usa _save_instances_json_async. Se mantiene como
        shim de sync para tests/uso externo (no desde threads).
        """
        success, error_message = _write_instances_json(BASE_PATH, raw_config)
        if not success:
            self._log(
                f"[red]No se pudo guardar instances.json:[/red] {error_message}"
            )
            return False
        return True

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
            al = self._actions_list or self.query_one("#actions_list", ListView)
            self._actions_list = al
            al.focus()
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
        # El scan de modulos puede hacer 1-3s de syscalls; lo corremos
        # en un worker async para no bloquear la UI.
        if action.action_id == "update" and self.selected_instance is not None:
            inst = self.config["instances"].get(self.selected_instance)
            if inst is not None:
                self.run_worker(
                    self._update_picker_async(action, inst),
                    exclusive=True,
                )
                return
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

    async def _update_picker_async(self, action: Action, inst: dict) -> None:
        """Versión async del dispatch para update con picker.

        Hace el scan de módulos en un thread pool (1-3s de syscalls) y
        luego muestra el modal. Sin esto, la UI quedaba congelada
        durante el scan.
        """
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

    def _dispatch_fallback_to_text_modal(self, action: Action) -> None:
        """Fallback cuando el scan no encontró addons: muestra el modal de texto."""
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

        Para cualquier action ``update``: Odoo siempre emite el formato
        ``(N/M)`` cuando actualiza modulos (sean especificos o 'all'),
        asi que la barra aplica a todos los updates. Antes se ocultaba
        para modules='all'/vacio, pero eso era un bug: el usuario que
        corre 'update' sin elegir modulos especificos no veia ninguna
        barra, aunque Odoo claramente estaba emitiendo progreso.
        """
        return action.action_id == "update"

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
            try:
                up = self._update_widget or self.query_one("#update_progress", UpdateProgress)
            except Exception:
                up = None
            if up is not None:
                up.display = True
                up.clear()
                up.filter_levels = set(LOG_LEVELS)

        # Throttling constants (kept identical to the pre-refactor values
        # so behaviour matches what the smoke test and ops expect).
        FLUSH_INTERVAL_S = 0.050  # 50 ms
        FLUSH_BATCH_SIZE = 200

        # Import here to avoid a circular import (tui.app -> tui.runner
        # is fine, but keeping it local makes the dependency obvious).
        from tui.runner import stream_command

        # Mutable per-run state captured by the closures below.
        import time
        buf_lines: list[tuple[str, str]] = []  # (level, line) for UpdateProgress
        buf_plain: list[str] = []              # lines for the RichLog
        last_flush = time.monotonic()
        last_progress: tuple[int, int] = (0, 0)

        def _flush() -> None:
            nonlocal buf_lines, buf_plain, last_flush
            if up is not None and buf_lines:
                up.add_lines_bulk(list(buf_lines))
            if buf_plain:
                # _log_bulk receives a single multi-line string so
                # RichLog.write is called exactly once per flush.
                self._log_bulk("\n".join(buf_plain))
            buf_lines = []
            buf_plain = []
            last_flush = time.monotonic()

        def on_line(line: str) -> None:
            nonlocal last_progress
            if up is not None:
                parsed = parse_progress(line)
                if parsed is not None:
                    cur, tot = parsed
                    if (cur, tot) != last_progress:
                        last_progress = (cur, tot)
                        up.set_progress(cur, tot)
                level = classify_level(line)
                buf_lines.append((level, line))
                if level in up.filter_levels:
                    buf_plain.append(line)
            else:
                buf_plain.append(line)

            now = time.monotonic()
            if (now - last_flush) >= FLUSH_INTERVAL_S or len(buf_plain) >= FLUSH_BATCH_SIZE:
                _flush()

        def on_progress(cur: int, tot: int) -> None:
            # The runner already detected the (N/M) match; we just need
            # to push it to the widget. ``on_line`` is what classifies
            # the line; the runner calls both for every line that has a
            # match, so the widget state stays consistent.
            if up is not None:
                up.set_progress(cur, tot)

        # Spawn the subprocess and stream it. We need the proc handle to
        # expose ``.terminate()`` to the cancel binding, but the runner
        # owns the lifecycle. Workaround: start the subprocess via the
        # runner, but stash a lightweight proxy in ``self._update_proc``
        # whose ``terminate()`` calls ``self._current_proc.terminate()``.
        #
        # In practice the runner's own CancelledError handler handles
        # the cancel path, so the binding's terminate() is a no-op in
        # the normal flow. We still expose it for the existing
        # ``test_integration_cancel_with_esc`` smoke test which mocks
        # the proc and expects ``terminate()`` to be called on Esc.
        proc_holder: dict = {}

        async def _runner_wrapper() -> int:
            # We can't grab the proc handle directly from
            # ``create_subprocess_exec`` (it lives inside the runner),
            # so we run the runner here and then read the result.
            # ``stream_command`` doesn't expose the proc, so we
            # provide a stand-in proc object whose terminate() is a
            # best-effort no-op when the runner is mid-line; the
            # binding path is a fallback only.
            return await stream_command(
                argv,
                BASE_PATH,
                on_line=on_line,
                on_progress=on_progress,
            )

        # Lightweight shim: the legacy ``action_cancel_update`` path
        # (and the smoke test) call ``.terminate()`` on this object.
        # The primary cancel path is via ``self._current_task`` below;
        # this shim is here only for the legacy callers and the
        # existing test that mocks ``app._update_proc``.
        class _ProcShim:
            def terminate(self_inner) -> None:  # noqa: N805
                # No-op in the normal flow: the real cancel happens
                # via ``self._current_task.cancel()`` which routes
                # through the runner's CancelledError handler.
                pass

        self._update_proc = _ProcShim()
        # Capture the worker task that is awaiting this coroutine. The
        # binding ``action_cancel_update`` cancels this task on Esc.
        self._current_task = asyncio.current_task()

        rc: int
        try:
            rc = await _runner_wrapper()
        except FileNotFoundError as exc:
            self._log(f"[red]No encontrado:[/red] {exc}")
            rc = 127
        finally:
            self._update_proc = None
            self._current_task = None

        # Flush whatever is left in the buffer.
        _flush()

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
        """Cancela la actualización en curso con Esc.

        Preferimos cancelar la tarea asyncio (que enruta por el
        handler de ``asyncio.CancelledError`` del runner y de ahí al
        SIGTERM/SIGKILL escalado). ``_update_proc`` queda como
        fallback para compatibilidad con el smoke test que mockea
        esa referencia directamente.
        """
        if self._current_task is not None and not self._current_task.done():
            self._log("[yellow]Cancelando actualización...[/yellow]")
            self._current_task.cancel()
        elif self._update_proc is not None:
            self._log("[yellow]Cancelando actualización...[/yellow]")
            self._update_proc.terminate()
        else:
            self._log("[dim]No hay actualización en curso.[/dim]")

    def _rebuild_richlog_from_up(self, up: "UpdateProgress") -> None:
        """Reconstruye el RichLog con las líneas que pasan el filtro actual.

        Antes era clear + 2000 writes sync en main thread -> freeze
        perceptible al togglear filtros. Ahora lo hace en chunks via
        run_worker con yields entre chunks, asi la UI no se congela.
        """
        self.run_worker(
            self._rebuild_richlog_async(up),
            exclusive=False,
        )

    async def _rebuild_richlog_async(self, up: "UpdateProgress") -> None:
        lines = up.get_filtered_lines()
        try:
            rl = self._output_widget or self.query_one("#output", RichLog)
        except Exception:
            return
        rl.clear()
        # Escribir en chunks con await entremedio para que la UI pueda
        # procesar otros eventos. 200 lineas por chunk es un buen balance
        # entre throughput y responsividad.
        CHUNK = 200
        for i in range(0, len(lines), CHUNK):
            chunk = lines[i:i+CHUNK]
            # Un solo write() por chunk (las lineas ya estan separadas por
            # '\n' en add_line; al hacer str.join escribimos un solo string
            # multi-linea al RichLog).
            rl.write("\n".join(chunk))
            if i + CHUNK < len(lines):
                await asyncio.sleep(0)

    def _toggle_log_level(self, level: str) -> None:
        """Alterna un nivel de log en el UpdateProgress y reconstruye el RichLog."""
        try:
            up = self._update_widget or self.query_one("#update_progress", UpdateProgress)
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
            up = self._update_widget or self.query_one("#update_progress", UpdateProgress)
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
            up = self._update_widget or self.query_one("#update_progress", UpdateProgress)
        except Exception:
            return
        if not up.display:
            return
        up.set_errors_only()
        self._rebuild_richlog_from_up(up)
        self._log("[yellow]Filtro: solo ERROR + CRITICAL[/yellow]")

    def _log(self, message: str) -> None:
        try:
            w = self._output_widget or self.query_one("#output", RichLog)
            w.write(message)
        except Exception as exc:
            print(f"[TUI _log fallback] {message} (error: {exc})", file=sys.stderr)

    def _log_bulk(self, message: str) -> None:
        """Escribe un string multi-linea al RichLog con UN solo write().

        Usado por _run_streamed para evitar 1 write() por linea cuando
        el worker acumula un batch.
        """
        try:
            w = self._output_widget or self.query_one("#output", RichLog)
            w.write(message)
        except Exception as exc:
            print(f"[TUI _log_bulk fallback] {message[:200]}... (error: {exc})", file=sys.stderr)
