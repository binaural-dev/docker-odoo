# Scripts disponibles

Esta carpeta agrupa utilidades para administrar y probar tu entorno de Odoo. La mayoría de los scripts hacen uso de las variables definidas en `.env`.




## Ejemplos de uso de scripts

### migrate-module

```sh
./scripts/migrate-module -d <base_de_datos> -i <modulo> -c <contenedor_odoo>
```
Migra el módulo `<modulo>` en la base de datos `<base_de_datos>` dentro del contenedor `<contenedor_odoo>`.

### odoo-backups.sh

```sh
./scripts/odoo-backups.sh -c <config.json> -s <servers.json> -d <base_de_datos>
```
Genera un respaldo de la base de datos `<base_de_datos>` y su filestore, utilizando los archivos de configuración y servidores indicados.

### odoo-pw

```sh
./scripts/odoo-pw -d <base_de_datos> -l <usuario>
```
Restablece la contraseña del usuario `<usuario>` en la base de datos `<base_de_datos>`, usando el valor de `RESET_PASSWORD` definido en el archivo `.env`. Si no se indica usuario, se restablece la contraseña de `admin`.

### odoo-test

```sh
./scripts/odoo-test
```
Ejecuta pruebas automatizadas sobre la base de datos `testing`.

### odoo-update

```sh
./scripts/odoo-update -d <base_de_datos> <modulo1> <modulo2> ...
```
Actualiza los módulos indicados (`<modulo1>`, `<modulo2>`, etc.) en la base de datos `<base_de_datos>`.

### restore_db.sh

```sh
./scripts/restore_db.sh -b <contenedor_db> -o <contenedor_odoo> -f <archivo_backup> -d <base_de_datos>
```
Restaura el backup `<archivo_backup>` en la base de datos `<base_de_datos>`, utilizando los contenedores `<contenedor_db>` (PostgreSQL) y `<contenedor_odoo>` (Odoo).


### Notas y solución de problemas para restore_db.sh

- El script detecta automáticamente si el archivo es `.dump` (usa `pg_restore`) o `.sql` (usa `psql`).
- Si ves el error `pg_restore: error: unsupported version (1.16) in file header`, significa que tu contenedor de PostgreSQL es más antiguo que la versión usada para generar el dump.  
  **Solución:** actualiza la variable `POSTGRES_IMG_VERSION` en tu `.env` y recrea el contenedor.
- Si después de restaurar y actualizar todos los módulos aparecen errores como `KeyError: 'ir.http'` en Odoo, puede deberse a:
  - Un dump incompleto o corrupto.
  - Falta de módulos en el path de addons.
  - Incompatibilidad entre la versión de Odoo y la base restaurada.
- Para máxima compatibilidad, solicita siempre el dump en formato SQL plano (`.sql`).
- Si tienes problemas, revisa los logs de restauración y asegúrate de que todos los módulos requeridos estén presentes en el entorno.

## Harness SDD (scripts `sdd_*`)

Los scripts `sdd_*`, los plugins de `opencode-plugins/` y los JSON de gobernanza son parte del flujo SDD → OpenCode. Mapa completo (que usar para cada necesidad, variables `SDD_*` y defaults): skill `sdd-harness-catalog` (`src/.opencode/skills/sdd-harness-catalog/SKILL.md`). Cada script debe tener dueno en `sdd-inventory.json`.

### Memoria persistente (Engram)

Memoria local y persistente para SDD, OpenCode y Claude Code. Convención de uso: skill `sdd-memory-protocol`.

- Configuración local (sin nube, sin consultas de versión): `source scripts/engram-env.sh`. Sin ella, el CLI `engram` a mano consulta GitHub por actualizaciones.
- Modo por job en OpenCode: `SDD_MEMORY_MODE=on|off` (default `off`) y `memory_ref:` en el `Context {}`. Ver `sdd_opencode_run.sh`.
- Sembrar lecciones de la auto-memoria: `python3 scripts/sdd_memory_seed.py [--dry-run] [--no-project]`.
- Captura de jobs terminados: `python3 scripts/sdd_memory_capture.py ingest JOB_DIR`; snapshot para un job: `snapshot --query Q --out P`.
- Hooks de Claude Code (`.claude/settings.json`): `scripts/hooks/engram_claude_hook.py` registra la sesión (`SessionStart`), la cierra (`SessionEnd`) y guarda el cierre de los subagentes de escritura (`SubagentStop`).
- Tests: `python3 -m unittest test_sdd_memory_capture test_sdd_memory_common test_engram_claude_hook` desde `scripts/`.
