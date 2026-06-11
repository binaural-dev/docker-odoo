"""ListView item widgets for the main screen."""

from textual.widgets import Label, ListItem

from tui.models import Action, CATEGORY_BADGE


class InstanceItem(ListItem):
    def __init__(self, name: str, version: str, port: int, database: str, enabled: bool = True):
        row = f" {name:<14}  {version:<5}  :{port:<5}  db: {database}"
        if not enabled:
            row = f"[dim]{row}  [off][/dim]"
        super().__init__(Label(row))
        self.instance_name = name
        self.instance_enabled = enabled


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
