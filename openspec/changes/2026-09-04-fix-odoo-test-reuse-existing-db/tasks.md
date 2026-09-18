# Tareas (completadas 2026-09-04)

- [x] Reproducir el bug con el comando real del usuario contra
      `integra_sync_operativo` (base real, módulo ya instalado):
      `Tests ejecutados: 0`, sin errores.
- [x] Leer `scripts/odoo-test` y confirmar la causa: `odoo_cmd` siempre arma
      `-i {modules_str}`, sin chequear si el módulo ya está instalado en una
      base reutilizada.
- [x] Agregar el chequeo antes de armar `odoo_cmd`: `db_exists()` +
      `query_module_states()` (ambas ya existían, reutilizadas) sobre
      `modules_str.split(",")`; si todos están `'installed'`, usar `-u` en
      vez de `-i`, con aviso impreso.
- [x] `python3 -m py_compile scripts/odoo-test` — sin errores de sintaxis.
- [x] Verificar con el comando real del usuario: ahora imprime el aviso de
      `-u` y corre `5 tests, 0 Fallos, 0 Errores`.
- [x] Limpiar el directorio `logs/` generado por `--all-verbose` durante la
      verificación (no forma parte del cambio, era de la corrida de prueba).
- [x] Actualizar `openspec/specs/odoo-cli-tooling/spec.md` con el requirement
      y sus dos escenarios.
