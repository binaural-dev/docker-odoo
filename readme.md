# Binaural Workspace — Multi-Instance Odoo Docker

Entorno de desarrollo que permite levantar **múltiples instancias de Odoo** (diferentes versiones, diferentes proyectos) desde un único directorio, cada una con sus propios addons, base de datos y puerto. Todo se configura en un archivo `instances.json`.

Compatible con Odoo 14.0, 16.0, 17.0, 18.0, 19.0 y master.
Compatible con Linux y macOS (AMD y ARM).

## Instalación Rápida

```bash
# 1. Clonar el repositorio
git clone git@github.com:binaural-dev/docker-odoo.git
cd docker-odoo

# 2. Crear el archivo de configuración
cp instances.example.json instances.json
# Editar instances.json según tus necesidades

# 3. Construir las imágenes
./odoo build

# 4. Iniciar las instancias
./odoo start
```

## Configuración: `instances.json`

El archivo tiene 3 secciones principales:

### `odoo_configs` — Configuraciones reutilizables de Odoo

Define configuraciones nombradas que luego se referencian desde las instancias. Equivalen a los parámetros del `odoo.conf`.

```json
{
  "odoo_configs": {
    "19.0_default": {
      "admin_password": "admin",
      "workers": 2,
      "without_demo": true,
      "list_db": true,
      "proxy_mode": true,
      "limit_memory_soft": 16000000000,
      "limit_memory_hard": 17000000000,
      "max_cron_threads": 1,
      "limit_time_real_cron": 0,
      "limit_time_real": 3600,
      "limit_time_cpu": 60,
      "db_maxconn": 200,
      "unaccent": false,
      "server_wide_modules": "",
      "addons": ["src/enterprise"]
    }
  }
}
```

### `databases` — Bases de datos (managed o externas)

Define las conexiones a PostgreSQL. `create_container` (default: `true`) controla si se crea un contenedor Docker o si se conecta a una DB externa.

```json
{
  "databases": {
    "pg16": {
      "postgres_version": 16,
      "port": 5432,
      "expose_host_port": false,
      "user": "odoo",
      "password": "odoo",
      "bootstrap_user": "odoo_bootstrap",
      "bootstrap_password": "cambiar-esto",
      "config": "postgresql.conf"
    },
    "external_pg16": {
      "create_container": false,
      "postgres_version": 16,
      "host": "192.168.1.100",
      "port": 5432,
      "user": "odoo",
      "password": "odoo"
    }
  }
}
```

Las bases de datos gestionadas (`create_container: true`) **no publican su puerto al host por defecto**: los contenedores Odoo se conectan directamente a `db-<nombre>:5432` a través de la red interna de Docker (`odoo-multi`), sin pasar por el host. Esto evita que un Postgres corriendo localmente en la máquina (Homebrew, Postgres.app, etc.) sobre el mismo puerto termine interceptando las conexiones.

Si necesitas conectarte a la base de datos desde el host (por ejemplo con un cliente de escritorio), agrega `"expose_host_port": true` para que se publique `port` en `docker-compose.generated.yml`. Para uso normal (`./odoo psql`, `./odoo bash`, backups, restores, pgAdmin) no hace falta: todos corren dentro de los contenedores y usan la red interna.

#### `user`/`password` vs `bootstrap_user`/`bootstrap_password`

Cada base de datos gestionada tiene dos identidades de Postgres:

- **`user`/`password`**: el rol que **Odoo usa para todo**. No es superusuario (tiene `LOGIN` y `CREATEDB`, nada más), aunque sí puede crear/alterar/borrar tablas de módulos vía herencia de privilegios del rol bootstrap. Es el único que debería usarse desde `./odoo psql`, backups, restores, etc.
- **`bootstrap_user`/`bootstrap_password`**: el rol que Postgres crea automáticamente al inicializar el volumen (`initdb`). Postgres nunca permite quitarle el atributo de superusuario a este rol específico ni reasignarle la propiedad de sus objetos — es una restricción del motor, no de configuración. Por eso no se usa directamente: en un volumen nuevo, el rol de `user` se crea aparte (no-superusuario) heredando los privilegios del bootstrap vía `GRANT`, y el bootstrap queda con `NOLOGIN` — existe porque es dueño de los objetos, pero nadie puede autenticarse con él.

Ambos campos son opcionales: si se omiten, se usa el mismo valor de `user`/`password` para el bootstrap (comportamiento anterior a este esquema, con el rol de Odoo siendo superusuario — no recomendado, pero sigue funcionando para no romper configs existentes).

Existe una **tercera** identidad opcional, a nivel de instancia (no de `databases`): `db_user`/`db_password`, para cuando varias instancias comparten un mismo servicio de Postgres. Ver "Instancias que comparten un mismo servicio de Postgres" más abajo.

### `instances` — Instancias de Odoo

Cada instancia define su versión de Odoo, puerto externo, base de datos y configuración. Puede sobreescribir valores del `odoo_config` base usando `overwrite_odoo_config`.

```json
{
  "instances": {
    "bananera": {
      "odoo_version": "19.0",
      "external_port": 8070,
      "database": "pg16",
      "odoo_config": "19.0_default",
      "overwrite_odoo_config": {
        "workers": 4,
        "addons": ["src/enterprise", "src/custom/bananera"],
        "db_name": "bananera_prod",
        "db_filter": "^bananera_"
      }
    },
    "client-b": {
      "odoo_version": "17.0",
      "external_port": 8071,
      "database": "external_pg16",
      "odoo_config": "17.0_default",
      "overwrite_odoo_config": {
        "addons": ["src/enterprise", "src/custom/client-b"]
      }
    }
  }
}
```

`db_filter` es el patrón de regex que Odoo usa en runtime para decidir qué bases de datos le pertenecen (ej. `^bananera_` matcheará `bananera_prod`, `bananera_staging`, etc.), y también lo respeta el CLI de gestión: `./odoo update -d all` para una instancia solo actualiza las bases que matchean su `db_filter`, no todas las del servicio de Postgres que comparte con otras instancias. Si una instancia no define `db_filter` (o es `"*"`), `-d all` sigue trayendo todas las bases del servicio, con una advertencia explícita en pantalla.

⚠️ **Importante**: `db_filter` solo rige el ruteo HTTP (selector de bases en `/web/database/manager`, sesión) y el `-d all` del CLI. **El cron interno de Odoo (`ir.cron`) nunca lo consulta** — es un mecanismo puramente de request web, confirmado leyendo el código fuente real de Odoo 14.0/16.0/17.0/19.0. Si dos instancias comparten un mismo servicio de Postgres, el cron de una puede terminar procesando (y modificando) datos de la base de la OTRA — esto ya pasó en producción una vez. Ver la sección siguiente para el aislamiento real.

### Instancias que comparten un mismo servicio de Postgres

Cuando **más de una** instancia usa el mismo `database` (mismo servicio de Postgres) y alguna de ellas corre cron (`max_cron_threads` distinto de `0`, que es el default), `./odoo` **exige** que cada una de esas instancias tenga, además de un `db_filter` específico:

```json
{
  "instances": {
    "bananera": {
      "odoo_version": "19.0",
      "external_port": 8070,
      "database": "pg16",
      "odoo_config": "19.0_default",
      "db_user": "app_bananera",
      "db_password": "<password dedicado>",
      "overwrite_odoo_config": {
        "db_filter": "^bananera_"
      }
    }
  }
}
```

`db_user`/`db_password` van en la **raíz** de la instancia (hermano de `database`/`overwrite_odoo_config`), no dentro de `overwrite_odoo_config`. Son las credenciales de un rol de Postgres **dedicado a esa instancia**, dueño únicamente de sus propias bases — es la protección real contra el problema del cron descrito arriba: cada rol solo ve/puede tocar lo suyo (`list_dbs()` de Odoo ya filtra por `datdba = current_user`), y además se revoca `CONNECT` de `PUBLIC` sobre esas bases, así que ni siquiera una conexión directa con otro rol puede abrirlas.

Si falta cualquiera de los dos requisitos (`db_filter` específico o `db_user`/`db_password`) en alguna instancia de un grupo así, **cualquier comando `./odoo` falla de entrada** con un error detallado listando qué instancia(s) y qué les falta. Escape hatch legítimo: poner `"max_cron_threads": 0` explícito en `overwrite_odoo_config` para una instancia que de verdad no necesita cron (por ejemplo, una copia de solo lectura) — deja constancia de que es intencional, no un olvido.

**Cómo aplicar credenciales nuevas a una instancia que ya tiene bases de datos creadas:**

```bash
# 1. Agregar db_user/db_password (raíz de la instancia) y un db_filter específico
#    (overwrite_odoo_config) en instances.json

# 2. Aprovisionar: crea el rol si no existe, transfiere el ownership de toda
#    base que matchee el db_filter, y revoca CONNECT de PUBLIC sobre ellas
./odoo provision-role bananera

# 3. Regenerar compose y recrear el contenedor para que use las credenciales nuevas
./odoo build
docker compose -f docker-compose.generated.yml up -d --no-deps odoo-bananera
```

`provision-role` puede requerir una ventana breve de mantenimiento de **todo** el servicio de Postgres (no solo de esa instancia) si el rol bootstrap del servicio está en `NOLOGIN` (lo normal) — el comando lo maneja solo y pide confirmación explícita antes de tocar nada.

⚠️ Cambiar `db_filter` en `instances.json` **no** re-dispara nada de esto automáticamente — ver la auditoría a continuación.

### Auditoría automática: `db_filter` vs. ownership real

Cada `./odoo build` corre, además de generar la configuración, una auditoría de solo lectura que compara el `db_filter` de cada instancia contra el estado real en Postgres (nunca modifica nada) y avisa si encuentra:

- Una base que matchea el `db_filter` de una instancia pero pertenece a otro rol (falta correr `provision-role`).
- Una base ya del rol correcto, pero con `CONNECT` de `PUBLIC` todavía sin revocar.
- Una base que dejó de matchear el `db_filter` actual de la instancia dueña (el filtro cambió después de aprovisionar — revisar si es intencional).
- Una base que matchea el `db_filter` de **más de una** instancia a la vez (regex solapados — riesgo real: correr `provision-role` en ese estado puede robarle la base a la instancia que ya la tenía).

No bloquea el build — solo informa, con el comando exacto a correr para resolver cada aviso.

**Corrección automática (solo para los avisos sin ambigüedad):** cuando la auditoría detecta bases con dueño incorrecto o con `CONNECT` sin revocar (los primeros dos casos de la lista), `./odoo build` pregunta al final si querés correr `provision-role` para esas instancias ahora mismo (agrupando por servicio de Postgres, igual que una migración manual). Los otros dos casos (filtro que cambió, filtros solapados) **nunca** se ofrecen para autocorrección — son ambiguos y requieren revisión humana antes de tocar ownership.

```
2 instancia(s) con diferencias que 'provision-role' puede corregir automaticamente: inst_a, inst_b
¿Correr 'provision-role' para todas ellas ahora? [y/N]:
```

Para correr `./odoo build` en un contexto no interactivo (CI, automatización), usá `--no-confirm`: se salta esta pregunta (y cualquier otra sin entrada de teclado) sin corregir nada automáticamente, dejando el aviso igual en pantalla para que alguien lo resuelva a mano después.

### `pgadmin` (opcional)

```json
{
  "pgadmin": {
    "enabled": true,
    "port": 5050,
    "email": "admin@admin.com",
    "password": "admin"
  }
}
```

## Estructura de carpetas

```
src/
    custom/
        bananera/          # Repositorio/proyecto A
        client-b/          # Repositorio/proyecto B
    enterprise/            # Módulos enterprise de Odoo
    third-party-addons/    # Módulos de terceros
```

Los addons de cada instancia se especifican en el campo `addons` de su configuración:
```json
"addons": ["src/enterprise", "src/custom/bananera"]
```

## Comandos disponibles: `./odoo`

Todos los comandos que aceptan `[instance]` operan sobre todas las instancias si no se especifica nombre.

| Comando | Descripción |
|---------|-------------|
| `build [--no-cache] [--no-confirm]` | Genera Dockerfiles, docker-compose y nginx config. Audita `db_filter` vs. ownership real y ofrece corregirlo (ver más abajo). Construye imágenes. `--no-confirm` salta esa pregunta para uso en CI/automatización. |
| `start [instance]` | Inicia instancia(s), DB(s) managed y nginx. |
| `stop [instance]` | Detiene instancia(s). Si la DB no es usada por otras, también se detiene. |
| `restart [instance]` | Reinicia instancia(s). |
| `bash <instance>` | Abre bash (como root) en el contenedor de la instancia. |
| `logs [instance]` | Muestra logs en tiempo real. |
| `list` | Lista contenedores en ejecución. |
| `remove [instance]` | Elimina contenedores y volúmenes. |
| `fix-files [instance]` | Corrige permisos del filestore. |
| `psql <instance> -d <db>` | Conecta a PostgreSQL. |
| `update <instance> [-d <db\|all>] [-m modules] [-f]` | Actualiza módulos de Odoo (una base o todas). Sin `-m`, actualiza todos los módulos usando `click-odoo-update` (solo los que cambiaron desde la última actualización); con `-f`/`--force` fuerza un upgrade completo de todos, sin importar qué cambió. Un módulo puntual (`-m modulo`) siempre se actualiza directo, sin pasar por ninguno de los dos caminos anteriores. |
| `init [instance]` | Verifica que los addons referenciados existen. |
| `sync <repo> <branch> [--v]` | Sincroniza submódulos de un repositorio custom. |
| `test <instance> <module[,module2,...]> [opciones]` | Ejecuta tests con cobertura (uno o varios módulos, opcionalmente su árbol de dependencias con `--recursive`). Ver `./odoo test -h`. |
| `provision-role <instance>` | Aprovisiona el rol de Postgres dedicado de una instancia: crea el rol si no existe, transfiere el ownership de toda base que matchee su `db_filter`, y revoca `CONNECT` de `PUBLIC` sobre ellas. Requiere `db_user`/`db_password` y un `db_filter` específico ya definidos en `instances.json`. Puede pedir una ventana breve de mantenimiento de todo el servicio de Postgres (pide confirmación antes). Ver "Instancias que comparten un mismo servicio de Postgres" arriba. |

### Ejemplos

```bash
# Construir todo
./odoo build

# Iniciar todas las instancias
./odoo start

# Iniciar solo una instancia
./odoo start bananera

# Ver logs de una instancia
./odoo logs bananera

# Detener una instancia sin afectar las demás
./odoo stop client-b

# Bash en un contenedor
./odoo bash bananera

# Conectar a psql
./odoo psql bananera -d bananera_prod

# Actualizar módulos
./odoo update bananera -d bananera_prod -m sale,purchase

# Actualizar todas las bases de datos de una instancia (solo lo que cambio, via click-odoo-update)
./odoo update bananera -d all

# Forzar un upgrade completo de todos los modulos, sin importar que cambio
./odoo update bananera -d all -f

# Correr tests con cobertura de un modulo
./odoo test bananera sale_extension

# Correr tests de varios modulos juntos
./odoo test bananera sale_extension,purchase_extension

# Correr tests de un modulo y todo su arbol de dependencias
./odoo test bananera sale_extension --recursive

# Reiniciar todo
./odoo restart

# Aprovisionar el rol dedicado de una instancia (ver seccion de instances.json)
./odoo provision-role bananera
```

En el comando `update`, el selector de bases incluye una opción visible de `all (todas las bases de datos)`.

## Scripts auxiliares

En la carpeta `scripts/` se encuentran herramientas de administración. Todos requieren el nombre de instancia como primer argumento:

```bash
# Backup
scripts/odoo_backup backup <instance> -d <dbname> -p <path>

# Restore
scripts/odoo_restore restore <instance> -z <zipfile> -d <new_dbname>

# Reset password
scripts/odoo-pw <instance> -d <dbname> [-l login] [-p password]

# Update modules
scripts/odoo-update <instance> -d <dbname> module1 module2

# Run tests
scripts/odoo-test <instance> [-d dbname] [-t test_tags] [-i modules]

# Pre-commit on modules
scripts/precommit <instance> -m <modules>
```

### `scripts/precommit` — Linting sobre módulos Odoo

Ejecuta `pre-commit` sobre los archivos de uno o varios módulos, resolviendo automáticamente sus rutas desde `instances.json`.

**Qué hace internamente:**
1. Instala `pre-commit` si no está disponible.
2. Clona (o actualiza vía `git fetch` + `git reset --hard`) el repo de configuración `binaural-dev/precommit-config-files` dentro de `.ignore/`.
3. Copia los archivos de configuración a la raíz del proyecto (sobrescribiendo los existentes).
4. Ejecuta `pre-commit install`.
5. Resuelve los paths de los módulos usando los `addons` de la instancia especificada.
6. Corre `pre-commit run --files <archivos>`.

**Uso básico:**
```bash
# Con instancia explícita
scripts/precommit binaural-19.0 -m binaural_brand,binaural_mrp

# Sin instancia → pregunta interactivamente
scripts/precommit -m binaural_brand

# Todos los módulos de la instancia
scripts/precommit binaural-19.0 -m all

# Desambiguar con path completo (si un nombre existe en más de un addon path)
scripts/precommit binaural-19.0 -m integra-addons/modulo_c,enterprise/modulo_c
```

## Cómo funciona internamente

1. `./odoo build` lee `instances.json` y genera:
   - `.resources/Dockerfile.{version}` por cada versión única de Odoo
   - `docker-compose.generated.yml` con todos los servicios
   - `.resources/nginx_configs/generated.conf` con un bloque server por instancia
2. Nginx escucha en los puertos externos y enruta a los contenedores Odoo internos (puertos 8069/8071).
3. Todas las instancias montan `./src` y cada una filtra sus addons via la variable `INSTANCE_ADDONS`.
4. Instancias con la misma `odoo_version` comparten la misma imagen Docker.

## Compatibilidad PostgreSQL

Para restaurar backups, la versión del contenedor debe ser igual o superior a la versión con que se generó el dump. Ajusta `postgres_version` en la sección `databases` según necesites.

## FAQ

**¿Cómo agrego un nuevo proyecto/instancia?**
1. Agrega la carpeta del proyecto en `src/custom/`
2. Agrega un `odoo_config` (o reutiliza uno existente)
3. Agrega una entrada en `instances` con la versión, puerto y addons
4. Ejecuta `./odoo build` y luego `./odoo start`

**¿Puedo tener dos instancias de la misma versión de Odoo?**
Sí. Cada una tendrá su propio contenedor, volúmenes y addons independientes.

**¿Puedo compartir la misma base de datos entre instancias?**
Sí. Varias instancias pueden referenciar la misma `database`. El contenedor de DB se crea una sola vez.
