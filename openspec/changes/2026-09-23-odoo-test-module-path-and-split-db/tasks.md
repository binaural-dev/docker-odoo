# Tareas (completadas 2026-09-23)

- [x] `scripts/odoo-test`: `resolve_requested_modules()` — resuelve
      `-m`/posicional (nombre, path dentro de `--addons`, o `all`) a una
      lista plana de módulos, antes de tocar el resto de la lógica
      (recursive/exclude/tags).
- [x] `scripts/odoo-test`: refactor del bloque de "una corrida" (antes
      inline en `run_command`) a `execute_test_run()`, reutilizable una vez
      (modo normal) o una vez por módulo (`--per-module-db`).
- [x] `scripts/odoo-test`: `compute_closure_for_seed()` — misma lógica de
      `--recursive`/`--exclude` (dependientes arrastrados), parametrizada
      por "target" (todos los módulos juntos, o un módulo semilla).
- [x] `scripts/odoo-test`: `--per-module-db`, `--out-summary-json` (nuevos
      flags), validaciones (`--per-module-db` + `-d` incompatibles,
      `--out-summary-json` sin `--per-module-db` es error).
- [x] `scripts/odoo-test`: `confirm_recursive_run_multi()` (una sola
      confirmación para los N árboles), `build_combined_test_report()`,
      `build_summary_report()`, `print_split_summary()`.
- [x] `odoo`: flags nuevos en el subparser `test` + forwarding tal cual
      (sin lógica propia) a `scripts/odoo-test`.
- [x] `odoo`: `translate_module_path_tokens()` — traduce un path host
      (relativo al repo o absoluto dentro de él) al equivalente de
      contenedor antes de pasarlo a `scripts/odoo-test`.
- [x] `odoo`: agregado el forwarding de `--no-confirm` al subcomando `test`
      (faltaba).
- [x] `python3 -m py_compile scripts/odoo-test odoo` — sin errores de
      sintaxis.
- [x] Unit test aislado (`SourceFileLoader`) de `resolve_requested_modules`
      con datos sintéticos: nombre suelto, path exacto, path anidado,
      `all`, mezcla nombre+path, path inválido (fuera de `--addons`).
- [x] Verificación con dry-run contra la instancia real `integra19`: path
      exacto → 1 módulo; `all` acotado a un `--addons` root → sus ~49
      módulos en una sola corrida combinada; `--per-module-db` con 2
      módulos → 2 comandos/DBs independientes impresos; `./odoo test` con
      path host-relativo → traducido correctamente a path de contenedor.
- [x] Verificación con corrida REAL contra `integra19`
      (`binaural_alternate_product_name,binaural_approvals_purchase
      --per-module-db --out-json --out-summary-json`): 2 módulos, 2 bases
      descartables creadas y borradas independientemente, JSON combinado y
      resumido con el shape exacto pedido, ambos `passed: true`.
- [x] Detectado y resuelto (fuera de alcance de este cambio, pero
      bloqueaba la verificación): `integra19` nunca había sido
      aprovisionada con su rol dedicado de Postgres — `WorkerCron` en loop
      de `permission denied`. Aprovisionado el rol + `GRANT odoo_integra19
      TO integra19` para heredar acceso a las tablas del rol legado que
      las poseía. Verificado sin errores tras reiniciar el contenedor.
      Verificado que `odoo-binaural`/`odoo-binaural_actual` (otras
      instancias corriendo en el mismo servicio Postgres compartido) no
      quedaron afectadas por los dos reinicios breves de `db-pg16`
      necesarios para el aprovisionamiento.
- [x] Actualizar `openspec/specs/odoo-cli-tooling/spec.md` con los
      requirements nuevos y sus escenarios.
