# Scripts de administración

Utilidades para administrar entornos Odoo multi-instancia.
La mayoría obtiene la configuración de `instances.json` a través de
`.resources/generators/config_loader.py`.

---

## `coverage` — Test runner con cobertura y DB temporal automática

Ejecuta tests de Odoo con `coverage.py` **real** (no un proxy propio):
`coverage run` mide líneas/ramas de código realmente ejecutadas mientras
corre `odoo --test-tags=...` sobre una DB temporal (`cov_YYYYMMDD_HHMMSS`
por defecto), que se borra al terminar salvo `--keep-db`.

```sh
./scripts/coverage \
  --odoo_container=<nombre> \
  --modules=<path_relativo> \
  --test_tags=<tags>

# Opcional:
  --db_name=<db>       # nombre fijo (default: cov_YYYYMMDD_HHMMSS)
  --keep-db            # no borrar la DB temp al salir
  --threshold=<pct>    # mínimo de cobertura (default: 70)
  --help
```

### Cómo se aplica el coverage (metodología)

1. **Scope**: `--source` de `coverage.py` se limita a los paths de
   `--modules` (los módulos custom que se están midiendo) — no mide Odoo
   core ni otros módulos instalados como dependencia, sólo el código propio
   del/los módulo(s) indicados.
2. **Medición**: `coverage run` envuelve al proceso Odoo completo (boot +
   instalación de los módulos + corrida de `--test-tags`). Cualquier línea
   ejecutada durante ese proceso cuenta, incluidos los `setUp`/`tearDown` de
   los tests.
3. **Umbral**: al final, `coverage report --fail-under=<threshold>` calcula
   el % real (línea `TOTAL` del reporte) y falla (`exit 1`) si queda por
   debajo del umbral (default 70%, configurable con `--threshold`).
4. **Resultado de los tests en sí** (¿pasaron o fallaron?) es una señal
   **completamente independiente** del % de cobertura — un test roto no
   deja de ejecutar líneas de código, así que la cobertura se sigue
   calculando igual. Por eso este script **siempre** muestra el % de
   cobertura, haya o no tests fallidos, y reporta ambas cosas por separado
   sin mezclarlas en un solo mensaje ambiguo:
   - `✅/❌ Cobertura >= /< umbral` — sólo sobre el %, nunca menciona tests.
   - `⚠️ Hubo errores en los tests` — sólo si algún test falló o tiró
     excepción, con el resumen (`X failed, Y error(s) of Z tests`) y el
     **nombre de cada test que falló**, extraído del log real de la
     corrida (guardado en `coverage_data/last_test_run.log` para inspección
     posterior — no hay que scrollear el boot completo de Odoo a mano).
   - El exit code es `1` si CUALQUIERA de los dos falla (cobertura baja
     y/o tests rotos), pero el mensaje impreso siempre distingue cuál.
5. **`coverage-run-all`** (más abajo) hereda esta misma distinción en su
   columna `ESTADO` del reporte final: nunca vas a ver un status ambiguo
   tipo "puede ser una cosa o la otra" — va a decir explícitamente
   `TEST_FAILURES`, `BELOW_THRESHOLD`, o ambos combinados, y en `DETALLE`
   lista los nombres de los tests que fallaron.

---

## `coverage-status` — Escaneo de qué clientes tienen tests (sin Docker)

Recorre `src/custom/*/` buscando `__manifest__.py` + carpeta `tests/`, sin
levantar Docker (excluye los submódulos compartidos `integra-addons`,
`third-party-addons`, `odoo-venezuela`). Por cada cliente con al menos un
módulo testeado, imprime el comando exacto de `coverage-run-all` para medir
el % real. Es un escaneo de presencia (¿hay tests o no?), no mide cobertura.

```sh
./scripts/coverage-status \
  [--pull] [--json] [--only-with-tests] [--help]
```

- `--pull`: antes de escanear, hace `git pull --ff-only` en cada repo (si
  está limpio; si tiene cambios sin commitear, lo salta y lo marca "dirty").
- `--json`: salida en JSON en vez de tabla, para consumir desde otro script.
- También disponible como `./odoo coverage-status`.

---

## `coverage-run-all` — Ciclo completo de coverage real, automatizado

Corre `coverage.py` real (no un proxy) para uno, varios o todos los clientes
que `coverage-status` reporta con tests. Por cada instancia:

1. Si tiene `"enabled": false` en `instances.json` (la norma — ver nota
   abajo), lo activa **temporalmente** y regenera `docker-compose.generated.yml`.
2. Buildea **solo** esa imagen (`docker compose build odoo-<instancia>`,
   nunca `./odoo build` sin argumentos, que reconstruye TODAS las instancias).
3. `./odoo start <instancia>` y espera a que el entrypoint termine de
   instalar dependencias y el servidor Odoo esté realmente arriba (no basta
   con que Postgres esté lista — ver "Aprendizajes" abajo).
4. Corre `scripts/coverage` real y parsea el % de la línea `TOTAL` **y**,
   si el exit code no fue 0, distingue por qué: parsea el output en busca
   del mensaje de umbral (`Coverage failure: total of...`) y de las líneas
   de test fallido/con error del logger de Odoo, por separado. El `ESTADO`
   final es uno de: `OK`, `BELOW_THRESHOLD` (cobertura baja, tests OK),
   `TEST_FAILURES` (algún test falló, cobertura puede estar bien igual),
   `TEST_FAILURES+BELOW_THRESHOLD` (ambos a la vez), o `ERROR` (no se pudo
   ni parsear el % de cobertura — algo se rompió antes de llegar ahí). La
   columna `DETALLE` lista los tests puntuales que fallaron por nombre.
5. Para el contenedor, borra la imagen **solo si la creó él mismo** (nunca
   toca imágenes que ya existían antes de esta corrida), y restaura
   `"enabled": false`.
6. Al final del lote, `docker builder prune -f` para no acumular cache.
7. Deja un CSV en `coverage_data/` con el resultado de todos los proyectos.

```sh
./scripts/coverage-run-all [proyecto ...] \
  [--pull] [--threshold=70] [--dry-run] \
  [--keep-running] [--keep-images] [--no-regen] \
  [--out=reporte.csv] [--help]
```

- Sin proyectos **y corriendo en una terminal interactiva**: muestra un
  checklist para elegir uno o varios (Espacio para marcar, `A` para
  todos, Enter para confirmar) — mismo menú que usan `./odoo test`,
  `update`, `sync`, etc. Sin proyectos y sin TTY (cron/CI/pipe): corre
  sobre todos los que tienen tests, como siempre.
- `--dry-run`: muestra el plan completo (qué activaría, buildearía, y
  restauraría) sin tocar nada.
- `--keep-running`: no para el contenedor al terminar (útil para debug).
- También disponible como `./odoo coverage [proyecto ...] [flags]`.

**Antes de tocar nada**, hace un backup de `instances.json` en
`instances.json.bak` — el archivo no está en git, así que esa es la única
red de seguridad manual si algo falla a mitad de camino (aunque el
`try/finally` interno ya garantiza restaurar `enabled` incluso ante errores).

**Aprendizajes / por qué existen los `wait_for_*`:** `./odoo start` (docker
compose up -d) devuelve el control apenas el contenedor arranca, **no**
cuando el entrypoint interno termina de instalar dependencias y generar el
`odoo.conf` final con el `addons_path` correcto. Correr coverage antes de
eso hace que Odoo sólo vea los addons por defecto e instale `base` — 0% de
cobertura falso, no por falta de tests sino porque nunca se instaló el
módulo. Por eso se espera explícitamente a la línea `HTTP service ...
running` en los logs del contenedor antes de correr `scripts/coverage`.

---

## `migrate-module` — Migración de módulo con vistas (OCA views_migration)

Instala un módulo cargando el helper de migración de vistas de OCA.
La versión de `views_migration_{major}` se resuelve automáticamente desde
`odoo_version` en `instances.json`.

```sh
./scripts/migrate-module <instancia> -d <base_de_datos> -i <modulo>
```

> Antes requería `-c <contenedor>`. Ahora toma el nombre de instancia
> y resuelve contenedor y versión desde instances.json.

---

## `odoo_active_users` — Usuarios online por base de datos

Cuenta usuarios activos en cada base de datos Odoo según la tabla
`bus_presence`, con ventana de tiempo configurable.

```sh
./scripts/odoo_active_users <instancia> \
  [--minutes 2] \
  [--include-portal] \
  [--host <host>] [--port <port>] [--user <user>] [--password <pass>]
```

---

## `odoo_backup` — Backup de DB + filestore en ZIP

Genera dump SQL + filestore y los empaqueta en un ZIP. Valida
compatibilidad de versiones de pg_dump y puede instalar el cliente
correcto automáticamente.

```sh
./scripts/odoo_backup backup <instancia> \
  --target-pg-major <major> \
  [-d <base>] [-p <path>] \
  [--pg-dump-bin <bin>] \
  [--no-fs] [--no-cleanup] [--verbose] [--yes]
```

- Sin `-d`: lista bases disponibles para elegir interactivamente.
- `--yes`: salta confirmaciones de limpieza (útil en CI/cron).
- `--target-pg-major`: ej. `16`, `17`. Si pg_dump no coincide, intenta
  instalar `postgresql-client-{major}` dentro del contenedor.

---

## `odoo_cron_backup` — Backup periódico con rotación

Wrapper de `odoo_backup` para ejecución programada (cron). Corre el backup
y luego limpia los ZIPs más antiguos manteniendo solo los N más recientes.

```sh
./scripts/odoo_cron_backup \
  --instance <instancia> \
  --database <base> \
  --backups-folder-path <path> \
  --backup-script-path <path> \
  --target-pg-major <major> \
  --log-file-path <path> \
  --log-retention-days <días> \
  --cleanup-keep <cantidad> \
  [--pg-dump-bin <bin>] [--no-fs] [--no-log-cleanup]
```

---

## `odoo_restore` — Restaurar backup desde ZIP

Extrae dump.sql + filestore de un ZIP de backup, valida compatibilidad
de versiones de PostgreSQL, crea la DB y restaura.

```sh
./scripts/odoo_restore restore <instancia> \
  -z <archivo.zip> -d <nueva_db> \
  [--workdir <path>] [--psql-bin <bin>] \
  [--db-prefix <prefijo>] \
  [--verbose] [--no-cleanup]
```

- Valida que la versión del servidor origen no sea más nueva que la
  del destino.
- Si la major de psql no coincide con la del dump, intenta instalar
  el cliente correcto automáticamente.
- `--db-prefix`: agrega un prefijo al nombre de la DB restaurada.

---

## `odoo_restore_scp` — Descarga SCP + restore + limpieza de expirados

Descarga un ZIP de backup desde un servidor remoto por SCP, ejecuta
`odoo_restore`, y opcionalmente limpia bases de datos y ZIPs vencidos
según su nombre (sufijo `__exp_YYYY_MM_DD`).

```sh
./scripts/odoo_restore_scp \
  --instance <instancia> \
  --host <host> --user <usuario> \
  --remote-path <ruta_remota> \
  --download-path <ruta_local> \
  [--port 22] [--identity-file <clave>] \
  [--retention-days <días>] \
  [--long-retention-days <días>] \
  [--force-download] \
  [--cleanup-dbs] [--cleanup-zips] \
  [--delay-cleanup-zips-days <días>] \
  [--log-csv-path <path>] \
  [--workdir <path>] [--psql-bin <bin>] \
  [--db-prefix <prefijo>] [--scp-timeout 300] \
  [--verbose]
```

- `--cleanup-dbs-only` / `--cleanup-zips-only`: modo solo limpieza.
- Sin `--retention-days`: restaura sin fecha de vencimiento.
- Con `--long-retention-days`: crea una segunda copia con retención
  extendida y sufijo `__long`.
- Soporta formato de backup de `odoo_backup` para resolución automática
  del ZIP más reciente desde carpeta remota.

---

## `odoo-pw` — Restablecer contraseña de usuario

Conecta a PostgreSQL vía el contenedor Odoo y actualiza la contraseña
de un usuario.

```sh
./scripts/odoo-pw <instancia> -d <base> \
  [-l admin] [-p admin]
```

- `-l`: login del usuario (default: `admin`)
- `-p`, `--password`: nueva contraseña (default: `admin`)

---

## `odoo-test` — Ejecutar tests Odoo

```sh
./scripts/odoo-test <instancia> \
  [-d testing] \
  [-t /binaural_accountant] \
  [-i l10n_ve,binaural_rate,account,binaural_accountant]
```

---

## `odoo-update` — Actualizar módulos

```sh
./scripts/odoo-update <instancia> -d <base> <modulo1> [<modulo2> ...]
```

- Sin módulos: actualiza `all`.
- `--load-language <locale>`: idioma a cargar (default: no se carga).

---

## `odoo-upgrade-manifest` — Bump de versión en manifests

Asistente interactivo para incrementar el número de versión en
`__manifest__.py` de módulos Odoo.

```sh
./scripts/odoo-upgrade-manifest
```

Escanea `src/` y `src/custom/`, permite seleccionar carpeta padre y
módulos a actualizar.

---

## `precommit` — Ejecutar pre-commit sobre módulos de una instancia

Clona/actualiza la configuración de pre-commit desde el repo interno y
ejecuta los hooks sobre los módulos de una instancia.

```sh
./scripts/precommit <instancia> -m <modulos>
```

- `-m all`: todos los módulos de la instancia.
- `-m modulo1,modulo2,integra-addons/modulo3`: rutas exactas.
