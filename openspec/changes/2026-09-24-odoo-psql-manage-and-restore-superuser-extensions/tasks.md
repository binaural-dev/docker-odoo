# Tareas (completadas 2026-09-24)

## Módulo compartido de break-glass

- [x] `.resources/generators/db_bootstrap.py`: mover `pg_exec()`,
      `bootstrap_needs_breakglass()` y `bootstrap_breakglass_enable()` acá
      desde `odoo` (única fuente, en vez de duplicarla de nuevo en
      `scripts/odoo_restore`).
- [x] `odoo`: importar de `generators.db_bootstrap` en vez de las
      definiciones locales; `_bootstrap_breakglass_enable()` queda como
      wrapper delgado que fija `COMPOSE_FILE`.
- [x] `scripts/odoo_restore`: importar de `generators.db_bootstrap`.

## Credenciales centralizadas

- [x] `.resources/generators/config_loader.py`:
      `resolve_instance_db_creds()` (rol dedicado si existe, si no el
      compartido) y `resolve_db_bootstrap_creds()` (bootstrap del
      servicio).
- [x] `odoo`: `psql_connect()`, `psql_remove_database()`,
      `reset_password()` usan `resolve_instance_db_creds()` en vez de leer
      `db_conf['user']`/`['password']` directo.
- [x] `scripts/odoo_restore`: usa `resolve_instance_db_creds()` +
      `resolve_db_bootstrap_creds()`.

## `./odoo psql --ps` (sin filtrar por instancia)

- [x] `psql_connect_all()`: elegir servicio → break-glass del bootstrap si
      hace falta → listar TODAS las bases reales (`_list_all_databases()`)
      → psql interactivo → siempre re-`NOLOGIN` al salir (`try/finally`).
- [x] Confirmación explícita antes de arrancar el break-glass (afecta a
      todo el servicio, no solo una instancia).
- [x] Flag `--ps`/`--postgres` en el subparser `psql`; `main()` saltea el
      prompt de instancia cuando está presente.

## `./odoo psql remove` (DROP DATABASE)

- [x] `psql_remove_database()`: modo instancia (credenciales normales, sin
      bootstrap) y modo `--ps` (igual que `psql_connect_all()`, elige
      cualquier base de cualquier servicio).
- [x] `_confirm_drop()`/`_confirm_drop_many()`: confirmación explícita,
      mismo estilo que `remove` de contenedores/volúmenes; lista todas las
      bases antes de una única confirmación cuando son varias.
- [x] `_drop_database()`: si falla por sesiones activas, ofrece
      `pg_terminate_backend` + reintento antes de darse por vencido.
- [x] Subcomando `remove` dentro de `psql` (`instance` posicional literal
      `"remove"` + `remove_instance` oculto para la instancia real),
      documentado en el `epilog` del subparser.

## `./odoo restore` (passthrough)

- [x] `main()`: si `sys.argv[1] == "restore"`, delega tal cual a
      `scripts/odoo_restore` antes de argparse (mismo patrón que `apk`).
- [x] Subparser `restore` agregado solo para que aparezca listado en
      `./odoo --help` (el parseo real lo hace `scripts/odoo_restore`).

## `scripts/odoo_restore` — extensiones no confiables

- [x] `DatabaseRestoreManager._dump_needs_superuser()`: escanea el `.sql`
      local buscando `CREATE EXTENSION IF NOT EXISTS ...` antes de
      copiarlo al contenedor.
- [x] `_set_instance_superuser(enabled)`: `ALTER ROLE ... SUPERUSER` /
      `NOSUPERUSER` sobre el rol de la instancia, autenticando con el rol
      bootstrap (rompe el break-glass si hace falta, vía
      `bootstrap_needs_breakglass`/`bootstrap_breakglass_enable`
      compartidos). Error explícito si el servicio no tiene
      `bootstrap_user`/`bootstrap_password` configurados.
- [x] `run_sql_restore()`: envuelve la ejecución del `.sql` en
      `_set_instance_superuser(True)`/`(False)` solo si
      `_dump_needs_superuser()` fue `True`; sin extensiones no confiables,
      comportamiento idéntico al anterior.
- [x] `_relock_bootstrap_if_needed()`: si se rompió el break-glass para
      esto, vuelve a poner el rol bootstrap en `NOLOGIN` al terminar
      (éxito o error).
- [x] `RestoreOrchestrator`/`main()`: propagar
      `bootstrap_user`/`bootstrap_password`/`bootstrap_db_conf`/
      `bootstrap_db_service_name`/`bootstrap_db_container` desde `main()`
      hasta `DatabaseRestoreManager`.

## Verificación

- [x] `python3 -m py_compile odoo scripts/odoo_restore scripts/odoo-test
      .resources/generators/config_loader.py
      .resources/generators/db_bootstrap.py` — sin errores.
- [x] `./odoo psql --help` / `./odoo restore --help` — flags y subcomando
      nuevos visibles, sin tocar Docker.
- [ ] Restore real de un dump con extensión no confiable (pendiente,
      fuera de este cambio: no había un dump así disponible para probar).
- [ ] `./odoo psql remove --ps` contra un servicio real (pendiente, fuera
      de este cambio).
- [x] Actualizar `openspec/specs/odoo-cli-tooling/spec.md` con los
      requirements nuevos y sus escenarios.
