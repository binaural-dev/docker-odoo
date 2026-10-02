---
name: docker-odoo-add-instance
description: Agrega una instancia nueva de Odoo a instances.json en este repo (docker-odoo), incluyendo el aislamiento de Postgres obligatorio (db_user/db_password/db_filter dedicados) cuando la instancia comparte servicio de Postgres con otras, y el provisionamiento real del rol via "./odoo provision-role". Usar cuando el usuario pida agregar/crear/montar una instancia nueva en este repo docker-odoo (ej. "agrega la instancia induvar", "monta un proyecto nuevo para el cliente X").
---

# Skill: docker-odoo-add-instance

## Contexto -- por qué esto no es solo "agregar un bloque JSON"

Este repo exige que, si una instancia comparte servicio de Postgres (`database`)
con otra(s), tenga un rol de Postgres **dedicado** (`db_user`/`db_password`)
y un `db_filter` específico. Si falta cualquiera de los dos, `load_config()`
revienta de entrada y **ningún** comando `./odoo` corre -- ni siquiera `build`.

Por qué existe esta regla (no es paranoia): el cron interno de Odoo (`ir.cron`)
**nunca** respeta `db_filter` -- eso es puramente ruteo HTTP. Si varias
instancias comparten un servicio de Postgres con el mismo usuario, el cron de
una puede procesar datos de la base de OTRA. Ya pasó en producción una vez
(`integra-maintenance-comercial-19.0.1` -> `integra-maintenance-19.0.1`). La
protección real es un rol de Postgres por instancia, dueño solo de sus
propias bases (`list_dbs()` de Odoo filtra por `datdba = current_user`).

Detalle completo: `readme.md`, sección "Instancias que comparten un mismo
servicio de Postgres" y `openspec/changes/2026-08-17-per-instance-postgres-roles-cron-isolation/`.

**Importante:** `./odoo build` sola **no** crea el rol en Postgres. Solo
genera config y, si ya existe una base con dueño incorrecto, *ofrece*
corregirlo. Para una instancia nueva (sin bases todavía) hay que correr
`./odoo provision-role <instancia>` a mano -- sin eso el contenedor arranca
pero no se puede conectar.

## Qué preguntar antes de tocar nada

Si el usuario no lo especificó ya en el pedido, preguntar:

1. **Nombre de la instancia** (clave en `instances.json`, ej. `induvar`).
2. **Versión de Odoo** (`16.0`/`17.0`/`19.0`/`20.0`/...).
3. **¿Comparte servicio de Postgres con otras instancias, o necesita uno propio?**
   - Si comparte: ¿cuál `database` (normalmente `pg16`)?
   - Si necesita uno propio: hay que agregar un bloque nuevo en `databases`
     (ver "Instancia con Postgres propio" más abajo) -- en ese caso **nada**
     de lo de aislamiento (`db_user`/`db_filter` obligatorio) aplica, porque
     la validación solo se activa si `len(instancias del mismo database) > 1`.
4. **Addons**: enterprise de la versión correspondiente
   (`src/enterprise-16`/`src/enterprise-17`/`src/enterprise-19`/`src/enterprise-20.0`)
   + repos custom bajo `src/custom/<nombre>/` (preguntar cuáles: propio del
   cliente, `integra-addons`, `third-party-addons`, `odoo-venezuela`,
   `server-tools`, `client_addons` -- varía por proyecto).
5. **¿Va a recibir un restore de un dump existente, o arranca de cero?**

No preguntar por puerto externo, password, ni memoria -- se resuelven solos
(ver pasos 1 y 2).

**Importante -- esta skill NO clona repositorios.** Solo decide qué rutas
van en la lista `addons` del JSON según lo que el usuario diga que necesita
el proyecto. Que esas carpetas existan de verdad en `src/custom/<nombre>/...`
(el repo del cliente, `integra-addons`, `third-party-addons`, etc.) es
responsabilidad manual del usuario -- ni esta skill ni `./odoo init` clonan
nada, `init` solo informa qué falta (ver paso 3.5).

## Paso a paso

Ejecutar siempre desde la raíz del repo (`BASE_PATH`, donde vive `./odoo`).

### 1. Elegir puerto externo libre

```bash
python3 -c "
import json
c = json.load(open('instances.json'))
print(sorted(conf['external_port'] for conf in c['instances'].values()))
"
```

Elegir cualquier puerto no usado, siguiendo el rango de la zona del repo
donde conceptualmente encaje (no hay convención estricta, solo que no choque).

### 2. Generar password dedicado

**Nunca** uses una password con comillas o backslashes -- `provision_role_sql()`
la mete cruda en una sentencia SQL (`PASSWORD '{db_password}'`); una comilla
rompe el SQL.

```bash
python3 -c "
import secrets, string
alphabet = string.ascii_letters + string.digits
print(''.join(secrets.choice(alphabet) for _ in range(28)))
"
```

### 3. Agregar el bloque a `instances.json`

Si comparte servicio de Postgres (caso normal, ej. `pg16`):

```json
"induvar": {
  "odoo_version": "17.0",
  "external_port": 7060,
  "database": "pg16",
  "odoo_config": "default",
  "db_user": "app_induvar",
  "db_password": "<password generado en el paso 2>",
  "overwrite_odoo_config": {
    "addons": [
      "src/enterprise-17",
      "src/custom/induvar",
      "src/custom/induvar/integra-addons",
      "src/custom/induvar/third-party-addons"
    ],
    "db_filter": "^induvar_",
    "limit_memory_soft": 2500000000,
    "limit_memory_hard": 3000000000,
    "mem_limit": "3.5g"
  }
}
```

Reglas duras para `db_user`/`db_filter` (la validación de `config_loader.py`
las exige, y NO avisa de forma amigable si fallan -- corta la ejecución con
un error en bloque):

- `db_user`: distinto a cualquier otro `db_user` de instancias que compartan
  el mismo `database`, y distinto del `user` del servicio compartido
  (`databases.<nombre>.user`). Convención: `app_<nombre_instancia>`.
- `db_filter`: específico, nunca vacío ni `*`, sin `%h`/`%d`. Además **no
  debe solapar** con el `db_filter` de ninguna otra instancia del mismo
  `database` -- antes de fijarlo, revisar los filtros existentes:
  ```bash
  python3 -c "
  import json
  c = json.load(open('instances.json'))
  for name, conf in c['instances'].items():
      if conf['database'] == 'pg16':  # ajustar al database elegido
          print(name, conf.get('overwrite_odoo_config', {}).get('db_filter'))
  "
  ```
  Un prefijo único tipo `^<nombre>_` casi siempre alcanza.
- Memoria: igualar el patrón que ya usan las demás instancias del repo
  (`limit_memory_soft: 2500000000`, `limit_memory_hard: 3000000000`,
  `mem_limit: "3.5g"`) salvo que el usuario pida algo distinto -- con menos
  de esto, instancias con Enterprise + varios addons custom entran en
  crash-loop por quedarse sin memoria interna de Odoo (vivido en este repo
  con `bodegonactual`/`dicosmo_17`, que se quedaron en el default genérico
  de 1GB/1.5GB y no booteaban).

#### Instancia con Postgres propio (sin compartir)

Si el usuario pidió un servicio de Postgres dedicado, agregar también un
bloque nuevo en `databases` (ver otros servicios ya definidos como plantilla)
y usar ese nombre en `"database"`. En este caso **no hace falta**
`db_user`/`db_password` ni un `db_filter` especial -- la validación de
aislamiento no se activa porque no hay otra instancia compartiendo ese
servicio.

### 4. Validar antes de tocar Docker

```bash
python3 -c "import json; json.load(open('instances.json')); print('JSON valido')"
python3 -c "
import sys, os
sys.path.insert(0, os.path.join('.', '.resources'))
from generators.config_loader import load_config
config = load_config('.')
print('OK: carga sin errores.')
"
```

Si esto falla, el mensaje de error ya dice exactamente qué instancia y qué
requisito falta -- no adivinar, leerlo.

### 4.5. Verificar que los addons existan en disco (no bloquea el build)

```bash
./odoo init induvar
```

Esto solo **informa** qué carpetas de `addons` faltan en `src/` -- no clona
nada. **No es un bloqueante para seguir** -- `build` genera la imagen base
(SO + Odoo + Enterprise) sin tocar `src/custom/` para nada (se monta como
volumen en runtime, no se copia en la imagen), y el entrypoint
(`.resources/entrypoint.d/400-auto-detect-addons`) si no encuentra una ruta
de `addons` solo tira un warning y sigue -- el contenedor arranca igual, nada
más sin ese módulo disponible para instalar. Avisar al usuario qué falta,
pero se puede seguir con `build`/`provision-role`/`start` sin esperar a que
clone nada; el custom hace falta recién cuando quiera instalar/usar ese
módulo (y ahí sí, después de clonarlo, hace falta `./odoo restart <instancia>`
para que el entrypoint vuelva a detectar el path).

### 5. Build

```bash
./odoo build
```

Si el servicio de Postgres ya tenía otras instancias, al final corre la
auditoría -- para una instancia nueva sin bases todavía no debería reportar
nada sobre ella.

### 6. Provisionar el rol dedicado (si comparte Postgres)

Paso obligatorio que `build` no hace solo:

```bash
./odoo provision-role induvar
```

Va a pedir confirmación y puede requerir un breve break-glass de **todo**
el servicio de Postgres (para de verdad en reinicia ese contenedor -- avisar
al usuario si hay otras instancias corriendo sobre el mismo servicio ahora
mismo, porque van a tener un corte breve de conexión). Con 0 bases
matcheando el filtro todavía, solo crea el rol vacío -- es el comportamiento
esperado, no un error.

### 7. Levantar la instancia y crear/restaurar su base

- **Desde cero:** `./odoo start induvar`, después crear la base desde
  `/web/database/manager` con un nombre que matchee el `db_filter`
  (ej. `induvar_prod` si el filtro es `^induvar_`). Como el contenedor ya
  se conecta con el rol dedicado (que tiene `CREATEDB`), Postgres lo hace
  dueño automáticamente -- sin pasos extra.
- **Restaurando un dump:** `./odoo restore induvar -z <zip> -d induvar_prod`.
  Después, volver a correr `./odoo build` -- si el restore dejó la base con
  otro dueño, la auditoría lo va a detectar y ofrece corregirlo con
  `provision-role` ahí mismo.

### 8. Verificar

```bash
curl -s -o /dev/null -w "%{http_code}\n" --max-time 5 "http://localhost:<external_port>/web/login"
```

`303` o `200` es señal de vida normal. Si da `000`, dar un momento más (el
primer boot con Enterprise + varios addons puede tardar) antes de asumir que
algo falló.

## Errores comunes a evitar (aprendidos en este repo)

- **No reusar `db_user` ni `db_filter` de otra instancia** por copiar/pegar
  un bloque existente y olvidar cambiarlos -- la validación lo bloquea todo,
  no solo la instancia nueva.
- **No olvidar la memoria** -- el default genérico (`odoo_config: "default"`)
  trae límites muy bajos (1GB/1.5GB) pensados como piso, no como lo que
  necesita una instancia real con Enterprise + custom.
- **Si la instancia YA tenía datos y se le agrega `db_user`/`db_password`
  después** (no es el caso de una instancia nueva, pero puede pasar al
  migrar una existente): agregar las credenciales + correr `provision-role`
  **no alcanza solo** -- hay que recrear su contenedor
  (`docker compose -f docker-compose.generated.yml up -d --no-deps odoo-<instancia>`)
  para que tome las credenciales nuevas, si no se queda usando las viejas en
  memoria hasta el próximo restart.
- **Password con comillas/backslash** rompe el SQL de `provision-role` --
  generarla siempre alfanumérica (ver paso 2).
