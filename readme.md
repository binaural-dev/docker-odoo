# Binaural Workspace

Binaural Workspace es un entorno de desarrollo diseñado para facilitar la ejecución y configuración de proyectos en Odoo. Con este repositorio, podrás levantar ambientes de desarrollo en Linux y macOS (AMD y ARM).

Es compatible con las versiones 14.0, 16.0, 17.0 y 18.0 de Odoo, permitiéndote elegir la que mejor se adapte a tu proyecto.

En cuanto a Windows, no se ha probado oficialmente, pero puede ser compatible utilizando WSL2 con Docker. Se recomienda verificar su funcionamiento en tu entorno antes de usarlo en producción.

## Instalación

Para comenzar a utilizar el espacio de trabajo, sigue los pasos a continuación.


### Clonar el repositorio:

```bash
git clone git@github.com:binaural-dev/docker-odoo.git
```

Accede al directorio:
```bash
cd docker-odoo
```

### Requerimientos

Instalar dotenv:

```bash
sudo apt-get install python3-dotenv
```

Esto es necesario para trabajar con el archivo de configuración .env, que almacenará todas las variables del entorno necesarias.

### Configurar el archivo .env

El archivo .env contiene las configuraciones para tu espacio de trabajo en Odoo. Deberás configurarlo antes de continuar. Puedes encontrar un archivo de ejemplo en el repositorio, el cual deberás modificar de acuerdo a tu entorno.

Para trabajar con la configuración por defecto, puedes ejecutar el siguiente comando para crear el .env

```bash
cp .env_example .env
```

> El `.env_example` está creado para levantar la versión 16.0 de Odoo. Si necesitas otra versión (como 14.0, 17.0 o 18.0), actualiza el archivo `.env` reemplazando las referencias por la versión deseada.

### Descripción de los campos de `.env_example`

El archivo de ejemplo agrupa sus variables en distintas secciones. Al comienzo se encuentran los parámetros que se utilizan al construir la imagen y al levantar los contenedores con Docker Compose. Luego aparecen opciones para definir el comportamiento de Odoo (equivalentes al `odoo.conf`) y ajustes relacionados con Traefik y el filtrado de bases de datos.

**Parámetros para Docker y Docker Compose**

- `PROJECT_NAME` define el prefijo para los nombres de los contenedores.
- `PORT_SERVICE_HOST_ODOO` y `PORT_SERVICE_CONTAINER_ODOO` indican el puerto de Odoo en tu máquina y dentro del contenedor.
- `ODOO_RELEASE`, `ODOO_VERSION` y `ODOO_MINOR` se usan para generar el Dockerfile correspondiente y organizar la red interna.
- `ODOO_SHA` permite verificar opcionalmente la integridad del paquete `.deb` descargado.
- `POSTGRES_IMG_VERSION`, `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD` determinan la versión y credenciales del contenedor de PostgreSQL.
- `PG_ADMIN_HOST_PORT` y `PG_ADMIN_SERVICE_CONTAINER_PORT` exponen la interfaz de pgAdmin.
- `PGDATABASE` es la base utilizada por defecto por los scripts.
- `RESET_PASSWORD` sirve como contraseña temporal para el script `odoo-pw`.
- `ENV_TYPE` indica si el entorno es de un miembro de Binaural (`binaural`) o de un colaborador externo (`external`). Según este valor el comando `./odoo init` clonará los repositorios privados o solo los públicos.

**Dominio y Traefik**

- `DOMAIN` define el dominio comodín que usa Traefik para enrutar hacia Odoo.
- `TRAEFIK_FRONTEND_PRIORITY` establece la prioridad de la regla de enrutamiento.
- `TRAEFIK_HOST_PORT` y `TRAEFIK_SERVICE_CONTAINER_PORT` permiten exponer el panel de Traefik si se desea.
- `DBFILTER` (comentado por defecto) puede activarse para que cada base de datos sea accesible mediante su propio subdominio.

**Parámetros de `odoo.conf`**

La sección marcada como "PARÁMETROS QUE NO SE SUELEN CAMBIAR" agrupa opciones que Odoo lee desde su archivo de configuración:

- `MAX_CRON_THREADS`, `WORKERS` y `LIST_DB` controlan hilos de cron, número de workers y visibilidad de la lista de bases de datos.
- `WITHOUT_DEMO` permite omitir los datos de demostración.
- `ADMIN_PASSWORD` define la contraseña del usuario administrador al iniciar la base.
- `PROXY_MODE` y `SERVER_MODE` ajustan el comportamiento cuando se ejecuta detrás de un proxy y el modo de servidor.
- `AEROO_DOCS_HOST` indica la ruta al servicio de reportes Aeroo.
- `LIMIT_TIME_REAL_CRON` y `LIMIT_TIME_REAL` configuran los límites de tiempo de Odoo.
- `UNACCENT` habilita la extensión `unaccent` en PostgreSQL si está disponible.
- `ODOO_UPGRADE_PATH` señala la ruta local del repositorio `odoo-upgrade` para desarrollo.
- `SERVER_WIDE_MODULES` permite cargar módulos globales en todas las bases.

### Clonar los Repositorios Necesarios

Binaural trabaja con módulos alojados en distintos repositorios privados. En caso de que no formes parte de la organización, aún podrás levantar el ambiente sin problemas.

Clonar repositorios:
```bash
./odoo init
```

Los repo en cuestion son:
 - [Odoo Enterprise](https://github.com/odoo/enterprise) (necesitas ser partner odoo para tener acceso a este repositorio)
 - [Integra Addons](https://github.com/binaural-dev/integra-addons) (aplica solo para los devs de binaural)
 - [Third Party Addons](https://github.com/binaural-dev/third-party-addons) (aplica solo para los devs de binaural)

 Si no tienes acceso a estos repositorios comunicate con nuestro equipo de DevOps.

### Construcción del Dockerfile

El archivo de Dockerfile se construye a partir de las configuraciones de tu archivo .env (por ello es importante especificar la versión de Odoo a utilizar en dicho archivo).

```bash
./odoo build
```
Este comando genera `./.resources/Dockerfile` y luego ejecuta `docker compose build`. Si intentas ejecutar
`docker compose build` sin haber corrido previamente `./odoo build`, obtendrás un error de "Dockerfile not found"
porque el Dockerfile dinámico aún no existe. Si `./odoo build` muestra `ModuleNotFoundError: No module named 'dotenv'`,
instala la dependencia con `sudo apt-get install python3-dotenv` o `pip install python-dotenv`.
Si la descarga del paquete de Odoo devuelve un `403 Forbidden`, verifica que tengas acceso a `nightly.odoo.com` y que el valor de `ODOO_RELEASE` apunte a un build disponible.

### Estructura de la carpeta a utilizar

```bash
- src /
    custom/ (submodules de git)
        /repository-1 (repositorio/proyecto)
        /repository-2 (otro repositorio/proyecto)
        /repository-n (otro repositorio/proyecto más)
    integra-addons/
        /module-01
        /module-02
    enterprise/ (módulos enterprise de Odoo)
        /module-01
        /module-02
    third-party-addons/ (módulos de terceros)
        /module-01
        /module-02
```

En este entorno, los módulos de Odoo se organizan mediante submódulos de Git, lo que proporciona mayor flexibilidad y facilita la gestión del código.

La estructura ha sido diseñada para el flujo de trabajo de Binaural; sin embargo, el entorno funcionará sin problemas incluso si algunos módulos no están disponibles.

> Para más información sobre los módulos de binaural, puedes visitar [Odoo Venezuela](https://github.com/binaural-dev/odoo-venezuela)

> En caso de que no formes parte de la organización, no contarás con los repositorios de integra-addons, enterprise y third-party-addons. En ese caso, puedes desarrollar tus propios módulos en el directorio `custom`.

Si tienes deseas agregar o desarrollar algún módulo para tu ambiente, puedes hacerlo de dos formas:

- Agregar el módulo en third-party-addons
- Agregar un repositorio en custom

Para agregar un repositorio en custom, ubícate en docker-odoo/src/custom/ y ejecuta `git clone repositorio-que-contiene-tus-módulos.git`


### Comandos disponibles en el script `odoo`

El script principal `./odoo` permite gestionar el entorno de Odoo de forma sencilla. Los comandos disponibles son:

| Comando         | Descripción                                                                                 |
|-----------------|--------------------------------------------------------------------------------------------|
| `run`           | Levanta los contenedores de Odoo en segundo plano (`docker compose up -d`).                |
| `stop`          | Detiene los contenedores de Odoo (`docker compose down`).                                  |
| `restart`       | Reinicia los contenedores de Odoo.                                                         |
| `build`         | Construye la imagen de Odoo según la configuración del `.env`. Usa `--no-cache` si deseas forzar la reconstrucción sin caché. |
| `bash`          | Abre una terminal bash dentro del contenedor de Odoo como root.                            |
| `init`          | Clona los repositorios necesarios en la carpeta `src/` según el tipo de entorno.           |
| `psql -d <db>`  | Abre una terminal psql conectada a la base de datos `<db>` del contenedor de Odoo.         |
| `sync <repo> <branch> [--v]` | Sincroniza un repositorio y sus submódulos con la rama indicada. Usa `--v` para ver la salida de git. |
| `logs`          | Muestra los últimos 10 logs de todos los servicios en tiempo real (`docker compose logs --tail 10 -f`). |

Ejemplos de uso:
```bash
# Levantar Odoo
./odoo run

# Detener Odoo
./odoo stop

# Reiniciar Odoo
./odoo restart

# Construir la imagen (con o sin caché)
./odoo build
./odoo build --no-cache

# Ver logs en tiempo real
./odoo logs

# Bash dentro del contenedor
./odoo bash

# Clonar repositorios necesarios
./odoo init

# Acceso a psql
./odoo psql -d <nombre_db>

# Sincronizar un repositorio custom y sus submódulos
./odoo sync <repo> <branch>
./odoo sync <repo> <branch> --v
```

### Acceso al Ambiente

El acceso a Odoo dependerá de la configuración establecida en el archivo .env.

- Opción 1: Acceso con Filtro de Base de Datos.

Si la variable DB_FILTER está activa en el .env, cada base de datos tendrá su propio subdominio (filtrado por el nombre de la base de datos). Esto permite acceder a distintas bases sin necesidad de seleccionarlas manualmente al ingresar al ambiente.

Ejemplo de acceso con DB_FILTER activo:
```bash
Base de datos "db"     →  db.odoo.localhost
Base de datos "prueba" →  prueba.odoo.localhost
Base de datos "17"     →  17.odoo.localhost
```

- Opción 2: Acceso General sin Filtro

Si no deseas utilizar el filtrado por dominio, simplemente comenta o elimina la variable DB_FILTER en el .env.

Ejemplo de acceso con DB_FILTER desactivado:
```bash
http://localhost:<PUERTO>
```

### Scripts útiles

En la carpeta [`scripts`](scripts/) encontrarás herramientas para realizar
distintas tareas de administración. Revisa la
[documentación de scripts](scripts/README.md) para conocer cada comando.


### Compatibilidad de versiones de PostgreSQL para restauración de backups

**IMPORTANTE:**  
Para restaurar un backup (.dump) de PostgreSQL, la versión del contenedor debe ser igual o superior a la versión con la que se generó el dump.  
Si restauras un .dump generado con PostgreSQL 16 en un contenedor con PostgreSQL 14, obtendrás errores como `pg_restore: error: unsupported version (1.16) in file header`.

- Ajusta la variable `POSTGRES_IMG_VERSION` en tu `.env` a la versión correcta (por ejemplo, `16`).
- Si no sabes la versión, puedes inspeccionar el dump con `head -n 5 archivo.dump` o pedir al responsable del backup la versión exacta.
- Para máxima compatibilidad, pide siempre el backup en formato SQL plano (.sql), que puede restaurarse en versiones iguales o superiores.

Consulta la documentación de scripts para más detalles sobre restauración.


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

---
