# Tests del CLI `./odoo` (no de módulos Odoo)

> Generado leyendo `tests/`, `scripts/test_pw_*.py`, `scripts/tui_smoke_test.py`,
> `odoo_cli/core/runner.py` y `odoo_cli/core/cli_runner.py`. Cubre **solo** los
> tests que verifican el propio CLI/orquestador (`odoo_cli/core/`, los
> generadores en `.resources/generators/`, y algunos scripts sueltos en
> `scripts/`). Los tests de módulos Odoo (los que corren dentro de un
> contenedor, contra una DB real, vía `--test-tags`) son un tema aparte —
> ver la sección 6 para no confundirlos con `scripts/coverage` y
> `scripts/odoo-test`.

## 1. Qué se testea acá (y qué no)

Este repo es un CLI (`./odoo`) más un puñado de scripts de administración.
Su lógica de negocio vive en `odoo_cli/core/actions/*.py` y se abstrae del
I/O de usuario (`print`/`input`/`subprocess`) a través de un
`typing.Protocol` llamado `Runner` (`odoo_cli/core/runner.py:28`). Los tests
de esta sección prueban **esa lógica**: parsing, validación de
`instances.json`, generación de `docker-compose.generated.yml`/nginx,
resolución de instancias, etc. — todo sin tocar Docker ni una base de datos
real.

No es lo mismo que "testear un módulo Odoo": eso corre `odoo` de verdad
dentro de un contenedor con `--test-tags`, y es lo que hacen
`scripts/odoo-test` y `scripts/coverage` (sección 6).

## 2. Estructura real

```
tests/
├── __init__.py                  # "Package marker for the unit tests (stdlib unittest)."
├── test_actions.py               # 1463 líneas — maintenance.py y validate.py
├── test_compose_generator.py     # compose_generator.py / nginx_generator.py
├── test_docker_exec_hygiene.py   # convención: nada de `docker exec`/`docker cp` crudo
├── test_prompts.py               # odoo_cli/core/prompts.py (prompt_for_tag)
└── test_runner.py                # CliRunner (confirm/select_one/run_streamed/logging)
```

`tests/` es un paquete Python real (tiene `__init__.py`), y ese detalle
importa: es lo que hace que `python3 -m unittest discover` funcione sin
flags adicionales desde la raíz del repo — lo confirmé corriéndolo (ver
sección 3).

Fuera de `tests/`, hay tests sueltos en `scripts/` que **no** forman parte
de este paquete (esa carpeta no tiene `__init__.py`, así que
`unittest discover` desde la raíz no los toca):

```
scripts/test_pw_returncode.py       # regresión: reset_password / odoo-pw ignoraba el returncode de psql
scripts/test_pw_db_validation.py    # regresión: -d apuntando a una DB inexistente no abortaba
scripts/test_pw_resolve_instance.py # regresión: -d <dbname> no bastaba para resolver la instancia
scripts/tui_smoke_test.py           # smoke tests de la TUI (Textual) — 9 escenarios, ver su docstring
```

Cada uno de los tres `test_pw_*.py` documenta en su propio docstring el bug
original que corrigió (returncode ignorado, DB inexistente, resolución de
instancia por `-d`). Como `scripts/odoo-pw` no tiene extensión `.py` (es un
ejecutable de texto), estos tests no lo importan con un `import` normal:
lo cargan a mano con `importlib.util.spec_from_loader(...)` +
`SourceFileLoader` (`scripts/test_pw_returncode.py:178-179`, y otra vez en
`222-223` para el segundo escenario) para poder testear sus funciones sin
invocarlo como subproceso. Ojo con no confundirlo con el mismo patrón que
aparece más arriba en el archivo (línea 32, `loader = SourceFileLoader(...)`,
y línea 33, `spec = importlib.util.spec_from_loader(...)`, dentro de
`_load_odoo_wrapper()`): ese carga un archivo distinto, el wrapper `./odoo`
de la raíz del repo (`ODOO_WRAPPER`), no `scripts/odoo-pw` (`ODOO_PW_SCRIPT`).

## 3. Cómo correrlos

Es **stdlib `unittest`**, no pytest — confirmado por los imports (`import
unittest`, `from unittest.mock import patch` en los cinco archivos de
`tests/`) y por el propio docstring de `test_runner.py`:

> "These tests intentionally use stdlib `unittest` (not pytest) so they
> match the style of `scripts/tui_smoke_test.py` and have no extra
> dependencies." (`tests/test_runner.py:7-9`)

No hay `pytest.ini`, `tox.ini` ni sección `[tool.pytest]` en ningún
`pyproject.toml`/`setup.cfg` en la raíz del repo — no hay configuración de
pytest, punto. (Si tenés `pytest` instalado en tu entorno igual puede
correr estos archivos, porque pytest sabe descubrir `unittest.TestCase`;
de hecho hay un `.pytest_cache/` en la raíz de alguna corrida manual previa.
Pero el flujo soportado y documentado en cada archivo es `unittest`.)

**Correr todo de una:**

```bash
python3 -m unittest discover -v
```

Lo corrí: descubre los 5 módulos de `tests/` y ejecuta 81 tests.

**Correr un módulo puntual** (cada archivo trae el comando exacto en su
docstring):

```bash
python3 -m unittest tests.test_runner -v
python3 -m unittest tests.test_actions -v
python3 -m unittest tests.test_docker_exec_hygiene -v
python3 -m unittest tests.test_compose_generator -v
python3 -m unittest tests.test_prompts -v
```

**Los tests sueltos de `scripts/`** se corren directo como script (no como
módulo, porque `scripts/` no es un paquete):

```bash
python3 scripts/test_pw_returncode.py -v
python3 scripts/test_pw_db_validation.py -v
python3 scripts/test_pw_resolve_instance.py -v
python3 scripts/tui_smoke_test.py -v
```

## 4. `FakeRunner`: qué es y para qué sirve

Las acciones (`odoo_cli/core/actions/*.py`) nunca llaman `print`/`input`/
`subprocess` directo — reciben un `runner: Runner` y le delegan todo el
I/O. El contrato completo (`odoo_cli/core/runner.py:28-90`):

```python
class Runner(Protocol):
    def info(self, msg: str) -> None: ...
    def warn(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...
    def confirm(self, prompt: str, default: bool = False) -> bool: ...
    def select_one(self, title: str, options: list[tuple[str, str]]) -> str | None: ...
    def select_many(self, title: str, options: list[tuple[str, str]]) -> list[str]: ...
    def prompt_text(self, prompt: str, default: str = "") -> str: ...
    def run_streamed(self, argv: list[str], cwd: str, on_line=None) -> int: ...
    def run_interactive(self, argv: list[str], cwd: str) -> int: ...
```

En producción eso lo implementa `CliRunner` (`odoo_cli/core/cli_runner.py`),
con ANSI real y `subprocess.run` real. En los tests, un `FakeRunner`
duck-typed contra el mismo contrato reemplaza toda esa capa: no hay TTY, no
hay `input()`, no hay proceso real — solo una lista de respuestas
pre-cargada y un log de mensajes para hacer asserts.

Ojo con un detalle real del código: `FakeRunner` **no está centralizado**.
Se define de cero en cada archivo que lo necesita — hay una clase
`FakeRunner` completa en `tests/test_actions.py:76-142` (con
`confirm`/`select_one`/`select_many`/`prompt_text`/`run_streamed`/
`run_interactive`) y otra, más chica, en `tests/test_prompts.py:23-34`
(solo `info` + `prompt_text`, que es todo lo que `prompt_for_tag`
necesita). No hay un `import FakeRunner` cruzado entre archivos — cada
test file trae la suya, del tamaño que le hace falta.

Fragmento resumido de la versión de `test_actions.py` (no textual: se
omiten el docstring de la clase, las anotaciones de tipo completas del
`__init__` y varios métodos intermedios — `select_one`, `select_many`,
`prompt_text`, `run_interactive`, `_push`/`info`/`warn`/`error` — que sí
están en el archivo real; ver `tests/test_actions.py:76-142` para la clase
entera):

```python
class FakeRunner:
    # ... (docstring y anotaciones de tipo omitidas acá)
    def __init__(self, confirm_answers=None, select_one_answers=None, text_answers=None):
        self.messages: list[tuple[str, str]] = []  # (level, text)
        self._confirm_q = list(confirm_answers or [])
        self._select_one_q = list(select_one_answers or [])
        self._text_q = list(text_answers or [])

    def confirm(self, prompt, default=False):
        if self._confirm_q:
            return self._confirm_q.pop(0)
        return default

    def run_streamed(self, argv, cwd, on_line=None):
        return 0
```

`confirm_answers=[False, True, True, False]` en un test
(`tests/test_actions.py:712`, dentro de
`test_noop_bump_on_reused_branch_still_reaches_push`) simula una secuencia
de `s`/`n` que el usuario tipearía en distintos prompts de una misma
acción — "¿otro submódulo?" → No, "¿reusar rama?" → Yes, "¿push?" → Yes,
"¿PR?" → No —, sin ningún `input()` real ni mock de `builtins.input`. (No
confundir con el test vecino de la línea 664, que arma
`FakeRunner(confirm_answers=[False, True, False])` — una secuencia de solo
3 elementos para un escenario distinto: el mismo flujo pero sin llegar a
preguntar por el PR.)

Hoy `test_actions.py` solo ejercita `odoo_cli/core/actions/maintenance.py`
(`sync`, `update_tags`, `submodule_status`, helpers como `_filter_tags`) y
`odoo_cli/core/actions/validate.py` (`validate_instances`,
`check_host_port_collisions`) — confirmado por sus únicos dos imports de
`odoo_cli.core.actions` (`tests/test_actions.py:27-39`). Las acciones de
`lifecycle.py`, `modules.py`, `access.py` y `hosts.py` no tienen ningún
test propio hoy (no hay ningún archivo que importe
`odoo_cli.core.actions.lifecycle`/`modules`/`access`/`hosts`) — y ojo, no
existe un directorio `tests/actions/`: `tests/` es un paquete plano, sin
subcarpeta por acción.

### Cómo agregar un test nuevo

No hace falta registrar nada en ningún lado: `unittest discover` levanta
automáticamente cualquier archivo `tests/test_*.py` con clases
`unittest.TestCase` adentro, solo por convención de nombre. Para agregar
cobertura a una acción que hoy no la tiene (por ejemplo `lifecycle.py`):

1. Creá `tests/test_lifecycle.py` (o similar) siguiendo el patrón de
   `test_actions.py`: importás la función de la acción, armás un
   `FakeRunner` con las respuestas que esa acción va a pedir, y le pasás
   `tmp_path`/fixtures en vez de tocar disco real cuando aplique.
2. Para el `FakeRunner`: si el archivo nuevo solo necesita `info` +
   `prompt_text` (como `test_prompts.py`), copiá la versión chica; si
   necesita el ciclo completo de confirmaciones/selección (como
   `test_actions.py`), copiá la versión completa. No hay una versión
   compartida para importar — cada archivo arma la suya del tamaño que le
   hace falta, y así se mantuvo hasta ahora.
3. Corré ese módulo solo mientras iterás (`python3 -m unittest
   tests.test_lifecycle -v`) y `python3 -m unittest discover -v` al final
   para confirmar que no rompiste nada del resto.

## 5. Un test de convención real: `test_docker_exec_hygiene.py`

Este es el ejemplo que pide la consigna de "qué tipo de reglas se testean
acá": no es un test de una función puntual, es un **regression guard**
sobre todo el repo — escanea el código fuente y falla si encuentra un
patrón prohibido. Archivo completo: `tests/test_docker_exec_hygiene.py`.

**Por qué existe** (línea 1-11 del propio archivo): el nombre real de un
contenedor está namespaced por el proyecto de Compose y no es
necesariamente `odoo-<instancia>` o `db-<db_name>`. Un `docker exec
<nombre>` o `docker cp <nombre>:...` crudo asume ese nombre y se rompe en
silencio apenas deja de cumplirse — que es exactamente lo que pasó cuando
se quitó `container_name:` del generador para arreglar el bug de DBs
compartidas entre deployments (2026-07-22, documentado en los propios
docstrings de `tests/test_docker_exec_hygiene.py:1-11` y
`tests/test_compose_generator.py:1-6`; confirmado también con `git log`:
el commit `fd98866`, fechado 2026-07-22 16:54:36 -0400, es
"fix(compose): drop fixed container_name from db/odoo/mailhog/pgadmin" y
describe en su mensaje el mismo escenario — dos deployments de un cliente,
staging y producción, terminando en el mismo contenedor/volumen de
Postgres). **Ojo, no confundir con otra cosa**: esto no es lo mismo que la
limitación de la sección 4 de `docs/migracion-master-a-multi.md` ("no
podés tener dos clones de este repo corriendo en paralelo en la misma
máquina") — ese doc no menciona este bug ni la fecha 2026-07-22 en ningún
lado, y describe un problema distinto (namespacing entre dos clones del
mismo repo corriendo en paralelo, no DBs compartidas entre deployments
separados que ya fue corregido acá).

**Pero ojo con una inconsistencia real entre ese doc y el código actual**:
esa sección 4 (commit `9a409f6`, escrito el 2026-08-06 — **después** del
fix `fd98866` del 2026-07-22) sigue listando "quitar `container_name` fijo"
como una de 3 opciones evaluadas pero "ninguna implementada aún". Esa
premisa puntual ya quedó desactualizada: verifiqué que
`.resources/generators/compose_generator.py` ya no tiene ninguna línea
`container_name: {container_name}` en los servicios de db/odoo/mailhog/
pgadmin (el propio commit `fd98866` la quitó, confirmado con `git show
fd98866`) y que `docker-compose.generated.yml` no tiene hoy ninguna clave
`container_name:` (`grep -n container_name` sin resultados en ambos). Es
decir, la opción A de `openspec/pending/multi-environment.md` ya está
implementada para ese recurso puntual, aunque ese doc no lo refleje. Lo que
sí sigue vigente de esa limitación es la red fija (`NETWORK_NAME =
"odoo-multi"` en `compose_generator.py:22`, sin prefijar por proyecto) y
los puertos fijos en `instances.json` — esos dos siguen bloqueando correr
dos clones en paralelo, solo que ya no por `container_name`. El fix correcto acá es siempre `docker
compose exec <servicio>` / `docker compose cp <servicio>:...`. Esto ya
está documentado como convención en `docs/comandos-odoo.md` para el
comando `bash` ("Usa `docker compose exec` (por nombre de *servicio*), no
`docker exec` por nombre de contenedor"); este test es lo que hace cumplir
esa regla en todo el repo, no solo en `bash`.

Explicación línea por línea:

```python
SCAN_ROOTS = ["odoo_cli", "scripts", os.path.join(".resources", "generators")]
```
(línea 29) Solo escanea estas tres carpetas — código *host-side* que
efectivamente invoca `docker`. Excluye a propósito `.resources/entrypoint.d/`
y similares porque ese código corre **dentro** de un contenedor y nunca
llama a `docker` él mismo (comentario en línea 26-28).

```python
BAD_SUBCOMMANDS = {"exec", "cp"}
BASH_RAW_PATTERN = re.compile(r"\bdocker\s+(exec|cp)\b")
```
(líneas 31-36) Dos detectores: uno para Python (AST), otro para bash
(regex). El regex de bash matchea `docker exec`/`docker cp` como palabras
adyacentes — y **no** matchea `docker compose ... exec` porque `compose`
queda en el medio y rompe la adyacencia (comentario explícito en línea
33-35).

```python
def _bad_calls_in_python(text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple)):
            continue
        first_two = [...]  # primeros 2 elementos, si son str literales
        if len(first_two) == 2 and first_two[0] == "docker" and first_two[1] in BAD_SUBCOMMANDS:
            bad_lines.append(node.lineno)
```
(líneas 71-93, resumido) Para Python no usa regex sobre texto — parsea el
AST de verdad y busca listas/tuplas literales tipo `["docker", "exec", ...]`
como las que arma `subprocess.run(["docker", "exec", container, ...])`. El
match solo mira los **dos primeros** elementos (`node.elts[:2]`) y exige que
ambos sean string literal (`docker` seguido de `exec`/`cp`) — la longitud
total de la lista es irrelevante: una lista/tupla de 2, 5 o 20 elementos
matchea igual mientras los dos primeros sean esos literales. El ejemplo que
este documento usa como evidencia viva (más abajo, `scripts/odoo_active_users:175`)
lo confirma: es una lista de **8** elementos
(`["docker", "exec", "-i", container, "python3", "-", str(args.minutes),
"1" if args.include_portal else "0"]`, `scripts/odoo_active_users:175-180`)
y el test la marca como offender sin problema, porque solo mira los dos
primeros. Si el parseo falla (`SyntaxError`), simplemente no reporta nada
de ese archivo (líneas 76-79) — no hace que el test explote por un archivo
no-Python con extensión rara.

```python
def _is_python(path, text):
    if path.endswith(".py"):
        return True
    first_line = text.splitlines()[0] if text else ""
    return "python" in first_line
```
(líneas 57-61) Clasifica por extensión **o** por shebang — necesario
porque, como vimos en la sección 2, scripts como `scripts/odoo-pw` son
Python sin extensión `.py`.

```python
def test_no_raw_docker_exec_or_cp(self):
    offenders = []
    for path in _iter_source_files():
        ...
        offenders.extend(f"{rel}:{lineno}" for lineno in bad_lines)
    self.assertFalse(offenders, "...")
```
(líneas 108-132) El test en sí: recorre todos los archivos de
`SCAN_ROOTS`, clasifica cada uno como Python o bash, corre el detector que
corresponda, y junta todos los offenders en una sola lista con formato
`archivo:línea`. Si la lista no está vacía, el `assertFalse` falla con un
mensaje que ya trae el motivo completo (por qué importa) más la lista
exacta de ofensores — pensado para que quien rompa la convención entienda
el "por qué" sin tener que abrir el archivo de test.

**Estado real, verificado corriendo la suite hoy (2026-08-06):** este test
**falla ahora mismo** en un caso genuino —
`scripts/odoo_active_users:175` usa `["docker", "exec", "-i", container, ...]`
crudo en vez de pasar por `docker compose exec`. Es la prueba de que la
regla no es teórica: agarra en el momento algo que otro `scripts/*`
efectivamente rompe.

## 6. Relación con `scripts/coverage` y `scripts/odoo-test`

Estos dos **no** están relacionados con lo de arriba — no tocan
`odoo_cli/core/`, no usan `unittest`, y no corren en tu host. Son wrappers
de bash/Python que ejecutan tests de **módulos Odoo**, dentro del
contenedor, contra una base real:

- `scripts/odoo-test <instancia> [-d db] [-t test_tags] [-i módulos]`
  (`scripts/odoo-test:1-43`) arma un `docker compose -f <compose_file>
  exec -T -u odoo <servicio> odoo --test-tags <tags> -d <db> -i <módulos>
  --without-demo=True --stop-after-init -c /home/odoo/.config/odoo.conf
  --http-port=19999 --workers 0` y corre eso — es literalmente invocar el
  binario `odoo` con sus propios test tags, no `unittest`/`pytest` de
  Python.
- `scripts/coverage --odoo_container=<servicio> --modules=<paths>
  --test_tags=<tags> [--threshold=70]` (`scripts/coverage:1-20`, el header
  documentado en comentarios) hace lo mismo pero además envuelve la corrida
  con `coverage.py` **dentro** del
  contenedor, contra una DB temporal (`cov_YYYYMMDD_HHMMSS` si no le pasás
  `--db_name`), y falla si el % de cobertura no llega al `--threshold`
  (default 70).

El `.coveragerc` que hay en `.resources/.coveragerc` es del mismo mundo:
apunta a paths de un cliente específico (`/home/odoo/src/custom/mds-telecom/
mds_splynx*`), es decir, es configuración para medir cobertura de **esos
módulos Odoo**, no del CLI. Si vas a tocar algo de `odoo_cli/core/` o
`.resources/generators/`, el `.coveragerc` de la raíz no aplica — para eso
están los `tests/test_*.py` de este documento.
