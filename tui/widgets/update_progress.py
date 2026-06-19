"""Widget de progreso de actualización de módulos.

Se muestra arriba del RichLog durante una operación ``update``
con módulos conocidos. Es puramente presentacional: recibe
eventos via reactives y bindings, no sabe de subprocesses.
"""

import asyncio

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Label, ProgressBar, Static

from tui.models import LOG_LEVELS, LOG_LEVEL_SHORT, FILTER_LEVEL_IDS
from tui.parser import classify_level


class UpdateProgress(Vertical):
    """Widget de progreso de actualización de módulos."""

    progress_current: int = reactive(0)
    progress_total: int = reactive(0)
    filter_levels: set[str] = reactive(set(LOG_LEVELS))

    def __init__(self, instance_name: str = "", modules: str = "", **kwargs):
        super().__init__(**kwargs)
        self._instance_name = instance_name
        self._modules = modules
        self._all_lines: list[tuple[str, str]] = []  # (level, line)
        self._idle_timer: asyncio.TimerHandle | None = None
        # Cached widget refs — populated in on_mount, fall back to
        # query_one in case the widget hasn't been mounted yet (e.g.
        # headless tests).
        self._pb: ProgressBar | None = None
        self._progress_label: Label | None = None
        self._remaining_label: Label | None = None

    def on_mount(self) -> None:
        """Cache widget refs once the DOM is ready."""
        try:
            self._pb = self.query_one("#up_progress", ProgressBar)
        except Exception:
            self._pb = None
        try:
            self._progress_label = self.query_one("#up_progress_label", Label)
        except Exception:
            self._progress_label = None
        try:
            self._remaining_label = self.query_one("#up_remaining", Label)
        except Exception:
            self._remaining_label = None

    def compose(self) -> ComposeResult:
        title = (
            f"Actualizando módulos — {self._instance_name}"
            if self._instance_name
            else "Actualizando módulos"
        )
        yield Static(title, id="up_title")
        yield ProgressBar(total=0, id="up_progress", show_percentage=True)
        yield Label("Progreso: 0 / 0 (0%)", id="up_progress_label")
        yield Label("Quedan: 0 módulos", id="up_remaining")
        with Horizontal(id="up_filters_row"):
            yield Static(self._filter_chip("INFO"), id="filt_info")
            yield Static(self._filter_chip("WARNING"), id="filter_warning")
            yield Static(self._filter_chip("ERROR"), id="filter_error")
            yield Static(self._filter_chip("CRITICAL"), id="filt_critical")
        with Horizontal(id="up_hints_row"):
            yield Static(" [Esc] Cancelar ", id="hint_esc")
            yield Static(" [0] Todos ", id="hint_all")
            yield Static(" [9] Solo error/warn ", id="hint_errors")

    # ----- filter chip helpers -----

    @staticmethod
    def _filter_chip(level: str, active: bool = True) -> str:
        short = LOG_LEVEL_SHORT.get(level, "?")
        mark = "✓" if active else "✗"
        color = "green" if active else "gray"
        return f"[{color}][{short}]{level} {mark}[/{color}]"

    def _refresh_filter_chips(self) -> None:
        for level, fid in FILTER_LEVEL_IDS.items():
            chip = self.query_one(f"#{fid}", Static)
            chip.update(self._filter_chip(level, level in self.filter_levels))

    # ----- progress and timeout -----

    def set_progress(self, current: int, total: int) -> None:
        self.progress_total = total
        self.progress_current = current
        self._reset_idle_timer()

    def _reset_idle_timer(self) -> None:
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None
        self._idle_timer = asyncio.get_event_loop().call_later(
            5.0, self._on_idle_timeout
        )

    def _on_idle_timeout(self) -> None:
        """Pasaron 5s sin progreso: cambia el ProgressBar a indeterminado."""
        try:
            pb = self._pb or self.query_one("#up_progress", ProgressBar)
        except Exception:
            return
        pb.total = None

    # ----- reactive watchers -----

    def watch_progress_current(self, value: int) -> None:
        try:
            pb = self._pb or self.query_one("#up_progress", ProgressBar)
            pl = self._progress_label or self.query_one("#up_progress_label", Label)
            rl = self._remaining_label or self.query_one("#up_remaining", Label)
        except Exception:
            return
        total = self.progress_total
        if total > 0:
            pb.progress = value
            pb.total = total
            pct = int(value / total * 100)
            pl.update(
                f"Progreso: {value} / {total} ({pct}%)"
            )
            remaining = total - value
            rl.update(
                f"Quedan: {remaining} módulo{'s' if remaining != 1 else ''}"
            )

    def watch_progress_total(self, value: int) -> None:
        if value > 0:
            try:
                pb = self._pb or self.query_one("#up_progress", ProgressBar)
            except Exception:
                return
            pb.total = value

    def watch_filter_levels(self, value: set[str]) -> None:
        self._refresh_filter_chips()

    # ----- line management -----

    def add_line(self, level: str, line: str) -> None:
        self._all_lines.append((level, line))
        if len(self._all_lines) > 2000:
            self._all_lines.pop(0)

    def add_lines_bulk(self, items: list[tuple[str, str]]) -> None:
        """Bulk append (level, line) tuples, trimming to max 2000.

        O(n) en lugar de O(n^2) que seria llamar add_line() en un loop
        con list.pop(0). Ademas las llamadas desde el worker vienen
        batched cada ~50ms.
        """
        if not items:
            return
        self._all_lines.extend(items)
        if len(self._all_lines) > 2000:
            # Mantener solo las ultimas 2000 (asumimos que el mas nuevo esta al final)
            del self._all_lines[: len(self._all_lines) - 2000]

    def get_filtered_lines(self) -> list[str]:
        """Retorna las líneas que pasan el filtro actual."""
        return [
            line
            for lvl, line in self._all_lines
            if lvl in self.filter_levels
        ]

    def clear(self) -> None:
        self._all_lines.clear()
        self.progress_current = 0
        self.progress_total = 0
        self._reset_idle_timer()

    # ----- click handlers for filter chips -----

    def on_click(self, event: events.Click) -> None:
        """Handle clicks on filter chips."""
        widget = event.widget
        if widget is None or not widget.id or not widget.id.startswith("filt_"):
            return
        level_map = {
            "filt_info": "INFO",
            "filter_warning": "WARNING",
            "filter_error": "ERROR",
            "filt_critical": "CRITICAL",
        }
        level = level_map.get(widget.id)
        if level is None:
            return
        self._toggle_level(level)

    def _toggle_level(self, level: str) -> None:
        if level in self.filter_levels:
            self.filter_levels = self.filter_levels - {level}
        else:
            self.filter_levels = self.filter_levels | {level}

    def set_all_levels(self, active: bool) -> None:
        if active:
            self.filter_levels = set(LOG_LEVELS)
        else:
            self.filter_levels = set()

    def set_errors_only(self) -> None:
        self.filter_levels = {"ERROR", "CRITICAL"}
