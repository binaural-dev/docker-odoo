# Arquitectura interna de `odoo_cli/core/`

> Generado leyendo el código real de `odoo_cli/core/runner.py`, `cli_runner.py`,
> `dispatch.py`, `instance.py`, `actions/*.py` y `tests/test_actions.py` — no es
> un resumen de memoria. Complementa a
> [`docs/comandos-odoo.md`](./comandos-odoo.md) (que documenta los comandos
> desde afuera) con la vista de "cómo está armado por dentro" el paquete que
> esos comandos terminan invocando.

## 1. El problema que resuelve este paquete

El `./odoo` original era un script bash/Python monolítico. Hoy `./odoo` es un
shim de 331 líneas (`odoo:1-36`, en la **raíz del repo** — no existe ningún
`odoo_cli/odoo`, el paquete `odoo_cli/` solo contiene `__init__.py` y
`core/`) cuyo único trabajo es armar el argparse, bootstrapear un runner
concreto y delegar todo el resto a `odoo_cli.core`:

```python
"""
Thin dispatcher: parses argparse, builds a :class:`CliRunner`, then
hands control to :func:`odoo_cli.core.dispatch.dispatch` which calls
the appropriate action module under :mod:`odoo_cli.core.actions`.
"""
```

La razón de separar así el código (documentada en
`docs/migracion-master-a-multi.md`) es que el `./odoo` original llegó a 1208
LOC monolíticas — la extracción a `odoo_cli/core/` con un `Runner` es lo que
permite que **la misma lógica de negocio** (start, stop, psql, update, ...) la
invoquen tanto el CLI real como, eventualmente, la TUI, sin duplicar código.

Las piezas:

- **`runner.py`** — el contrato (`Protocol`) que toda action consume para
  hacer I/O.
- **`cli_runner.py`** — la implementación concreta que usa `print`/`input`/
  `subprocess` (la que usa `./odoo` hoy).
- **`dispatch.py`** — el router: toma el `Namespace` de argparse y llama a la
  función de `actions/*.py` que corresponde.
- **`instance.py`** — helpers de solo-lectura sobre `instances.json` y los
  contenedores (declara ser "runner-agnostic", aunque en la práctica tiene
  una excepción puntual — ver sección 5).
- **`actions/*.py`** — la lógica de negocio real de cada subcomando, escrita
  contra el `Runner` como parámetro (aunque, como se ve en la sección 7, no
  siempre se respeta el contrato al pie de la letra).

## 2. El `Runner` Protocol: por qué `Protocol` y no `ABC`

La justificación está escrita como docstring de módulo en
`odoo_cli/core/runner.py:1-21`, textual (cita completa, sin omitir el párrafo
sobre `TextualRunner` de las líneas 17-20):

```python
"""Runner protocol — the user-I/O surface used by every action module.

Why a Protocol (and not an ABC)?
-------------------------------
The actions live in :mod:`odoo_cli.core.actions` and need to call
``runner.info(...)``, ``runner.confirm(...)``, ``runner.run_streamed(...)``,
etc. We want them to be testable with a ``FakeRunner`` that records calls
and stubs subprocess. We also want them to be callable from the real
``CliRunner`` and, eventually, a ``TextualRunner``.

A :class:`typing.Protocol` gives us structural typing: the actions can
type-annotate ``runner: Runner`` and Python's duck typing is enough.
The action modules do not need to import the protocol at runtime to
work; the protocol is for humans and type checkers, not for the
runtime contract.

The future ``TextualRunner`` (out of scope for this batch) will be a
separate class in this package that implements the same protocol but
routes every method to the Textual event loop / widgets. It will be
wired up when the TUI starts using the action modules directly.
"""
```

En criollo: con una `ABC` cada implementación (`CliRunner`, `FakeRunner`, la
futura `TextualRunner`) tendría que heredar explícitamente de la clase base
para que `isinstance`/el type checker la reconozcan. Con `Protocol` alcanza con
que la clase tenga los métodos con la firma correcta — **duck typing
verificado estáticamente**. Esto es lo que le permite a `tests/test_actions.py`
definir un `FakeRunner` que es una clase plana sin herencia (`class
FakeRunner:` a secas, `tests/test_actions.py:76`) y que igual tipa como
`Runner` en cualquier action.

La clase `Runner` arranca en `odoo_cli/core/runner.py:28` y sus nueve métodos
ocupan las líneas 37-90. Cada método real lleva su propio docstring de una o
más líneas (no un cuerpo `...`) — el bloque de abajo es un **resumen de las
firmas**, sin los docstrings individuales, pensado para lectura rápida; para
el texto exacto de cada docstring hay que ir al archivo:

```python
class Runner(Protocol):
    def info(self, msg: str) -> None: ...
    def warn(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...
    def confirm(self, prompt: str, default: bool = False) -> bool: ...
    def select_one(self, title: str, options: list[tuple[str, str]]) -> str | None: ...
    def select_many(self, title: str, options: list[tuple[str, str]]) -> list[str]: ...
    def prompt_text(self, prompt: str, default: str = "") -> str: ...
    def run_streamed(self, argv: list[str], cwd: str, on_line: Callable[[str], None] | None = None) -> int: ...
    def run_interactive(self, argv: list[str], cwd: str) -> int: ...
```

La regla que se declara junto al contrato (`odoo_cli/core/runner.py:33-35`) es
tajante: **las actions nunca deben llamar `print`/`input`/`subprocess.run`
directamente** — todo pasa por el runner. Como se documenta en la sección 5 y
la sección 7, esta regla **no se cumple hoy** en varios puntos del código: es
la intención declarada, no una invariante verificada.

Nueve métodos, tres familias:

| Familia | Métodos | Uso |
|---|---|---|
| Logging | `info`, `warn`, `error` | Líneas de estado (colores en CLI) |
| Prompts | `confirm`, `select_one`, `select_many`, `prompt_text` | Preguntarle algo al usuario |
| Subprocess | `run_streamed`, `run_interactive` | Correr comandos externos (docker, git) |

## 3. `CliRunner`: la implementación real

`odoo_cli/core/cli_runner.py` es la implementación que usa `./odoo` hoy. Su
propio docstring de módulo describe el fallback de `select_one`/`select_many`
así (`odoo_cli/core/cli_runner.py:12-17`):

```python
"""
The simple ``input()`` fallback for ``select_one`` / ``select_many`` is
intentionally minimal: in commit 6 (extract prompts) it will be
replaced by the full ANSI grid menu that lives in
:mod:`odoo_cli.core.prompts`. We do NOT want to drag that menu into
this module — keeping the surface small is what lets the future
``TextualRunner`` override it cleanly.
"""
```

**Este docstring quedó desactualizado y hoy describe algo que ya no pasa.**
`git log --oneline -- odoo_cli/core/prompts.py` muestra que el "commit 6"
mencionado ya se hizo hace rato: `3bb89c4 refactor(odoo): extract prompts to
odoo_cli.core.prompts using CliRunner` está mergeado, y sobre él hay commits
posteriores (`64d33d7`, `df2fb13`, `2adb142`) que siguen tocando ese módulo.
`odoo_cli/core/prompts.py` existe, tiene 601 líneas y define
`prompt_selection` completamente implementado. Como consecuencia:
`odoo_cli.core.prompts` **siempre** se importa con éxito en un checkout
normal del repo, así que el `except ImportError:` de
`CliRunner.select_one`/`select_many` (`cli_runner.py:138-161,170-200`) es
código muerto en la práctica — nunca se dispara salvo que alguien borre o
rompa `prompts.py` a propósito. Lo que ve cualquier usuario de `./odoo` hoy
es el menú ANSI grid de `prompts.py` (`prompt_selection`), no el fallback
numerado con `input()`.

Dos detalles concretos de implementación que vale la pena registrar:

- **Colores ANSI fijos** (`odoo_cli/core/cli_runner.py:29-32`): `_INFO` cian
  (`\033[1;36m`), `_WARN` amarillo (`\033[1;33m`), `_ERR` rojo (`\033[1;31m`).
  Son los mismos códigos que usaba el `./odoo` legacy — están documentados así
  para que quien migre otro runner sepa qué colores replicar.
- **`confirm()` lee raw keypresses cuando hay TTY** (`cli_runner.py:51-127`):
  usa `termios`/`tty.setraw` para que `Esc` responda "No" sin necesitar
  Enter — un atajo rápido equivalente a tipear `n`. Si `stdin` no es una TTY
  (pipes, tests, CI) cae a un `input()` simple. El default (`s`/`S` vs `n`/`N`)
  se respeta igual en ambos caminos; acciones destructivas (`remove`,
  `git push`) pasan `default=False` a propósito, así que ahí Enter/Esc
  siempre contestan "No".
- **`run_streamed` captura AMBOS streams, no solo stdout**
  (`cli_runner.py:210-232`): la llamada real es
  `subprocess.run(argv, cwd=cwd, capture_output=True, text=True)`
  (`cli_runner.py:223-228`), sin ningún `stderr=` explícito. En la semántica
  estándar de `subprocess.run`, `capture_output=True` fija **tanto**
  `stdout=PIPE` **como** `stderr=PIPE` — no hereda nada del proceso padre.
  El propio docstring del método (`cli_runner.py:220-221`) afirma lo
  contrario ("`stderr` is inherited from the parent process so errors... are
  still visible"), pero es un comentario incorrecto que nadie corrigió: el
  método nunca lee `result.stderr` en ninguna parte de su cuerpo, así que el
  stderr del subproceso queda **capturado y descartado en silencio** — lo
  opuesto de "sigue siendo visible". Esto es relevante en la práctica porque
  `run_streamed` es el método que documentan usar los "comandos cuyo stdout
  el usuario quiere ver" (ver sección 7): si esos comandos fallan y escriben
  el error a stderr, ese error no se muestra en ningún lado.

## 4. `dispatch.py`: cómo un comando llega a `actions/*.py`

El docstring de módulo (`odoo_cli/core/dispatch.py:1-26`) explica la razón de
tener el dispatch en un archivo separado: es la "wiring" entre argparse (qué
subcomando eligió el usuario) y las funciones de `odoo_cli.core.actions`, y
mantenerlo separado hace que sea reusable desde la TUI y fácil de testear
(`dispatch(runner, args, config)` + assert sobre lo que grabó el runner).

La función pública es una sola:

```python
def dispatch(
    runner: "Runner", args: "Namespace", config: dict, base_path: str
) -> int:
```

Internamente es un `if/elif` largo sobre `args.action` (`dispatch.py:176-290`)
que llama a la función de `actions/*.py` correspondiente, por ejemplo:

```python
elif args.action == "start":
    start_odoo(runner, config, args.instance)
```

Antes de despachar, hay una resolución de instancia para los subcomandos que
la necesitan. El set `_INSTANCE_AWARE_ACTIONS`
(`dispatch.py:87-90`) enumera exactamente cuáles:

```python
_INSTANCE_AWARE_ACTIONS = {
    "start", "stop", "restart", "logs", "remove",
    "fix-files", "init", "bash", "psql", "pw", "update",
}
```

Para esos, `_resolve_instance()` (`dispatch.py:93-132`) decide la instancia:
si `args.instance` ya vino con valor, se usa tal cual; el caso especial es
`pw -d <db>` sin instancia — ahí busca en qué instancias existe esa base con
`find_instances_with_db` (de `instance.py`) y, si hay una sola coincidencia,
la usa sin preguntar. **Si hay varias, no llama a `runner.select_one` (el
método del `Runner` Protocol)**: llama directamente a la función
`prompt_selection` de `odoo_cli.core.prompts`
(`dispatch.py:118-130`, import en la línea 119, llamada en las líneas
126-130), que hace su propio manejo de teclado raw con `termios` por fuera
del contrato `Runner`. Es decir, este camino bypasea el Protocol descrito en
la sección 2 en vez de ejercitarlo — `runner.select_one` como método del
contrato solo se ejercita hoy en `tests/test_runner.py`, no en este flujo
real de `dispatch.py`. En cualquier otro caso, `_resolve_instance` cae a
`prompt_for_instance`.

El caso especial documentado en el propio módulo es `tui`
(`dispatch.py:20-26,154-170`): la acción `tui` **no** llama a
`odoo_cli.core.actions` — lanza `tui.__main__.main()` directamente, porque la
TUI es "su propio programa" y `./odoo tui` es solo un entry point delgado.
Antes de llamarlo, reescribe `sys.argv` quitando el `"tui"` posicional para
que el argparse interno de la TUI no lo rechace.

## 5. Helpers de `instance.py`

`instance.py` **se declara** deliberadamente runner-agnostic en su propio
docstring de módulo (`instance.py:1-16`): "these helpers don't print
anything and don't talk to the user". **Esto no es cierto al 100%**: hay una
excepción puntual, y está justo en la primera función del archivo.
`get_instance_services` (`instance.py:45-65`, el mismo rango que cita este
documento para esa función) llama a `print()` dos veces y luego a
`sys.exit(1)` cuando la instancia pedida no existe en `instances.json`:

```python
if instance not in config["instances"]:
    print(
        f"Error: Instancia '{instance}' no existe en instances.json"
    )
    print(
        f"Instancias disponibles: "
        f"{', '.join(config['instances'].keys())}"
    )
    sys.exit(1)
```

(`instance.py:56-63`, confirmado con `grep -n "print(" instance.py`, que
solo devuelve esas dos líneas — ambas dentro de esta función. No hay otro
`print` en el resto del archivo). O sea: el resto de `instance.py` sí es
runner-agnostic tal como se describe, pero esta función puntual le habla al
usuario por stdout y termina el proceso sin pasar por ningún `Runner` —
justo lo que el módulo dice no hacer. En la práctica esto es relevante
porque `get_instance_services` la llaman `odoo_cli/core/actions/access.py`
(`show_logs`, línea 72) y varias funciones de `lifecycle.py` (`start_odoo`
línea 113, `stop_odoo` línea 163, `remove_odoo` línea 258, `fix_filestore`
línea 293) — `dispatch.py` **no** es un llamador: `grep -n
"get_instance_services" odoo_cli/core/dispatch.py` no devuelve ningún
resultado —, así que ese `sys.exit(1)` puede dispararse en medio de un flujo
que, por lo demás, reporta todo a través del `runner`.

La razón declarada en el docstring de módulo (`instance.py:9-16`) para
separar este archivo de las actions sigue siendo válida como intención: "qué
servicio/DB/usuario existe" vs. la lógica de workflow que sí vive en las
actions — la excepción de arriba no invalida el diseño general, pero sí hay
que tenerla presente.

Funciones principales:

- `get_instance_services(config, instance=None)` — nombres de servicio compose
  (`odoo-<nombre>`) para una instancia o todas. Sale con `print()` +
  `sys.exit(1)` si la instancia no existe en `instances.json`
  (`instance.py:45-65`) — ver la excepción documentada arriba.
- `get_db_services(config, instance=None)` — igual pero para `db-<nombre>`;
  respeta el flag `create_container` de cada base (una DB externa con
  `create_container=false` no genera un servicio, `instance.py:68-92`).
- `get_databases(config, instance)` / `get_users(config, instance, dbname)` —
  ejecutan `psql -At -c "SELECT ..."` dentro del contenedor Odoo vía
  `docker compose exec` y devuelven `[]` silenciosamente ante cualquier error
  (`instance.py:100-171`) — la responsabilidad de manejar el caso vacío
  (típicamente cayendo a input manual) queda del lado del caller.
- `find_instances_with_db(config, dbname)` — recorre todas las instancias
  llamando a `_instance_has_db` (`instance.py:174-218`); es lo que usa
  `dispatch._resolve_instance` para el caso `pw -d`.
- `get_custom_repos` / `get_custom_modules` — lectura de filesystem pura sobre
  `src/custom/` y las rutas de `addons` de una instancia (`instance.py:226-266`).

## 6. Cómo se testea: `FakeRunner`

`tests/test_actions.py` define un `FakeRunner` (`tests/test_actions.py:76-142`)
que es exactamente lo que el docstring de `runner.py` promete: una clase
plana, sin herencia de nada, que satisface el `Protocol` por duck typing.

```python
class FakeRunner:
    """Minimal in-memory ``Runner`` for tests.

    Records every call to ``info``/``warn``/``error`` in ``messages``
    and answers ``confirm``/``select_*``/``prompt_text`` from a
    pre-loaded sequence of responses.

    The action modules are duck-typed against :class:`Runner`, so a
    plain class with the right method names is enough — no need to
    inherit from any base.
    """

    def __init__(
        self,
        confirm_answers: list[bool] | None = None,
        select_one_answers: list[str | None] | None = None,
        text_answers: list[str] | None = None,
    ) -> None:
        self.messages: list[tuple[str, str]] = []  # (level, text)
        ...
```

`info`/`warn`/`error` graban `(nivel, texto)` en `self.messages` en vez de
imprimir; `confirm`/`select_one`/`prompt_text` consumen de una cola
pre-cargada (`confirm_answers`, `select_one_answers`, `text_answers`) y caen al
`default` cuando la cola se vacía; `run_streamed`/`run_interactive` devuelven
`0` sin tocar el sistema real. `tests/test_prompts.py` define su propio
`FakeRunner` (más chico, enfocado en `prompt_text`) para testear
`odoo_cli/core/prompts.py` en aislamiento.

Ejemplo real de uso: `ValidateInstancesTest` arranca en
`tests/test_actions.py:145`, pero **no** contiguo con el método que se
transcribe a continuación — entre la declaración de la clase y
`test_duplicate_external_port_exits` hay un helper `_make_config`
(`tests/test_actions.py:148-162`) y otro test completo,
`test_passes_for_valid_config` (`tests/test_actions.py:164-169`), que se
omiten acá por brevedad:

```python
class ValidateInstancesTest(unittest.TestCase):
    def _make_config(self, **overrides) -> dict:
        ...  # (omitido — construye un instances.json mínimo)

    def test_passes_for_valid_config(self):
        ...  # (omitido)

    # tests/test_actions.py:171
    def test_duplicate_external_port_exits(self):
        config = self._make_config()
        config["instances"]["b"] = {
            "external_port": 8069,  # clashes with a.external_port
            "longpolling_port": 8073,
            "database": "db_b",
        }
        config["databases"]["db_b"] = {"user": "odoo", "password": "odoo", "port": 5432}
        runner = FakeRunner()
        with self.assertRaises(SystemExit) as cm:
            validate_instances(runner, config)
        self.assertEqual(cm.exception.code, 1)
        err_texts = [m[1] for m in runner.messages if m[0] == "error"]
        self.assertTrue(...)
```

Esto es exactamente lo que el docstring de `runner.py` señala como la
motivación de usar `Protocol`: la action (`validate_instances`) no sabe ni le
importa que la está llamando un test — solo ve algo que cumple la forma de
`Runner`.

## 7. Un comando real de punta a punta: `start`

Para no quedarnos en la teoría, así se ve `start_odoo`
(`odoo_cli/core/actions/lifecycle.py:100-155`) usando el `Runner`:

```python
def start_odoo(runner: "Runner", config: dict, instance: str | None) -> None:
    """Start database(s), Odoo instance(s), and nginx."""
    if instance:
        runner.info(f"\n=== ▶️  INICIANDO INSTANCIA: {instance.upper()} ===\n")
    else:
        runner.info("\n=== ▶️  INICIANDO TODAS LAS INSTANCIAS ===\n")

    from odoo_cli.core.actions.validate import check_host_port_collisions

    check_host_port_collisions(runner, config, compose_file=COMPOSE_FILE)

    db_services = get_db_services(config, instance)
    odoo_services = get_instance_services(config, instance)

    # Start managed DBs
    if db_services:
        runner.info("→ Iniciando base(s) de datos...")
        _docker_compose(runner, "up", "-d", *db_services)
    ...
```

Y el helper interno que envuelve todo `docker compose`
(`odoo_cli/core/actions/lifecycle.py:38-50` — la función arranca en la línea
38, no en la 35; las líneas 35-37 son la constante `COMPOSE_FILE =
"docker-compose.generated.yml"` seguida de líneas en blanco):

```python
def _docker_compose(runner: "Runner", *args: str) -> int:
    """Run ``docker compose -f COMPOSE_FILE <args>`` and stream its output.
    ...
    We deliberately do NOT use ``run_streamed`` here: the docker compose CLI
    produces its own progress bars and TTY-aware output, and capturing that
    into a Python buffer would mangle it (no TTY → no progress, no colors).
    """
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, *args]
    runner.info(" ".join(cmd))
    return runner.run_interactive(cmd, cwd=".")
```

Nótese la decisión explícita: `_docker_compose` usa `run_interactive` (no
`run_streamed`) precisamente porque `docker compose` necesita la TTY para sus
barras de progreso — es la misma distinción de la tabla de la sección 2,
aplicada en la práctica.

**Corrección importante sobre esta misma función.** El módulo dice en su
docstring (`lifecycle.py:1-16`) que las actions "share the same shape: emit a
banner via `runner.info`/`runner.warn`, run one or more `docker compose`
subprocesses through `runner.run_streamed`" — pero `start_odoo` (la función
citada arriba, línea por línea) **no termina ahí**: después de levantar los
servicios Odoo llama dos veces a `subprocess.run(...)` **directo**,
bypaseando el `Runner` por completo:

```python
# Fix filestore permissions
for svc in odoo_services:
    try:
        subprocess.run(
            [
                "docker", "compose", "-f", COMPOSE_FILE, "exec", "-T", "-u", "root", svc,
                "chown", "-R", "odoo:odoo", "/home/odoo/data",
            ],
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
```

(`lifecycle.py:127-135`, chown del filestore) y, más abajo, antes de levantar
nginx:

```python
subprocess.run(
    ["docker", "compose", "-f", COMPOSE_FILE, "rm", "-s", "-f", "nginx"],
    stderr=subprocess.DEVNULL,
)
```

(`lifecycle.py:143-146`, force-recreate de nginx). Ninguna de las dos pasa
por `runner.run_streamed`/`run_interactive`; ninguna reporta nada al usuario
a través del `runner` (los `try/except Exception: pass` tragan cualquier
error en silencio, incluso más allá de lo que ya descarta `stderr=DEVNULL`).

El mismo patrón se repite en otras dos funciones de este mismo archivo:
`remove_odoo` tiene un `subprocess.run(["docker", "compose", "-f",
COMPOSE_FILE, "rm", "-s", "-v", "-f", svc])` directo en
`lifecycle.py:260-265` (cuando `instance` viene con valor), y `fix_filestore`
repite el mismo chown directo en `lifecycle.py:297-303`. En total,
`lifecycle.py` tiene 4 llamadas a `subprocess.run(` fuera del `Runner`
(líneas 127, 143, 260 y 297) — y el patrón no es exclusivo de este archivo:
`grep -rn "subprocess.run(" odoo_cli/core/actions/*.py` devuelve 44
ocurrencias en total en `actions/`, repartidas también en `access.py`,
`hosts.py`, `validate.py`, `modules.py` y `maintenance.py`.

Esto contradice directamente la regla "tajante" citada en la sección 2 (las
actions nunca deben llamar `subprocess.run` directo) y también la afirmación
de que `lifecycle.py` la respeta al pie de la letra. Lo más probable, a
juzgar por el propio código, es que esta regla se aplique estrictamente solo
a la comunicación *con el usuario* (banners, confirmaciones) y no a
subprocesos "silenciosos" de mantenimiento (chown, rm de un servicio antes de
recrearlo) cuyo resultado no se muestra — pero eso no está documentado en
ningún docstring, es una inferencia a partir del código, no una regla
escrita.

Un segundo ejemplo, con `confirm()` en el camino destructivo
(`odoo_cli/core/actions/lifecycle.py:247-255`):

```python
def remove_odoo(runner: "Runner", config: dict, instance: str | None) -> None:
    ...
    runner.warn(
        f"\n⚠️  \033[1mPELIGRO\033[0m: Esto eliminará {target} "
        f"y sus volúmenes de datos."
    )
    if not runner.confirm(
        "¿Estás seguro de que deseas continuar?", default=False
    ):
        runner.info("\nOperación cancelada.")
        return
```

Este fragmento sí es fiel al `Runner` — el `confirm()` real está ahí. Pero,
como se muestra arriba, unas líneas más abajo en la misma función
(`lifecycle.py:260-265`) aparece el `subprocess.run` directo que el
documento no debe omitir.

Desde 2026-08, `remove_odoo` además tiene un gate previo al `confirm()`:
si la instancia (o, en el caso de `remove` sin argumento, cualquier
instancia de la config) tiene `"production": true` en `instances.json`
(`config_loader.is_production_instance`), la función corta con
`runner.error(...)` + `sys.exit(1)` **antes** de llegar al `runner.warn`/
`confirm` de arriba — ni siquiera se muestra el prompt. Ver
`lifecycle.py:220-241`.

## 8. El plan hacia `TextualRunner`

La nota más explícita sobre esto **no** está en `odoo_cli/core/`, sino en el
propio shim de la raíz del repo (`odoo:19-35`, **no** `odoo_cli/odoo` — ese
path no existe):

```python
"""
Future Textual integration
--------------------------
The Textual TUI (in :mod:`tui`) is independent for now: it spawns
``./odoo <action> ...`` via :mod:`tui.actions`, which means each
action runs in its own subprocess and prints to the TUI's
log widget. A future refactor could:

  1. Add a :class:`odoo_cli.core.runner.TextualRunner` that
     implements the same :class:`Runner` protocol but routes
     I/O through Textual widgets.
  2. Have the TUI import :mod:`odoo_cli.core.dispatch` directly
     and call ``dispatch(textual_runner, args, config, base_path)``
     from a worker thread.

That would eliminate the per-action subprocess and let the TUI
control every print/log line in real time. Out of scope for this
batch.
"""
```

Y el mismo plan se repite, en menor detalle, en tres lugares de
`odoo_cli/core/`:

- `odoo_cli/core/runner.py:17-20` — "The future ``TextualRunner`` (out of
  scope for this batch) will be a separate class in this package that
  implements the same protocol but routes every method to the Textual event
  loop / widgets."
- `odoo_cli/core/cli_runner.py:15-17` — justifica por qué `CliRunner` no debe
  cargar con el menú ANSI completo: "keeping the surface small is what lets
  the future ``TextualRunner`` override it cleanly." (Nota: como se explica
  en la sección 3, ese mismo docstring describe un fallback de `input()` que
  hoy es código muerto — el menú ANSI ya está extraído a `prompts.py`.)
- `odoo_cli/core/__init__.py:10-12` — "A future :class:`TextualRunner` (NOT in
  this batch) — the Textual TUI reuses the same action modules and routes
  their I/O through Textual widgets instead of stdout/stdin/subprocess." (La
  línea 9 de ese mismo archivo todavía pertenece a la viñeta anterior, sobre
  `CliRunner` — el párrafo de `TextualRunner` empieza en la 10, no en la 9.)

Es decir: **hoy la TUI no comparte runtime con el CLI**. `tui/` tiene su
propio `dispatch.py` y `runner.py`, con un modelo completamente distinto: cada
acción se dispara como subprocess de `./odoo <acción> ...`
(`tui/dispatch.py` + `tui/actions.py`) y el output se parsea/streamea hacia un
`RichLog` de Textual. El plan de unificación consiste en:

1. Escribir una clase `TextualRunner` en `odoo_cli/core/` que implemente el
   mismo `Runner` Protocol, pero enrutando `info`/`warn`/`confirm`/etc. hacia
   widgets de Textual en vez de a stdout/stdin.
2. Que la TUI importe `odoo_cli.core.dispatch` directamente y llame
   `dispatch(textual_runner, args, config, base_path)` desde un worker
   thread, en vez de spawnear `./odoo` como subprocess por cada acción.

El beneficio explícito que se busca es eliminar el subprocess por acción y
que la TUI controle cada línea de log en tiempo real, sin la capa intermedia
de parsear stdout de un proceso hijo. A la fecha de este documento **no está
implementado** — es trabajo futuro, marcado "out of scope for this batch" en
el propio código.

## 9. Resumen de responsabilidades

| Módulo | Responsabilidad | No hace |
|---|---|---|
| `runner.py` | Define el contrato `Runner` (`Protocol`) | No implementa nada |
| `cli_runner.py` | `CliRunner`: implementación real con print/input/subprocess | No conoce las actions |
| `dispatch.py` | Rutea `args.action` → función de `actions/*.py` | No implementa lógica de negocio |
| `instance.py` | Lee `instances.json` + hace `psql` de solo-lectura | Casi no le habla al usuario ni usa `Runner` — salvo `get_instance_services`, que sí llama `print`+`sys.exit(1)` directo (sección 5) |
| `actions/*.py` | Lógica de negocio de cada subcomando, contra `Runner` | En teoría nunca debería llamar `print`/`input`/`subprocess` directo; en la práctica `lifecycle.py` y otros módulos de `actions/` sí lo hacen para subprocesos "silenciosos" (sección 7) |
| `tests/test_actions.py::FakeRunner` | Runner in-memory para tests | No es una subclase de nada — duck typing puro |
