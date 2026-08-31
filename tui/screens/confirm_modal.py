"""Confirmation modal (yes / no).

UX:
- Title en accent (bold)
- Message centrado y legible (padding generoso)
- Botones No / Si con colores rojo / verde para reforzar la accion
- Cancelar con Esc, seleccionar con Enter
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmModal(ModalScreen[bool]):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit_yes", "Yes"),
    ]

    def __init__(
        self,
        title: str,
        message: str,
        yes_label: str = "✓ Sí, confirmar",
        no_label: str = "✕ No, cancelar",
    ):
        super().__init__()
        self.title_text = title
        self.message = message
        self.yes_label = yes_label
        self.no_label = no_label

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_box"):
            yield Label(self.title_text, id="modal_title")
            yield Label(self.message, id="modal_message")
            with Horizontal(id="modal_buttons"):
                yield Button(self.no_label, id="no", variant="error")
                yield Button(self.yes_label, id="yes", variant="success")

    def on_mount(self) -> None:
        # Focus en el "No" por default: las confirmaciones destructivas
        # son mas seguras si el usuario tiene que moverse a proposito.
        self.query_one("#no", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        elif event.button.id == "no":
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_submit_yes(self) -> None:
        self.dismiss(True)
