# `.resources/generators/` — motor de generación de `./odoo build`

> Referencia técnica de los módulos Python que `./odoo build` invoca para
> traducir `instances.json` en artefactos reales (Dockerfiles,
> `docker-compose.generated.yml`, config de nginx). Complementa a
> [`readme.md`](../readme.md) y a
> [`migracion-master-a-multi.md`](migracion-master-a-multi.md).

## 1. Dónde vive y cómo se importa

`.resources/generators/` es un paquete Python plano (`__init__.py` de 4
líneas, solo docstring — sin re-exports). No se importa como
`.resources.generators.x`; los launchers (`./odoo`, `./odoo-tui`) agregan
`.resources/` a `sys.path`, así que en el resto del código se importa como
`generators.<modulo>` a secas. El único consumidor real hoy es
`odoo_cli/core/actions/lifecycle.py::build_odoo`, que hace los imports
**dentro de la función** (no al tope del módulo) — el comentario en el código
explica por qué: para que `odoo_cli.core.actions.lifecycle` se pueda importar
sin que `.resources/` ya esté en `sys.path` (relevante para tests que
importan el paquete `odoo_cli` sin pasar por el launcher).

```
generators/
├── __init__.py            # 4 LOC, solo docstring
├── config_loader.py        # 264 LOC — carga/valida instances.json
├── compose_generator.py    # 385 LOC — genera docker-compose.generated.yml
├── dockerfile_generator.py #  49 LOC — concatena Dockerfile por versión
├── nginx_generator.py      # 161 LOC — genera nginx generated.conf
├── prompt_utils.py         # 194 LOC — menú interactivo (NO USADO, ver §5)
└── pw_helpers.py           #  78 LOC — helper compartido por ./odoo pw
```

(LOC verificado con `wc -l .resources/generators/*.py` el 2026-08-11.)

## 2. Orden real de ejecución en `./odoo build`

`build_odoo()` en `odoo_cli/core/actions/lifecycle.py:58-92` llama a los
generadores en este orden exacto:

```python
unique_versions = get_unique_odoo_versions(config)          # config_loader
dockerfile_map = generate_dockerfiles(base_path, unique_versions)  # dockerfile_generator
generate_compose(base_path, config, dockerfile_map)          # compose_generator
generate_nginx_config(base_path, config)                     # nginx_generator
_docker_compose(runner, "build", ...)                        # docker compose build
```

`config` ya llegó cargado (vía `config_loader.load_config`) antes de entrar a
`build_odoo` — el propio `config_loader` no se invoca desde acá salvo para
`get_unique_odoo_versions`.

### 2.1 `config_loader.py` — carga y valida `instances.json`

- `_strip_json_comments(text)`: parser char-a-char que remueve comentarios
  `//` de estilo JSONC, respetando comillas simples/dobles y escapes (`\"`).
  Esto es lo que permite que `instances.json` tenga comentarios inline en el
  editor aunque `json.loads` no los entienda nativamente — el archivo real
  sigue siendo JSON estricto después de la limpieza.
- `load_config(base_path)`: lee `instances.json`, limpia comentarios,
  parsea, **filtra instancias con `enabled: false`** (default `True` si el
  campo no está), y valida. Esta es la función que usan el CLI y los
  generadores.
- `load_full_config(base_path)`: variante **sin filtrar** por `enabled` —
  pensada para la TUI, que necesita ver/togglear instancias deshabilitadas
  en pantalla. Aplica la misma validación (`_validate_config`) sobre la
  estructura completa.
- `_validate_config` / `_validate_database` / `_validate_instance`: chequean
  secciones requeridas (`odoo_configs`, `databases`, `instances`), campos
  obligatorios por instancia (`odoo_version`, `external_port`, `database`,
  `odoo_config`), referencias cruzadas válidas (`database` e `odoo_config`
  deben existir), y **unicidad de `external_port`** entre instancias. Nota:
  la validación de puertos únicos (`_validate_instance`, líneas 186-192)
  se re-ejecuta una vez por instancia dentro del loop de
  `_validate_config` — es `O(n²)` pero irrelevante en la práctica (decenas
  de instancias, no miles).
- `resolve_instance_config`: aplica el merge `odoo_config` base +
  `overwrite_odoo_config` (shallow — `dict.update`, no merge recursivo: si
  `overwrite_odoo_config` define una key que ya existe en el `odoo_config`
  base, la pisa entera, no la mergea campo a campo).
- `get_db_host(db_name, db_conf)`: si `create_container` es `True` (default),
  devuelve `db-<nombre>` (DNS interno de Docker); si es `False`, devuelve
  `db_conf["host"]` (DB externa/manual).
- `get_db_internal_port(db_conf)`: **siempre** devuelve el puerto en el que
  Postgres escucha *dentro* del contenedor (5432, o `internal_port` si la DB
  es externa) — NUNCA el `port` configurado en `instances.json`, que es
  el puerto **host-side** y solo se usa si `expose_host_port: true`. Confundir
  estos dos es el error más fácil de cometer si alguien toca este archivo:
  el docstring en el código (líneas 228-240) lo advierte explícitamente.

### 2.2 `dockerfile_generator.py` — un Dockerfile por versión de Odoo usada

Función única: `generate_dockerfiles(base_path, unique_versions)`. Por cada
versión única detectada en `instances.json` (vía
`config_loader.get_unique_odoo_versions`, que es literalmente
`set(inst["odoo_version"] for inst in config["instances"].values())`):

1. Lee `.resources/dockerfiles/<version>_Dockerfile` (el archivo
   version-específico — hoy existen `14.0`, `16.0`, `17.0`, `18.0`, `19.0` y
   `master`, verificado con `ls .resources/dockerfiles/`).
2. Lee `.resources/Dockerfile.template` (61 líneas, común a todas las
   versiones).
3. Concatena versión-específico + template, escribe el resultado en
   `.resources/Dockerfile.<version>`.

Si falta el `Dockerfile.template` o el `<version>_Dockerfile` correspondiente,
hace `sys.exit(1)` con un mensaje de error — no hay fallback silencioso. Esto
confirma la fila de la tabla comparativa en `migracion-master-a-multi.md`:
"igual [al Dockerfile viejo], pero uno por versión de Odoo usada, compartido
entre instancias de esa versión" — si dos instancias usan `17.0`, comparten
el mismo `Dockerfile.17.0` (y por ende la misma imagen base), aunque tengan
`database` o `odoo_config` distintos.

### 2.3 `compose_generator.py` — el generador más grande (385 LOC)

Función pública: `generate_compose(base_path, config, dockerfile_map)`.
Escribe `docker-compose.generated.yml` con este orden de secciones:

1. **Header** — comentario `# Auto-generated ... DO NOT EDIT MANUALLY`.
2. **Servicios de DB** (`_db_service`, uno por entrada en
   `get_managed_databases(config)` — o sea, las que tienen
   `create_container: true` o no definen el campo). Cada servicio:
   - usa `postgresql.<perfil>.conf` vía `command` si `db_conf.get("config")`
     está seteado (monta `.resources/dbconfigs/` como volumen).
   - imagen taggeada como `local_odoo_db_<project>_<db_name>:<pg_version>`
     — el prefijo `<project>` (ver más abajo, `_project_slug`) es lo que
     evita colisión de tags entre dos checkouts del mismo repo.
   - **NO publica el puerto al host** salvo que `expose_host_port: true`
     — coincide exactamente con lo documentado en la fila "Puerto DB al
     host" de la tabla comparativa en `migracion-master-a-multi.md`.
3. **Servicios Odoo** (`_odoo_service`, uno por instancia). Cosas no
   obvias leyendo solo `instances.json`:
   - El nombre de imagen es `local_odoo_<project>_<inst_name>:<odoo_minor>`
     (no incluye el nombre de la DB).
   - `depends_on` solo se agrega si la DB de esa instancia tiene
     `create_container: true` — para DBs externas no hay `depends_on`
     (Docker no puede esperar a que un host externo esté listo).
   - Monta 5 volúmenes por instancia:
     `<inst>-web`, `./src` (compartido, NO por-instancia — todas las
     instancias ven el mismo árbol de `src/`), `.resources/.coveragerc`
     (compartido, solo-lectura), `<inst>-data`, `<inst>-py3`, `<inst>-py`.
   - Cada variable de `odoo_config`/`overwrite_odoo_config` se vuelca como
     variable de entorno con un default hardcodeado en Python si falta en
     el JSON (ver líneas 235-255 — p. ej. `workers` default `2`,
     `limit_memory_soft` default `16000000000`). Estos defaults **no están
     documentados en ningún lado fuera del código fuente** — si alguien
     pregunta "¿qué pasa si no seteo `workers`?", la respuesta está acá,
     no en `instances.example.jsonc`.
   - `addons` se serializa como CSV en `INSTANCE_ADDONS`, consumida por el
     entrypoint `.resources/entrypoint.d/400-auto-detect-addons` (verificado:
     ese script lee `os.environ.get("INSTANCE_ADDONS", "")` y, si está
     seteada, usa esa lista explícita en vez de autodetectar addons por
     convención de carpetas).
4. **Servicio nginx** (`_nginx_service`) — un único servicio nginx para
   *todas* las instancias (no uno por instancia). Publica el puerto 80 más
   el `external_port` de cada instancia individualmente (necesario porque
   nginx corre en su propio contenedor y Docker requiere publicar cada
   puerto por separado, aunque el ruteo interno lo resuelva un solo
   `generated.conf`).
5. **pgAdmin** (opcional, si `pgadmin.enabled`).
6. **MailHog** (opcional, si `mailhog.enabled`) — servicio SMTP catcher para
   dev; no estaba documentado en ninguno de los otros docs existentes.
7. **Volumes** y **Networks** (red única `odoo-multi`, driver `bridge`).

**`_project_slug(base_path)`** (líneas 29-43) es el mecanismo — no
documentado en `readme.md` ni en `migracion-master-a-multi.md` antes de este
doc — que permite tener *dos checkouts distintos* de `docker-odoo` en la
misma máquina sin que sus **imágenes** Docker colisionen: deriva un slug del
nombre del directorio contenedor (p. ej. `docker-odoo` → `docker-odoo`,
`docker-odoo-cliente-x` → `docker-odoo-cliente-x`) y lo usa como parte del
tag de imagen. Importante: esto **no contradice** la limitación conocida en
`migracion-master-a-multi.md` §4 ("no podés tener dos clones corriendo en
paralelo") — esa limitación es sobre contenedores/red/puertos en ejecución
simultánea, mientras que `_project_slug` solo evita que el `docker build` de
un checkout pise el tag de imagen del otro. Ambos clones seguirían
chocando en `container_name`, la red `odoo-multi` (nombre fijo, no
namespaced) y los puertos si intentaran levantar contenedores a la vez.

### 2.4 `nginx_generator.py` — un server block por instancia, doble-stack

`generate_nginx_config(base_path, config)` escribe
`.resources/nginx_configs/generated.conf` con un bloque `server {}` por
instancia (más uno para pgAdmin y otro para MailHog si están habilitados).
Cada bloque de instancia:

- escucha en **dos puertos simultáneamente**: el `external_port` propio Y el
  80 (`_listen_lines`) — esto es lo que permite los dos modos de acceso
  documentados en el header del archivo: `localhost:<puerto>` y
  `<instancia>.local` (puerto 80, resuelto por `/etc/hosts` vía
  `./odoo hosts apply`).
- el **primer bloque generado** (`is_first=True`) se marca
  `default_server` en el puerto 80 — necesario para que nginx no emita
  warnings por Host headers no matcheados (p. ej. `curl localhost` sin
  header `Host` explícito).
- rutea `/websocket` por separado hacia el puerto gevent (8071) con headers
  de upgrade (`Connection: Upgrade`) para el longpolling/websocket de Odoo;
  todo lo demás va al puerto HTTP normal (8069).
- usa `resolver 127.0.0.11 valid=30s` (el DNS interno de Docker) en vez de
  resolver el nombre del contenedor una sola vez al arrancar nginx — esto
  permite que nginx seemlessly recupere el nuevo IP de un contenedor Odoo si
  se reinicia (`docker compose restart odoo-<inst>` cambia su IP interna).

## 3. `pw_helpers.py` — no es parte del pipeline de `build`, es un helper de runtime

A diferencia de los 4 módulos anteriores (que solo corren durante
`./odoo build`), `pw_helpers._check_db_exists` se invoca en runtime desde
`odoo_cli/core/actions/modules.py:143` (probablemente el comando
`./odoo pw`, cambio de contraseña de admin). Verificado por grep de
consumidores reales:

```
odoo_cli/core/actions/modules.py:143: from generators.pw_helpers import _check_db_exists
```

Hace dos queries `psql` vía `docker compose exec` (nunca `docker exec`
plano — el docstring explica por qué: el `container_name` real ya no es fijo,
se namespacea por proyecto vía `_project_slug`, así que hay que resolver
siempre a través del *nombre de servicio* de compose y el `compose_file`
explícito): una para chequear si la DB pedida existe, y si no, otra para
listar las DBs disponibles y poder dar un mensaje de error útil. Si el
primer `psql` falla (`returncode != 0`), asume que la DB no existe y no
intenta listar alternativas (no hay forma de distinguir "DB no existe" de
"no pude conectarme" sin inspeccionar stderr, y el código no lo hace).

Este módulo tiene tests dedicados en
`scripts/test_pw_returncode.py` y `scripts/test_pw_resolve_instance.py`
(mockean `_check_db_exists` y `prompt_selection` — pero el `prompt_selection`
que mockean ahí es el de `odoo_cli.core.prompts`, no el de este paquete, ver
§5).

## 4. `__init__.py` — no re-exporta nada

Son 4 líneas, solo el docstring del paquete. No hay `__all__` ni
re-exports — cada módulo se importa por su path completo
(`from generators.compose_generator import generate_compose`, etc.). Quien
agregue un generador nuevo debe replicar ese patrón de import explícito en
`lifecycle.py`; no existe un registro central de generadores.

## 5. Hallazgo: `prompt_utils.py` es código muerto

`generators/prompt_utils.py` (194 LOC) define su propia `prompt_selection`
— un menú interactivo con navegación por flechas, grid multi-columna y modo
`multi`. **No tiene ningún consumidor en el árbol actual**: verificado con

```bash
grep -rn "prompt_utils\|from generators import" --include="*.py" .
```

que no devuelve resultados fuera del propio archivo. La `prompt_selection`
que sí se usa en todo el CLI (`odoo_cli/core/cli_runner.py`,
`odoo_cli/core/dispatch.py`, `odoo_cli/core/prompts.py`) es una
**implementación distinta y no relacionada** que vive en
`odoo_cli/core/prompts.py:48`. Ambas resuelven el mismo problema (menú de
selección con navegación) pero son código independiente — no hay
delegación entre ellas.

Esto es relevante para cualquiera que toque `.resources/generators/`
pensando que está editando el menú interactivo real del CLI/TUI: no lo
está. El archivo vivo a modificar es `odoo_cli/core/prompts.py`.
**Este doc no asume la intención original** (¿un refactor a medias que
migró la lógica a `odoo_cli/core/` y olvidó borrar el original? ¿un
experimento paralelo?) — solo constata el estado actual: `prompt_utils.py`
puede borrarse sin romper nada, sujeto a que el equipo confirme que no hay
un plan de volver a usarlo.

## 6. Qué NO cubre este documento

- El contenido de los templates de Dockerfile (`.resources/dockerfiles/*`,
  `.resources/Dockerfile.template`) — son Dockerfiles planos, no generados
  por Python.
- Los scripts de `entrypoint.d/` (incluido `400-auto-detect-addons`,
  mencionado acá solo como consumidor de `INSTANCE_ADDONS`) — son shell/
  Python que corren dentro del contenedor Odoo en runtime, no parte de
  `.resources/generators/`.
- La arquitectura de `odoo_cli/core/` (Runner, dispatch, actions) — ver
  [`arquitectura-odoo-cli-core.md`](arquitectura-odoo-cli-core.md).
