# Scripts disponibles

Esta carpeta agrupa utilidades para administrar y probar tu entorno de Odoo. La mayoría de los scripts hacen uso de las variables definidas en `.env`.




## Ejemplos de uso de scripts

### migrate-module

```sh
./scripts/migrate-module -d <base_de_datos> -i <modulo> -c <contenedor_odoo>
```
Migra el módulo `<modulo>` en la base de datos `<base_de_datos>` dentro del contenedor `<contenedor_odoo>`.

### odoo-backups.sh

```sh
./scripts/odoo-backups.sh -c <config.json> -s <servers.json> -d <base_de_datos>
```
Genera un respaldo de la base de datos `<base_de_datos>` y su filestore, utilizando los archivos de configuración y servidores indicados.

### odoo-pw

```sh
./scripts/odoo-pw -d <base_de_datos> -l <usuario>
```
Restablece la contraseña del usuario `<usuario>` en la base de datos `<base_de_datos>`, usando el valor de `RESET_PASSWORD` definido en el archivo `.env`. Si no se indica usuario, se restablece la contraseña de `admin`.

### odoo-test

```sh
./scripts/odoo-test <modulo> --container <contenedor> --addons <ruta1,ruta2,...>
```
Instala uno o varios módulos en una base propia y corre su suite bajo `coverage`,
con el resultado exacto por test (no parsea texto: inyecta un hook y consulta
`ir_module_module` directamente). Desde el launcher es `./odoo test <instancia>
<modulo>`, que resuelve el contenedor y los addons desde `instances.json`.

Lo más usado:

| Flag | Para qué |
|---|---|
| `--recursive` | Mide el subárbol completo de dependencias en vez de un módulo solo |
| `--out-coverage-json`, `--out-json`, `--out-logs` | Exportan cobertura, resultado por test y log completo |
| `--out-coverage-json-raw` | Segundo JSON de cobertura **sin aplicar el `omit`**: una entrada por cada archivo medido, tests incluidos. De ahí se derivan las dos formas de contar sin volver a medir |
| `--db-template <base>` | Clona la base de una plantilla ya horneada en vez de instalarla desde cero: de minutos a segundos por corrida |
| `--timeout <s>` | Corta una suite colgada (exit code 124) sin perder la cobertura parcial |
| `--no-confirm` | Salta las confirmaciones de `--recursive`, para automatización |

`./scripts/odoo-test -h` tiene el detalle completo y las razones de cada
decisión (por qué `--workers 0`, por qué los puertos aleatorios, por qué el
filestore se copia junto con la base clonada).

### coverage-sweep

```sh
# 1. hornear la plantilla (una vez por versión de Odoo)
./scripts/coverage-sweep template --instance cov_19 --db tpl_cov_19

# 2. medir TODOS los módulos de unos repos, uno por uno y aislado
./scripts/coverage-sweep run --instance cov_19 --line 19.0 --slug 19 \
    --repos integra-addons,odoo-venezuela \
    --db-template tpl_cov_19 --jobs 2 --timeout 2400 \
    --out logs/coverage-sweep/2026-09-07_19.0

# 3. cómo va / qué falta        4. limpiar bases colgadas
./scripts/coverage-sweep status --out logs/coverage-sweep/2026-09-07_19.0
./scripts/coverage-sweep clean --instance cov_19 --yes
```

Orquesta un barrido completo: arma la lista de trabajo, **descarta antes de
correr** los módulos cuya dependencia no existe en el `addons_path` (con el
motivo escrito, en vez de quemarles el timeout), corre `odoo-test` por módulo, y
deja un `result.json` por módulo con cobertura, clasificación y — para los que
no instalan — el estado real de `ir_module_module` y la causa sacada del log.

Cada módulo queda con **las dos formas de contar la misma medición**, derivadas
del JSON sin filtrar: `pct`/`stmts`/`miss` cuentan solo el código de producción,
y `pct_all`/`stmts_all`/`miss_all` cuentan también los archivos de test y el
andamiaje (`__init__.py`, `__manifest__.py`). La segunda da un número más alto
—un archivo de test se ejecuta por definición al correr la suite— y sirve para
comparar contra mediciones que contaban así. Verificado: la derivación de la
primera reproduce exacto el total que da `coverage` aplicando el `omit`.

Es **reanudable**: si se corta, volver a correr el mismo comando retoma donde
quedó. El fingerprint de cada resultado incluye el commit del repo, así que si
el código cambió el módulo se vuelve a medir en vez de devolver un número viejo.

`--jobs 2` es el techo prudente: cada corrida pica 1-2 GB y el `mem_limit` por
defecto del contenedor son 4 GB, así que conviene darle `"mem_limit": "8g"` a la
instancia del barrido antes de subirlo.

### coverage-sweep-aggregate

```sh
./scripts/coverage-sweep-aggregate \
    --run 19.0=logs/coverage-sweep/2026-09-07_19.0 \
    --baseline deliverables/coverage-sweep/baseline-2026-08.json \
    --measured-at "7-8 de septiembre de 2026" \
    --out deliverables/coverage-sweep/dataset-2026-09.json

# valida la aritmética contra la medición histórica, sin medir nada
./scripts/coverage-sweep-aggregate --selftest \
    --baseline deliverables/coverage-sweep/baseline-2026-08.json
```

Junta uno o varios barridos en un solo dataset, con los agregados por línea y
por repo, la comparación entre líneas y el progreso contra una medición
anterior.

El `--selftest` recalcula los agregados de la línea base desde sus propios
módulos y los compara contra los guardados: es la prueba de que las fórmulas de
este script dan los mismos números que el informe anterior. **Correrlo antes de
publicar cualquier comparación.**

#### Montar una instancia de barrido

El barrido no debe correr en la instancia de trabajo de nadie: los submódulos de
una instancia están en la rama que su dueño necesita, y una corrida de horas la
dejaría con otro código y compitiendo por su `mem_limit`. En su lugar, checkouts
propios y una instancia dedicada por línea:

```sh
# checkout pineado (clone --local: sin red para los objetos, con hardlinks)
git clone --local --no-checkout src/custom/<alguna>/integra-addons src/_sweep/19.0/integra-addons
git -C src/_sweep/19.0/integra-addons remote set-url origin git@github.com:binaural-dev/integra-addons.git
git -C src/_sweep/19.0/integra-addons fetch origin 19.0 --tags
git -C src/_sweep/19.0/integra-addons checkout -B 19.0 FETCH_HEAD
```

Y la entrada en `instances.json` (que es local a cada máquina, está en
`.gitignore`):

```json
"cov_19": {
  "odoo_version": "19.0", "external_port": 8103,
  "database": "pg16", "odoo_config": "default",
  "overwrite_odoo_config": {
    "addons": ["src/enterprise-19", "src/_sweep/19.0/integra-addons",
               "src/_sweep/19.0/odoo-venezuela", "src/_sweep/19.0/third-party-addons"],
    "max_cron_threads": 0,
    "workers": 0,
    "mem_limit": "8g",
    "list_db": false,
    "db_filter": "^covs_19_"
  }
}
```

`max_cron_threads: 0` es obligatorio: sin eso la validación de aislamiento hace
fallar el `build`. `list_db: false` + `db_filter` mantienen las bases del
barrido fuera del selector de todo el mundo. Ojo: la clave que el generador lee
es **`db_filter`**, no `dbfilter` — un `dbfilter` se ignora en silencio.

Para levantarla sin recrear los contenedores que ya están corriendo:

```sh
./odoo build --no-confirm
docker compose -f docker-compose.generated.yml up -d --no-deps odoo-cov_19
```

### odoo-update

```sh
./scripts/odoo-update -d <base_de_datos> <modulo1> <modulo2> ...
```
Actualiza los módulos indicados (`<modulo1>`, `<modulo2>`, etc.) en la base de datos `<base_de_datos>`.

### restore_db.sh

```sh
./scripts/restore_db.sh -b <contenedor_db> -o <contenedor_odoo> -f <archivo_backup> -d <base_de_datos>
```
Restaura el backup `<archivo_backup>` en la base de datos `<base_de_datos>`, utilizando los contenedores `<contenedor_db>` (PostgreSQL) y `<contenedor_odoo>` (Odoo).


### Notas y solución de problemas para restore_db.sh

- El script detecta automáticamente si el archivo es `.dump` (usa `pg_restore`) o `.sql` (usa `psql`).
- Si ves el error `pg_restore: error: unsupported version (1.16) in file header`, significa que tu contenedor de PostgreSQL es más antiguo que la versión usada para generar el dump.  
  **Solución:** actualiza la variable `POSTGRES_IMG_VERSION` en tu `.env` y recrea el contenedor.
- Si después de restaurar y actualizar todos los módulos aparecen errores como `KeyError: 'ir.http'` en Odoo, puede deberse a:
  - Un dump incompleto o corrupto.
  - Falta de módulos en el path de addons.
  - Incompatibilidad entre la versión de Odoo y la base restaurada.
- Para máxima compatibilidad, solicita siempre el dump en formato SQL plano (`.sql`).
- Si tienes problemas, revisa los logs de restauración y asegúrate de que todos los módulos requeridos estén presentes en el entorno.

