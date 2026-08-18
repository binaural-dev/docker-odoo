# Diseño (retroactivo)

## Alternativas evaluadas

### A. Parche a Odoo (`server_wide_modules`, monkeypatch de `ir_cron`)

Reemplazar `ir_cron._process_jobs`/`IrCron._process_jobs` para que sí
evalúe `dbfilter` antes de correr cada job. Investigado y **verificado
contra el código fuente real** de las 4 versiones en uso/soportadas:

| Odoo | `_process_jobs` | Listado de bases | Ejecución final |
|---|---|---|---|
| 19.0 | `IrCron._process_jobs`, `@staticmethod` | `cron_database_list()` | directo |
| 17.0 | `ir_cron._process_jobs`, `@classmethod` | `WorkerCron._db_list()` (prefork) / itera registries en memoria (threaded) | directo |
| 16.0 | idéntico a 17.0 | idéntico a 17.0 | directo |
| 14.0 | idéntico a 17.0 | idéntico a 17.0 | indirecto, vía `_acquire_job` (que igual termina llamando al método ya parcheado — búsqueda dinámica del atributo, no referencia cacheada) |

Implementado y probado end-to-end (incluyendo el caso de aceptación
principal: replicar la topología exacta del incidente real) contra
imágenes oficiales de las 4 versiones. Con salvaguarda dura
(`sys.exit(1)`, ya que `SystemExit` es lo único que
`load_server_wide_modules()` no atrapa) si se detecta una versión/modo no
verificado.

**Descartado como solución de fondo** — decisión explícita de no tocar
código de Odoo cuando existe una alternativa que no lo requiere. Se
mantiene el módulo en el repo (`.resources/odoo_addons/cron_dbfilter_guard/`)
sin usar por ninguna instancia.

### B. Rol de Postgres dedicado por instancia (elegida)

`list_dbs()` (`odoo/service/db.py`) ya filtra por
`datdba = current_user` cuando `db_name` no está fijado — es el mecanismo
que el cron nativo de Odoo usa para listar bases. Dándole a cada instancia
su propio rol, dueño solo de sus bases, ese filtro nativo alcanza sin
tocar código de Odoo. Se suma `REVOKE CONNECT ... FROM PUBLIC` +
`GRANT CONNECT ... TO <rol>` como capa adicional que bloquea la conexión
en sí — cubre también el modo threaded, que ni siquiera pasa por
`list_dbs()` para el cron.

Ventaja decisiva sobre (A): la protección es "gratis" para cualquier
código futuro que pueda cruzar bases (no solo el cron), y sobrevive
upgrades de Odoo sin re-verificar nada contra el core.

## Por qué la migración se agrupó por servicio, no por instancia

Crear un rol nuevo requiere `CREATEROLE`, que solo tiene el rol bootstrap
de cada servicio — deliberadamente en `NOLOGIN`. Habilitarlo requiere el
mecanismo de "break-glass" (`postgres --single`, parar/arrancar el
contenedor) ya usado en el cambio de 2026-08-15. Agrupar todas las
instancias de un mismo servicio bajo una sola ventana de break-glass evitó
8 ventanas de mantenimiento (una por instancia) reduciéndolas a 2 (una por
servicio de Postgres real).

## Error real cometido y corregido durante la migración

`REASSIGN OWNED BY <rol origen> TO <rol nuevo>`, ejecutado conectado a una
base puntual, reasignó de encima la propiedad de **todas** las demás
bases del clúster que pertenecían al rol origen (incluida `postgres`) —
`pg_database` es un catálogo compartido a nivel de clúster, no local a la
conexión. Detectado verificando el estado final contra lo esperado (nunca
asumido), corregido devolviendo el ownership de las bases ajenas con
`ALTER DATABASE ... OWNER TO` (preciso, sin efectos de lado) y usando
`GRANT <rol_actual> TO <rol_nuevo>` (membresía) para las tablas en vez de
`REASSIGN OWNED`. Regla codificada en el comentario de
`provision_role_sql()`: **nunca usar `REASSIGN OWNED` para este tipo de
migración**.

## Por qué la auditoría de drift no necesita break-glass

El ownership y el nombre de cada base (`pg_database.datdba`, `datname`)
son metadata de catálogo, visibles para **cualquier** rol logueable del
clúster — no hace falta ser superusuario ni dueño para leerlos. Por eso
`audit_db_filter_drift()` puede correr con el rol de servicio normal (el
mismo que ya usan los contenedores Odoo), sin ningún privilegio elevado,
en cada `./odoo build`, sin fricción operativa.
