# Agente de docker-odoo

API HTTP (FastAPI) que corre en el host y es **lo único** que toca `instances.json`, `git` y Docker. El módulo `micro_saas` gestiona las instancias llamando a esta API con un token. Así ningún contenedor Odoo necesita montar el repo ni `docker.sock`.

Forma parte de `docker-odoo` (vive en `.resources/docker-odoo-agent`) y gestiona el checkout que lo contiene. No corre nada hasta instalarlo.

## Instalación

Desde la raíz de `docker-odoo`:

```bash
./odoo agent install --check                  # diagnóstico, sin cambios
./odoo agent install --token-name general-18  # instala o actualiza
./odoo agent                                  # lo activa o lo desactiva
./odoo agent status
```

`./odoo agent install` ejecuta `install.sh` de esta carpeta con los mismos flags. Funciona en Linux (servicio systemd) y en macOS (LaunchAgent de launchd).

## Configuración

`install.sh` guarda la configuración en `var/agent.env` (ignorado por git):

| Variable | Qué es | Por defecto |
|---|---|---|
| `DOCKER_ODOO_ROOT` | Checkout de docker-odoo que gestiona el agente | el que contiene esta carpeta |
| `AGENT_PORT` | Puerto de la API | `9000` |
| `AGENT_HOST` | Interfaz de escucha | `0.0.0.0` |
| `AGENT_TOKENS_FILE` | Hashes de los tokens | `var/agent_tokens.json` |
| `AGENT_AUDIT_LOG` | Log de auditoría | `var/agent_audit.log` |
| `AGENT_MAX_FAILED_ATTEMPTS` / `AGENT_BLOCK_SECONDS` | Bloqueo por tokens inválidos | `10` / `900` |

Las variables de entorno tienen prioridad sobre `var/agent.env`.

Guía completa (host, Odoo, migración desde el esquema de montajes, acceso remoto y problemas frecuentes): **[INSTALL.md](INSTALL.md)**.

## Tokens

```bash
./odoo agent token create general-18              # lectura y escritura
./odoo agent token create monitor --read-only     # solo GET
./odoo agent token list
./odoo agent token revoke general-18
```

- El token (`doa_<id>_<secreto>`) se muestra **una sola vez** al crearlo. En disco solo se guarda su hash SHA-256, en `var/agent_tokens.json` (permisos `0600`, ignorado por git).
- Las órdenes se ejecutan desde la raíz de `docker-odoo`.
- Pégalo en Odoo: **Gestión de instancias > Ajustes**, campos *Agent URL* (`http://host.docker.internal:9000`) y *Agent Token*. Pulsa *Test connection*.
- Revocar un token corta el acceso de inmediato, sin reiniciar el servicio.

## Seguridad

| Capa | Qué hace |
|---|---|
| Token Bearer | Obligatorio en todo menos `/health`. Comparación en tiempo constante. |
| Scopes | `read` para GET y `write` para todo lo demás. |
| Bloqueo por fallos | Tras `AGENT_MAX_FAILED_ATTEMPTS` (10) tokens inválidos, la IP queda bloqueada `AGENT_BLOCK_SECONDS` (900 s). |
| Auditoría | Cada llamada, aceptada o rechazada, queda en `var/agent_audit.log` con IP, token y ruta. |
| Validación | Slugs, ramas, módulos, bases y rutas de addons se validan con listas blancas. Los comandos se ejecutan sin shell. |
| Claves protegidas | Desde la API solo se pueden cambiar `odoo_version`, `external_port`, `database`, `odoo_config`, `domain`, `workers`, `without_demo`, `addons` (solo `src/...`) y `db_filter`. `extra_volumes` y el resto se preservan y solo se editan a mano. |
| Secretos | `GET /instances` oculta las contraseñas. Los tokens de GitHub se eliminan de la salida y no quedan guardados en `.git/config`. |

El agente acepta conexiones desde cualquier origen (entornos locales o remotos): el control de acceso es el token. Si se usa fuera del propio host, publícalo detrás de HTTPS (por ejemplo, un server block de nginx con certificado), porque por HTTP plano el token viaja legible por la red.

## Rol de Postgres por instancia

Desde docker-odoo con roles dedicados, cuando varias instancias comparten un servicio de Postgres y tienen cron activo (`max_cron_threads` distinto de 0; el valor por defecto de Odoo es 1), cada una necesita un `db_filter` específico y un rol propio (`db_user`/`db_password` en la raíz de su entrada). Odoo no aplica `dbfilter` al cron: sin rol propio, el cron de una instancia puede procesar las bases de otra. Sin cron (`max_cron_threads: 0`) no se exige nada.

En `PUT /instances/{slug}`:

- `db_user` ausente o `null` conserva el rol actual; `""` lo quita (vuelve al usuario del servicio, solo válido sin cron o sin servicio compartido).
- Sin `db_password`, el agente genera una al crear o cambiar el rol y la guarda en `instances.json`; nunca se devuelve (`***`).
- Por seguridad (el CLI los mete en SQL y en el compose sin comillas): `db_user` en `[a-z0-9_]` empezando por letra o `_`; `db_password` de 12 a 128 caracteres en `[A-Za-z0-9_.-]`; `db_filter` sin comillas simples.

Flujo para una instancia nueva o que pasa a tener rol: `PUT` → `POST /instances/{slug}/provision-role` (si `needs_provision`) → `start`. `provision-role` sirve también cuando ya hay bases creadas: les pasa la propiedad al rol.

Si quien llama tiene su propia base en ese mismo servicio de Postgres (micro_saas en general-18), debe pedir `provision-role` con `"background": true`: el agente valida, responde al momento con `job_id` y hace el trabajo en segundo plano. Con la llamada síncrona, el reinicio de Postgres le corta la conexión a quien espera la respuesta. El resultado se consulta con `GET /jobs/{job_id}`.

Las bases que la instancia crea **después** de aprovisionar (gestor de bases de Odoo, restore desde la UI) nacen con `CONNECT` abierto a `PUBLIC`. `POST /restrict-connect` (`./odoo restrict-connect [instancia]`) lo cierra con el propio rol de cada instancia, que es dueño de esas bases, así que no reinicia nada. Solo toca bases del rol que cumplen su `db_filter`. `./odoo build` lo aplica también a lo que su auditoría marca como `connect_open`. micro_saas lo llama con un cron.

## Endpoints

| Método | Ruta | Scope | Hace |
|---|---|---|---|
| GET | `/health` | — | Comprueba que el servicio está vivo |
| GET | `/whoami` | read | Nombre y scopes del token |
| GET | `/instances` | read | `instances.json` sin secretos, más las claves de `odoo_configs` y `databases` |
| GET | `/instances/status` | read | Estado de cada contenedor `odoo-<slug>` |
| PUT | `/instances/{slug}` | write | Crea o actualiza la entrada (merge y la misma validación que `./odoo build`). Acepta `max_cron_threads`, `db_user` y `db_password` (ver "Rol de Postgres por instancia"). Devuelve `needs_provision` cuando cambió el rol, su contraseña o el `db_filter` |
| POST | `/instances/{slug}/provision-role` | write | `./odoo provision-role <slug>`: crea el rol si no existe, le da la propiedad de las bases que cumplen `db_filter` y cierra `CONNECT` a `PUBLIC`. **Reinicia el contenedor `db-<servicio>`** (todas sus instancias pierden la conexión un momento). Con `recreate` (por defecto) regenera configs y recrea `odoo-<slug>` si está corriendo, para que use su rol. Con `background` responde `{job_id}` al momento (ver `/jobs`); `delay` (0-60 s) retrasa el inicio del trabajo para que quien llama confirme su transacción antes del reinicio. Uno a la vez (409) |
| GET | `/jobs/{job_id}` | read | Estado de un trabajo en segundo plano: `status` (`running`, `done`, `failed`) y, al terminar, `result` con la misma forma que la respuesta síncrona. Solo en memoria: si el agente se reinicia, 404 |
| POST | `/restrict-connect` | write | `./odoo restrict-connect [instance]`: cierra `CONNECT` de `PUBLIC` en las bases que un rol ya posee y cumplen su `db_filter` (sin `instance`, en todas las instancias). No reinicia nada |
| DELETE | `/instances/{slug}` | write | Borra el contenedor y la entrada, regenera compose y nginx. Si tenía rol propio, guarda sus credenciales en `var/removed_instance_roles.json` (600) para la purga |
| POST | `/build` | write | `./odoo build` (uno a la vez; si hay otro en curso, 409) |
| POST | `/instances/{slug}/start` · `stop` · `restart` | write | Opera solo sobre `odoo-<slug>`; `start` también sincroniza nginx |
| POST | `/instances/{slug}/modules/update` | write | `odoo -u <módulos> -d <base>` |
| GET | `/instances/{slug}/repos` | read | Repos de la instancia: la propia carpeta `src/custom/<slug>/` si es un repo (`dir: "."`), subcarpetas y submódulos. Incluye rama, commit y módulos; las URLs salen sin credenciales |
| POST | `/instances/{slug}/purge` | write | Borra lo que deja una instancia ya eliminada: las bases de `database` cuyo nombre cumple `db_filter` (debe empezar por `^`), sus volúmenes (`<slug>-web` con el filestore, `-data`, `-py3`, `-py`) y `src/custom/<slug>/`. Se niega si el slug sigue en `instances.json` y conserva las bases que también cumplan el `db_filter` de otra instancia. Si la instancia tenía rol propio, borra las bases con ese rol (su dueño); el rol queda en Postgres porque `DROP ROLE` requiere superusuario |
| POST | `/instances/{slug}/repos` | write | `git clone --recurse-submodules -b <branch>` en `src/custom/<slug>/<dir>` (crea la carpeta de la instancia si no existe). Con `token`, el repo y sus submódulos van por HTTPS con el token, sin guardarlo en `.git/config`. Si la carpeta ya existe no clona y avisa con `branch_mismatch` si está en otra rama |
| POST | `/instances/{slug}/repos/pull` | write | Lleva el repo `dir` a lo último de `branch`: `fetch`, cambio de rama y `merge --ff-only` (nunca crea merges; si diverge o hay cambios locales que estorban, no toca nada). Devuelve `changed_modules`. Opcional: `update_submodules` |
| POST | `/repos/pull` | write | Igual que el anterior, pero el repo se indica con `path` relativo a la raíz de docker-odoo (p. ej. `/src/custom/bp-staging`). Debe quedar dentro de `src/`; se rechazan `..` y symlinks que salgan de ahí |
| GET | `/databases/{key}` | read | Bases reales en ese servidor Postgres |

Las operaciones que ejecutan comandos responden `{"ok", "returncode", "command", "output"}`.
