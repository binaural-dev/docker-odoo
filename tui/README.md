# TUI — Textual launcher for docker-odoo

Interfaz interactiva (Textual) sobre el CLI `./odoo`. Lanzala con:

- `./odoo-tui` (shim, deprecado pero mantenido por compat)
- `./odoo tui` (subcommand nuevo, preferido)
- `python3 -m tui` (desarrollo)

## Arquitectura

```
tui/
  app.py            455 LOC  DockerOdooApp: entry point, compose, on_mount, event wiring
  dispatch.py       502 LOC  Action dispatch: _dispatch, _update_picker_async, modal result handlers
  runner.py         218 LOC  stream_command (asyncio subprocess + readline) + run_interactive
  keybindings.py    288 LOC  BINDINGS + action_* methods (cancel, toggle, filter, etc.) + instances.json save
  parser.py          37 LOC  Pure functions: parse_progress, classify_level
  config.py          27 LOC  Paths + generators.config_loader re-exports
  models.py         155 LOC  Declarative: Action, ACTIONS, CATEGORY_ORDER, LOG_LEVEL_COLORS
  actions.py        100 LOC  Argv builders for invoking ./odoo
  __main__.py        44 LOC  CLI entry + --dev flag
  __init__.py         1 LOC
  screens/
    module_picker.py        fzf-style module selector (OptionList)
    input_modal.py          generic input form
    confirm_modal.py        yes/no confirmation
  widgets/
    update_progress.py      progress bar + log level filters + cancel button
    items.py                InstanceItem, AllInstancesItem, ActionItem, CategoryHeaderItem
  styles/
    odoo-tui.tcss          Textual CSS
```

## Performance notes (sesión 2026-06-16)

El bug "se cuelga al realizar operaciones" reportado por el usuario fue
causado por `subprocess.Popen(bufsize=1, stdout=PIPE)`: en Python, ese modo
SOLO es line-buffered cuando el fd es un tty. Con PIPE, cae a block-buffering
(4-8 KB), y Odoo no flushea seguido → el `for line in proc.stdout` quedaba
esperando → UI congelada.

**Fix**: `tui/runner.py` usa `asyncio.create_subprocess_exec` +
`await stream.readline()`, que sí es line-buffered real.

Otras mejoras:
- Cache de widgets (`#output`, `#update_progress`) en `on_mount` para no
  hacer `query_one` por línea
- Cancel con `terminate() → wait(5s) → kill() → wait(2s)` (no más zombies)
- `_save_instances_json` puro, nunca toca DOM desde thread secundario

## Tests

`scripts/tui_smoke_test.py` — 47/47 OK, incluye 3 tests de regresión
(`TuiStreamingRegressionTest`):

- `test_streaming_with_slow_output_does_not_hang`
- `test_streaming_cancelled_returns_partial`
- `test_save_json_from_thread_does_not_crash`

Para correr: `python3 scripts/tui_smoke_test.py -v`
