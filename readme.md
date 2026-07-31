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
      "user": "odoo",
      "password": "odoo",
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
        "db_name": "bananera_prod"
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
| `build [--no-cache]` | Genera Dockerfiles, docker-compose y nginx config. Construye imágenes. |
| `start [instance]` | Inicia instancia(s), DB(s) managed y nginx. |
| `stop [instance]` | Detiene instancia(s). Si la DB no es usada por otras, también se detiene. |
| `restart [instance]` | Reinicia instancia(s). |
| `bash <instance>` | Abre bash (como root) en el contenedor de la instancia. |
| `logs [instance]` | Muestra logs en tiempo real. |
| `list` | Lista contenedores en ejecución. |
| `remove [instance]` | Elimina contenedores y volúmenes. |
| `fix-files [instance]` | Corrige permisos del filestore. |
| `psql <instance> -d <db>` | Conecta a PostgreSQL. |
| `update <instance> [-d <db\|all>] [-m modules]` | Actualiza módulos de Odoo (una base o todas). |
| `init [instance]` | Verifica que los addons referenciados existen. |
| `sync <repo> <branch> [--v]` | Sincroniza submódulos de un repositorio custom. |

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

# Actualizar todas las bases de datos de una instancia
./odoo update bananera -d all

# Reiniciar todo
./odoo restart
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

### Compatibilidad de versiones de PostgreSQL para restauración de backups

**IMPORTANTE:**  
Para restaurar un backup (.dump) de PostgreSQL, la versión del contenedor debe ser igual o superior a la versión con la que se generó el dump.  
Si restauras un .dump generado con PostgreSQL 16 en un contenedor con PostgreSQL 14, obtendrás errores como `pg_restore: error: unsupported version (1.16) in file header`.

- Ajusta la variable `POSTGRES_IMG_VERSION` en tu `.env` a la versión correcta (por ejemplo, `16`).
- Si no sabes la versión, puedes inspeccionar el dump con `head -n 5 archivo.dump` o pedir al responsable del backup la versión exacta.
- Para máxima compatibilidad, pide siempre el backup en formato SQL plano (.sql), que puede restaurarse en versiones iguales o superiores.

Consulta la documentación de scripts para más detalles sobre restauración.

### FAQ

#### ¿Cómo configurar addons_path?

Cada vez que añades un nuevo repositorio a la carpeta custom, este será automáticamente detectado por el entorno.

#### ¿Qué es todo esto?
Para entender completamente el funcionamiento del entorno, te recomendamos familiarizarte con los comandos de la terminal de Linux, Docker, Traefik y, por supuesto, Odoo.

Si tienes alguna pregunta, no dudes en contactar con el equipo. Si no eres parte del equipo de desarrollo de Binaural, por favor utiliza los Issues en GitHub (siguiendo el código de conducta establecido).

# 📘 Comandos Disponibles del Script de Gestión Odoo -> ./odoo

Este script proporciona una interfaz de línea de comandos para administrar entornos Odoo basados en Docker. La siguiente tabla resume todos los comandos disponibles, su función y cuándo deben utilizarse.

---

## 📋 Tabla de Comandos

| Comando | Descripción | Cuándo usarlo |
|--------|-------------|----------------|
| `start` | Inicia Odoo, PostgreSQL y pgAdmin (si aplica). | Primera ejecución, después de un `stop` o tras reiniciar el servidor. |
| `stop` | Detiene los contenedores de Odoo y PostgreSQL. | Para liberar recursos o antes de un reinicio. |
| `restart` | Reinicia completamente Odoo y la base de datos. | Tras cambios en configuración o errores persistentes. |
| `fix-files` | Corrige permisos del filestore de Odoo. | Cuando Odoo no puede leer/escribir archivos. |
| `bash` | Abre una consola dentro del contenedor Odoo. | Depuración o ejecución manual de comandos. |
| `init` | Clona los repositorios necesarios según el entorno. | Primera instalación o regeneración de `src/`. |
| `logs` | Muestra logs en tiempo real de Odoo y PostgreSQL. | Diagnóstico de errores o monitoreo. |
| `list` | Lista los contenedores activos del entorno. | Verificar si Odoo está corriendo. |
| `remove` | Elimina contenedores y volúmenes (incluye datos). | Reset total del entorno. |
| `build` | Construye la imagen Docker de Odoo. | Cambios en Dockerfile o dependencias. |
| `psql -d <dbname>` | Abre una consola PostgreSQL dentro del contenedor. | Consultas SQL o depuración de BD. |
| `sync <repo> <branch> [--v]` | Sincroniza repositorios y submódulos. | Cambios de rama, actualizaciones o conflictos. |
| `update -d <dbname> -m <modules>` | Actualiza módulos Odoo dentro del contenedor. | Desarrollo o despliegue de cambios. |
| `test -d <dbname> -m <module>` | Ejecuta todas las pruebas unitarias de un modulo en una base de datos. | Desarrollo o pruebas QA de cambios. |


---
