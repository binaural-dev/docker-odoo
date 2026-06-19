"""Domain types, constants, and action definitions.

Purely declarative — no side effects, no Textual imports.
"""

from dataclasses import dataclass, field


# Arg kinds requested from the user before the command is built.
ARG_INSTANCE = "instance"   # pre-selected from the instance list
ARG_DB = "db"               # database name (with picker when possible)
ARG_MODULES = "modules"     # comma-separated modules
ARG_USER = "user"           # login
ARG_PASSWORD = "password"   # password (default: admin)
ARG_REPO = "repo"           # git repo name
ARG_BRANCH = "branch"       # git branch
ARG_ZIP = "zip"             # backup zip file
ARG_DEST_DB = "dest_db"     # destination database name
ARG_TARGET_PG = "pg_major"  # target postgres major version
ARG_PATH = "path"           # generic output path
ARG_TEST_TAGS = "test_tags"
ARG_INSTALL = "install_modules"
ARG_LANG = "load_language"  # optional, only used by the update action


@dataclass
class Action:
    action_id: str
    label: str
    category: str
    description: str
    needs: list = field(default_factory=list)
    interactive: bool = False  # bash/logs: suspend TUI, run, resume
    needs_all_option: bool = False  # show "Todas las instancias" entry


ACTIONS: list[Action] = [
    # Lifecycle
    Action("build", "Build images", "Lifecycle",
           "Genera Dockerfiles, compose y nginx; construye imágenes",
           needs_all_option=True),
    Action("start", "Start", "Lifecycle",
           "Inicia instancia(s) y DB(s) managed",
           needs=[ARG_INSTANCE], needs_all_option=True),
    Action("stop", "Stop", "Lifecycle",
           "Detiene instancia(s) y DB(s) si quedan huérfanas",
           needs=[ARG_INSTANCE], needs_all_option=True),
    Action("restart", "Restart", "Lifecycle",
           "Reinicia instancia(s)",
           needs=[ARG_INSTANCE], needs_all_option=True),
    Action("list", "List containers", "Lifecycle",
           "Lista contenedores docker compose en ejecución"),

    # Acceso
    Action("bash", "Bash en contenedor", "Acceso",
           "Abre una shell interactiva dentro del contenedor Odoo",
           needs=[ARG_INSTANCE], interactive=True),
    Action("logs", "Logs", "Acceso",
           "Sigue los logs en tiempo real",
           needs=[ARG_INSTANCE], interactive=True, needs_all_option=True),
    Action("psql", "psql", "Acceso",
           "Conecta a PostgreSQL dentro del contenedor Odoo",
           needs=[ARG_INSTANCE, ARG_DB], interactive=True),

    # Mantenimiento
    Action("fix-files", "Fix filestore perms", "Mantenimiento",
           "Corrige permisos del filestore",
           needs=[ARG_INSTANCE], needs_all_option=True),
    Action("init", "Init addons check", "Mantenimiento",
           "Verifica que los addons referenciados existen",
           needs=[ARG_INSTANCE], needs_all_option=True),
    Action("validate-instances", "Validate instances.json", "Mantenimiento",
           "Valida el archivo instances.json"),
    Action("hosts-status", "Sync /etc/hosts", "Mantenimiento",
           "Muestra diff entre /etc/hosts y los subdominios esperados"),
    Action("remove", "Remove", "Mantenimiento",
           "Elimina contenedores y volúmenes de la instancia",
           needs=[ARG_INSTANCE], needs_all_option=True),

    # Módulos / DB
    Action("update", "Update módulos", "Módulos / DB",
           "Actualiza módulos via scripts/odoo-update (admite --load-language)",
           needs=[ARG_INSTANCE, ARG_DB, ARG_MODULES]),
    Action("pw", "Reset password", "Módulos / DB",
           "Restablece la contraseña de un usuario",
           needs=[ARG_INSTANCE, ARG_DB, ARG_USER, ARG_PASSWORD]),

    # Sync
    Action("sync", "Sync submódulos", "Sync",
           "Sincroniza submódulos de un repo custom",
           needs=[ARG_REPO, ARG_BRANCH]),

    # Scripts auxiliares
    Action("script:backup", "Backup", "Scripts",
           "Genera dump SQL + filestore en ZIP",
           needs=[ARG_INSTANCE, ARG_DB, ARG_TARGET_PG, ARG_PATH]),
    Action("script:restore", "Restore", "Scripts",
           "Restaura un backup ZIP a una nueva DB",
           needs=[ARG_INSTANCE, ARG_ZIP, ARG_DEST_DB]),
    Action("script:test", "Run tests", "Scripts",
           "Ejecuta tests Odoo con tags y módulos",
           needs=[ARG_INSTANCE, ARG_DB, ARG_TEST_TAGS, ARG_INSTALL]),
    Action("script:precommit", "Pre-commit", "Scripts",
           "Corre pre-commit sobre los módulos de la instancia",
           needs=[ARG_INSTANCE]),
    Action("script:active_users", "Active users", "Scripts",
           "Cuenta usuarios activos por DB (bus_presence)",
           needs=[ARG_INSTANCE]),
    Action("script:migrate", "Migrate module", "Scripts",
           "Instala un módulo cargando el helper de migración de vistas OCA",
           needs=[ARG_INSTANCE, ARG_DB]),
    Action("script:upgrade_manifest", "Bump manifest version", "Scripts",
           "Asistente para incrementar la versión en __manifest__.py"),
]


CATEGORY_ORDER = [
    "Lifecycle",
    "Acceso",
    "Mantenimiento",
    "Módulos / DB",
    "Sync",
    "Scripts",
]


LOG_LEVELS = ("CRITICAL", "ERROR", "WARNING", "INFO")
LOG_LEVEL_COLORS = {
    "CRITICAL": "red bold",
    "ERROR": "red",
    "WARNING": "yellow",
    "INFO": "blue",
}
LOG_LEVEL_SHORT = {
    "CRITICAL": "C",
    "ERROR": "E",
    "WARNING": "W",
    "INFO": "I",
}


CATEGORY_BADGE = {
    "Lifecycle": "Lifecycle",
    "Acceso": "Acceso",
    "Mantenimiento": "Mant.",
    "Módulos / DB": "Módulos",
    "Sync": "Sync",
    "Scripts": "Scripts",
}


FILTER_LEVEL_IDS = {
    "CRITICAL": "filt_critical",
    "ERROR": "filter_error",
    "WARNING": "filter_warning",
    "INFO": "filt_info",
}
