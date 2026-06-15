# Sesión 2026-06-15 — Merge multi-instance + perfiles PostgreSQL

## Contexto

Al retomar el repo, había un merge en curso desde `origin/master-multi` que
resolvimos, más una serie de refactors al schema de configuración. El repo
arrancaba con 19 instancias en `instances.json` y carpetas huérfanas en
`src/custom/` que correspondían a instancias nunca registradas. Además, la
configuración de PostgreSQL era un único perfil genérico que servía a las
31 instancias, sin separación entre la versión del motor y la carga esperada.

## Trabajo realizado

### 1. Resolución de merge conflicts

Commit: `0a837d1` — "Merge branch 'origin/master-multi' into master-multi_bin-daldana"

**Archivos:** `odoo` y `readme.md`

| Conflicto | HEAD | origin | Resolución |
|-----------|------|--------|-----------|
| `bash_update_modules` | `subprocess.run(list)` sin return | `os.system(str)` con return | `subprocess.run(cmd).returncode` (más seguro + mantiene exit code) |
| `prompt_selection` | (no existía) | menú interactivo completo con flechas, multi-select, grid | Adoptar el de origin |
| `_instance_has_db` + `_resolve_instance_for_action` | funciones nuevas para resolver instancia por DB | (no las tenía) | Mantener las de HEAD |
| `prompt_for_database` | sin `allow_all` | con `allow_all=True` + opción "all" | Usar la de origin (con `allow_all`) |
| `readme.md` | sección TUI completa (v3) | una línea sobre `-d all` | Mantener ambas |

### 2. 12 instancias faltantes agregadas

**Problema:** existían 13 carpetas en `src/custom/` sin entrada en `instances.json`.
Una de ellas (`odoo-farmacia-xana`) es repo compartido, no instancia — descartada.

**Carpetas agregadas como instancias:**

| Instancia | v | Puerto | Notas |
|-----------|---|--------|-------|
| giralda | 19.0 | 8089 | 13 addons propios `lagiralda_*` |
| avpharma | 19.0 | 8090 | solo submódulos compartidos |
| demo-integration-core | 17.0 | 8091 | entorno demo |
| demo-integration-ext | 17.0 | 8092 | entorno demo |
| integration-homologation | 17.0 | 8093 | entorno de homologación |
| integration-operative | 17.0 | 8094 | entorno operativo |
| bananera | 17.0 | 8095 | 1 addon propio `bananera_romana` |
| contiflex | 19.0 | 8096 | única instancia v19 inicial con 3 addons propios |
| nuevomercadopetare | 16.0 | 8097 | 4 addons propios, sin `odoo-venezuela` |
| turaser | 17.0 | 8098 | 7 addons propios `turaser_*` |
| cigars-core | 17.0 | 8099 | sin addons propios, solo submódulos |
| cigars-ext | 17.0 | 8100 | sin addons propios, sin `odoo-venezuela` |

**Total final:** 31 instancias registradas.

### 3. Refactor de configuración de PostgreSQL

Commit: `a668c17` — "feat(db): postgres tuning profiles (small/medium/large/xlarge)"

**Iteración:**

1. **Primer intento (descartado):** configs por versión de Odoo
   (`postgresql.v16.conf`, `v17`, `v18`, `v19`). El usuario detectó que esto
   capturaba el factor equivocado: la versión de Odoo no determina el tuning
   de RAM/concurrencia, eso lo determina la **carga esperada**.

2. **Decisión final:** 4 perfiles agnósticos a versión, basados en cuántas
   instancias comparten la misma DB:

   | Perfil | Archivo | `shared_buffers` | `max_connections` | `max_worker_processes` | Target |
   |--------|---------|------------------|-------------------|------------------------|--------|
   | small | `postgresql.small.conf` | 1GB | 60 | 2 | 1-3 instancias |
   | medium | `postgresql.medium.conf` | 2GB | 100 | 4 | 4-10 instancias |
   | large | `postgresql.large.conf` | 4GB | 200 | 8 | 11-20 instancias |
   | xlarge | `postgresql.xlarge.conf` | 8GB | 300 | 16 | 20+ instancias |

**Asignación inicial:**

| DB | postgres_version | Perfil | # instancias |
|----|------------------|--------|--------------|
| v16 | 15 | small | 2 |
| v17 | 16 | xlarge | 23 |
| v18 | 17 | small | 3 |
| v19 | 18 | small | 3 |

**Decisión arquitectónica clave:** separar `postgres_version` (eje de
compatibilidad con Odoo) de `config` (eje de tuning de workload). Son ortogonales.
Escalar = cambiar un solo campo en `instances.json`, no editar archivos de tuning.

### 4. Documentación

En el mismo commit `a668c17`:

- **`readme.md`:** nueva sección "Perfiles de PostgreSQL" (~75 líneas) con tabla
  de decisión, hardware sugerido, ejemplo de escalado y justificación del diseño.
- **`readme.md`:** tabla de compatibilidad Odoo ↔ PostgreSQL agregada.
- **`readme.md`:** nueva entrada FAQ sobre elección de perfil.
- **`instances.example`:** header comment en sección `databases` explicando los
  dos ejes.

## Validación

- `./odoo validate-instances` → ✅ pasa
- `./odoo build` → ✅ genera `docker-compose.generated.yml` con los 4 DBs y sus
  perfiles correctos
- `git status` → ✅ working tree limpio (excepto `instances.example.json` que
  ya estaba borrado desde el merge)

## Decisiones explícitas del usuario

- **No** agregar `odoo-farmacia-xana` como instancia (es repo compartido).
- **No** borrar/limpiar el config grande de PostgreSQL en el primer refactor —
  mea culpa, lo había sobreinterpretado. Aprendí la lección: ante
  "borra lo viejo" preguntar primero si hay valor histórico.
- **giralda, avpharma, contiflex** son v19 (confirmado por manifest).
- **demo-integration-*, integration-*** son v17 (confirmado por manifest).
- **Perfiles en vez de por versión** — el usuario guió esta decisión con
  mejor criterio arquitectónico que el mío inicial.
- **Password admin:** se mantiene `"admin"` por ahora (decidido en sesión).

## Archivos modificados

```
.resources/dbconfigs/postgresql.small.conf   (nuevo)
.resources/dbconfigs/postgresql.medium.conf  (nuevo)
.resources/dbconfigs/postgresql.large.conf   (nuevo)
.resources/dbconfigs/postgresql.xlarge.conf  (nuevo)
.resources/dbconfigs/postgresql.conf         (borrado)
.resources/dbconfigs/postgresql.4gb.2cpu.conf (borrado)
instances.json                                (modificado: 12 instancias + DBs)
instances.example                             (modificado: profiles comment)
readme.md                                     (modificado: nueva sección + FAQ)
openspec/                                     (nuevo: este documento)
```

## Commits de la sesión

```
a668c17 feat(db): postgres tuning profiles (small/medium/large/xlarge)
0a837d1 Merge branch 'origin/master-multi' into master-multi_bin-daldana
b5fd75c chore(infra): coveragerc para mds-telecom + odoo-update no bindea 8069
```
