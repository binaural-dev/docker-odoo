# Rol de Postgres dedicado por instancia — aislar el cron entre instancias que comparten un servicio

**Estado: implementado y verificado (2026-08-17).** Este documento es
retroactivo — describe una remediación ya aplicada, no un cambio pendiente de
aprobación.

## Por qué

Varias instancias de Odoo comparten un mismo servicio de Postgres (ej. 7
instancias en `pg16_odoo_17`, cada una con su propio `db_filter`). Confirmado
leyendo el código fuente real de Odoo (14.0/16.0/17.0/19.0, dentro de las
imágenes ya construidas): **el cron interno de Odoo (`ir.cron`) no respeta
`dbfilter` en absoluto** — `dbfilter` es un mecanismo puramente de ruteo HTTP
(selector de bases, sesión), nunca consultado desde el dispatcher de cron
(`ir_cron._process_jobs`/`IrCron._process_jobs`, `WorkerCron._db_list`,
`ThreadedServer.cron_thread`).

Esto ya causó un incidente real: `integra-maintenance-comercial-19.0.1`
corrió scheduled actions sobre la base de `integra-maintenance-19.0.1`
(comparten el servicio `pg16`), subiéndole el `failure_count`. Un operador lo
mitigó a mano (`MAX_CRON_THREADS: 1→0` directo en el compose generado) —
mitigación que se revirtió sola al regenerarse el archivo, porque nunca fue
durable en `instances.json`.

Se evaluaron dos enfoques: (a) parchear el dispatcher de cron de Odoo
(`server_wide_modules`, monkeypatch) para que sí respete `dbfilter`, o (b)
resolverlo a nivel de Postgres, dándole a cada instancia su propio rol,
dueño solo de sus propias bases. Se implementó y probó (a) contra Odoo
14.0/16.0/17.0/19.0 reales, pero se descartó como solución de fondo a favor
de (b): **no toca código de Odoo**, y `list_dbs()` (la función que el cron
nativo ya usa para listar bases cuando `db_name` no está fijado) **ya
filtra por `datdba = current_user`** — con un rol por instancia, ese filtro
nativo alcanza sin parchear nada.

## Qué cambia

- **Rol de Postgres dedicado por instancia**: cuando >1 instancia comparte
  un `database` (servicio de Postgres) y alguna corre cron
  (`max_cron_threads != 0`), cada instancia del grupo necesita su propio
  rol — no superusuario, `LOGIN CREATEDB`, miembro del rol bootstrap del
  servicio (hereda DDL sin heredar `SUPERUSER`, que nunca se hereda por
  membresía) — dueño únicamente de las bases que matchean su `db_filter`.
- **`REVOKE CONNECT ... FROM PUBLIC` + `GRANT CONNECT ... TO <rol>`** por
  cada base de la instancia: capa adicional que bloquea la conexión en sí
  (no solo el filtro de `list_dbs()`), protegiendo también el modo
  threaded (que ni siquiera llama a `list_dbs()` para el cron — solo itera
  `Registry.registries.d`, registries ya cargados en memoria).
- **`instances.json`**: nuevos campos opcionales `db_user`/`db_password` en
  la raíz de cada instancia (hermano de `database`, no dentro de
  `overwrite_odoo_config`).
- **`.resources/generators/config_loader.py`**: `_validate_cron_dbfilter_isolation()`
  (llamada desde `_validate_config()`, corre en todo comando `./odoo`)
  agrupa instancias por `database`; para grupos >1 con cron activo, exige
  `db_filter` específico (no vacío/`"*"`, sin placeholders `%h`/`%d` — no
  hay host de request que resolver desde cron) **y** `db_user`/`db_password`
  propios. Sin esto, el CLI completo se bloquea con un error detallado.
  Escape hatch: `max_cron_threads: 0` explícito.
- **`.resources/generators/compose_generator.py`**: `_odoo_service()` usa
  `db_user`/`db_password` de la instancia si están definidos, con fallback
  al rol de servicio compartido (`database.user`/`password`) — no rompe
  configs existentes sin estos campos.
- **Comando nuevo `./odoo provision-role <instance>`** (`odoo`, funciones
  `_resolve_provision_target`, `_bootstrap_needs_breakglass`,
  `_bootstrap_breakglass_enable`, `provision_role_sql`,
  `provision_instance_role`): crea/actualiza el rol, resuelve qué bases
  matchean el `db_filter` vía `pg_database.datname ~ <filter>`, y para cada
  una hace `ALTER DATABASE ... OWNER TO` + `REVOKE`/`GRANT CONNECT`.
  Requiere el rol bootstrap del servicio logueable (`CREATEROLE`); si está
  en `NOLOGIN` (lo normal), aplica un "break-glass" temporal
  (`postgres --single`, ya documentado en el cambio de 2026-08-15) y lo
  re-bloquea al terminar. Pide confirmación explícita antes de tocar nada.
- **Nunca usa `REASSIGN OWNED`**: probado en producción que, ejecutado
  conectado a una base puntual, reasigna la propiedad de **todas** las
  bases del clúster que pertenecían al rol origen (objeto compartido
  `pg_database`, no local a la conexión) — efecto secundario real,
  detectado y corregido en el momento. Se usa siempre `ALTER DATABASE
  "<db>" OWNER TO <rol>` (preciso, sin efectos de lado) en su lugar.
- **Auditoría automática (`audit_db_filter_drift()` / `print_db_filter_audit()`,
  corre en cada `./odoo build`)**: consulta de solo lectura (rol de
  servicio normal, sin break-glass — la metadata de `pg_database` es
  visible para cualquier rol logueable) que compara el `db_filter`
  resuelto de cada instancia contra el ownership/`CONNECT` real, y avisa
  (sin bloquear) 4 tipos de desalineación: rol dueño incorrecto, `CONNECT`
  de `PUBLIC` sin revocar, base que dejó de matchear tras cambiar el
  filtro, y filtros de distintas instancias solapados sobre la misma base.
  Existe porque nada re-sincroniza esto solo cuando se edita `db_filter` a
  mano en `instances.json`.
- **Corrección automática opcional al final de `./odoo build`**: de los 4
  tipos de drift, solo "dueño incorrecto" y "`CONNECT` sin revocar" son
  corregibles sin ambigüedad (aplicar `provision-role` con el `db_filter`
  vigente siempre da el resultado correcto). Para esos casos, el build
  pregunta si correr `provision-role` ahora mismo para las instancias
  afectadas, agrupando por servicio de Postgres (`provision_instances_grouped()`,
  mismo patrón que la migración batch: un solo break-glass por servicio,
  no uno por instancia). Los otros dos tipos ("filtro que ya no matchea",
  "filtros solapados") **nunca** se ofrecen para autocorrección — requieren
  criterio humano. Flag `--no-confirm` (y manejo explícito de `EOFError`
  en el `input()`) para que un build no interactivo (CI/automatización)
  nunca se cuelgue ni corrija nada sin confirmación explícita.
- Módulo `cron_dbfilter_guard` (parche de Odoo, capas A/B, probado contra
  14.0/16.0/17.0/19.0 reales) queda en el repo (`.resources/odoo_addons/`)
  como código disponible pero **no usado** por ninguna instancia — se
  prefirió la solución de Postgres, que no toca código de Odoo.

## Impacto

- **10 instancias migradas** a rol dedicado: los 2 pilotos originales
  (`integra-maintenance-19.0.1`, `integra-maintenance-comercial-19.0.1`,
  afectados por el incidente real) más 8 instancias adicionales en
  `pg16`/`pg16_odoo_17`, todas verificadas (ownership correcto, `CONNECT`
  restringido, contenedores recreados con las credenciales nuevas,
  respondiendo HTTP sin errores).
- **2 ventanas de mantenimiento breves** de los servicios completos
  (`db-pg16`, `db-pg16_odoo_17`), no una por instancia — el
  break-glass se agrupa por servicio.
- **Sin pérdida de datos**: verificado conteo de bases y ownership final
  contra lo esperado en ambos servicios antes/después.
- **Compatibilidad**: instancias que no comparten `database` con nadie más,
  o que declaran `max_cron_threads: 0`, no requieren nada de esto — la
  validación solo aplica al caso de riesgo real.
- **Pendiente / fuera de este cambio**: script de auditoría *reactiva* que
  además detecte bases nunca reclamadas por ningún `db_filter` (huérfanas,
  aún propiedad del rol de servicio compartido) — hoy la auditoría de
  build solo compara contra instancias existentes, no hace un barrido
  completo de "bases sin dueño claro".
