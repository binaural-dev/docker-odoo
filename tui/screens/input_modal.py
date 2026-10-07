"""Generic modal that asks one or more labelled inputs.

UX:
- Title prominente con color de accent y separacion del resto
- Subtitle opcional (en dim italic) para contexto
- Cada field tiene label visible + input + hint opcional
- Fields opcionales se marcan con sufijo (opcional)
- Buttons Cancelar / Ejecutar claramente diferenciados (error / success)
- Boton Enter submitea, Esc cancela
"""

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from tui.models import ARG_LANG  # used indirectly via field keys


class InputModal(ModalScreen[Optional[dict]]):
    """Generic modal that asks one or more labelled inputs."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+enter", "submit", "Submit"),
    ]

    def __init__(
        self,
        title: str,
        fields: list,
        defaults: Optional[dict] = None,
        subtitle: str = "",
    ):
        super().__init__()
        self.title_text = title
        self.subtitle_text = subtitle
        # fields: list of {key, label, placeholder, password, hint, optional}
        self.fields = fields
        self.defaults = defaults or {}

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_box"):
            yield Label(self.title_text, id="modal_title")
            if self.subtitle_text:
                yield Label(self.subtitle_text, id="modal_subtitle")
            with Vertical(id="modal_fields"):
                self._inputs: dict = {}
                for f in self.fields:
                    label_text = f["label"]
                    if f.get("optional"):
                        label_text += "  [dim](opcional)[/dim]"
                    yield Label(label_text, classes="field_label")
                    placeholder = f.get("placeholder", "")
                    pw = f.get("password", False)
                    inp = Input(
                        placeholder=placeholder,
                        password=pw,
                        id=f"inp_{f['key']}",
                    )
                    if f["key"] in self.defaults:
                        inp.value = str(self.defaults[f["key"]])
                    self._inputs[f["key"]] = inp
                    yield inp
                    if f.get("hint"):
                        yield Label(f["hint"], classes="field_hint")
            with Horizontal(id="modal_buttons"):
                yield Button("✕ Cancelar  [dim](Esc)[/dim]", id="cancel", variant="error")
                yield Button("✓ Ejecutar  [dim](Enter)[/dim]", id="ok", variant="success")

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
            self._submit()

    def _submit(self) -> None:
        if not self._inputs:
            self.dismiss({})
            return
        result = {}
        for key, inp in self._inputs.items():
            value = inp.value.strip()
            if not value:
                # Si el field es opcional, lo aceptamos vacio.
                # Si no, no submitteamos y dejamos que el user corrija.
                field = next((f for f in self.fields if f["key"] == key), None)
                if field and field.get("optional"):
                    continue
                inp.focus()
                return
            result[key] = value
        self.dismiss(result)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_submit(self) -> None:
        self._submit()
