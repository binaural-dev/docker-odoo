# `./odoo psql --ps`/`remove` (gestión de bases sin filtrar) y `restore` con extensiones que requieren superuser

**Estado: implementado (2026-09-24).**

## Por qué

Desde el aislamiento de roles por instancia
(`openspec/changes/2026-08-17-per-instance-postgres-roles-cron-isolation/`),
cada instancia con rol dedicado solo puede ver/conectar a sus propias bases
(`CONNECT` revocado de `PUBLIC`). Eso deja dos huecos operativos:

1. **No hay forma, desde el CLI, de ver o borrar una base de datos que no
   matchee ninguna instancia conocida** (huérfana, de otro `db_filter`, o de
   una instancia que ya no está en `instances.json`) — `./odoo psql` siempre
   filtra por instancia, y no existe ningún comando para eliminar una base.
   Antes de este cambio, esto requería entrar a mano con `docker exec` y el
   rol bootstrap, saltándose cualquier confirmación o registro.
2. **`scripts/odoo_restore` no podía restaurar un dump que necesitara crear
   una extensión no confiable** (ej. `pgvector`/`vector`, `CREATE EXTENSION`
   sin `trusted` en `pg_available_extensions`) — el rol de la instancia
   nunca es superusuario (por diseño, ver `postgres-security`), así que el
   restore fallaba con `must be superuser to create this extension` a mitad
   de un dump de miles de líneas, sin forma de continuar sin intervención
   manual sobre el clúster.

Además, la lógica de "romper el NOLOGIN del rol bootstrap temporalmente"
(`_bootstrap_needs_breakglass`/`_bootstrap_breakglass_enable`) ya existía
duplicada una sola vez, dentro de `odoo` (para `provision-role`); al
necesitarla también desde `scripts/odoo_restore` (script standalone, no
importa de `odoo`), tocaba elegir entre duplicarla de nuevo o compartirla.

## Qué cambia

- **`.resources/generators/db_bootstrap.py`** (nuevo módulo): única fuente
  de `pg_exec()`, `bootstrap_needs_breakglass()` y
  `bootstrap_breakglass_enable()` — el break-glass del rol bootstrap
  (parar el servicio, `postgres --single` para forzar `ALTER ROLE ...
  LOGIN`, volver a levantarlo) documentado en el cambio de 2026-08-15.
  `odoo` (para `provision-role` y los comandos nuevos de `psql`) y
  `scripts/odoo_restore` importan de acá en vez de tener su propia copia.
- **`.resources/generators/config_loader.py`**: `resolve_instance_db_creds()`
  (rol dedicado de la instancia si `db_user`/`db_password` están definidos,
  si no el rol de servicio compartido) y `resolve_db_bootstrap_creds()`
  (`bootstrap_user`/`bootstrap_password` del servicio, con su propio
  fallback) — centralizan una resolución de credenciales que antes se
  repetía inline en cada llamador (`psql_connect`, `psql_remove_database`,
  `reset_password`, `scripts/odoo_restore`).
- **`./odoo psql --ps`/`--postgres`** (nuevo flag, sin instancia): elegí un
  servicio de Postgres (`databases.<nombre>`) y cualquiera de sus bases
  reales, **sin filtrar por instancia/`db_filter`** — para bases huérfanas
  o de instancias fuera de `instances.json`. Requiere el rol bootstrap
  logueable; si está en `NOLOGIN` (lo normal), aplica break-glass temporal
  (reinicia el contenedor del servicio — afecta a TODAS las instancias que
  lo comparten, no solo una) y siempre lo vuelve a poner en `NOLOGIN` al
  salir (`try/finally`, incluso ante `Ctrl-C` o error). Pide confirmación
  explícita antes de arrancar el break-glass.
- **`./odoo psql remove [instancia] [-d db] [--ps]`** (subcomando nuevo):
  elimina (`DROP DATABASE`) una o más bases, siempre con confirmación
  explícita (mismo estilo que `remove` de contenedores/volúmenes) —
  listando todas antes de una única confirmación si son varias. Sin
  `--ps`, usa las credenciales de la instancia (mismo camino que
  `psql_connect`, sin necesitar el rol bootstrap). Con `--ps`, igual que
  `psql --ps`: cualquier base de cualquier servicio, vía break-glass. Si
  el `DROP DATABASE` falla porque hay sesiones activas (instancia
  corriendo con el pool de conexiones abierto), ofrece terminarlas
  (`pg_terminate_backend`) y reintenta una vez, en vez de obligar a un
  `./odoo stop <instancia>` manual antes de poder borrar una base ya
  confirmada.
- **`./odoo restore ...`**: `restore` pasa a ser un subcomando de primera
  clase de `./odoo` — passthrough directo (como `apk`) a
  `scripts/odoo_restore restore ...` antes de llegar a argparse, sin
  duplicar sus flags. Antes solo se podía invocar
  `scripts/odoo_restore restore ...` directo.
- **`scripts/odoo_restore` — extensiones no confiables en el dump**: antes
  de ejecutar el `.sql`, escanea el dump buscando líneas `CREATE EXTENSION
  IF NOT EXISTS ...`. Si encuentra alguna, otorga `SUPERUSER` temporal al
  rol de la instancia (vía el rol bootstrap del servicio — break-glass si
  hace falta) **solo durante la ejecución del `.sql`** (`try/finally`), lo
  revoca al terminar (éxito o error) y, si tuvo que romper el break-glass,
  vuelve a poner el rol bootstrap en `NOLOGIN`. Sin extensiones no
  confiables en el dump, el comportamiento es idéntico al anterior (no se
  toca el rol bootstrap para nada). Si el dump las necesita pero el
  servicio no tiene `bootstrap_user`/`bootstrap_password` configurados,
  aborta con un error explícito antes de tocar Docker.

## Fuera de alcance, deliberadamente

- No se agrega un modo "listar bases huérfanas" automático (ver
  `openspec/changes/2026-08-17-per-instance-postgres-roles-cron-isolation/`,
  pendiente ahí): `psql --ps` deja **ver** cualquier base a mano, pero no
  hay detección proactiva de cuáles no pertenecen a ninguna instancia.
- El otorgamiento de `SUPERUSER` en `scripts/odoo_restore` es exclusivo
  para permitir que el dump cree sus propias extensiones tal como fue
  generado (no se reordenan ni se pre-crean statements del dump); no se
  usa para ningún otro paso del restore (filestore, creación de la base
  vacía, etc.), que siguen con el rol normal de la instancia.

## Verificado

- `python3 -m py_compile odoo scripts/odoo_restore scripts/odoo-test
  .resources/generators/config_loader.py
  .resources/generators/db_bootstrap.py` — sin errores de sintaxis.
- `./odoo psql --help` y `./odoo restore --help` (nivel argparse, sin
  Docker): flags/subcomandos nuevos aparecen con la ayuda esperada.
- No se corrió un restore real con extensión no confiable ni un `psql
  remove --ps` contra un servicio real como parte de este cambio — queda
  pendiente la primera vez que haga falta en la práctica (dump con
  `pgvector` o similar, o limpieza de una base huérfana real).
