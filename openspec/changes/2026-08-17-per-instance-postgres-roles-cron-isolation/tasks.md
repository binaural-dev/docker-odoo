# Tareas (todas completadas el 2026-08-17)

## Investigación

- [x] Confirmar contra el código fuente real de Odoo 14.0/16.0/17.0/19.0 que
      `dbfilter` nunca se consulta desde el dispatcher de cron (solo ruteo
      HTTP).
- [x] Confirmar que `list_dbs()` ya filtra por `datdba = current_user`
      cuando `db_name` no está fijado en la config — la base del enfoque
      elegido.
- [x] Diseñar, implementar y probar (contenedores descartables, 4
      combinaciones de versión/modo) un parche alternativo a nivel de Odoo
      (`cron_dbfilter_guard`, `server_wide_modules`) — descartado como
      solución de fondo a favor del enfoque de Postgres, pero conservado en
      el repo como código disponible.

## Validación obligatoria (`config_loader.py`)

- [x] Agregar `_validate_cron_dbfilter_isolation()`, llamada desde
      `_validate_config()`: agrupa instancias por `database`; para grupos
      >1 con `max_cron_threads != 0`, exige `db_filter` específico (sin
      `%h`/`%d`) y `db_user`/`db_password` propios.
- [x] Mensaje de error detallado por categoría (sin filtro, filtro con
      placeholders, sin credenciales), listando instancias afectadas y el
      comando para resolverlo.
- [x] Verificar que corre en cualquier comando `./odoo` (no solo `build`).

## Rol dedicado por instancia (Postgres)

- [x] `compose_generator.py::_odoo_service()`: usar `db_user`/`db_password`
      de la instancia si están definidos, fallback al rol de servicio
      compartido.
- [x] CLI `./odoo provision-role <instance>`:
      `_resolve_provision_target`, `_bootstrap_needs_breakglass`,
      `_bootstrap_breakglass_enable`, `provision_role_sql`,
      `provision_instance_role`.
- [x] `provision_role_sql()`: `CREATE ROLE`/`ALTER ROLE ... PASSWORD`
      idempotentes, `GRANT <bootstrap> TO <rol>`, resolver bases vía
      `pg_database.datname ~ <db_filter>`, y por cada una `ALTER DATABASE
      ... OWNER TO` + `REVOKE`/`GRANT CONNECT` — nunca `REASSIGN OWNED`
      (efecto secundario cluster-wide detectado y corregido durante la
      migración real).
- [x] Migrar los 2 pilotos afectados por el incidente real
      (`integra-maintenance-19.0.1`, `integra-maintenance-comercial-19.0.1`)
      a rol dedicado; quitar `cron_dbfilter_guard` de su config (ya no
      hace falta).
- [x] Migrar las 8 instancias restantes que comparten `pg16`/`pg16_odoo_17`,
      agrupando el break-glass por servicio (2 ventanas de mantenimiento en
      vez de 8).
- [x] Regenerar `docker-compose.generated.yml` y recrear los 8 contenedores
      con las credenciales nuevas; verificar HTTP y logs sin errores.
- [x] Re-correr `provision-role` sobre los 2 pilotos para aplicarles
      también el `REVOKE CONNECT` (solo tenían el ownership transferido a
      mano, de antes de que existiera la herramienta).
- [x] Verificar estado final: ownership completo y correcto en ambos
      servicios, `CONNECT` de `PUBLIC` revocado en todas las bases
      migradas, ambos roles bootstrap de nuevo en `NOLOGIN`.

## Auditoría de drift (`db_filter` vs. ownership real)

- [x] `_fetch_database_ownership()`: lectura de `pg_database` con el rol de
      servicio normal (sin break-glass — metadata de catálogo visible para
      cualquier rol logueable).
- [x] `audit_db_filter_drift()`: 4 categorías de aviso (rol dueño
      incorrecto, `CONNECT` sin revocar, base que dejó de matchear el
      filtro, filtros solapados entre instancias).
- [x] `print_db_filter_audit()`, enganchado en `build_odoo()` — corre en
      cada `./odoo build`, nunca bloquea.
- [x] Probado contra el estado real (sale limpio) y contra 4 configs
      sintéticas que fuerzan cada categoría de aviso.
- [x] `audit_db_filter_drift()` devuelve hallazgos estructurados (`category`,
      `instance`, `fixable`, `message`) en vez de solo strings, para poder
      decidir programáticamente qué corregir.
- [x] `_maybe_fix_drift()`: al final de `./odoo build`, si hay hallazgos
      `fixable=True` (dueño incorrecto, `CONNECT` sin revocar), pregunta si
      correr `provision-role` para esas instancias ahora. Los hallazgos
      ambiguos (`filter_drift`, `overlap`) nunca se ofrecen.
- [x] `provision_instances_grouped()`: agrupa las instancias a corregir por
      servicio de Postgres, un solo break-glass por servicio (reusa el
      patrón de la migración batch).
- [x] Flag `--no-confirm` en `./odoo build` + manejo de `EOFError` en el
      `input()`, para que un build no interactivo (CI/automatización)
      nunca se cuelgue ni corrija nada sin confirmación explícita.
- [x] Probado con configs sintéticas y funciones de Postgres mockeadas:
      `no_confirm=True` omite sin preguntar; sin entrada interactiva
      (EOF) omite sin crashear; confirmando "y" agrupa correctamente por
      servicio (un solo break-glass para 2 instancias del mismo servicio);
      hallazgos ambiguos nunca terminan en la lista de instancias a
      corregir.

## Documentación

- [x] `readme.md`: sección de instancias que comparten servicio de
      Postgres, `provision-role` en la tabla de comandos y ejemplos,
      auditoría de build.
- [x] `instances.example.json`: dos instancias sobre el mismo `database`
      con `db_user`/`db_password`.
- [x] `instances.example`: mismo escenario, con comentarios explicando el
      por qué.
- [x] `openspec/specs/postgres-security/spec.md`: nuevos requirements.
- [x] `openspec/project.md`: tercera identidad de rol en la arquitectura.
