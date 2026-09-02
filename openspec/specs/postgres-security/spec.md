# postgres-security

Capability que describe cómo debe estar aislado y protegido cada clúster
Postgres gestionado por `instances.json`, a partir de la remediación del
incidente XMRig (2026-08-15).

## ADDED Requirements

### Requirement: El rol que usa Odoo para conectarse NUNCA debe ser superusuario

Cada servicio de base de datos (`databases.<nombre>` en `instances.json`) DEBE
tener un rol de aplicación (`user`/`password`) con `rolsuper = false`. Odoo, y
cualquier herramienta que use las credenciales de `instances.json`, se conecta
exclusivamente con este rol.

#### Scenario: Verificar que el rol de app no es superusuario
- **WHEN** se consulta `SELECT rolsuper FROM pg_roles WHERE rolname = '<user>'`
  usando el `user` configurado para un servicio en `instances.json`
- **THEN** el resultado debe ser `false`

#### Scenario: `COPY ... FROM/TO PROGRAM` debe estar bloqueado para el rol de app
- **WHEN** el rol de app ejecuta `COPY (SELECT 1) TO PROGRAM 'echo test'`
- **THEN** Postgres debe rechazarlo con `permission denied to COPY to or from an
  external program`

### Requirement: El rol bootstrap del clúster no debe ser usable para autenticarse

El rol que Postgres crea automáticamente al inicializar cada clúster (`initdb`,
siempre superusuario por restricción del motor) DEBE tener `NOLOGIN` una vez que
el rol de aplicación existe y ha heredado sus privilegios de owner.

#### Scenario: El rol bootstrap no puede autenticarse
- **WHEN** se intenta conectar con las credenciales del `bootstrap_user`
  configurado para un servicio
- **THEN** Postgres debe rechazar la conexión con
  `FATAL: role "<bootstrap_user>" is not permitted to log in`

### Requirement: El rol de app debe poder operar sobre los objetos existentes sin ser dueño directo

El rol de aplicación DEBE tener privilegios equivalentes a los de owner (vía
membresía heredada del rol bootstrap) sobre todas las bases y objetos que
gestiona, para que las migraciones de módulos de Odoo (`ALTER TABLE`, `CREATE
INDEX`, `DROP TABLE`, etc.) sigan funcionando sin necesitar superusuario.

#### Scenario: DDL sobre una tabla propiedad del bootstrap
- **GIVEN** una tabla creada y propiedad del rol bootstrap
- **WHEN** el rol de app ejecuta `ALTER TABLE` o `DROP TABLE` sobre ella
- **THEN** la operación debe completarse sin error de permisos

#### Scenario: Creación de bases de datos nuevas
- **WHEN** el rol de app ejecuta `CREATE DATABASE`
- **THEN** la operación debe completarse sin error de permisos (requiere
  `CREATEDB` en el rol de app)

### Requirement: Los puertos de Postgres no deben publicarse al host por defecto

Ningún servicio de base de datos gestionado debe exponer su puerto al host (ni,
por extensión, a internet) salvo que se configure explícitamente.

#### Scenario: Generación del compose sin exposición
- **GIVEN** un servicio de base de datos en `instances.json` sin
  `expose_host_port: true`
- **WHEN** se genera `docker-compose.generated.yml`
- **THEN** el servicio `db-<nombre>` no debe tener bloque `ports:`

#### Scenario: Exposición explícita opt-in
- **GIVEN** un servicio de base de datos con `expose_host_port: true`
- **WHEN** se genera `docker-compose.generated.yml`
- **THEN** el servicio SÍ debe tener `ports: ["<port>:5432"]`

### Requirement: Un volumen de datos nuevo debe nacer con el mismo esquema de dos roles

Cualquier volumen Postgres creado desde cero (primer arranque, `initdb`) DEBE
terminar con el rol de aplicación creado, con privilegios heredados del
bootstrap, y el bootstrap en `NOLOGIN` — sin intervención manual.

#### Scenario: Primer arranque de un volumen nuevo
- **GIVEN** un contenedor Postgres construido desde `db.Dockerfile` con
  `APP_DB_USER`/`APP_DB_PASSWORD` definidos y un volumen de datos vacío
- **WHEN** el contenedor arranca por primera vez
- **THEN** al finalizar la inicialización debe existir el rol `APP_DB_USER`
  (`LOGIN CREATEDB`, no superusuario), debe ser miembro del rol bootstrap
  (`POSTGRES_USER`), y el rol bootstrap debe quedar en `NOLOGIN`

### Requirement: Instancias que comparten un servicio de Postgres deben tener rol y filtro propios cuando corren cron

El cron interno de Odoo (`ir.cron`) no consulta `dbfilter` — solo rige el
ruteo HTTP. Cuando más de una instancia comparte un mismo `database` en
`instances.json`, cada instancia con `max_cron_threads != 0` DEBE tener un
`db_filter` específico (no vacío, no `"*"`, sin placeholders `%h`/`%d`) Y
credenciales propias (`db_user`/`db_password`, a nivel raíz de la
instancia) de un rol de Postgres dedicado, dueño únicamente de las bases
que matchean su `db_filter`.

#### Scenario: Validación bloquea instancias sin aislar
- **GIVEN** dos o más instancias con el mismo `database` y al menos una
  con `max_cron_threads != 0`
- **WHEN** a alguna le falta `db_filter` específico o `db_user`/`db_password`
- **THEN** `load_config()` DEBE fallar con un error detallado listando las
  instancias afectadas y qué les falta

#### Scenario: Escape hatch explícito
- **GIVEN** una instancia en un grupo compartido con `max_cron_threads: 0`
  en `overwrite_odoo_config`
- **THEN** esa instancia NO debe requerir `db_filter` específico ni
  `db_user`/`db_password` propios

### Requirement: El rol dedicado de cada instancia debe ser realmente único

Dentro de un grupo de instancias que comparten `database`, el `db_user` de
cada una DEBE ser distinto al de cualquier otra instancia del mismo grupo,
y distinto al rol de servicio compartido (`databases.<nombre>.user`). Un
`db_user` repetido no aísla nada — Postgres ve un único rol, dueño de la
unión de las bases de ambas instancias. Este chequeo aplica
independientemente del escape hatch de `max_cron_threads: 0`, porque la
colisión de identidad de rol es un problema estructural, no ligado al cron.

#### Scenario: `db_user` repetido entre dos instancias del grupo
- **GIVEN** dos instancias del mismo grupo con el mismo valor de `db_user`
- **WHEN** se corre `load_config()`
- **THEN** DEBE fallar con un error listando el `db_user` repetido y las
  instancias que lo comparten

#### Scenario: `db_user` igual al rol de servicio compartido
- **GIVEN** una instancia de un grupo compartido cuyo `db_user` coincide
  con `databases.<nombre>.user`
- **WHEN** se corre `load_config()`
- **THEN** DEBE fallar, porque esa instancia no tiene en realidad un rol
  dedicado — sigue usando el mismo rol que las instancias sin credenciales
  propias

### Requirement: El rol dedicado de una instancia debe ser el único con `CONNECT` sobre sus bases

Además de ser el `datdba` (dueño) de cada base que le corresponde según su
`db_filter`, el rol dedicado de una instancia DEBE ser el único rol con
privilegio `CONNECT` sobre esas bases — `PUBLIC` no debe conservarlo.

#### Scenario: `CONNECT` revocado tras aprovisionar
- **GIVEN** una base migrada con `./odoo provision-role <instance>`
- **WHEN** se consulta `has_database_privilege('public', '<db>', 'CONNECT')`
- **THEN** el resultado debe ser `false`

#### Scenario: Aprovisionamiento nunca usa `REASSIGN OWNED`
- **WHEN** se transfiere el ownership de una base a un rol dedicado
- **THEN** DEBE usarse `ALTER DATABASE "<db>" OWNER TO <rol>` (preciso, sin
  efectos de lado en otras bases del clúster) — nunca `REASSIGN OWNED`,
  que reasigna objetos compartidos cluster-wide (`pg_database.datdba` de
  bases no relacionadas) al ejecutarse conectado a una sola base

### Requirement: El drift entre `db_filter` y el ownership real debe auditarse en cada build

Como editar `db_filter` en `instances.json` no re-dispara automáticamente
ningún cambio de ownership/ACL en Postgres, cada `./odoo build` DEBE
correr una auditoría de solo lectura que compare, por cada servicio
compartido por más de una instancia, el `db_filter` resuelto contra el
estado real, y avisar (sin bloquear el build) cuando:
- una base matchea el `db_filter` de una instancia pero pertenece a otro rol,
- una base del rol correcto todavía tiene `CONNECT` abierto a `PUBLIC`,
- una base dejó de matchear el `db_filter` de la instancia que la posee,
- una base matchea el `db_filter` de más de una instancia a la vez.

#### Scenario: Estado alineado
- **GIVEN** todas las instancias de un servicio compartido con ownership y
  `CONNECT` consistentes con su `db_filter` actual
- **WHEN** se corre `./odoo build`
- **THEN** la auditoría debe reportar "sin diferencias" y el build debe
  continuar

#### Scenario: Drift detectado no bloquea el build
- **GIVEN** una base cuyo ownership real no coincide con el `db_filter`
  vigente de su instancia
- **WHEN** se corre `./odoo build`
- **THEN** la auditoría debe imprimir el aviso correspondiente, y el build
  de igual forma debe completarse

### Requirement: Solo el drift sin ambigüedad puede ofrecerse para corrección automática

De los 4 tipos de drift que detecta la auditoría, únicamente "dueño
incorrecto" y "`CONNECT` sin revocar" DEBEN ofrecerse para corrección
automática vía `provision-role` — porque aplicar `provision-role` con el
`db_filter` vigente siempre produce el resultado correcto en esos dos
casos. "Filtro que ya no matchea" y "filtros solapados" NUNCA deben
ofrecerse para autocorrección, porque requieren una decisión humana
(¿la base cambia de dueño a propósito?, ¿cuál de los regex solapados está
mal escrito?) antes de tocar ownership.

#### Scenario: `./odoo build` ofrece corregir solo lo no ambiguo
- **GIVEN** una auditoría con hallazgos de "dueño incorrecto" y de
  "filtros solapados" a la vez
- **WHEN** termina de imprimir los avisos
- **THEN** DEBE preguntar si corregir automáticamente solo la(s)
  instancia(s) del hallazgo de "dueño incorrecto", nunca las involucradas
  en el solapamiento

#### Scenario: Corrección automática agrupa por servicio de Postgres
- **GIVEN** dos o más instancias con drift corregible que comparten el
  mismo servicio de Postgres
- **WHEN** se confirma la corrección automática
- **THEN** DEBE aplicarse una sola ventana de break-glass para ese
  servicio (no una por instancia), igual que una migración manual agrupada

#### Scenario: Uso no interactivo no debe bloquearse ni corregir sin confirmación
- **GIVEN** `./odoo build` corriendo sin entrada de teclado disponible
  (automatización/CI) o con `--no-confirm`
- **WHEN** la auditoría encuentra drift corregible
- **THEN** el build DEBE completarse sin lanzar ninguna corrección
  automática y sin fallar por falta de entrada interactiva
