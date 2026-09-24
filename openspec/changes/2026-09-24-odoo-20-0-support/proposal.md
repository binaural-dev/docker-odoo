# Soporte para Odoo 20.0

**Estado: implementado y verificado (2026-09-24).**

## Por qué

Odoo 20.0 ya tiene rama propia en `odoo/odoo` (`20.0`, default del repo) y
en `binaural-dev/enterprise` (`20.0`), con nightly build disponible
(`nightly.odoo.com/20.0/nightly/deb/odoo_20.0.latest_all.deb`) — aún no es
un release final, pero ya es instalable igual que se instalaron 17.0/19.0
en su momento (mismo mecanismo: `.deb` de nightly, no un release
"estable" pineado). Hace falta poder levantar una instancia de prueba
contra Enterprise 20.0 puro (sin custom addons) para empezar a evaluarla
antes de que algún cliente la pida.

Este repo genera un Dockerfile por versión de Odoo de forma completamente
genérica (`.resources/generators/dockerfile_generator.py` concatena
`.resources/dockerfiles/<version>_Dockerfile` + `Dockerfile.template`; los
generadores de compose/config no tienen ninguna lista de versiones
hardcodeada) — agregar una versión nueva es, en principio, solo agregar su
Dockerfile fuente. Se verificó que efectivamente no hace falta tocar
ningún generador.

## Qué cambia

- **`.resources/dockerfiles/20.0_Dockerfile`** (nuevo): copia de
  `19.0_Dockerfile` con las tres URLs pineadas a la versión
  (`debian/control`, `requirements.txt`, el `.deb` de nightly) apuntando a
  `20.0` en vez de `19.0`. Nada más cambia: la imagen base sigue siendo
  `ubuntu:noble` (Python 3.12), que Odoo 20.0 sigue soportando
  (`MIN_PY_VERSION = (3, 12)`, `MAX_PY_VERSION = (3, 14)` en
  `odoo/release.py` de la rama `20.0`) — no hace falta saltar a una imagen
  con Python más nuevo. La lista de paquetes apt/pip no está hardcodeada
  en el Dockerfile: se resuelve en build-time leyendo `debian/control`
  (apt) y `requirements.txt` (pip) de la rama real de `odoo/odoo`, así que
  las diferencias de dependencias entre 19.0 y 20.0 (ver abajo) ya se
  manejan solas, sin tocar el Dockerfile.
- **`instances.example.json`**: nueva instancia de ejemplo `demo-odoo20`
  (Enterprise puro, sin custom addons) documentando el patrón.
- **`instances.json`** (local, gitignored, no versionado): nueva instancia
  real `odoo20` para poder levantar y probar Enterprise 20.0 en este
  entorno — mismo servicio `pg16` compartido que el resto (ver
  "Postgres" abajo), rol dedicado (`db_user`/`db_password`) porque
  comparte `pg16` con instancias que corren cron, `addons: ["src/enterprise-20.0"]`
  únicamente.
- **`src/enterprise-20.0`** (local, gitignored, no versionado): clon de
  `git@github.com:binaural-dev/enterprise`, rama `20.0` (mismo patrón que
  `src/enterprise-19.0`/`src/enterprise-17.0`: clon plano fuera de este
  repo, no submódulo de Git).
- **`readme.md`**: nota sobre el `MIN_PG_VERSION` de Odoo 20.0 al elegir
  `postgres_version` para el servicio de una instancia 20.0.

## Diferencias de paquetes/dependencias: 19.0 → 20.0 (Odoo upstream)

Confirmado leyendo directamente `debian/control`/`requirements.txt`/
`odoo/release.py` de las ramas `19.0` y `20.0` de `odoo/odoo` en GitHub
(no son suposiciones — se resuelven solas en build-time, documentado acá
para referencia):

- **Postgres mínimo sube de 13 a 16** (`MIN_PG_VERSION` en
  `odoo/release.py`: `13` en 19.0, `16` en 20.0). El servicio `pg16` que
  ya usa este repo para todo (`postgres_version: 16`) sigue siendo válido
  — justo en el mínimo, sin margen — pero cualquier instalación que
  todavía corra un servicio en Postgres 13/14/15 para una instancia 19.0
  **no puede** reusar ese mismo servicio para una instancia 20.0.
- **Python mínimo sube de 3.10 a 3.12** (`MIN_PY_VERSION`). Sin impacto
  acá: la imagen ya usa `ubuntu:noble` (Python 3.12) desde 19.0.
- **Agregado**: `python3-h11`/`h11==0.16.0` (nueva dependencia directa,
  Odoo 20.0 la fija explícitamente por un CVE del paquenete empaquetado
  en Ubuntu/Debian).
- **Eliminados**: `libjs-underscore` (debian/control) y `python3-tz`/
  `pytz` (debian/control y requirements.txt — Odoo 20.0 dejó de depender
  de `pytz`, reemplazado por el soporte nativo de zonas horarias de
  Python 3.9+) y `xlwt` (requirements.txt — ya no se usa para exportar
  `.xls` del formato viejo).
- Todo lo demás en `requirements.txt` son solo simplificaciones de los
  `python_version` condicionales (se eliminaron los pines para Python
  <3.11, porque Debian/Ubuntu 24.04 ya trae 3.12) — mismas versiones
  finales que ya se instalaban para 19.0 en esta imagen (`noble`/py3.12).

## Fuera de alcance, deliberadamente

- No se agrega validación automática que compare `postgres_version` del
  servicio contra el `MIN_PG_VERSION` real de cada versión de Odoo
  usada (leer `odoo/release.py` requeriría tener el código fuente de esa
  versión disponible en build-time, cosa que este repo no hace — instala
  Odoo desde el `.deb` de nightly, no desde un checkout de `src/odoo`).
  Documentado acá como advertencia operativa, no como chequeo del CLI.
- No se migra ninguna instancia real de cliente a 20.0 — la instancia
  nueva (`odoo20`) es solo para evaluar la versión antes de que haga
  falta en un cliente real.
- No se crea un servicio de Postgres nuevo — se reusa `pg16` (ya cumple
  el mínimo de 20.0), mismo patrón que ya coexiste con instancias 14.0 y
  19.0 en este entorno.

## Verificado

- `git ls-remote --heads git@github.com:binaural-dev/enterprise` — rama
  `20.0` existe.
- `nightly.odoo.com/20.0/nightly/deb/` — build de nightly disponible
  (`odoo_20.0.latest_all.deb`, generado 2026-09-23).
- Clon real de `src/enterprise-20.0` (rama `20.0`, `--depth 1`, mismo
  patrón que las demás carpetas `src/enterprise-*`).
- `load_config()` (validación completa de `config_loader.py`, incluida la
  de aislamiento cron/`db_filter`) sobre el `instances.json` real con la
  instancia `odoo20` agregada: sin errores.
- `generate_dockerfiles()` con las 3 versiones reales del `instances.json`
  (`14.0`, `19.0`, `20.0`): genera `.resources/Dockerfile.20.0` sin
  errores, a partir de `dockerfiles/20.0_Dockerfile` + el template común.
- `generate_compose()` de punta a punta: el servicio `odoo-odoo20` queda
  en `docker-compose.generated.yml` apuntando a
  `./.resources/Dockerfile.20.0`, con `INSTANCE_ADDONS: "src/enterprise-20.0"`,
  `PGUSER`/`DBFILTER` del rol dedicado, y `depends_on: db-pg16`.
- **No se corrió `./odoo build odoo20` real** (construir la imagen y
  levantar el contenedor) como parte de este cambio — queda para cuando
  se quiera evaluar la versión en la práctica.
