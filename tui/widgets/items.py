"""ListView item widgets for the main screen."""

from textual.widgets import Label, ListItem

from tui.models import Action, CATEGORY_BADGE


class InstanceItem(ListItem):
    def __init__(self, name: str, version: str, port: int, database: str, enabled: bool = True):
        self._name = name
        self._version = version
        self._port = port
        self._database = database
        super().__init__(Label(self._render_row(enabled)))
        self.instance_name = name
        self.instance_enabled = enabled

    def _render_row(self, enabled: bool) -> str:
        row = f" {self._name:<14}  {self._version:<5}  :{self._port:<5}  db: {self._database}"
        if not enabled:
            row = f"[dim]{row}  [off][/dim]"
        return row

    def update_enabled(self, enabled: bool) -> None:
        """Update the visible label in-place (sin repintar la lista entera)."""
        self.instance_enabled = enabled
        try:
            label = self.query_one(Label)
            label.update(self._render_row(enabled))
        except Exception:
            pass


class AllInstancesItem(ListItem):
    def __init__(self, enabled_count: int = 0):
        label = " Todas las instancias" if enabled_count > 0 else \
            " [dim]Todas las instancias (ninguna habilitada)[/dim]"
        super().__init__(Label(label))
        self.instance_name = None
        self.disabled = enabled_count == 0


class ActionItem(ListItem):
    def __init__(self, action: Action):
        badge = CATEGORY_BADGE.get(action.category, "")
        super().__init__(Label(f" {badge:<10} {action.label}"))
        self.action = action


class NoInstanceActionItem(ListItem):
    """Special: actions that don't need an instance (build, list, validate, sync, upgrade_manifest)."""

    def __init__(self, action: Action):
        badge = CATEGORY_BADGE.get(action.category, "")
        super().__init__(Label(f" {badge:<10} {action.label}"))
        self.action = action
