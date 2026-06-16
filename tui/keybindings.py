"""Keybindings and binding-triggered side effects for the TUI.

This is a mixin: methods on ``KeybindingsMixin`` expect ``self`` to be
a ``DockerOdooApp`` (or any class that provides the same surface). It
centralises:

  * The ``BINDINGS`` list (the table of keyboard shortcuts).
  * All ``action_*`` methods (one per binding).
  * The persistence side effects triggered by ``action_toggle_instance``
    (the ``_save_instances_json_*`` family).
  * The log-filter UI helpers (``_toggle_log_level``,
    ``_rebuild_richlog_from_up``).

The split exists for the same reason as the dispatch mixin: keeping
``tui/app.py`` readable and isolating concerns. A new binding only
touches this file; a new dispatch rule only touches ``tui/dispatch.py``.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from textual.binding import Binding
from textual.widgets import ListView, Label

from tui.config import BASE_PATH, is_instance_enabled, load_full_config
from tui.widgets.items import (
    AllInstancesItem,
    InstanceItem,
)
from tui.widgets.update_progress import UpdateProgress


# The shared BINDINGS list. Re-exported from here so DockerOdooApp
# doesn't need to know the full list — it just inherits the mixin.
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


class KeybindingsMixin:
    """Mixin providing BINDINGS + all action_* handlers.

    Expected attributes on ``self`` (provided by ``DockerOdooApp``):
      - ``_raw_config: dict`` (full instances.json)
      - ``config: dict`` (filtered view)
      - ``_instances_list: ListView``
      - ``_actions_list: ListView``
      - ``_output_widget: RichLog``
      - ``_update_widget: UpdateProgress``
      - ``_current_task: Optional[asyncio.Task]``
      - ``_update_proc: Optional[object]``
      - ``_log(message)``
      - ``refresh_instances()``
    """

    _raw_config: dict
    config: dict
    _instances_list: Optional[ListView]
    _actions_list: Optional[ListView]
    _output_widget: Optional[object]
    _update_widget: Optional[object]
    _current_task: Optional[asyncio.Task]
    _update_proc: Optional[object]

    # ---- toggle persistence (bound to Space) ----

    def action_toggle_instance(self) -> None:
        """Toggle the ``enabled`` flag of the highlighted instance and persist.

        Optimizado: NO relee instances.json ni repinta la lista entera.
        Solo actualiza in-place el item afectado y la vista filtrada
        (self.config). El save a disco corre en background.
        """
        list_view = self._instances_list
        if list_view is None:
            try:
                list_view = self.query_one("#instances_list", ListView)
                self._instances_list = list_view
            except Exception:
                return
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
        from tui.app import _write_instances_json
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
        from tui.app import _write_instances_json
        success, error_message = _write_instances_json(BASE_PATH, raw_config)
        if not success:
            self._log(
                f"[red]No se pudo guardar instances.json:[/red] {error_message}"
            )
            return False
        return True

    # ---- cancel ----

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

    # ---- refresh ----

    def action_refresh(self) -> None:
        """Recarga instances.json y repinta las dos listas."""
        self.refresh_instances()
        self.refresh_actions()
        self._log("[green]Instancias y acciones recargadas.[/green]")

    # ---- log level filter ----

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
            rl = self._output_widget or self.query_one("#output", object)
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
