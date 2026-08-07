# Migración: `master` → `master-multi` (y por qué existe esta rama)

> Documento de referencia para la reunión de equipo. Complementa al
> [`readme.md`](../readme.md) (que documenta el estado actual completo) con el
> **contraste** contra el modelo viejo y una guía paso a paso para migrar tu
> entorno local.

## 1. El cambio de paradigma en una frase

`master` levanta **una** instancia de Odoo por clon del repo, configurada por
`.env`. `master-multi` levanta **N instancias** (distintas versiones, distintos
clientes, distintas DBs) desde un único clon, configuradas declarativamente en
`instances.json`.

No es un fork con features nuevas encima — es un modelo de configuración
distinto. Por eso migrar no es "actualizar un flag", es cambiar de archivo de
configuración y de mental model.

## 2. Comparación conceptual

| Eje | `master` | `master-multi` |
|---|---|---|
| Config | `.env` (una por clon) | `instances.json` (todas las instancias) |
| Cardinalidad | 1 instancia Odoo por clon | N instancias por clon, cualquier mezcla de versiones |
| Reverse proxy | Traefik, ruteo por `DOMAIN` wildcard | nginx generado, ruteo por puerto **y** subdominio `<instancia>.local` |
| Compose | `docker-compose.app.yml` / `.db.yml` / `.pgadmin.yml` estáticos | `docker-compose.generated.yml` generado por `.resources/generators/compose_generator.py` |
| Dockerfile | `.resources/Dockerfile.template` + `.env` | igual, pero **uno por versión de Odoo usada**, compartido entre instancias de esa versión |
| Postgres | 1 contenedor, 1 perfil de tuning fijo (`postgresql.4gb.2cpu.conf`) | contenedor por `database` definida, tuning por perfil (`small`/`medium`/`large`/`xlarge`), desacoplado de la versión de Odoo |
| Puerto DB al host | expuesto siempre (`EXTERNAL_PORT_POSTGRES`) | **no expuesto por default** — red interna de Docker; opt-in con `expose_host_port: true` |
| CLI | `./odoo` (script bash monolítico) | `./odoo` (Python, shim de 323 LOC → delega a `odoo_cli/core/`) |
| Interfaz | solo CLI | CLI + TUI (`./odoo tui` / `./odoo-tui`, Textual) |
| Clonado de addons | `./odoo init` clona repos según `ENV_TYPE` (`binaural`/`external`) | `./odoo init` es **solo reporte** (qué falta), el clonado es manual o vía `./odoo sync` sobre submódulos existentes |
| Gestión de submódulos | manual | `./odoo sync`, `./odoo update-tags`, `./odoo submodule-status` |

## 3. Por qué se hizo así (contexto de decisiones)

- **Perfiles de Postgres en vez de config por versión de Odoo**: se intentó
  primero un perfil por versión (`postgresql.v17.conf`, etc.) y se descartó — el
  motor de tuning correcto es **cuántas instancias comparten esa DB**, no qué
  versión de Odoo corren. Son ejes ortogonales: escalar de `small` a `medium`
  es cambiar un campo en `instances.json`, no tocar archivos de tuning.
- **Red interna de Docker para las DBs managed**: exponer el puerto 5432 al
  host generaba conflicto con un Postgres local (Homebrew, Postgres.app) que
  terminaba interceptando conexiones. Ahora los contenedores Odoo hablan con
  `db-<nombre>:5432` por la red `odoo-multi`; el host solo lo ve si pedís
  `expose_host_port: true` explícitamente.
- **nginx + subdominios `.local` en vez de solo puertos**: varias instancias
  serviditas por `localhost:<puerto>` comparten origin a nivel de cookies del
  browser, lo que rompía CSRF al tener varias abiertas a la vez. Un subdominio
  por instancia (`contiflex.local`) aísla las cookies por host real.
- **Extracción a `odoo_cli/core/`**: el `./odoo` original llegó a 1208 LOC
  monolíticas. Se extrajo a un paquete con un `Runner` (`typing.Protocol` con
  `info`/`warn`/`confirm`/`run_streamed`) para que la misma lógica de negocio
  la puedan invocar el CLI (`CliRunner`) y la TUI, sin duplicar código. Quedó
  en 276 LOC el shim.
- **TUI (Textual)**: pensada como capa aditiva — nunca reemplaza al CLI, solo
  arma los comandos y muestra el output en pantalla. Pasó por varias rondas de
  fixes de performance (streaming bloqueante con `Popen`, freezes al togglear
  filtros) documentadas en `docs/tui-v3-plan.md`.

## 4. Limitación conocida, todavía sin resolver

**No podés tener dos clones de este repo corriendo en paralelo en la misma
máquina.** `container_name`, la red `odoo-multi` y los puertos están fijos —
un segundo clone choca con "name already in use" o bind errors. Está
diagnosticado en [`openspec/pending/multi-environment.md`](../openspec/pending/multi-environment.md)
con 3 opciones evaluadas (quitar `container_name` fijo / agregar
`project_prefix` configurable / documentar `COMPOSE_PROJECT_NAME` como
workaround) pero **ninguna implementada aún**. Si en la reunión surge la
pregunta de "¿puedo tener un ambiente de prueba aparte?", la respuesta hoy es
no sin tocar código.

## 5. Guía de migración paso a paso

Asumiendo que hoy tenés un checkout en `master` con tu `.env` funcionando:

### Paso 1 — Traer la rama nueva

```bash
git fetch origin
git checkout master-multi   # o la rama de feature que corresponda
```

### Paso 2 — Crear tu `instances.json` desde el template

```bash
cp instances.example.jsonc instances.json
```

El `.jsonc` tiene comentarios inline explicando cada campo — `instances.json`
en sí debe ser JSON estricto (sin comentarios), lo carga `json.load()`.

### Paso 3 — Traducir tu `.env` a una entrada de `instances.json`

Tabla de equivalencia directa:

| Variable en `.env` | Dónde va en `instances.json` |
|---|---|
| `PROJECT_NAME` | nombre de la instancia (la key dentro de `instances`) |
| `ODOO_VERSION` | `instances.<nombre>.odoo_version` |
| `EXTERNAL_PORT_ODOO` | `instances.<nombre>.external_port` |
| `ADMIN_PASSWORD` | `odoo_configs.<config>.admin_password` |
| `WORKERS` | `odoo_configs.<config>.workers` |
| `LIST_DB` | `odoo_configs.<config>.list_db` |
| `WITHOUT_DEMO` | `odoo_configs.<config>.without_demo` |
| `PROXY_MODE` | `odoo_configs.<config>.proxy_mode` |
| `SERVER_MODE` | `overwrite_odoo_config.server_mode` |
| `LIMIT_MEMORY_SOFT` / `_HARD` | `odoo_configs.<config>.limit_memory_soft` / `_hard` |
| `MAX_CRON_THREADS` | `odoo_configs.<config>.max_cron_threads` |
| `LIMIT_TIME_REAL_CRON` / `LIMIT_TIME_REAL` / `LIMIT_TIME_CPU` | mismos nombres en `odoo_configs.<config>` |
| `DB_MAXCONN` | `odoo_configs.<config>.db_maxconn` |
| `UNACCENT` | `odoo_configs.<config>.unaccent` |
| `SERVER_WIDE_MODULES` | `odoo_configs.<config>.server_wide_modules` |
| `DBFILTER` | `overwrite_odoo_config.db_filter` |
| `PGDATABASE` / `DB_NAME` | `overwrite_odoo_config.db_name` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `databases.<db>.user` / `.password` |
| `POSTGRES_IMG_VERSION` | `databases.<db>.postgres_version` |
| `EXTERNAL_PORT_POSTGRES` | `databases.<db>.port` (**ya no se expone al host por default** — ver sección 3) |
| `PGADMIN_ENABLED` / `_EXTERNAL_PORT` / `_DEFAULT_EMAIL` / `_DEFAULT_PASSWORD` | `pgadmin.enabled` / `.port` / `.email` / `.password` |
| `ODOO_SRC_PATH` | fijo, siempre `src/` — los addons se listan explícitos en `addons: [...]` |
| `DOMAIN`, vars de Traefik | **no tienen equivalente** — el ruteo ahora es nginx generado, sin config manual |
| `ENV_TYPE`, `ORG_NAME` | **no tienen equivalente** — `./odoo init` ya no clona repos automáticamente, ver paso 4 |

Ejemplo mínimo resultante:

```jsonc
{
  "odoo_configs": {
    "17.0_default": {
      "admin_password": "admin",
      "workers": 2,
      "without_demo": true,
      "list_db": true,
      "proxy_mode": true
    }
  },
  "databases": {
    "mi_db": {
      "postgres_version": 16,
      "port": 5432,
      "user": "odoo",
      "password": "odoo",
      "config": "postgresql.small.conf"
    }
  },
  "instances": {
    "mi-proyecto": {
      "odoo_version": "17.0",
      "external_port": 8071,
      "database": "mi_db",
      "odoo_config": "17.0_default",
      "overwrite_odoo_config": {
        "addons": ["src/enterprise", "src/custom/mi-proyecto"]
      }
    }
  }
}
```

### Paso 4 — Ubicar tus addons en `src/custom/<nombre-instancia>`

En `master`, `./odoo init` clonaba repos automáticamente según `ENV_TYPE`. En
`master-multi` eso ya no pasa: cloná manualmente el repo de tu cliente en
`src/custom/<nombre>` (o corré `./odoo sync <repo> <branch>` si ya está
clonado y solo necesitás actualizar submódulos), y listalo en `addons` de tu
instancia.

### Paso 5 — Build y start

```bash
./odoo build
./odoo start mi-proyecto
```

`build` genera `docker-compose.generated.yml`, el/los `Dockerfile` por versión
usada, y la config de nginx — reemplaza lo que antes eran los 3 `docker-compose.*.yml`
estáticos.

### Paso 6 (opcional) — Subdominio local

Si querés `mi-proyecto.local` en vez de `localhost:8071` (evita el problema de
CSRF si vas a tener varias instancias abiertas a la vez en el browser):

```bash
./odoo hosts status     # ver diff
sudo ./odoo hosts apply # aplicar (requiere root, no se automatiza en build)
```

`localhost:<puerto>` sigue funcionando siempre en paralelo — esto es opt-in.

### Paso 7 — Validar

```bash
./odoo validate-instances   # o la action equivalente vía TUI
./odoo psql mi-proyecto -d <db_name>
```

### Checklist rápido

- [ ] `instances.json` creado desde `instances.example.jsonc`
- [ ] Instancia con `odoo_version`, `external_port` único, `database`, `odoo_config`
- [ ] Addons del cliente en `src/custom/<nombre>` y listados en `addons`
- [ ] `postgres_version` coincide con la mínima soportada por la versión de Odoo (ver tabla en `readme.md`)
- [ ] `./odoo build` sin errores
- [ ] `./odoo start <nombre>` levanta y accedés por `localhost:<puerto>`

## 6. Qué explorar después de la reunión

- `readme.md` — referencia completa y actualizada del modelo nuevo (secciones
  de perfiles de Postgres, subdominios, TUI, arquitectura de `odoo_cli/core/`).
- `tui/README.md` y `docs/tui-v3-plan.md` — detalle de la TUI y su backlog.
- `openspec/sessions/` — bitácora de las decisiones de arquitectura tomadas
  sesión a sesión, con el razonamiento detrás de cada una.
- `openspec/pending/multi-environment.md` — el problema abierto de multi-clone
  en paralelo, si alguien quiere tomarlo.
