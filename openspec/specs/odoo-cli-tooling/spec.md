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
