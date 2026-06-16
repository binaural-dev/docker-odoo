"""DockerOdooApp — main Textual application for the docker-odoo TUI.

This module is the composition root: it wires up the widget tree,
hooks the event handlers, and inherits behaviour from two mixins:

  * ``DispatchMixin`` (tui.dispatch) — the action-dispatch pipeline.
  * ``KeybindingsMixin`` (tui.keybindings) — BINDINGS + action_*.

It also hosts the streaming coroutine (``_run_streamed``) because
that one is tightly coupled to the per-instance UI state (progress
widget, RichLog, log throttling). Moving it out would require
passing too many callbacks to be worth it.
"""

import asyncio
import json
import os
import shlex
import sys
import time
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    ListView,
    RichLog,
    Static,
    Label,
)

from tui.config import BASE_PATH, TCSS_PATH, is_instance_enabled, load_full_config
from tui.dispatch import DispatchMixin
from tui.keybindings import BINDINGS, KeybindingsMixin
from tui.models import Action, LOG_LEVELS
from tui.parser import classify_level, parse_progress
from tui.screens.confirm_modal import ConfirmModal
from tui.screens.input_modal import InputModal
from tui.screens.module_picker import ModulePicker
from tui.widgets.items import (
    ActionItem,
    AllInstancesItem,
    CategoryHeaderItem,
    EmptyStateItem,
    InstanceItem,
    NoInstanceActionItem,
)
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


class DockerOdooApp(DispatchMixin, KeybindingsMixin, App):
    """Textual app: instances list | actions list | progress | output."""

    CSS_PATH = TCSS_PATH
    BINDINGS = BINDINGS

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
        # cancel path cancels ``_current_task`` instead; this attribute
        # is the legacy fallback used only by the test.
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
        from tui.models import ACTIONS, CATEGORY_ORDER
        total = 0
        for cat in CATEGORY_ORDER:
            # Solo agregar header si hay al menos una accion en esta categoria
            cat_actions = [a for a in ACTIONS if a.category == cat]
            if not cat_actions:
                continue
            list_view.append(CategoryHeaderItem(cat))
            from tui.models import ARG_INSTANCE
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

    # ---------- streaming execution (app.py owns this) ----------

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
            rc = await stream_command(
                argv,
                BASE_PATH,
                on_line=on_line,
                on_progress=on_progress,
            )
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

    # ---------- log sink (used by the mixins) ----------

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
