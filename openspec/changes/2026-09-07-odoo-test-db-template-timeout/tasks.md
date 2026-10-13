# Tareas (completadas 2026-09-07)

- [x] Confirmar leyendo el fuente de Odoo en los dos contenedores (17.0 y 19.0)
      que `-i` contra una plantilla ya poblada es correcto y que **no** hace
      falta `-u`, en vez de asumirlo.
- [x] `create_db(container, db, template=None)` con `createdb -T`, reintento
      acotado a la plantilla, y copia del filestore.
- [x] `drop_db()` con `--force` y borrado del filestore, para no acumular bases
      huérfanas a lo largo de un barrido de cientos de corridas.
- [x] Implementar el timeout DENTRO del contenedor (`timeout` de coreutils
      prefijando solo el `coverage run`), tras confirmar que matar el
      `docker exec` no mata el proceso de adentro.
- [x] `run_and_capture()` con reloj de respaldo, drenaje de stdout en hilo y
      `pkill -f "<db_name>"` como kill hook.
- [x] `compute_verdict()`: exit code 124 → `fail_reason` propio `"timeout"`,
      separado de `process_exit_nonzero`.
- [x] Exportar `module_states` y `exit_code` en `--out-json`.
- [x] Agregar `--out-coverage-json-raw` y verificar que de ese JSON se deriva
      exacto el total que da `coverage` con el `omit` aplicado (42/75/36 contra
      63/133/38 sobre el mismo módulo).
- [x] Reenviar los flags nuevos y `--no-confirm` desde `./odoo test`.
- [x] Verificar que sin los flags nuevos el comando generado es idéntico
      (diff de `--dry-run` antes/después, normalizando los puertos aleatorios).
- [x] Verificar que la plantilla no altera las cifras (mismo pct/stmts/miss con
      y sin ella) y que el timeout deja todo limpio.
- [x] Documentar los dos flags en el `USAGE` del script y en `scripts/README.md`.
