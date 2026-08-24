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

El template con valores por defecto y comentarios inline vive en
`instances.example.jsonc` — copialo a `instances.json` y editá según
tus necesidades. El archivo tiene 3 secciones principales:

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
      "expose_host_port": false,
      "user": "odoo",
      "password": "odoo",
      "bootstrap_user": "odoo_bootstrap",
      "bootstrap_password": "cambiar-esto",
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

Las bases de datos gestionadas (`create_container: true`) **no publican su puerto al host por defecto**: los contenedores Odoo se conectan directamente a `db-<nombre>:5432` a través de la red interna de Docker (`odoo-multi`), sin pasar por el host. Esto evita que un Postgres corriendo localmente en la máquina (Homebrew, Postgres.app, etc.) sobre el mismo puerto termine interceptando las conexiones.

Si necesitas conectarte a la base de datos desde el host (por ejemplo con un cliente de escritorio), agrega `"expose_host_port": true` para que se publique `port` en `docker-compose.generated.yml`. Para uso normal (`./odoo psql`, `./odoo bash`, backups, restores, pgAdmin) no hace falta: todos corren dentro de los contenedores y usan la red interna.

#### `user`/`password` vs `bootstrap_user`/`bootstrap_password`

Cada base de datos gestionada tiene dos identidades de Postgres:

- **`user`/`password`**: el rol que **Odoo usa para todo**. No es superusuario (tiene `LOGIN` y `CREATEDB`, nada más), aunque sí puede crear/alterar/borrar tablas de módulos vía herencia de privilegios del rol bootstrap. Es el único que debería usarse desde `./odoo psql`, backups, restores, etc.
- **`bootstrap_user`/`bootstrap_password`**: el rol que Postgres crea automáticamente al inicializar el volumen (`initdb`). Postgres nunca permite quitarle el atributo de superusuario a este rol específico ni reasignarle la propiedad de sus objetos — es una restricción del motor, no de configuración. Por eso no se usa directamente: en un volumen nuevo, el rol de `user` se crea aparte (no-superusuario) heredando los privilegios del bootstrap vía `GRANT`, y el bootstrap queda con `NOLOGIN` — existe porque es dueño de los objetos, pero nadie puede autenticarse con él.

Ambos campos son opcionales: si se omiten, se usa el mismo valor de `user`/`password` para el bootstrap (comportamiento anterior a este esquema, con el rol de Odoo siendo superusuario — no recomendado, pero sigue funcionando para no romper configs existentes).

Existe una **tercera** identidad opcional, a nivel de instancia (no de `databases`): `db_user`/`db_password`, para cuando varias instancias comparten un mismo servicio de Postgres. Ver "Instancias que comparten un mismo servicio de Postgres" más abajo.

### `instances` — Instancias de Odoo

Cada instancia define su versión de Odoo, puerto externo, base de datos y configuración. Puede sobreescribir valores del `odoo_config` base usando `overwrite_odoo_config`. El flag opcional `"enabled"` (default `true`) controla si la instancia aparece en `./odoo build/start/stop/...` y en la TUI; podés togglerlo desde la TUI con `Space` y el cambio se persiste en `instances.json`.

El flag opcional `"production"` (default `false`) marca una instancia como productiva. Hoy lo único que hace es **bloquear duro `./odoo remove`** contra esa instancia (y contra `./odoo remove` sin argumento, si *alguna* instancia de la config es productiva) — no hay confirmación que lo salve ni override por flag: para borrarla de verdad hay que sacar `"production": true` a mano en `instances.json` primero. Pensado para hosts on-premise donde conviven una instancia de prueba y una de producción en el mismo Docker.

El flag `"dev_mode"` (default `false`, dentro de `overwrite_odoo_config` o del `odoo_config` base, igual que `workers`/`without_demo`) agrega `--dev=all` al comando de arranque de Odoo (autoreload de código/assets — útil en desarrollo). **No se puede combinar con `"production": true`**: `instances.json` se rechaza al cargar (`ValueError`) si una instancia productiva tiene `dev_mode` activo — en producción corresponde `./odoo update`, no dev mode.

```json
{
  "instances": {
    "bananera": {
      "odoo_version": "19.0",
      "external_port": 8070,
      "database": "pg16",
      "odoo_config": "19.0_default",
      "production": true,
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
        "addons": ["src/enterprise", "src/custom/client-b"],
        "dev_mode": true
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

La validación también exige que `db_user` sea **realmente distinto** entre instancias del mismo grupo, y distinto del rol de servicio compartido (`databases.<nombre>.user`) — si dos instancias apuntan al mismo `db_user` (por ejemplo, copiando una instancia y olvidando cambiarlo), Postgres ve un solo rol dueño de la unión de bases de ambas, y el aislamiento no existe aunque cada una tenga su `db_filter` "propio". Este chequeo aplica siempre, incluso si una de las dos tiene `max_cron_threads: 0` — el problema es de identidad de rol, no de cron.

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

Todos los comandos que aceptan `[instance]` operan sobre todas las instancias si no se especifica nombre. El subcomando `tui` (ver [TUI interactiva](#tui-interactiva-odoo-tui--odoo-tui)) es un entry point alternativo a `./odoo-tui`.

El script `./odoo` es un shim liviano (331 LOC) que delega a `odoo_cli/core/`, el package que implementa la lógica. Las acciones viven en `odoo_cli/core/actions/` y se invocan vía `odoo_cli/core/dispatch.py`, que mapea `argparse` a acción. El contrato de I/O con el usuario está abstraído en `odoo_cli.core.runner.Runner` (un `typing.Protocol` con `info`/`warn`/`confirm`/`run_streamed`), lo que permite testear las acciones con un `FakeRunner` y deja la puerta abierta a un futuro `TextualRunner` que reutilice las mismas acciones desde la TUI.

| Ruta | Responsabilidad |
|------|-----------------|
| `odoo_cli/core/runner.py` | `Runner` Protocol — superficie de I/O de las acciones |
| `odoo_cli/core/cli_runner.py` | `CliRunner` — implementación real con `print`/`input`/`subprocess` |
| `odoo_cli/core/dispatch.py` | Mapea `argparse` a funciones de `actions/`; maneja el caso especial `tui` |
| `odoo_cli/core/instance.py` | Helpers: `get_instance_services`, `get_db_services`, `get_users`, `get_databases`, `get_custom_repos`, `get_custom_modules` |
| `odoo_cli/core/prompts.py` | Prompts interactivos (`prompt_selection`, `prompt_for_instance`, etc.) |
| `odoo_cli/core/actions/validate.py` | `validate_instances` |
| `odoo_cli/core/actions/lifecycle.py` | `build_odoo`, `start_odoo`, `stop_odoo`, `restart_odoo`, `remove_odoo` |
| `odoo_cli/core/actions/access.py` | `run_bash`, `show_logs`, `list_containers`, `psql_connect`, `fix_filestore` |
| `odoo_cli/core/actions/modules.py` | `update`, `reset_password`, `bash_update_modules` |
| `odoo_cli/core/actions/maintenance.py` | `init_addons`, `sync`, `update_tags`, `update_tags_bulk`, `submodule_status` |
| `odoo_cli/core/actions/hosts.py` | `hosts_status`, `hosts_apply`, `hosts_show` |

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
| `pw <instance> [-d <db>] [-l <login>] [-p <password>]` | Restablece la contraseña de un usuario. |
| `update <instance> [-d <db\|all>] [-m modules] [-f]` | Actualiza módulos de Odoo (una base o todas). Sin `-m`, actualiza todos los módulos usando `click-odoo-update` (solo los que cambiaron desde la última actualización); con `-f`/`--force` fuerza un upgrade completo de todos, sin importar qué cambió. Un módulo puntual (`-m modulo`) siempre se actualiza directo, sin pasar por ninguno de los dos caminos anteriores. |
| `init [instance]` | Verifica que los addons referenciados existen. |
| `new [nombre] [repo] [branch] [version]` | Wizard: clona el repo del cliente y da de alta la instancia en `instances.json`. |
| `sync <repo> <branch> [--v]` | Sincroniza submódulos de un repositorio custom. |
| `test <instance> <module[,module2,...]> [opciones]` | Ejecuta tests con cobertura (uno o varios módulos, opcionalmente su árbol de dependencias con `--recursive`). Ver `./odoo test -h`. |
| `update-tags [proyecto] [branch_origin] [submodulo] [tag] [--v]` | Bumpea uno o más submódulos a un tag específico, en una rama nueva para PR. Todo argumento faltante se pregunta interactivamente (proyecto, rama base, submódulo, tag — con menú de tags filtrable, ej: `19, alpha`). Push y `gh pr create` se ofrecen al final, cada uno con su propia confirmación. |
| `update-tags-bulk [odoo_version] [submodulo] [tag] [--branch-origin BRANCH] [--projects p1,p2,...] [--v]` | Bumpea uno o más submódulos (mismo loop "¿otro submódulo?" que `update-tags`) en varios proyectos de la misma versión de Odoo a la vez (todas las instancias de `instances.json`, estén `enabled` o no). Los bumps se resuelven una sola vez contra un proyecto de referencia; antes de tocar cualquier otro proyecto se muestra el plan completo y se pide confirmarlo; push/PR/merge se confirman también una sola vez para todo el lote. Cada proyecto termina con **una sola rama y un solo PR** con todos los bumps indicados, no uno por submódulo. Un proyecto sin alguno de los submódulos/tags pedidos se saltea ese bump puntual (o el proyecto entero si no le aplica ninguno) sin frenar al resto. |
| `submodule-status [proyecto]` | Muestra en qué tag/rama/hash está parado cada submódulo (y el repo del proyecto en sí) — de solo lectura, no toca git. Sin proyecto, corre sobre todos los de `src/custom/`. |
| `validate-instances` | Valida `instances.json` de forma explícita (ya corre implícitamente antes de cualquier comando). |
| `hosts [status\|show\|apply\|dry-run]` | Sincroniza `/etc/hosts` con los subdominios de las instances. Ver [Subdominios locales por instance](#subdominios-locales-por-instance). |
| `coverage-status [--json] [--pull] [--only-with-tests]` | Escaneo rápido (sin Docker) de qué clientes tienen módulos con `tests/`. |
| `coverage [proyecto...] [opciones]` | Corre `coverage.py` real (build scoped + start + coverage + stop + limpieza, automatizado) para uno, varios o todos los clientes con tests. |
| `provision-role <instance>` | Aprovisiona el rol de Postgres dedicado de una instancia: crea el rol si no existe, transfiere el ownership de toda base que matchee su `db_filter`, y revoca `CONNECT` de `PUBLIC` sobre ellas. Requiere `db_user`/`db_password` y un `db_filter` específico ya definidos en `instances.json`. Puede pedir una ventana breve de mantenimiento de todo el servicio de Postgres (pide confirmación antes). Ver "Instancias que comparten un mismo servicio de Postgres" arriba. |
| `tui` | Lanza la TUI interactiva (equivalente a `./odoo-tui`). |

Referencia detallada de cada comando (comportamiento interno, validaciones,
gotchas): [`docs/comandos-odoo.md`](docs/comandos-odoo.md).

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

# Ver en qué tag/rama/hash está parado cada submódulo de un proyecto
./odoo submodule-status bananera

# Lo mismo para todos los proyectos de src/custom/
./odoo submodule-status

# Bumpear un submódulo a un tag y preparar el PR (todo interactivo si se omite)
./odoo update-tags bananera

# Bumpear el mismo submódulo/tag en varios proyectos de la misma versión de una
# (todo interactivo: elige versión, proyectos, submódulo y tag)
./odoo update-tags-bulk

# Lo mismo, todo por flags: sin moverse de la rama en la que ya está cada proyecto
./odoo update-tags-bulk 17.0 odoo-venezuela l10nve_17.0.3.4.2 --projects contiflex,gno,syf

# Lo mismo, pero parando cada proyecto en 'staging' antes de ramificar
./odoo update-tags-bulk 17.0 odoo-venezuela l10nve_17.0.3.4.2 --branch-origin staging

# Aprovisionar el rol dedicado de una instancia (ver seccion de instances.json)
./odoo provision-role bananera
```

## Subdominios locales por instance

Cada instance puede accederse por un subdominio local (`<inst_name>.local`)
además del port externo. Esto aísla las cookies del browser por **host**
(subdominio) en vez de por port, lo que resuelve el problema de CSRF que
ocurre cuando varias instances se sirven desde el mismo `localhost`.

### Cómo funciona

En el build, `.resources/generators/nginx_generator.py` emite un server
block por instance con dos directivas `listen` y un `server_name`
compuesto:

```nginx
server {
    listen 8072 default_server;
    listen 80;
    server_name contiflex.local localhost;
    location / { proxy_pass http://odoo-contiflex:8069; }
}
```

Resultado: las 3 URLs siguientes llevan a la misma instance, pero con
orígenes distintos para el browser:

- `http://contiflex.local` (subdominio, port 80)
- `http://contiflex.local:8072` (subdominio + port legacy)
- `http://localhost:8072` (compat con scripts antiguos)

Opcionales también: `pgadmin.local` (si `pgadmin.enabled=true`) y
`mailhog.local` (si `mailhog.enabled=true`).

### Setup del `/etc/hosts`

`/etc/hosts` requiere root, así que **no se automatiza en el build**.
Tres formas de tenerlo al día:

1. **TUI**: abrí la TUI y si los hosts están desincronizados, el log
   muestra un warning amarillo con el comando. También hay una action
   **Sync /etc/hosts** en la categoría Mantenimiento que muestra el
   diff y el comando a correr.

2. **CLI**:
   ```bash
   ./odoo hosts status     # muestra el diff
   ./odoo hosts show       # lista los subdominios esperados
   sudo ./odoo hosts apply # aplica (requiere root)
   ```

3. **Manual**:
   ```bash
   sudo python3 scripts/odoo_hosts
   ```
   El script es idempotente: usa un sentinel `# odoo-managed` para
   reemplazar solo su propio bloque, sin tocar las demás entradas.

### Notas operativas

- El setup es **dinámico**: activá/desactivá instances en
  `instances.json`, corré `./odoo build` y volvé a aplicar hosts.
  Entradas huérfanas se eliminan en la próxima corrida.
- Si no querés usar subdominios, no corras `sudo ./odoo hosts apply`.
  El acceso por `localhost:PORT` sigue funcionando indefinidamente
  (dual-stack). Solo perdés el aislamiento de cookies.
- **Devices embedded** (scanners, balanzas, impresoras Zebra) que
  apuntan a `http://SERVER_IP:PORT` siguen funcionando porque nginx
  escucha en ambos: el port externo y el 80.

## TUI interactiva: `./odoo-tui` / `./odoo tui`

Una interfaz de terminal (Textual) que envuelve `./odoo` y los scripts de
`scripts/`. **No reemplaza el CLI**: `./odoo <comando>` sigue funcionando
exactamente igual que antes. La TUI es una capa aditiva que arma los
comandos por vos y muestra el output en pantalla.

```bash
# Dependencia: textual (>= 0.50). Instalar con:
pip install --user textual

# Lanzar la TUI (modo normal) — dos entry points equivalentes:
./odoo-tui
# o bien, via el CLI unificado:
./odoo tui

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
| `c` | Copiar las últimas 500 líneas del output al portapapeles |
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
- **Sync**: `sync` (submódulos git de un repo custom), `update-tags` (bump
  interactivo de submódulo a un tag en una rama nueva — suspende la TUI y
  te da la terminal real, porque necesita su loop de confirmaciones),
  `submodule-status` (de solo lectura, corre streameado como cualquier
  acción normal)
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

### Performance y cancelación

La TUI está diseñada para no colgarse durante operaciones largas
(instalación de muchos módulos, logs con mucho output, etc.):

- **Streaming asíncrono**: `tui/runner.py` usa `asyncio.create_subprocess_exec`
  + `readline()` en lugar de `subprocess.Popen(bufsize=1, PIPE)` con
  iteración bloqueante. `Popen` con PIPE cae en block-buffering de
  Python (4-8 KB) y Odoo no flushea seguido, lo que se manifestaba
  como TUI congelado durante operaciones largas.
- **Cancel con timeout**: durante un `update` podés presionar `Esc`;
  el runner manda `SIGTERM` y, si el proceso no termina en 5s, escala
  a `SIGKILL`.
- **Widgets cacheados**: las queries a `self.query_one(...)` sobre
  widgets accedidos cada línea se cachean para evitar el overhead de
  atravesar el DOM de Textual en cada iteración.
- **Thread safety**: `_save_instances_json` (persistencia del toggle
  `enabled` con `Space`) está protegido, y los workers ya no tocan el
  DOM directamente — todo va por `call_from_thread` o eventos del loop.

Hay un test de regresión específico para el bug de streaming en
`scripts/tui_smoke_test.py:TuiStreamingRegressionTest.test_streaming_with_slow_output_does_not_hang`.

### Arquitectura del TUI

El `app.py` original (906 LOC) se partió en cuatro módulos para que
cada uno sea legible y testeable en isolation:

| Ruta | Contenido |
|------|-----------|
| `tui/app.py` | `DockerOdooApp` — composición, ciclo de vida, eventos de la app (558 LOC) |
| `tui/dispatch.py` | `DispatchMixin` — mapea acciones a comandos y orquesta modales (553 LOC) |
| `tui/runner.py` | Runner async (`stream_command`) — streamea stdout sin bloquear el event loop (218 LOC) |
| `tui/keybindings.py` | Handlers de atajos (`r`, `Space`, `Esc`, `Tab`, `1`-`4`, etc.) (306 LOC) |
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

## Tooling relacionado

- El **MCP server** (antes en `mcp-server/` de este repo) vive ahora en
  `ai-tools/skills-ai/mcp-server/` y se auto-descubre cuando se corre
  desde un clone de docker-odoo. Ver su README.
