"""Confirmation modal (yes / no)."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmModal(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, message: str, yes_label: str = "Sí", no_label: str = "No"):
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_cancel(self) -> None:
        self.dismiss(False)
