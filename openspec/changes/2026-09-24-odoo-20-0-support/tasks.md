# Tareas (completadas 2026-09-24)

## Investigación (odoo/odoo, rama `20.0` real en GitHub)

- [x] Confirmar que la rama `20.0` existe en `odoo/odoo` (default del
      repo) y en `binaural-dev/enterprise`.
- [x] Confirmar nightly build disponible
      (`nightly.odoo.com/20.0/nightly/deb/odoo_20.0.latest_all.deb`).
- [x] Diff de `debian/control` (Depends) entre ramas `19.0` y `20.0`:
      agregado `python3-h11`; eliminados `libjs-underscore`,
      `python3-tz`.
- [x] Diff de `requirements.txt` entre `19.0` y `20.0`: agregado
      `h11==0.16.0`; eliminados `pytz`, `xlwt`; resto son solo
      simplificaciones de condicionales `python_version` (mismas
      versiones finales para py3.12/noble).
- [x] `odoo/release.py` de ambas ramas: `MIN_PG_VERSION` sube de `13`
      (19.0) a `16` (20.0); `MIN_PY_VERSION` sube de `(3, 10)` a
      `(3, 12)` (sin impacto, ya se usa `ubuntu:noble`).

## Dockerfile

- [x] `.resources/dockerfiles/20.0_Dockerfile`: copia de
      `19.0_Dockerfile` con las URLs de `debian/control`,
      `requirements.txt` y el `.deb` de nightly apuntando a `20.0`
      (única diferencia — confirmado con `diff`). Imagen base sin
      cambios (`ubuntu:noble`).
- [x] Verificado que ningún generador (`config_loader.py`,
      `compose_generator.py`, `dockerfile_generator.py`) tiene una lista
      de versiones de Odoo hardcodeada (`grep` de `19.0`/`18.0`/etc. en
      código, no solo comentarios) — agregar el Dockerfile alcanza.

## Instancia de ejemplo y real

- [x] `instances.example.json`: instancia `demo-odoo20` (Enterprise
      puro, `addons: ["src/enterprise-20.0"]`, sin custom addons).
- [x] `instances.json` (local, no versionado): instancia real `odoo20`
      agregada — `database: pg16`, rol dedicado
      (`db_user: odoo_odoo20`, `db_filter: ^odoo20_`, mismo patrón que
      el resto de instancias sobre `pg16`, requerido porque comparte el
      servicio con instancias que corren cron), `addons:
      ["src/enterprise-20.0"]` únicamente.
- [x] `src/enterprise-20.0`: clon real (`git clone --branch 20.0
      --depth 1 git@github.com:binaural-dev/enterprise`), mismo patrón
      que `src/enterprise-19.0`/`src/enterprise-17.0`.

## Verificación

- [x] `load_config()` sobre el `instances.json` real con `odoo20`
      agregada: pasa toda la validación (incluida la de aislamiento
      cron/`db_filter` de
      `openspec/changes/2026-08-17-per-instance-postgres-roles-cron-isolation/`),
      sin errores.
- [x] `generate_dockerfiles()` con las 3 versiones reales
      (`14.0`/`19.0`/`20.0`): genera `.resources/Dockerfile.20.0` sin
      errores.
- [x] `generate_compose()` de punta a punta: servicio `odoo-odoo20`
      generado correctamente en `docker-compose.generated.yml`
      (Dockerfile, `INSTANCE_ADDONS`, `PGUSER`/`DBFILTER` del rol
      dedicado, `depends_on: db-pg16`).
- [x] `./odoo build` + `./odoo start odoo20` real: imagen
      `local_odoo_odoo20:20` construida, contenedor `odoo-odoo20`
      levantado contra `db-pg16` (rol dedicado `odoo_odoo20`).
- [x] Detectado con la corrida real (no visible en generación en seco):
      `http://localhost:9009/` daba `502` — Odoo 20.0 cambió el default
      de `--http-interface` a `127.0.0.1` (antes `0.0.0.0`), así que
      quedaba escuchando HTTP/gevent solo en loopback, inalcanzable
      desde el contenedor de nginx. Confirmado inspeccionando
      `/proc/net/tcp` dentro del contenedor.
- [x] Fix: `http_interface = 0.0.0.0` explícito en
      `.resources/conf.d/30-proxy-mode.conf` (aplica a toda versión, no
      solo 20.0 — no-op en <20.0). Verificado con rebuild +
      `./odoo restart odoo20`: `/proc/net/tcp` pasa a `0.0.0.0:8069`, y
      `curl http://localhost:9009/` responde `303` → `/odoo` → `200`
      (página de Odoo real).
- [x] Actualizar `readme.md` con la nota de `MIN_PG_VERSION` de Odoo
      20.0.
- [x] Actualizar `openspec/project.md` si aplica — no aplicó: no cambia
      la arquitectura de roles/Postgres, solo agrega una versión de
      Odoo soportada.
