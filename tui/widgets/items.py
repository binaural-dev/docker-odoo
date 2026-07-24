"""ListView item widgets for the main screen."""

from textual.widgets import Label, ListItem

from tui.models import Action, CATEGORY_BADGE_WIDTH


class InstanceItem(ListItem):
    """Una instancia con su version, puerto y database.

    Layout:  [●/○] nombre  v17.0  :8070  db: conti
    El indicador circular muestra si esta habilitada (● verde) o
    deshabilitada (○ gris), para que el usuario distinga de un vistazo
    cuales instancias van a ejecutarse con el comando.
    """

    def __init__(self, name: str, version: str, port: int, database: str, enabled: bool = True):
        self._name = name
        self._version = version
        self._port = port
        self._database = database
        super().__init__(Label(self._render_row(enabled)))
        self.instance_name = name
        self.instance_enabled = enabled

    def _render_row(self, enabled: bool) -> str:
        indicator = "[green]●[/green]" if enabled else "[dim]○[/dim]"
        # Padding manual del nombre (sin markup) para que el ancho visible
        # sea consistente independiente de si esta enabled o dim.
        name_visible = self._name.ljust(22)
        if enabled:
            name_part = name_visible
        else:
            # Wrapeamos cada palabra con dim para que el padding se mantenga
            # pero todo el texto quede gris.
            name_part = f"[dim]{name_visible}[/dim]"
        version_part = f"[dim]v{self._version:<6}[/dim]"
        port_part = f"[dim]:{self._port:<5}[/dim]"
        db_part = f"[dim]db: {self._database}[/dim]"
        return f" {indicator}  {name_part}  {version_part}  {port_part}  {db_part}"

    def update_enabled(self, enabled: bool) -> None:
        """Update el indicador visual in-place (sin repintar la lista)."""
        self.instance_enabled = enabled
        try:
            label = self.query_one(Label)
            label.update(self._render_row(enabled))
        except Exception:
            pass


class AllInstancesItem(ListItem):
    """Item especial de la lista de instancias: "Todas las instancias".

    Se renderiza como un ListItem cyan con la cuenta de instancias
    habilitadas; si ninguna esta habilitada, se muestra dim y queda
    disabled para que el usuario no ejecute un comando sobre un set
    vacio por accidente.
    """

    def __init__(self, enabled_count: int = 0):
        # Icono + label para distinguir de las instancias individuales
        if enabled_count > 0:
            label = f" [bold cyan]\u2192 Todas las instancias ({enabled_count})[/bold cyan]"
        else:
            label = " [dim]\u2192 Todas las instancias (ninguna habilitada)[/dim]"
        super().__init__(Label(label))
        self.instance_name = None
        self.disabled = enabled_count == 0


class EmptyStateItem(ListItem):
    """Item de placeholder para listas vacias (sin instancias, sin acciones, etc).

    No es seleccionable. Muestra un mensaje centrado con un hint
    para que el usuario sepa que hacer.
    """

    def __init__(self, message: str, hint: str = ""):
        label = f"\n[dim italic]{message}[/dim italic]"
        if hint:
            label += f"\n[dim]{hint}[/dim]"
        super().__init__(Label(label))
        self.disabled = True
        self.instance_name = None


class ActionItem(ListItem):
    """Una accion de la lista derecha.

    Layout:  [cyan]Lifecycle[/cyan]   Build images
    El nombre de la categoria se muestra en cyan como badge visual.
    El label de la accion va en texto normal.
    """

    def __init__(self, action: Action):
        badge = f"{action.category:<{CATEGORY_BADGE_WIDTH}}"
        super().__init__(Label(f" [cyan]{badge}[/cyan]  {action.label}"))
        self.action = action


class CategoryHeaderItem(ListItem):
    """Header visual para agrupar acciones por categoria en la lista.

    No es seleccionable (disabled=True), solo provee separador visual
    entre grupos de acciones.
    """

    def __init__(self, category: str):
        self._category = category
        super().__init__(Label(f" ── {category} ──"))
        self.disabled = True
        self.instance_name = None
        # Agregamos una clase CSS via attribute para que el .tcss
        # pueda darle estilo de header (background, bold, etc).
        self.add_class("category_header")


class NoInstanceActionItem(ListItem):
    """Special: actions that don't need an instance (build, list, validate, sync, upgrade_manifest)."""

    def __init__(self, action: Action):
        badge = f"{action.category:<{CATEGORY_BADGE_WIDTH}}"
        super().__init__(Label(f" [cyan]{badge}[/cyan]  {action.label}"))
        self.action = action
