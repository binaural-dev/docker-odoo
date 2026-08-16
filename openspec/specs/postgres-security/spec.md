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
