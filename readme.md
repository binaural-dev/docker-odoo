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
cp instances.example.jsonc instances.json
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

Cada DB tiene **dos ejes de configuración independientes**:

- **`postgres_version`**: versión del motor PostgreSQL (15/16/17/18). Determina compatibilidad con Odoo. Ver [Compatibilidad PostgreSQL](#compatibilidad-postgresql).
- **`config`**: perfil de tuning según la carga esperada. Ver [Perfiles de PostgreSQL](#perfiles-de-postgresql) abajo.

```json
{
  "databases": {
    "v17": {
      "postgres_version": 16,
      "port": 5432,
      "user": "odoo",
      "password": "odoo",
      "config": "postgresql.xlarge.conf"
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

Cada instancia define su versión de Odoo, puerto externo, base de datos y configuración. Puede sobreescribir valores del `odoo_config` base usando `overwrite_odoo_config`. El flag opcional `"enabled"` (default `true`) controla si la instancia aparece en `./odoo build/start/stop/...` y en la TUI; podés togglerlo desde la TUI con `Space` y el cambio se persiste en `instances.json`.

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
    },
    "client-paused": {
      "enabled": false,
      "odoo_version": "19.0",
      "external_port": 8072,
      "database": "pg16",
      "odoo_config": "19.0_default",
      "overwrite_odoo_config": {
        "addons": ["src/enterprise", "src/custom/client-paused"]
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

## TUI interactiva: `./odoo-tui`

Una interfaz de terminal (Textual) que envuelve `./odoo` y los scripts de
`scripts/`. **No reemplaza el CLI**: `./odoo <comando>` sigue funcionando
exactamente igual que antes. La TUI es una capa aditiva que arma los
comandos por vos y muestra el output en pantalla.

```bash
# Dependencia: textual (>= 0.50). Instalar con:
pip install --user textual

# Lanzar la TUI (modo normal)
./odoo-tui

# Lanzar la TUI con herramientas de desarrollo (hot-reload de CSS, consola)
./odoo-tui --dev
```

El flag `--dev` activa el modo desarrollo de Textual: recarga el CSS en
caliente al editar `tui/styles/odoo-tui.tcss` y abre una consola interactiva
con `Ctrl+P` → devtools. Ideal para diseñar componentes.

### Flujo

1. Lista las instancias definidas en `instances.json` (izquierda).
2. Lista las acciones disponibles agrupadas por categoría (derecha):
   `Lifecycle`, `Acceso`, `Mantenimiento`, `Módulos / DB`, `Sync`, `Scripts`.
3. Elegís instancia → elegís acción → si la acción requiere datos
   (DB, módulos, login, archivo ZIP, etc.) aparece un modal para completarlos.
4. El comando se invoca y el output se stream en el panel inferior.

### Picker fzf para `Update módulos`

La acción `Update módulos` detecta los addons locales de la instancia
seleccionada (recorriendo los paths declarados en `overwrite_odoo_config`)
y abre un picker estilo fzf con dos paneles: `Disponibles` (módulos
encontrados en disco) y `A actualizar` (los que vas acumulando).

- Filtrá tipeando en el campo `Filtro` (match por substring case-insensitive).
- `Enter` sobre un módulo disponible lo agrega (o lo quita) de la selección.
- `Tab` cambia el foco entre el campo de filtro y las listas.
- `L` limpia la selección.
- `E` ejecuta (o el botón `Ejecutar`).
- `Esc` cancela.

**Selección vacía = todos los módulos.** Si confirmás sin elegir ninguno,
se ejecuta `all` (la etiqueta del botón cambia a `Ejecutar (all)`).
Si la instancia no tiene addons en disco, el picker se salta y se usa
el modal de texto clásico, que además acepta `--load-language=es_VE`.

### Progreso en vivo durante la actualización

Cuando ejecutás `Update` con módulos seleccionados, aparece un recuadro
verde arriba del panel de output que muestra:

```
┌─ Actualizando módulos ─ bananera_prod ───────────────────┐
│  Progreso:  ████████░░░░░░░░░░░░  45 / 234 (19%)        │
│  Quedan: 189 módulos                                     │
│  [I]INFO ✓  [W]WARNING ✓  [E]ERROR ✓  [C]CRITICAL ✓     │
│  [Esc] Cancelar   [0] Todos   [9] Solo error/warn       │
└──────────────────────────────────────────────────────────┘
```

- Odoo emite el formato `(N/M)` en su stdout mientras actualiza módulos;
  la TUI lo parsea y actualiza la barra en tiempo real.
- Podés filtrar el nivel de log que se muestra en el panel inferior
  usando las teclas `1`-`4` para togglear cada nivel, `0` para todos,
  y `9` para solo errores y warnings.

### Atajos de teclado

| Tecla | Acción |
|-------|--------|
| `Tab` | Cambia el foco entre paneles |
| `↑` / `↓` | Navegar dentro de un panel |
| `Enter` | Seleccionar instancia / ejecutar acción |
| `r` | Refrescar instancias desde `instances.json` |
| `Space` | Toggle `enabled` de la instancia seleccionada (persiste en `instances.json`) |
| `q` / `Esc` | Salir / cancelar modal |

**Durante la actualización de módulos:**

| Tecla | Acción |
|-------|--------|
| `1`-`4` | Toggle nivel de log (1=INFO, 2=WARNING, 3=ERROR, 4=CRITICAL) |
| `0` | Mostrar todos los niveles |
| `9` | Mostrar solo ERROR + CRITICAL |
| `Esc` | Cancelar la actualización en curso |

### Acciones soportadas

- **Lifecycle**: `build`, `start`, `stop`, `restart`, `list`
- **Acceso**: `bash`, `logs`, `psql` (suspenden la TUI y devuelven el control
  al terminar el comando interactivo)
- **Mantenimiento**: `fix-files`, `init`, `validate-instances`, `remove`
- **Módulos / DB**: `update` (admite `--load-language`), `pw` (reset de password)
- **Sync**: `sync` (submódulos git de un repo custom)
- **Scripts**: `backup`, `restore`, `test`, `precommit`, `active-users`,
  `migrate`, `update-manifest`

`start`/`stop`/`restart`/`logs`/`fix-files`/`init`/`remove` aceptan la
opción **"Todas las instancias"**; la TUI los itera por vos y evita que
tengas que tipear el flag ni enfrentar el prompt interactivo del CLI.

### Tests automatizados de la TUI

La TUI tiene una suite de tests de humo que verifica que los componentes
arrancan, los widgets se componen, y las features clave no se rompen:

```bash
# Todos los tests de la TUI (sin Docker, mockea subprocess)
python3 scripts/tui_smoke_test.py -v

# Validación del CSS (verifica que el archivo .tcss parsea correctamente)
python3 scripts/tui_check_css.py
```

El package `tui/` está estructurado por capas:

| Ruta | Contenido |
|------|-----------|
| `tui/app.py` | `DockerOdooApp` — lógica principal, bindings, dispatch |
| `tui/models.py` | `Action`, constantes, tipos |
| `tui/actions.py` | Constructores de comandos (`_odoo_cli_args`, `_script_args`) |
| `tui/parser.py` | Parseo de progreso `(N/M)` y clasificación de niveles de log |
| `tui/screens/` | Modales: `InputModal`, `ConfirmModal`, `ModulePicker` |
| `tui/widgets/` | Componentes: `UpdateProgress`, `InstanceItem`, `ActionItem` |
| `tui/styles/odoo-tui.tcss` | Estilos en Textual CSS |

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

## Perfiles de PostgreSQL

El campo `config` de cada `database` apunta a uno de los **perfiles de tuning** en `.resources/dbconfigs/postgresql.*.conf`. Los perfiles son agnósticos a la versión de Odoo: capturan la **carga esperada** (cantidad de instancias que comparten la DB), no la versión del motor.

### Los 4 perfiles

| Perfil | Archivo | `shared_buffers` | `max_connections` | `max_worker_processes` | Target |
|--------|---------|------------------|-------------------|------------------------|--------|
| **small** | `postgresql.small.conf` | 1GB | 60 | 2 | 1-3 instancias Odoo |
| **medium** | `postgresql.medium.conf` | 2GB | 100 | 4 | 4-10 instancias Odoo |
| **large** | `postgresql.large.conf` | 4GB | 200 | 8 | 11-20 instancias Odoo |
| **xlarge** | `postgresql.xlarge.conf` | 8GB | 300 | 16 | 20+ instancias Odoo |

Hardware sugerido por perfil:

| Perfil | RAM física | CPU | Storage |
|--------|-----------|-----|---------|
| small | 4GB | 2 | SSD |
| medium | 8GB | 4 | SSD |
| large | 16GB | 8 | SSD |
| xlarge | 32GB+ | 16+ | NVMe SSD |

### ¿Cómo elijo perfil?

El factor decisivo es **cuántas instancias Odoo comparten la misma DB** apuntando a esa `database`. No cuántas instancias tenés en total.

```
¿Cuántas instancias apuntan a esta database?
│
├── 1-3   → small
├── 4-10  → medium
├── 11-20 → large
└── 20+   → xlarge
```

**Ejemplo:** tenés 31 instancias totales pero agrupadas así:
- `v17` con 23 instancias → xlarge (es una sola DB compartida)
- `v18` con 3 instancias → small
- `v19` con 3 instancias → small
- `v16` con 2 instancias → small

### Escalar un perfil

Cuando una `database` crece (ej: le sumás 3 instancias más a `v18` y pasa de 3 a 6 instancias), **solo cambiás el campo `config` en `instances.json`** — no tocás archivos de tuning:

```diff
   "databases": {
     "v18": {
       "postgres_version": 17,
       "port": 5432,
       "user": "odoo",
       "password": "odoo",
-      "config": "postgresql.small.conf"
+      "config": "postgresql.medium.conf"
     }
   }
```

Después corré `./odoo build` para regenerar el compose con el nuevo `command` que monta el perfil.

### ¿Por qué perfiles y no por versión de Odoo?

La versión de Odoo determina `postgres_version` (compatibilidad del motor). El perfil determina tuning de RAM/CPU/concurrencia. Son **ejes ortogonales**:

- Odoo 17 y Odoo 19 con la misma carga → mismo perfil
- Odoo 17 con 5 instancias y Odoo 17 con 20 instancias → perfiles distintos

Si los perfiles fueran por versión, cambiar de `small` a `medium` implicaría renombrar archivos o duplicar configs por versión. Con perfiles, un cambio se hace en un solo campo.

### Tuning fino

Los perfiles son valores por defecto razonables. Si necesitás ajustar (ej: subir `work_mem` para reports pesados), **editá el archivo del perfil correspondiente** en `.resources/dbconfigs/`. Los cambios aplican a todas las DBs que usen ese perfil.

> ⚠️ No dupliques archivos de perfil para "tunear una sola DB". Si una DB tiene necesidades únicas, considerá:
> - Crear un perfil nuevo (ej: `postgresql.xlarge_igtf.conf` para la DB que corre IGTF pesado)
> - O migrar esa DB a su propio contenedor con un perfil dedicado

## Compatibilidad PostgreSQL

Para restaurar backups, la versión del contenedor debe ser igual o superior a la versión con que se generó el dump. Ajusta `postgres_version` en la sección `databases` según necesites.

### Versiones soportadas por Odoo

| Odoo | PostgreSQL mínimo | Recomendado |
|------|-------------------|-------------|
| 16.0 | 14 | 15 |
| 17.0 | 15 | 16 |
| 18.0 | 16 | 17 |
| 19.0 | 17 | 18 |

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

**¿Qué perfil de PostgreSQL uso para mi DB?**
Depende de cuántas instancias apuntan a esa `database`, no de la versión de Odoo. Ver [Perfiles de PostgreSQL](#perfiles-de-postgresql). Regla rápida: 1-3 → `small`, 4-10 → `medium`, 11-20 → `large`, 20+ → `xlarge`.
