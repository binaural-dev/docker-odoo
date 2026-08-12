# Referencia: comandos de `./odoo`

> Generado a partir del código real (`odoo`, `odoo_cli/core/dispatch.py`,
> `odoo_cli/core/actions/*.py`) — no de una copia del `--help`, que puede
> quedar desactualizada. Complementa a la tabla resumida del
> [`readme.md`](../readme.md#comandos-disponibles-odoo), que **no incluye
> `pw`, `new` ni `validate-instances`**.

Todo comando corre `os.chdir(BASE_PATH)` primero (la raíz del repo, sin
importar desde dónde lo invoques) y carga + valida `instances.json` antes de
ejecutar cualquier acción — si el archivo no existe o tiene puertos
duplicados/DBs inexistentes, falla ahí mismo con un mensaje claro, antes de
tocar Docker.

## Tabla rápida

| Comando | Instancia | Qué hace |
|---|---|---|
| `build [--no-cache]` | — | Genera `docker-compose.generated.yml`, Dockerfile(s) y config de nginx; construye imágenes |
| `start [instancia]` | opcional* | Levanta DB(s) managed, instancia(s) Odoo y nginx |
| `stop [instancia]` | opcional* | Detiene instancia(s); apaga su DB solo si nadie más la usa |
| `restart [instancia]` | opcional* | `stop` + `start` |
| `bash [instancia]` | opcional* | Shell root dentro del contenedor Odoo |
| `logs [instancia]` | opcional* | `docker compose logs -f`, tail 10, streaming |
| `list` | — | `docker compose ps` |
| `remove [instancia]` | opcional* | Borra contenedores + **volúmenes** (pide confirmación) |
| `fix-files [instancia]` | opcional* | `chown -R odoo:odoo` sobre el filestore |
| `psql [instancia] [-d db]` | opcional* | Conecta a psql dentro del contenedor Odoo |
| `pw [instancia] [-d db] [-l login] [-p pass]` | opcional* | Resetea contraseña de un usuario |
| `update [instancia] [-d db\|all] [-m mods]` | opcional* | `odoo -u <mods> -d <db> --stop-after-init` |
| `init [instancia]` | opcional | Reporta qué `addons` faltan en disco (no clona) |
| `new [nombre] [repo] [branch] [version]` | — | Wizard: clona repo del cliente + registra la instancia |
| `sync [repo] [branch]` | — | Sincroniza submódulos de un repo en `src/custom/` |
| `update-tags [proyecto] [branch] [submódulo] [tag]` | — | Bump de un submódulo a un tag, en rama nueva para PR |
| `submodule-status [proyecto] [--ref r1,r2]` | — | Solo lectura: tag/rama/hash de cada submódulo |
| `validate-instances` | — | Valida `instances.json` (ya corrió implícitamente antes de cualquier comando) |
| `hosts [status\|show\|apply\|dry-run]` | — | Sincroniza `/etc/hosts` con los subdominios `.local` |
| `tui` | — | Lanza la TUI (Textual), equivalente a `./odoo-tui` |

\* *"opcional"* = sin instancia, la acción se pregunta interactivamente
(menú con flechas) **o** se aplica a todas, según el comando — ver detalle
abajo de cada uno.

---

## Lifecycle

### `build [--no-cache]`

Regenera **todo** el runtime a partir de `instances.json`:

1. `Dockerfile` por cada versión de Odoo única en uso (`.resources/generators/dockerfile_generator.py`)
2. `docker-compose.generated.yml` (`compose_generator.py`)
3. Config de nginx (`nginx_generator.py`) — un `server` block por instancia
4. `docker compose build` (o `build --no-cache`)

Corré `build` cada vez que agregás/quitás una instancia, cambiás puertos, o
tocás el `Dockerfile.template`. Instancias con la misma `odoo_version`
comparten imagen: un cambio al template las afecta a todas.

### `start [instancia]`

Sin instancia: levanta **todas** las habilitadas (`enabled: true`). Con
instancia: solo esa.

Orden interno: valida colisión de puertos con otro proyecto Docker en el
host → levanta DB(s) managed → levanta contenedor(es) Odoo → `chown`
filestore → **fuerza recreate de nginx** (`rm -f` + `up -d`), porque nginx
solo lee su config al arrancar y el bind-mount pudo haber cambiado en el
último `build`. Al final imprime la URL `http://localhost:<puerto>` de cada
instancia levantada.

### `stop [instancia]`

Sin instancia: `docker compose down` (todo). Con instancia: para solo esa
instancia, y **apaga su DB únicamente si ninguna otra instancia habilitada
la usa** — si la comparte con otra, te avisa cuál y la deja corriendo.

### `restart [instancia]`

Es literalmente `stop_odoo` seguido de `start_odoo` sobre el mismo target.

### `remove [instancia]`

**Destructivo** — borra contenedores y volúmenes (datos + filestore). Pide
confirmación explícita (default `No`), y al terminar pregunta si querés
levantar el entorno de nuevo en blanco (default `Sí`). Sin instancia,
apunta a "TODAS las instancias y bases de datos".

**Bloqueado para producción**: si la instancia objetivo tiene
`"production": true` en `instances.json`, el comando se rechaza directo
(exit code 1) — ni siquiera se llega a mostrar la confirmación. Lo mismo
pasa con `remove` sin argumento si *cualquier* instancia de la config está
marcada como producción, ya que borraría todo por igual. No hay flag ni
confirmación que lo salve: la única forma de desbloquearlo es editar
`instances.json` a mano y sacar el flag.

### `fix-files [instancia]`

`chown -R odoo:odoo /home/odoo/data` dentro del/los contenedor(es). Útil
cuando un restore o una operación desde el host deja el filestore con
permisos de root.

### `list`

`docker compose ps` sin más. No filtra por instancia.

---

## Acceso

### `bash [instancia]`

Antes de abrir el shell, verifica que el servicio esté en la lista de
`docker compose ps --status running` — si no está corriendo, te dice
`./odoo start <instancia>` en vez de fallar con un error críptico de Docker.
Usa `docker compose exec` (por nombre de *servicio*), no `docker exec` por
nombre de contenedor — el nombre real del contenedor está namespaced por el
proyecto de Compose, ya no es necesariamente `odoo-<instancia>`.

### `logs [instancia]`

Con instancia: logs de su Odoo **y** su DB juntos. Sin instancia: logs de
todo el compose. Siempre `--tail=10 -f` (streaming, no dump completo).

### `psql [instancia] [-d db]`

Sin `-d`, te pregunta la base (con menú si hay más de una). Corre `psql`
**dentro** del contenedor Odoo (no necesitás el cliente de Postgres en tu
host), conectando a `db-<nombre>:5432` por la red interna.

---

## Módulos y datos

### `update [instancia] [-d db|all] [-m módulos]`

Corre `odoo --stop-after-init --workers=0 -u <módulos> -d <db>` dentro del
contenedor.

- `-d all`: itera **todas** las bases de la instancia, acumula fallas por
  base y termina con exit code 1 si alguna falló (te dice cuáles).
- Sin `-m`: te pregunta módulos (o usá `all` para actualizar todo).
- No pisa el puerto 8069 real: usa `--http-port 9999` mientras corre el
  update, para no chocar con la instancia si sigue arriba.

### `pw [instancia] [-d db] [-l login] [-p password]`

Antes de tocar nada, valida en este orden:

1. **La DB existe** en el contenedor (si no, lista las disponibles y sale).
2. **El login existe exacto** (case-sensitive, como Odoo). Si no existe
   exacto pero sí case-insensitive, sugiere `¿Quisiste decir 'ADMIN'?` en
   vez de fallar a ciegas.
3. Corre el `UPDATE` y **verifica que afectó una fila** — `psql` devuelve
   exit 0 aunque el `UPDATE` afecte 0 filas, así que un chequeo ingenuo del
   returncode mentiría diciendo "✅ actualizada" sin haber hecho nada.

Por diseño, **nunca lista todos los logins** en un error (expondría
emails/usuarios reales del cliente) — solo sugiere el case-corregido o te
da el comando `psql` para que investigues vos mismo.

Si pasás `-d <db>` sin instancia, y esa DB solo existe en una instancia, la
resuelve sola; si existe en varias, te pregunta cuál.

---

## Alta de instancias y addons

### `new [nombre] [repo] [branch] [version]`

Wizard (delega a `scripts/create_instance.py`) que automatiza dar de alta
un cliente nuevo:

1. Exige URL **SSH** del repo (rechaza `http(s)://` — para que el clonado
   funcione con tus llaves, no con login interactivo).
2. Clona a `src/custom/<nombre>` e inicializa submódulos recursivamente.
3. Pregunta el puerto externo, sugiriendo el próximo libre; rechaza
   puertos ya usados.
4. Elige `odoo_config`: busca `<version>_full`, si no existe cae a
   `default`.
5. Arma la lista de `addons` automáticamente: detecta
   `src/enterprise_v<major>` (o `src/enterprise` si no existe esa
   variante), agrega `src/custom/<nombre>`, detecta una carpeta
   `client_addons/` dentro del repo, y lee `.gitmodules` para sumar cada
   submódulo como addon path.
6. Escribe la entrada nueva directamente en `instances.json`.

Después de `new`, el siguiente paso siempre es `./odoo build && ./odoo start <nombre>`.

### `init [instancia]`

**Solo reporta** — no clona nada (a diferencia del `./odoo init` de
`master`, que sí clonaba repos según `ENV_TYPE`). Para cada addon
declarado en la instancia, dice si el path existe en disco o falta. Si
falta, te toca clonarlo a mano o correr `./odoo sync`.

---

## Submódulos y sync

### `sync [repo] [branch] [--v]`

Sincroniza los submódulos de un repo ya clonado en `src/custom/`:
`stash` → `checkout <branch>` → `pull` → `submodule update --init
--recursive`. Sin argumentos, pregunta repo y rama interactivamente.
`--v` muestra la salida cruda de git (por defecto se resume).

### `update-tags [proyecto] [branch_origin] [submódulo] [tag] [--v]`

Bumpea un submódulo a un tag específico, en una rama nueva pensada para
abrir PR. Todo argumento faltante se pregunta:

- **proyecto**: se busca en `src/custom/`.
- **submódulo**: se detecta leyendo `.gitmodules`.
- **tag**: menú filtrable — podés tipear `19, alpha` para filtrar por
  ambos términos a la vez (AND, no OR).
- Nombra la rama nueva como `bump/<branch_origin>/<submodulo>-<tag>...`
  (capado a 3 bumps + `+N-mas` si son muchos), anidada bajo la rama base
  para no confundir bumps de `17.0` con bumps de `18.0`.
- Al final ofrece `git push` y `gh pr create`, cada uno con su propia
  confirmación — nunca automático.

### `submodule-status [proyecto] [--ref rama1,rama2]`

**Read-only**, no hace `checkout` ni `pull`. Sin `--ref`, muestra lo que
está físicamente checkeado ahora (tag exacto vía `git describe`, si no
hay tag exacto la rama, si no hay rama el hash corto marcado `(detached)`).
Con `--ref`, lee el puntero del submódulo directo del árbol de git para
esa(s) rama(s) sin tocar el working tree — útil para comparar qué tag
tiene `release` vs `staging` sin moverte de tu branch actual.

---

## Configuración y red

### `validate-instances`

Valida `instances.json` explícitamente. En la práctica es redundante en
uso normal — **cualquier** comando de `./odoo` ya corre esta validación
antes de ejecutar nada — pero sirve como chequeo rápido standalone (ej.
en un pre-commit o CI) sin disparar ninguna acción de Docker.

### `hosts [status|show|apply|dry-run]`

Sincroniza `/etc/hosts` con los subdominios `<instancia>.local` de las
instancias habilitadas (+ `pgadmin.local` / `mailhog.local` si están
activos).

- `status` (default): diff entre lo esperado y lo que hay, sin tocar nada.
- `show`: lista los subdominios que *deberían* estar.
- `apply`: escribe el bloque gestionado (sentinel `# odoo-managed`) —
  **requiere root**; si no corrés como root, te imprime el comando exacto
  con `sudo` en vez de fallar.
- `dry-run`: como `apply` pero sin escribir.

---

## TUI

### `tui`

Lanza la interfaz Textual (equivalente a `./odoo-tui`). Hoy es un proceso
separado que invoca `./odoo <acción>` como subprocess por cada acción que
disparás desde la TUI — no comparte el runtime de Python con el CLI
todavía (ver nota "Textual integration" en el propio código de `./odoo`
sobre el futuro `TextualRunner`). Ver [`tui/README.md`](../tui/README.md)
para atajos de teclado y detalle de la interfaz.

---

## Lo que NO es `./odoo`

Backup, restore, tests, coverage, precommit, migración de módulos y bump
de versión de manifest son **scripts independientes** en `scripts/`, no
subcomandos de `./odoo` — cada uno toma el nombre de instancia como primer
argumento y resuelve el resto desde `instances.json`. Referencia completa
en [`scripts/README.md`](../scripts/README.md).
