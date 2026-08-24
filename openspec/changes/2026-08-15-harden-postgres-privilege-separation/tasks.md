# Tareas (todas completadas el 2026-08-15)

## Investigación / contención del incidente

- [x] Escanear `ir_cron`/`ir_act_server` en las 38 bases de ambos servicios
      buscando patrones de RCE/malware (script corregido: el original fallaba en
      silencio por falta de `psql` en el host y por consultar una columna
      inexistente en `ir_cron`).
- [x] Identificar las 4 bases comprometidas y neutralizar el código malicioso
      (reemplazado por marcador, no borrado — se preserva evidencia forense).
- [x] Confirmar que el ataque no escapó del contenedor Postgres al host
      (`Privileged=false`, `PidMode` normal en ambos servicios).
- [x] Cerrar el vector de entrada original: verificar que
      `expose_host_port: false` (default) ya estaba aplicado en la rama
      `master-multi` — puertos `5502`/`5503` ya no publicados a `0.0.0.0`.

## Separación de roles (este cambio)

- [x] Confirmar que `ALTER ROLE ... NOSUPERUSER` falla sobre el rol bootstrap en
      ambos servicios (comportamiento esperado de Postgres, no bug).
- [x] Confirmar que `REASSIGN OWNED BY bootstrap TO <nuevo rol>` también falla
      ("required by the database system").
- [x] Crear rol de app no-superusuario (`LOGIN CREATEDB`) en `pg16` y en
      `pg16_odoo_17`.
- [x] `ALTER DATABASE <db> OWNER TO <rol de app>` en las 22 bases de `pg16` y las
      18 de `pg16_odoo_17`.
- [x] `GRANT <bootstrap> TO <app>` en ambos servicios.
- [x] Validar en las bases reales: `is_superuser=off`, `COPY TO PROGRAM` →
      denegado, `ALTER TABLE`/`DROP TABLE` sobre tablas del bootstrap → funciona,
      `CREATE DATABASE` → funciona.
- [x] `ALTER ROLE <bootstrap> NOLOGIN` en ambos servicios; confirmar que ya no
      puede autenticarse.
- [x] Actualizar `instances.json` (`user`/`password` = rol de app,
      `bootstrap_user`/`bootstrap_password` = rol bootstrap).
- [x] Actualizar `.resources/generators/compose_generator.py` para emitir
      `POSTGRES_USER`/`POSTGRES_PASSWORD` desde los campos `bootstrap_*` y nuevas
      env vars `APP_DB_USER`/`APP_DB_PASSWORD`.
- [x] Regenerar `docker-compose.generated.yml` sin rebuild completo de imágenes
      (invocando `generate_compose` directamente).
- [x] Recrear `db-pg16`/`db-pg16_odoo_17` con el compose actualizado; confirmar
      que los datos siguen intactos (conteo de bases antes/después) y que los
      puertos siguen sin publicarse.
- [x] Crear `.resources/db_create_app_role.sh` y engancharlo en
      `.resources/db.Dockerfile` (`docker-entrypoint-initdb.d/zz_create_app_role.sh`)
      para que un volumen nuevo nazca con el mismo esquema automáticamente.
- [x] Validar el script en un contenedor descartable con volumen 100% nuevo
      (imagen y contenedor de prueba, no tocar los reales).
- [x] Corregir bug preexistente de `.resources/db_install_extensions.sh`
      (`apt-get` fallaba por `Permission denied` al correr como usuario no-root
      en `docker-entrypoint-initdb.d`); revalidado en el mismo contenedor
      descartable.
- [x] Rotar la contraseña del usuario `admin` de Odoo (`res_users`, no la de
      Postgres) en las 4 bases que estuvieron comprometidas.
- [x] Commit de los archivos de código tocados (excluidos `instances.json` y
      `docker-compose.generated.yml`, ambos en `.gitignore` — nunca se
      versionan contraseñas).
