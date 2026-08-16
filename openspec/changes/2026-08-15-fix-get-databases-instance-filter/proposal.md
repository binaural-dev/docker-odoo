# `get_databases()` debe respetar el `db_filter` de la instancia

**Estado: implementado y verificado (2026-08-15).**

## Por qué

`./odoo update -m <modulo> -d all -i integra-17.0` era lentísimo. Causa
confirmada leyendo el código, no solo el síntoma: `get_databases()`
(`odoo:395`) hacía
`SELECT datname FROM pg_database WHERE datistemplate = false AND datname NOT
IN ('postgres', 'template1')` — trae **todas** las bases del servicio de
Postgres completo (`pg16` o `pg16_odoo_17`), sin filtrar por la instancia
pedida. Con varias instancias compartiendo un mismo servicio (ej.
`pg16_odoo_17` con 17 bases), `-d all` terminaba actualizando el módulo en
bases de otros proyectos que ni siquiera lo tienen instalado.

Cada instancia ya define `overwrite_odoo_config.db_filter` (ej.
`"^integra\\-17\\.0"` para `integra-17.0`, `"^comercial-19_"` para las de
comercial) — el mismo patrón de regex que usa Odoo en runtime para su propio
selector de bases. Ese campo nunca se leía desde el CLI de gestión.

## Qué cambia

`get_databases()` ahora resuelve el `db_filter` efectivo de la instancia (vía
`resolve_instance_config`) y lo aplica como filtro SQL
(`datname ~ '<patron>'`), con las comillas simples del patrón escapadas antes
de insertarlo en el literal SQL. Sin `db_filter` (o con `"*"`), se mantiene el
comportamiento anterior (listar todas las bases del servicio) pero con una
advertencia explícita impresa en pantalla — no se cambia nada existente
silenciosamente.

Como el fix vive dentro de la función misma, cubre automáticamente todos sus
call sites (`prompt_for_database` y el handler de `update`) sin tocarlos por
separado.

## Impacto

Validado contra los contenedores reales:
- `integra-17.0` (`db_filter: ^integra\-17\.0`): antes traía las 17 bases de
  `pg16_odoo_17`, ahora trae solo `integra-17.0`.
- Una instancia con `db_filter` más amplio (`^comercial-19_`, varias bases
  hermanas) sigue trayendo correctamente sus 7 bases — el fix no
  sobre-restringe a coincidencia exacta.
