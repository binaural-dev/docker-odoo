"""fzf-style two-pane module picker modal."""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option


class ModulePicker(ModalScreen[Optional[list]]):
    """fzf-style two-pane module picker.

    Left pane: filtered list of available modules (those found on disk
    under the instance's resolved addons paths). Modules already in
    ``selected`` are prefixed with a check mark.
    Right pane: the modules the user has picked.
    Bottom: footer with key hints and an Execute button.

    On dismiss returns:
      * ``None``  -> user cancelled (Esc)
      * ``[]``    -> user confirmed with an empty selection (interpreted
                     as ``all`` by the caller; the Execute button label
                     changes to "Ejecutar (all)" in that case)
      * ``[m1, m2, ...]`` -> user-confirmed module list
    """

    BINDINGS = [
        Binding("escape", "cancel_picker", "Cancel"),
        Binding("l", "clear_selection", "Limpiar"),
        Binding("e", "execute_picker", "Ejecutar"),
    ]

    def __init__(
        self,
        instance_name: str,
        available_modules: list,
        preselected: Optional[list] = None,
    ):
        super().__init__()
        self.instance_name = instance_name
        self.available_modules = sorted(available_modules)
        self.preselected = list(preselected or [])
        self.selected: list[str] = list(self.preselected)
        self._filter: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_box"):
            yield Label(
                f"Update módulos — {self.instance_name}", id="modal_title"
            )
            yield Label(
                f"Seleccioná los módulos a actualizar. "
                f"[dim](vacío = todos)[/dim]",
                id="modal_subtitle",
            )
            yield Label("Filtro:", classes="field_label")
            yield Input(placeholder="escribí para filtrar por nombre", id="filter_input")
            with Horizontal(id="picker_panes"):
                with Vertical(id="picker_left"):
                    yield Label("Disponibles", classes="field_label")
                    yield OptionList(id="available_list")
                with Vertical(id="picker_right"):
                    yield Label("A actualizar", classes="field_label")
                    yield OptionList(id="selected_list")
            with Horizontal(id="picker_hints_row"):
                yield Static(
                    "[Tab] cambiar panel   "
                    "[Enter] +/-   "
                    "[L] limpiar   [E] ejecutar   [Esc] cancelar",
                    id="picker_hints",
                )
            with Horizontal(id="modal_buttons"):
                yield Button("✕ Cancelar  [dim](Esc)[/dim]", id="cancel", variant="error")
                yield Button("✓ Ejecutar", id="ok", variant="success")

    def on_mount(self) -> None:
        self._render_available()
        self._render_selected()
        self.query_one("#filter_input", Input).focus()

    # ----- rendering -----

    def _render_available(self) -> None:
        view = self.query_one("#available_list", OptionList)
        view.clear_options()
        needle = self._filter.lower()
        for m in self.available_modules:
            if needle and needle not in m.lower():
                continue
            label = f" ✓ {m}" if m in self.selected else f"   {m}"
            view.add_option(Option(label, id=m))

    def _render_selected(self) -> None:
        view = self.query_one("#selected_list", OptionList)
        view.clear_options()
        for m in self.selected:
            view.add_option(Option(f" ▸ {m}", id=m))
        self._refresh_execute_label()

    def _refresh_execute_label(self) -> None:
        btn = self.query_one("#ok", Button)
        if self.selected:
            btn.label = f"Ejecutar ({len(self.selected)})"
        else:
            btn.label = "Ejecutar (all)"

    # ----- events -----

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter_input":
            return
        self._filter = event.value
        self._render_available()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        name = getattr(event.option, "id", None)
        if name is None:
            return
        if event.option_list.id == "available_list":
            if name in self.selected:
                self.selected.remove(name)
            else:
                self.selected.append(name)
            self._render_available()
            self._render_selected()
        elif event.option_list.id == "selected_list":
            if name in self.selected:
                self.selected.remove(name)
            self._render_available()
            self._render_selected()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.action_cancel_picker()
        elif event.button.id == "ok":
            self.action_execute_picker()

    # ----- actions -----

    def action_cancel_picker(self) -> None:
        self.dismiss(None)

    def action_clear_selection(self) -> None:
        self.selected = []
        self._render_available()
        self._render_selected()

    def action_execute_picker(self) -> None:
        # An empty selection means "all" — the caller handles the
        # semantics; we just hand back an empty list.
        self.dismiss(list(self.selected))
