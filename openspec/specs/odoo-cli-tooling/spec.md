# odoo-cli-tooling

Capability que describe el comportamiento esperado del script de gestión
`/home/docker-odoo/odoo`.

## ADDED Requirements

### Requirement: Las operaciones sobre "todas las bases" deben respetar el alcance de la instancia

Cuando se listan o iteran bases de datos para una instancia específica, el CLI
DEBE limitarse a las bases que pertenecen a esa instancia (según su
`db_filter` efectivo), no a todas las bases del servicio de Postgres
compartido.

#### Scenario: `-d all` en una instancia con `db_filter` específico
- **GIVEN** una instancia cuyo `db_filter` efectivo matchea solo un subconjunto
  de las bases del servicio de Postgres que usa
- **WHEN** se listan sus bases de datos (ej. `./odoo update -d all -i
  <instancia>`)
- **THEN** solo deben incluirse las bases que matchean ese `db_filter`, no las
  de otras instancias que comparten el mismo servicio

#### Scenario: Instancia sin `db_filter` específico
- **GIVEN** una instancia cuyo `db_filter` es `"*"` o no está definido
- **WHEN** se listan sus bases de datos
- **THEN** se listan todas las bases del servicio (comportamiento previo,
  sin romper nada existente) pero se imprime una advertencia explícita

### Requirement: Actualizar "todos los módulos" no debe forzar una elección interactiva

Si no se especifica un módulo puntual, el CLI DEBE proceder a actualizar
todos los módulos sin desplegar una lista de selección.

#### Scenario: `./odoo update` sin `-m`
- **WHEN** se ejecuta `update` sin pasar `-m`
- **THEN** el CLI actualiza todos los módulos directamente, sin prompt
  interactivo de selección

### Requirement: Actualizar "todos los módulos" debe ser incremental por defecto

Actualizar todos los módulos DEBE, por defecto, tocar solo los módulos cuyo
contenido cambió desde la última actualización, no reprocesar literalmente
todos los módulos instalados.

#### Scenario: Actualización sin forzar
- **WHEN** se actualiza el destino "todos los módulos" sin el flag de forzado
- **THEN** el CLI usa una herramienta de actualización incremental (basada en
  hash de contenido) en vez de forzar el upgrade de cada módulo instalado

#### Scenario: Actualización forzada
- **GIVEN** se pasa el flag de forzado (`-f`/`--force`)
- **WHEN** se actualiza el destino "todos los módulos"
- **THEN** se fuerza un upgrade completo de todos los módulos instalados,
  sin importar si cambiaron

#### Scenario: Actualización de un módulo específico
- **GIVEN** se pasa un módulo puntual (`-m <modulo>`)
- **WHEN** se ejecuta `update`
- **THEN** se actualiza exactamente ese módulo, sin pasar por la lógica de
  actualización incremental ni por el flag de forzado

### Requirement: Shell operativo de Odoo contra una instancia

El CLI DEBE exponer un subcomando `shell` que ejecute operaciones one-shot del
ORM (o abra un REPL interactivo) contra una instancia y base seleccionadas, sin
necesidad de entrar al contenedor ni escribir un script ad-hoc.

#### Scenario: `./odoo shell` sin instancia
- **GIVEN** no se pasa instancia
- **WHEN** se ejecuta `./odoo shell`
- **THEN** se elige la instancia interactivamente y se abre el REPL de esa
  instancia sobre la base elegida

#### Scenario: `search` con dominio, campos, límite y orden
- **WHEN** se ejecuta `./odoo shell <instancia> search -m <modelo> --domain "[[...]]" --fields "a,b" --limit N --order "campo asc"`
- **THEN** se devuelven los registros que matchean el dominio leyendo solo los
  campos pedidos, limitados y ordenados

#### Scenario: `method` sobre registros puntuales
- **GIVEN** se pasa `--ids`
- **WHEN** se ejecuta `./odoo shell <instancia> method -m <modelo> -n <metodo> --ids 10,1`
- **THEN** se llama `getattr(env[modelo].browse([10,1]), metodo)` (sin importar
  si el método es privado, `_prefijado`) y se imprime su resultado

#### Scenario: `method` sobre registros buscados
- **GIVEN** NO se pasa `--ids` pero sí `--limit N` y `--order`
- **WHEN** se ejecuta `./odoo shell <instancia> method -m <modelo> -n <metodo> --limit 10 --order "id asc"`
- **THEN** el método se ejecuta sobre los registros que matchean el dominio
  (por defecto todos, salvo `--limit`/`--order`)

#### Scenario: modificación de datos con rollback
- **GIVEN** se pasa `--no-commit`
- **WHEN** se ejecuta una operación que modifica (`create`/`write`/`unlink`)
- **THEN** el cambio se revierte al final (dry-run), sin persistir

#### Scenario: `unlink` requiere confirmación
- **WHEN** se ejecuta `unlink` sin `--yes`
- **THEN** se aborta con error, sin tocar datos

### Requirement: Generación reproducible del APK/AAB de la app (`./odoo apk`)

El CLI DEBE exponer un subcomando `apk` que genere el APK/AAB firmado de la
app de ventas (TWA vía Bubblewrap) corriendo el toolchain (Node, OpenJDK 17,
Android SDK) en un contenedor, sin instalar nada en el host salvo Docker. Los
valores de configuración (dominio, package, versión, keystore, etc.) se leen
de `pwa.json` en la raíz del repo, con precedencia flag CLI > env
`APK_STOREPASS` > `pwa.json` > default del script.

#### Scenario: build desde `pwa.json`
- **GIVEN** un `pwa.json` con `instance`, `domain`, `package`, `version`,
  `version_code` y `storepass`
- **WHEN** se ejecuta `./odoo apk`
- **THEN** se construye la imagen (si falta), se ejecuta la build adentro y
  quedan `app-release-signed.apk`, `app-release-bundle.aab` y
  `assetlinks.json` en `.ignore/apk-build/<instance>/` del host

#### Scenario: instancia local por HTTP (`--scheme http`)
- **GIVEN** `scheme: "http"` en `pwa.json` (o `--scheme http`)
- **WHEN** se genera el APK
- **THEN** el `launchUrl` horneado en el APK usa `http://host:puerto` (se
  parchea el `build.gradle` que Bubblewrap genera con `https://` en duro)

#### Scenario: instalación por USB
- **GIVEN** un dispositivo Android conectado por USB con depuración habilitada
- **WHEN** se ejecuta `./odoo apk usb-install`
- **THEN** se instala `adb` si falta (según macOS/Linux), se espera el
  dispositivo autorizado, se instala la APK con `adb install -r` y se abre la
  app; si no hay APK todavía, primero se genera

### Requirement: `./odoo test` reutiliza una base ya provisionada sin dejar de ejecutar tests

Cuando `-d`/`--db` apunta a una base que ya existe y el/los módulo(s) pedidos
ya están instalados ahí, el CLI DEBE forzar una actualización (`-u`) en vez de
una instalación (`-i`) al invocar Odoo, para que el código Python del módulo
se recargue y sus tests se redescubran. `-i` sobre un módulo ya instalado es
un no-op para Odoo: no falla, pero tampoco corre ni un solo test — silencio
indistinguible de "no había nada que probar".

#### Scenario: base nueva o módulo no instalado (comportamiento sin cambios)
- **GIVEN** `-d` no apunta a una base existente, o la base existe pero el
  módulo pedido no está instalado ahí
- **WHEN** se ejecuta `./odoo test`
- **THEN** se usa `-i` como hasta ahora (flujo normal: base descartable,
  instalación fresca)

#### Scenario: base existente con el módulo ya instalado
- **GIVEN** `-d <base>` apunta a una base que ya existe y TODOS los módulos
  pedidos figuran `state = 'installed'` en `ir_module_module` de esa base
- **WHEN** se ejecuta `./odoo test -i <instancia> -m <modulo> -d <base>
  --no-rm-db`
- **THEN** el CLI imprime que va a usar `-u` en su lugar, Odoo recarga el
  código del módulo y sus tests corren normalmente (visible en el resumen
  como `Tests ejecutados: N`, no `0`)

### Requirement: `./odoo test` / `scripts/odoo-test` aceptan un path o `all` en `-m`

`-m`/el posicional de `test` DEBE aceptar, por token separado por coma,
además de un nombre de módulo suelto: un path (dentro de los `--addons`
resueltos de la instancia) que expanda a todos los módulos que contenga, o
el literal `all` que expanda a todos los módulos escaneados en todos los
`--addons`.

#### Scenario: path exacto a un módulo
- **WHEN** se ejecuta `./odoo test <instancia> -m <path_a_un_modulo>`
  (path dentro de los addons de la instancia, host-relativo o absoluto
  dentro del repo)
- **THEN** el CLI lo traduce al path equivalente dentro del contenedor y
  se resuelve a exactamente ese módulo

#### Scenario: path a un directorio con varios módulos
- **WHEN** se ejecuta `./odoo test <instancia> -m <path_a_un_directorio>`
  y ese directorio (dentro de alguno de los `--addons` de la instancia,
  igual o anidado) contiene varios módulos (`__manifest__.py`)
- **THEN** se resuelve a la lista de TODOS esos módulos, y se testean
  juntos (o por separado, si además se pasa `--per-module-db`)

#### Scenario: path fuera de los `--addons`
- **WHEN** se ejecuta `./odoo test <instancia> -m <path>` y `<path>` no
  está dentro (igual o anidado) de ninguno de los `--addons` de la
  instancia
- **THEN** el CLI aborta con un error explícito, sin ejecutar nada

#### Scenario: `-m all`
- **WHEN** se ejecuta `./odoo test <instancia> -m all`
- **THEN** se resuelve a TODOS los módulos escaneados en TODOS los
  `--addons` de la instancia

### Requirement: `--per-module-db` corre cada módulo en su propia base de datos

`scripts/odoo-test` DEBE exponer un flag `--per-module-db` que, dada la
lista de módulos ya resuelta (de nombres sueltos, un path, o `all`), corra
cada módulo de forma independiente y secuencial: su propia base de datos
(autogenerada), su propia instalación, su propia corrida de tests y su
propia medición de cobertura — en vez de todos juntos en una sola base
(comportamiento por defecto sin este flag). No es compatible con
`-d`/`--db` explícito.

#### Scenario: varios módulos con `--per-module-db`
- **GIVEN** se pasan N módulos (por nombre, path, o `all`)
- **WHEN** se ejecuta con `--per-module-db`
- **THEN** se crean y destruyen N bases de datos independientes,
  secuencialmente, cada una con el veredicto de un solo módulo

#### Scenario: `--per-module-db` con `--recursive`
- **GIVEN** se pasan varios módulos con `--per-module-db --recursive`
- **WHEN** se calcula el árbol de dependencias
- **THEN** el árbol se calcula POR módulo semilla (no combinado): un
  módulo compartido entre varios de los indicados se instala y testea más
  de una vez, una por cada base independiente. Se muestran los N árboles
  juntos y se pide UNA sola confirmación antes de arrancar (salvo
  `--no-confirm`)

#### Scenario: `--per-module-db` junto con `-d`/`--db`
- **WHEN** se ejecuta con `--per-module-db` y `-d`/`--db` a la vez
- **THEN** el CLI aborta con un error explícito antes de tocar Docker/DB

### Requirement: Reportes JSON recortados y por-módulo con `--per-module-db`

Con `--per-module-db`, `--out-coverage-json`/`--out-logs` DEBEN escribir un
subarchivo por módulo (`<ruta>/<modulo>/coverage.json`,
`<ruta>/<modulo>/test_run.log`); `--out-json` DEBE exportar un único JSON
combinado, recortado, un módulo por key
(`{modulo: {at_install, post_install, totals, verdict: {passed}}}`); y el
flag `--out-summary-json` (solo válido junto con `--per-module-db`) DEBE
exportar un JSON ultra-resumido, un módulo por key
(`{modulo: {passed, coverage}}`).

#### Scenario: exportando los tres reportes con `--per-module-db`
- **WHEN** se ejecuta con `--per-module-db --out-coverage-json <dir1>
  --out-logs <dir2> --out-json <archivo> --out-summary-json <archivo2>`
- **THEN** `<dir1>`/`<dir2>` quedan con un subdirectorio por módulo
  (`coverage.json`/`test_run.log` dentro de cada uno), y `<archivo>`/
  `<archivo2>` quedan con un único JSON combinado cada uno, con todos los
  módulos como keys

#### Scenario: `--out-summary-json` sin `--per-module-db`
- **WHEN** se ejecuta `--out-summary-json <ruta>` sin `--per-module-db`
- **THEN** el CLI aborta con un error explícito, sin ejecutar nada

### Requirement: `./odoo psql --ps` conecta a cualquier base de un servicio, sin filtrar por instancia

`./odoo psql` DEBE aceptar un flag `--ps`/`--postgres` que, en vez de
filtrar por instancia/`db_filter`, deje elegir un servicio de Postgres
(`databases.<nombre>`) y cualquiera de sus bases reales. Si el rol
bootstrap del servicio está en `NOLOGIN` (estado normal tras
`provision-role`), el CLI DEBE romper ese `NOLOGIN` temporalmente
(break-glass) y volverlo a poner en `NOLOGIN` al salir, sin importar cómo
termine la sesión (éxito, error, o cancelación).

#### Scenario: `--ps` con el rol bootstrap en `NOLOGIN`
- **WHEN** se ejecuta `./odoo psql --ps`, se confirma la advertencia, y el
  rol bootstrap del servicio elegido está en `NOLOGIN`
- **THEN** el CLI aplica break-glass, deja elegir cualquier base real del
  servicio (no solo las de una instancia), abre psql interactivo, y al
  salir vuelve a dejar el rol bootstrap en `NOLOGIN`

#### Scenario: `--ps` sin confirmar
- **WHEN** se ejecuta `./odoo psql --ps` y se responde que no a la
  confirmación
- **THEN** el CLI cancela sin tocar el rol bootstrap ni Docker

### Requirement: `./odoo psql remove` elimina una base de datos con confirmación explícita

`./odoo psql` DEBE aceptar un subcomando `remove` (`./odoo psql remove
[instancia] [-d db] [--ps]`) que elimine (`DROP DATABASE`) una o más
bases, pidiendo siempre confirmación explícita antes de borrar. Sin
`--ps`, usa las credenciales normales de la instancia (sin necesitar el
rol bootstrap); con `--ps`, igual que `psql --ps`, elige entre cualquier
base de cualquier servicio vía break-glass.

#### Scenario: eliminar una base de una instancia
- **WHEN** se ejecuta `./odoo psql remove <instancia> -d <db>` y se
  confirma
- **THEN** la base se elimina con las credenciales de la instancia, sin
  tocar el rol bootstrap

#### Scenario: eliminar varias bases en una sola pasada
- **GIVEN** se seleccionan varias bases a eliminar
- **WHEN** se confirma
- **THEN** el CLI lista todas antes de pedir una única confirmación, y
  elimina cada una, reportando éxito/error por separado

#### Scenario: base con sesiones activas
- **WHEN** el `DROP DATABASE` falla porque la base tiene conexiones
  activas
- **THEN** el CLI ofrece terminarlas (`pg_terminate_backend`) y reintenta
  el borrado una vez, en vez de fallar directo

#### Scenario: eliminar sin confirmar
- **WHEN** se responde que no a la confirmación de borrado
- **THEN** el CLI cancela sin eliminar ninguna base

### Requirement: `./odoo restore` reenvía a `scripts/odoo_restore` sin duplicar flags

`./odoo restore ...` DEBE delegar tal cual (passthrough, antes de
argparse) en `scripts/odoo_restore restore ...`, sin reimplementar ni
duplicar sus flags — mismo patrón que `./odoo apk`.

#### Scenario: `./odoo restore` con los flags de `scripts/odoo_restore`
- **WHEN** se ejecuta `./odoo restore <instancia> -z <zip> -d <db>
  [flags de scripts/odoo_restore]`
- **THEN** el CLI invoca `scripts/odoo_restore restore` con exactamente
  esos argumentos, y el código de salida es el mismo que devuelve ese
  script

### Requirement: El restore otorga superuser temporal cuando el dump necesita crear extensiones no confiables

`scripts/odoo_restore` DEBE detectar, antes de ejecutar el `.sql` del
dump, si contiene sentencias `CREATE EXTENSION IF NOT EXISTS ...`. Si las
tiene, DEBE otorgar `SUPERUSER` temporal al rol de la instancia (vía el
rol bootstrap del servicio, rompiendo su `NOLOGIN` si hace falta) solo
durante la ejecución de ese `.sql`, revocándolo siempre al terminar (éxito
o error) y volviendo a bloquear el rol bootstrap si el break-glass se
rompió para esto. Sin extensiones no confiables en el dump, el
comportamiento DEBE ser idéntico al de antes de este cambio (el rol
bootstrap no se toca).

#### Scenario: dump con extensión no confiable
- **GIVEN** un dump `.sql` que incluye `CREATE EXTENSION IF NOT EXISTS
  vector`
- **WHEN** se ejecuta el restore
- **THEN** el rol de la instancia recibe `SUPERUSER` temporal antes de
  correr el `.sql`, lo pierde apenas termina (con o sin error), y si el
  rol bootstrap tuvo que romper `NOLOGIN` para esto, vuelve a quedar en
  `NOLOGIN`

#### Scenario: dump sin extensiones no confiables
- **WHEN** se ejecuta el restore de un dump que no contiene `CREATE
  EXTENSION IF NOT EXISTS`
- **THEN** el rol de la instancia nunca recibe `SUPERUSER`, y el rol
  bootstrap del servicio no se toca en absoluto

#### Scenario: servicio sin credenciales de bootstrap configuradas
- **GIVEN** el dump necesita `SUPERUSER` pero el servicio de Postgres no
  tiene `bootstrap_user`/`bootstrap_password` configurados
- **WHEN** se ejecuta el restore
- **THEN** el CLI aborta con un error explícito antes de tocar Docker
