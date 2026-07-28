# TUI — Textual launcher for docker-odoo

Interfaz interactiva (Textual) sobre el CLI `./odoo`. Lanzala con:

- `./odoo-tui` (shim, deprecado pero mantenido por compat)
- `./odoo tui` (subcommand nuevo, preferido)
- `python3 -m tui` (desarrollo)

## Arquitectura

```
tui/
  app.py            558 LOC  DockerOdooApp: entry point, compose, on_mount, event wiring, streaming
  dispatch.py       553 LOC  Action dispatch: _dispatch, _update_picker_async, modal result handlers
  runner.py         218 LOC  stream_command (asyncio subprocess + readline) + run_interactive
  keybindings.py    306 LOC  BINDINGS + action_* methods (cancel, toggle, filter, etc.) + instances.json save
  parser.py          37 LOC  Pure functions: parse_progress, classify_level
  config.py          27 LOC  Paths + generators.config_loader re-exports
  models.py         165 LOC  Declarative: Action, ACTIONS, CATEGORY_ORDER, CATEGORY_BADGE_WIDTH
  actions.py        100 LOC  Argv builders for invoking ./odoo
  __main__.py        44 LOC  CLI entry + --dev flag
  __init__.py         1 LOC
  screens/
    module_picker.py  163 LOC  fzf-style module selector (OptionList)
    input_modal.py    110 LOC  generic input form
    confirm_modal.py   59 LOC  yes/no confirmation
  widgets/
    update_progress.py  212 LOC  progress bar + log level filters + cancel button
    items.py             125 LOC  InstanceItem, AllInstancesItem, ActionItem, CategoryHeaderItem
  styles/
    odoo-tui.tcss       252 LOC  Textual CSS externo (hot-reload, ver abajo)
```

(LOC al 2026-07-28; correr `wc -l tui/*.py tui/screens/*.py tui/widgets/*.py tui/styles/*.tcss`
para el número exacto si volvió a cambiar.)

## Acciones interactivas vs. streameadas: cuándo usar cada una

Toda `Action` en `models.py` corre de una de dos formas — la elección es
`interactive: bool`, no una tercera opción:

- **Streameada (default, `interactive=False`)**: `_execute_one` corre el
  comando vía `tui.runner.stream_command`, con su stdout mostrado en vivo en
  el `RichLog`. Correcta para cualquier acción cuyo `Runner` del lado del
  CLI solo llama `info`/`warn`/`error` — es decir, que no necesita leer
  nada de stdin más allá de lo que ya se le pasó por argv. `sync` y
  `submodule-status` son así: una vez que el proyecto/branch llegan como
  argumento, corren de punta a punta sin más interacción.
- **Interactiva (`interactive=True`)**: `_execute_one` llama
  `self._run_interactive`, que hace `self.suspend()` y le entrega el
  terminal real al subproceso (`tui.runner.run_interactive`, sin
  streaming). Necesaria para cualquier acción cuyo `Runner` del lado del
  CLI llama `confirm`/`prompt_text`/`prompt_selection` — no hay forma de
  responder eso desde un `RichLog` que solo muestra texto. `bash`, `logs`,
  `psql` y `update-tags` son así: `update-tags` en particular tiene un loop
  de "¿otro submódulo?" + confirmaciones de push/PR que solo tienen sentido
  con una TTY real detrás.

Un campo de `InputModal` puede necesitar volverse opcional **solo para una
acción específica** aunque otras acciones compartan la misma constante de
arg — `ARG_REPO` es requerido para `sync` pero opcional para
`submodule-status` (vacío = "todos los proyectos"). Esto se resuelve con un
`if action.action_id == "...":` puntual en el loop que arma `fields` dentro
de `DispatchMixin._dispatch`, no cambiando el dict base de
`_arg_to_field` — ese dict es compartido y una edición ahí afecta a todas
las acciones que usan ese arg.

## RichLog: siempre escapar contenido no confiable

El `RichLog` de `app.py` se crea con `markup=True` para que los mensajes
propios del TUI (`self._log("[green]✓ OK[/green]")`) salgan con color. Eso
implica que **cualquier texto que no sea un literal escrito a mano en el
código** — stdout de un subproceso, un mensaje de excepción, un nombre de
instancia raro — tiene que pasar por `rich.markup.escape()` antes de
interpolarse en un `_log(f"...")`. Sin eso, un traceback de Odoo con un
dominio tipo `[('field','=',1)]`, o un `OSError` con `[Errno 2] ...`, rompe
o garabatea el log entero.

El punto de entrada canónico es `app.py:_run_streamed.on_line`: ahí se
escapa una sola vez, antes de que la línea llegue tanto al `RichLog` como
al buffer de `UpdateProgress` (que la puede volver a escribir sin escapar
si no se hace ahí, al togglear un filtro de nivel con `1`/`2`/`3`/`4`).

## Buffers con límite de tamaño (evitar memory leak)

Tres estructuras acumulan líneas de log durante la vida de la app y **las
tres deben estar capadas** al mismo valor (2000), o una sesión larga
corriendo varios `update` grandes las hace crecer sin límite:

- `RichLog(..., max_lines=2000)` en `app.py` (lo cappea Textual mismo).
- `UpdateProgress._all_lines` — capado a mano en `add_lines_bulk`/`add_line`.
- `DockerOdooApp._output_buffer` (espejo en texto plano para
  `action_copy_output`) — capado a mano en `_trim_output_buffer()`.

Si agregás un cuarto buffer que también acumule líneas de log, cappealo
igual desde el día uno — es más fácil olvidarlo que un widget visible
(Textual no se queja, el buffer solo crece en silencio hasta que la sesión
se pone lenta).

## Diseño / CSS (`tui/styles/odoo-tui.tcss`)

- **Responsive**: los anchos de modales/paneles usan `%` con `min-width`/
  `max-width` (no columnas fijas), para que se achiquen en terminales o
  panes de tmux angostas en vez de desbordar. Si agregás un widget con
  ancho fijo, pensalo dos veces — es el error que se corrigió en
  `#modal_box` (`width: 70` → `width: 90%`).
- **No declares CSS que nada en Python asigna**: hubo clases (`.active`/
  `.inactive` en los chips de filtro) que existían en el `.tcss` pero
  ningún widget las agregaba nunca — el estado real se manejaba con
  markup inline en Python. CSS "muerto" así confunde más de lo que ayuda.
- Hot-reload: `textual run --dev ./odoo-tui` recarga el `.tcss` sin
  reiniciar la app (el CSS está externalizado desde la sesión 2026-06-10).

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

## Performance notes (sesión 2026-07-24)

El usuario reportó que la TUI "se pone lenta" con el uso continuado (no al
tildarse de golpe, sino degradando en una sesión larga). Se descartó
primero `rich.markup.escape()` (agregado esa misma sesión, ver arriba) con
un benchmark: ~1.3µs por línea, 100k líneas = 0.13s — no explica nada
perceptible.

**Causa real:** `DockerOdooApp._output_buffer` no tenía tope, a diferencia
de los otros dos buffers de log (ver sección "Buffers con límite de
tamaño" arriba). Cada línea de cada acción corrida en la sesión —
especialmente `update`, que puede emitir decenas de miles— se acumulaba
ahí para siempre.

**Fix:** `_trim_output_buffer()` recorta a las últimas `MAX_OUTPUT_BUFFER_LINES`
(2000) después de cada `_log`/`_log_bulk`. `action_copy_output` solo usa las
últimas 500, así que no cambió su comportamiento.

## Tests

`scripts/tui_smoke_test.py` — 51/51 OK, incluye 3 tests de regresión
(`TuiStreamingRegressionTest`):

- `test_streaming_with_slow_output_does_not_hang`
- `test_streaming_cancelled_returns_partial`
- `test_save_json_from_thread_does_not_crash`

y una clase de integración de dispatch (`TuiActionDispatchIntegrationTest`,
sesión 2026-07-28) que navega el `ListView`/`InputModal` reales con `Pilot`
en vez de llamar `_dispatch`/`_odoo_cli_args` directamente — solo mockea la
frontera final del subproceso (`stream_command` o `_run_interactive`, según
si la acción es streameada o interactiva). Útil como plantilla para
verificar el dispatch real de cualquier acción nueva, no solo el argv que
construye en aislamiento:

- `test_submodule_status_empty_repo_means_all_projects`
- `test_submodule_status_with_project_typed_in`
- `test_update_tags_routes_through_interactive_suspend_path`
- `test_sync_still_requires_repo_unlike_submodule_status` (guardrail: el
  campo opcional de `submodule-status` no se filtra a `sync`)

Para correr: `python3 scripts/tui_smoke_test.py -v`
