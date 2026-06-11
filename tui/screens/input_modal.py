"""Generic modal that asks one or more labelled inputs."""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from tui.models import ARG_LANG  # used indirectly via field keys


class InputModal(ModalScreen[Optional[dict]]):
    """Generic modal that asks one or more labelled inputs."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, fields: list, defaults: Optional[dict] = None):
        super().__init__()
        self.title_text = title
        self.fields = fields  # list of dicts: {key, label, placeholder, password}
        self.defaults = defaults or {}

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_box"):
            yield Label(self.title_text, id="modal_title")
            with Vertical(id="modal_fields"):
                self._inputs = {}
                for f in self.fields:
                    yield Label(f["label"], classes="field_label")
                    placeholder = f.get("placeholder", "")
                    pw = f.get("password", False)
                    inp = Input(placeholder=placeholder, password=pw, id=f"inp_{f['key']}")
                    if f["key"] in self.defaults:
                        inp.value = str(self.defaults[f["key"]])
                    self._inputs[f["key"]] = inp
                    yield inp
            with Horizontal(id="modal_buttons"):
                yield Button("Cancelar", id="cancel", variant="error")
                yield Button("Ejecutar", id="ok", variant="success")

    def on_mount(self) -> None:
        first = self.query(Input).first()
        if first is not None:
            first.focus()
        else:
            ok = self.query_one("#ok", Button)
            ok.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "ok":
            if not self._inputs:
                self.dismiss({})
            else:
                self.dismiss({k: inp.value.strip() for k, inp in self._inputs.items()})

    def action_cancel(self) -> None:
        self.dismiss(None)
