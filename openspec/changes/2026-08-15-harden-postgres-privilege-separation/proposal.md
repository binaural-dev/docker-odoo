# Separar el rol de Postgres en bootstrap (superusuario) y app (sin privilegios)

**Estado: implementado y verificado (2026-08-15).** Este documento es retroactivo —
describe una remediación de incidente ya aplicada, no un cambio pendiente de
aprobación.

## Por qué

El 2026-08-15 se detectó un compromiso activo (minero de criptomonedas XMRig) en 4
bases de datos de producción/QA (`integra-17.0`, `integra-maintenance-17.0.1`,
`integra-l10nve_17.0`, `integra-maintenance-l10nve_17.0.1`, todas en el servicio
`pg16_odoo_17`). El atacante insertó `ir.actions.server` con código Python
disfrazado de "health monitor" que ejecutaba:

```python
env.cr.execute("COPY ... FROM PROGRAM '<comando de shell>'")
```

`COPY ... FROM/TO PROGRAM` es una función de Postgres que ejecuta comandos de shell
en el proceso del servidor. Solo funciona si el rol conectado es superusuario (o
tiene el privilegio `pg_execute_server_program`). El rol `odoo` que usaban **ambos**
servicios Postgres (`pg16` y `pg16_odoo_17`) era superusuario — permitiendo RCE
completo desde una simple sentencia SQL, sin necesitar ninguna vulnerabilidad de
Odoo en sí.

Cadena completa del ataque (ver también
`incident_xmrig_admin_compromise_2026-08.md` en la memoria del asistente):

1. Postgres estaba expuesto directo a internet (puertos `5502`/`5503` publicados a
   `0.0.0.0`) — vector de entrada original. Ya corregido antes de este cambio (el
   usuario ya había hecho `expose_host_port` opt-in en una rama previa).
2. Con acceso directo a Postgres (o vía RPC de Odoo), el atacante insertó
   `ir.act_server`/`ir.cron` maliciosos directamente por SQL — el campo
   `create_uid` mostraba "admin" solo porque es metadata escribible por SQL
   directo, no porque hubiera credenciales de admin de Odoo comprometidas
   necesariamente.
3. El payload descarga un binario XMRig desde un C2 externo y mina Monero,
   intentando además persistencia (cron, systemd, backdoor SSH) — neutralizado
   pero irrelevante para este cambio puntual, que se enfoca en cerrar el
   mecanismo de escalación (`COPY FROM PROGRAM`), no en el malware en sí.

Aun con el puerto cerrado, el rol seguía siendo superusuario — cualquier fuga de
credencial futura (o cualquier código Python ejecutado dentro de un
`ir.actions.server`, que Odoo permite a usuarios con permisos de administrador)
habría bastado para repetir el mismo ataque. Este cambio cierra esa vía de raíz.

## Qué cambia

- El rol que Postgres crea automáticamente al inicializar el clúster (`initdb`) ya
  no es el que usa Odoo. Postgres **no permite** quitarle `SUPERUSER` a ese rol
  específico (`ALTER ROLE ... NOSUPERUSER` → `ERROR: permission denied to alter
  role / The bootstrap user must have the SUPERUSER attribute`) ni reasignarle la
  propiedad de sus objetos (`REASSIGN OWNED BY ...` → `ERROR: cannot reassign
  ownership of objects owned by role ... because they are required by the
  database system`) — son restricciones duras del motor, no de configuración.
- En su lugar: se crea un **segundo rol, no-superusuario**, con `LOGIN CREATEDB`,
  que hereda los privilegios de owner del bootstrap vía
  `GRANT <bootstrap> TO <app>` — esto le da derechos de `ALTER`/`DROP` sobre las
  tablas ya existentes (necesario para que Odoo pueda seguir haciendo migraciones
  de módulos) **sin** heredar nunca el bit de superusuario, porque en Postgres eso
  jamás se hereda por membresía, solo por atributo propio del rol o por
  `SET ROLE`/`SET SESSION AUTHORIZATION` explícito — algo que Odoo no hace.
- El rol bootstrap queda en `NOLOGIN` — nadie puede autenticarse con él por ningún
  método, ya que no hace falta: sigue siendo dueño de los objetos, pero la
  membresía no requiere que el "padre" pueda loguearse.
- `instances.json` separa `user`/`password` (rol de app) de `bootstrap_user`/
  `bootstrap_password` (rol interno, opcional — con fallback a `user`/`password`
  si no se define, por compatibilidad con configs anteriores al esquema).
- `.resources/generators/compose_generator.py` emite `POSTGRES_USER`/
  `POSTGRES_PASSWORD` desde los campos `bootstrap_*`, y agrega `APP_DB_USER`/
  `APP_DB_PASSWORD` como nuevas variables de entorno del servicio de base de
  datos.
- `.resources/db_create_app_role.sh` (nuevo, corre como
  `docker-entrypoint-initdb.d/zz_create_app_role.sh`) reproduce este mismo
  esquema automáticamente en cualquier volumen creado desde cero — sin esto,
  cada volumen nuevo habría nacido con el mismo problema.
- Bug preexistente corregido de paso: `.resources/db_install_extensions.sh` hacía
  `apt-get install` en tiempo de init, pero ese paso corre como el usuario no-root
  `postgres` (así funciona `docker-entrypoint-initdb.d`), así que fallaba con
  `Permission denied` y abortaba **todo** el arranque en cualquier volumen
  genuinamente nuevo — invisible hasta ahora porque los contenedores reales
  siempre reusan volúmenes ya inicializados. `pgvector` ya se instala como root en
  tiempo de build (`db.Dockerfile`), así que el script ahora solo verifica que el
  paquete esté disponible.

## Impacto

- **Bases afectadas**: `pg16` (22 bases) y `pg16_odoo_17` (18 bases) — ambos
  servicios completos, no solo las 4 que estuvieron infectadas.
- **Sin downtime**: aplicado en caliente sobre los contenedores ya corriendo, sin
  reiniciar Postgres ni perder datos (verificado: conteo de bases intacto antes/
  después en ambos servicios).
- **Compatibilidad**: verificado que Odoo sigue pudiendo hacer `CREATE TABLE`/
  `ALTER TABLE`/`DROP TABLE` (migraciones de módulos) y `CREATE DATABASE`
  (creación de instancias nuevas) con el rol de app. Único cambio de
  comportamiento real: `COPY ... FROM/TO PROGRAM` ahora da `permission denied` —
  que es exactamente el objetivo.
- **Contraseñas rotadas** (no versionadas, viven solo en `instances.json` local y
  en el gestor de secretos del equipo): rol app y rol bootstrap de ambos
  servicios, más la contraseña de `admin` (usuario de Odoo, `res_users`) en las 4
  bases que estuvieron comprometidas.
- **Pendiente, fuera de este cambio**: revisar si el rol bootstrap debería además
  perder `CREATEROLE`; auditar `list_db: true` y la contraseña compartida
  `admin_password` en `instances.json`; confirmar que el Cloud Firewall de
  DigitalOcean bloquea los puertos de Postgres a nivel de plataforma como capa
  adicional.
