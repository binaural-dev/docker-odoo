# Tareas (completadas 2026-08-15)

- [x] Confirmar que `click-odoo-update` no estaba instalada en ninguna
      imagen (probado en 4 imágenes distintas), a pesar de ya estar
      referenciada en `700-fix-dbs`.
- [x] Agregar `click-odoo-contrib` a `.resources/Dockerfile.template`.
- [x] Regenerar `.resources/Dockerfile.17.0`/`.resources/Dockerfile.19.0` y
      reconstruir una imagen de prueba (`odoo-integra-17.0`) para validar.
- [x] Revisar `click-odoo-update --help` real dentro de la imagen para
      confirmar flags (`-d`, `--if-exists`, `--update-all`).
- [x] Agregar flag `-f`/`--force` al subparser `update`.
- [x] Quitar la llamada a `prompt_for_modules()` cuando `args.m is None` —
      pasar directo a `"all"`.
- [x] Modificar `bash_update_modules()` para bifurcar entre
      `click-odoo-update` (destino "all") y `odoo -u <modules>` (módulo
      específico), con `--update-all` cuando se pasa `-f`.
- [x] Eliminar `prompt_for_modules()` (quedó sin llamadores) sin tocar
      `get_custom_modules()` (sigue en uso por `prompt_for_test_modules`).
- [x] Validar sintaxis (`py_compile`) y `python3 odoo update --help`.
