# TUI — Issues & Backlog Tracker

**Origen:** doc de handoff de la sesión 2026-06-10 (revisión de `tui.py` → TUI v2 → TUI v3).
Los dos objetivos de esa sesión (PR #103 y "TUI v3": CSS externo + `OptionList` en
`ModulePicker`) ya están **mergeados y en `master-multi_bin-daldana`** — verificado
2026-07-24: `tui/app.py` usa `CSS_PATH = TCSS_PATH`, `tui/screens/module_picker.py`
ya usa `OptionList`. Se recortaron las secciones de plan/quick-start de esa sesión
porque documentaban paso a paso un trabajo que ya está hecho; lo único que sigue
vivo de este doc es la tabla de issues, el backlog y las referencias de abajo.

El branch local `feat/tui-v3-external-css-optionlist` (y su remoto
`feat/tui-v3-css-optionlist-dev-flag`) quedaron sin pushear/mergear formalmente
pero su contenido ya está superado por lo que hay en `master-multi_bin-daldana` —
revisar si todavía aportan algo antes de basar trabajo nuevo sobre ellos.

---

## Issues abiertos del review original de `tui.py`

Del review de 15 puntos sobre la versión original (antes de v2):

| # | Issue | Estado |
|---|---|---|
| 1 | Dispatcher bloquea acciones sin instancia | **Resuelto en v2** (todas las acciones sin `ARG_INSTANCE` ahora pasan el guard) |
| 2 | `remove` salta confirmación destructiva | **Resuelto** — `dispatch.py:_dispatch` pushea `ConfirmModal` antes de ejecutar `remove` |
| 3 | RichLog markup collision (stdout crudo → markup) | **Resuelto (2026-07-24)** — `on_line` en `app.py:_run_streamed` escapa cada línea con `rich.markup.escape` antes de bufferearla (cubre tanto el write directo al `RichLog` como el replay vía `UpdateProgress.get_filtered_lines()` al togglear filtros de nivel). También se escaparon los mensajes de excepción interpolados en `_log()` (`app.py`, `dispatch.py`, `keybindings.py`) |
| 4 | No se puede cancelar comando largo | **Resuelto** — `Esc` cancela `_current_task`, que dispara SIGTERM→SIGKILL en `runner.py:_terminate_and_reap` |
| 5-10 | Dead code (`ConfirmModal` instancia, `to_dict`, `needs_db_first`, `selected_instance` reactive, `tab` binding, `Refresh` label) | **Algunos resueltos en v2**, verificar `to_dict`/`needs_db_first` en próxima pasada de limpieza |
| 11 | Defaults hardcoded a Binaural (`/binaural_accountant`, etc.) | **Resuelto (2026-07-24)** — `_arg_defaults` para `script:test` ya no prefillea `test_tags`/`install_modules`; el placeholder en `_arg_to_field` sigue mostrando el ejemplo, pero el campo arranca vacío para no imponer valores de un proyecto a otro |
| 12 | `_save_instances_json` revierte in-memory en `PermissionError` | **Resuelto en v2** |
| 13 | CATEGORY_BADGE padding inconsistente | **Resuelto (2026-07-24)** — se reemplazó la tabla de abreviaturas manuales (`Mant.`, `Módulos`, ...) por `CATEGORY_BADGE_WIDTH = max(len(cat) for cat in CATEGORY_ORDER)` en `models.py`; ahora todas las categorías se muestran completas y el ancho se autoajusta si se agrega una categoría más larga |
| 14 | RichLog sin tope de líneas | **Resuelto en v2** — `RichLog(..., max_lines=2000)` en `app.py:153` |
| 15 | Mapeo `script:` → path duplica conocimiento del FS | **Abierto** |

**Nota (2026-07-24):** este doc quedó desactualizado por varias sesiones — varios ítems marcados "Abierto" ya estaban resueltos en el código antes de esta pasada. Antes de retomar un ítem de esta tabla, verificar el código actual en vez de confiar en el estado acá anotado.

---

## Backlog priorizado (no incluido en v2 ni v3)

| Prioridad | Item | Dónde |
|---|---|---|
| ~~Media~~ | ~~Wirear `ConfirmModal` a la acción `remove`~~ — **hecho** | `dispatch.py:_dispatch` |
| ~~Media~~ | ~~Decidir `needs_db_first`~~ — **resuelto**: el campo ya no existe en el código (verificado 2026-07-24, 0 matches en `tui/`) | — |
| Media | Test unitario de `ModulePicker.on_option_list_option_selected` (ambos paneles) | nuevo `tests/test_module_picker.py` |
| ~~Baja~~ | ~~Fix `instances.example.json`: `client-b` referencia `external_pg16` no definida~~ — **resuelto**: verificado 2026-07-24, `client-b` referencia `database: "v17"`, que sí existe en `databases`. El archivo además se renombró a `instances.example.jsonc` desde la sesión 2026-06-15 | `instances.example.jsonc` |
| ~~Baja~~ | ~~RichLog `max_lines=N`~~ — **hecho** | `app.py:153` |
| ~~Media~~ | ~~Silent-swallow~~ — **hecho**: `_hosts_check_and_warn`/`_warn_unknown_modules` ahora loguean; los `except Exception: pass` de cacheo de widgets en `app.py:on_mount` ya tienen comentario explicando que son deliberados (headless tests) | `app.py` |
| ~~Baja~~ | ~~Cancelación de comando largo~~ — **hecho** (SIGTERM→SIGKILL vía `runner.py`) | `_run_streamed` / `runner.py` |
| Nueva (2026-07-24) | Memory leak: `_output_buffer` sin cap crecía sin límite en sesiones largas — **hecho**, capado a 2000 líneas | `app.py:_trim_output_buffer` |
| Estratégico | Evaluar `Textualize/trogon` como alternativa arquitectónica (auto-TUI desde Click). No aplicar; requiere replantear el producto. | https://github.com/Textualize/trogon |
| ~~DX~~ | ~~Documentar `textual run --dev ./odoo-tui` en el readme~~ — **ya estaba hecho** (verificado 2026-07-24: `readme.md` línea ~309 ya documenta el flag `--dev` y el hot-reload de CSS); este ítem del backlog estaba desactualizado, no el código | `readme.md` |

---

## Referencias Textual (para futuras sesiones)

- **matan-h/written-in-textual** — best-of curado de 130 listas con 93K estrellas. Proyectos relevantes para nosotros:
  - `Textualize/trogon` (auto-genera TUI desde Click CLI) — alternativa arquitectónica
  - `darrenburns/textual-autocomplete` — autocomplete dropdown, podría reemplazar el filter manual del ModulePicker
  - `mitosch/textual-select` — searchable select
  - `harlequin` — SQL IDE, patrón "input + resultados"
- **realpython.com/python-textual** — tutorial oficial-style. Cubre widgets, TCSS, `textual-dev`, layouts, events/actions.
  - URL: https://realpython.com/python-textual/

---

## Convenciones del repo (siguen vigentes)

- El usuario está iterando rápido sobre la TUI; prefiere PRs stacked sobre esperar merges.
- Los commits se basan con `git mv` para preservar historial (verificado que `git log --follow` lo rastrea).
- Convention commits lowercase (`feat`, `chore`, `docs`, `refactor`) — el repo acepta los dos formatos pero los commits nuevos van en lowercase.
- El usuario **no usa** el flujo de issues con `status:approved` (Binaural no parece enforce). El skill `branch-pr` se relaja acá: se acepta `Ticket: none, Tarea: none`.
- La label correcta para PRs de feature en este repo es `enhancement` (no `type:feature` que el skill sugiere).
- Hay tensión entre la guía de `branch-pr` (strict issue-first) y la práctica real del repo (sin issues, sin labels `type:*`). Para próximos PRs, usar la convención del repo y documentar la divergencia en el PR body.
