# Tareas (completadas 2026-09-02)

- [x] Investigar CLI existentes (OdooTerminal, click-odoo, odoo-shell de PyPI,
      wrappers de la comunidad) y confirmar que ninguno cubre la gramática
      pedida fuera del navegador; `click-odoo` ya está en las imágenes
      (14.0 y 19.0) y sirve de motor.
- [x] Confirmar en runtime que `docker exec -i <container> click-odoo -d <db>
      --no-interactive` corre snippets por stdin y que métodos privados
      (`_compute_display_name`) se ejecutan sin error server-side.
- [x] Crear `scripts/odoo-shell`: CLI argparse standalone con globales
      (`--container`, `-d/--db`, `--user`, `--no-commit`, `--json`) y
      subcomandos `shell`, `search`, `read`, `browse` (alias), `count`,
      `create`, `write`, `unlink` (con `--yes`), `method`.
- [x] Construir snippets Python y ejecutarlos por stdin a click-odoo; parsear
      salida por marcadores `__ODOO_SHELL_RESULT__`/`__ODOO_SHELL_ERROR__`
      para aislarla del ruido de logs.
- [x] Parsear `--domain`/`--values`/`-a`/`-k` con `ast.literal_eval`
      (seguro), con formato `clave:valor,...` para `-k`.
- [x] `method` con `--ids` → browse; sin ids → search (sin limit = todos);
      `getattr` permite métodos privados.
- [x] Agregar subparser `shell` al launcher `odoo` (instancia posicional,
      `-d`, `--user`, REMAINDER patrón `apk`), re-clasificar posicional
      ambiguo, extraer `-d` del REMAINDER, incluir en
      `actions_with_instance`, y delegar a `scripts/odoo-shell`.
- [x] Verificar end-to-end en `odoo-binaural` (Odoo 19): search, read/browse,
      count, create/write con `--no-commit` (rollback), method privado con
      ids y con `--limit`/`--order`, method con `-a`/`-k`, unlink sin `--yes`
      aborta.
- [x] Actualizar `openspec/specs/odoo-cli-tooling/spec.md` con el requirement
      y sus escenarios.
- [x] Actualizar `readme.md`: fila en tabla + sección con un ejemplo por
      subcomando.