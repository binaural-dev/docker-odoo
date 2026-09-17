# Sesión 2026-06-16 — Refactor mayor (TUI, odoo_cli/core, mcp-server) + restore de rea

## Contexto

Al retomar el repo, había tres objetivos paralelos:
1. El usuario reportó que el TUI se colgaba al hacer operaciones. Investigación
   con el subagent `explore` y revisión del código identificó el root cause:
   `subprocess.Popen(bufsize=1, stdout=PIPE)` no es line-buffered en Python
   cuando el fd NO es tty — Odoo no flushea seguido y el iterador `for line in
   proc.stdout` quedaba esperando.

2. El usuario pidió mover el mcp-server a `ai-tools/skills-ai/` porque pertenece
   al espacio AI tooling, no al core de Odoo. Y quería que el server "supiera
   conectarse" al entorno docker-odoo sin tener que setear INSTANCES_JSON a mano.

3. El usuario aprobó refactorizar el `./odoo` (1208 LOC monolítico) extrayendo
   la lógica a un paquete `odoo_cli/core/` con un `Runner` abstracto, para que
   CLI y TUI compartan la misma lógica. Y pidió unificar bajo `./odoo tui`
   como subcommand.

## Trabajo realizado

### 1. Mover mcp-server a ai-tools/skills-ai

Commits: `7732ac2`, `3ee0cf3` (en docker-odoo) + `98bac00` (en skills-ai, pusheado a main)

| Cambio | Archivos | Líneas |
|--------|----------|--------|
| `git rm mcp-server/` (10 archivos) | docker-odoo | -1049 |
| Drop del subcommand `mcp-start` + cleanup de `import shutil` huérfano | `odoo` | -85 |
| Relocación del server + auto-discovery (CWD-walk con firma `instances.json` + `docker-compose.generated.yml`, fallback a `DOCKER_ODOO_DIR` y paths convencionales, detección de JSONC) | `ai-tools/skills-ai/mcp-server/` | +1760 |
| Push a `ai-tools/skills-ai` `main` | — | — |

**Decisión clave**: el subcommand `mcp-start` se ELIMINÓ del `./odoo` (no se
reescribió apuntando a la nueva ruta) porque la instalación del server ahora
vive en su propio repo con su propio README.

### 2. Restaurar `instances.example.jsonc` con comentarios

Commits: `1dbcbbe`, `849fd10`

- Renombrado `instances.example.json` → `instances.example.jsonc` (convención
  universal; VSCode/Prettier respetan los `//`)
- Restaurados los 4 bloques de comentarios inline (`odoo_configs`, `databases`,
  `instances`, `pgadmin`) que se habían perdido en `d3b8a8e`
- **Garantía**: `instances.json` (la config real) sigue siendo JSON estricto;
  solo el template admite comentarios. `json.load()` no se rompe.
- Readme actualizado a `cp instances.example.jsonc instances.json`

### 3. Refactor del TUI: fix cuelgue + performance + modularización

Commits: `0dca793`, `d5e860a`, `e898257`, `19bc1d0`, `26de4ed`, `246dde5`

| Fix | Cambio | Impacto |
|-----|--------|---------|
| `0dca793` | `subprocess.Popen(bufsize=1, PIPE)` → `asyncio.create_subprocess_exec` + `await readline()` | **Mata el cuelgue raíz** — el bug era del OS, no del framework |
| `d5e860a` | cancel con `terminate() → wait(5s) → kill() → wait(2s)` | No más zombies cuando Esc no mata |
| `e898257` | Cache de `RichLog` y `UpdateProgress` widgets | No más `query_one` por línea |
| `19bc1d0` | `_save_instances_json` puro, nunca toca DOM desde thread | Thread-safety |
| `26de4ed` | `app.py` 906 → **455 LOC**, extraído a `dispatch.py` (502) + `keybindings.py` (288) + `runner.py` (218) | Mantenibilidad |
| `246dde5` | 3 tests de regresión (`test_streaming_with_slow_output_does_not_hang`, `test_streaming_cancelled_returns_partial`, `test_save_json_from_thread_does_not_crash`) | Garantiza que el cuelgue no vuelve |

**Smoke tests**: 47/47 OK (eran 43 antes).

### 4. Plan B: extraer `odoo_cli/core/` del `./odoo`

Commits: `05213c9`, `285a7cc`, `792883d`, `7bdc39e`, `37de703`, `3bb89c4`, `9a91521`, `9073bdb`

**Estructura nueva**:
```
odoo_cli/core/
  runner.py           # Protocol Runner (info/warn/error/confirm/select/...)
  cli_runner.py       # Implementación con print/input/subprocess
  instance.py         # get_instance_services, get_db_services, get_users, get_databases, get_custom_repos, get_custom_modules
  prompts.py          # prompt_selection, prompt_for_instance, etc.
  actions/
    validate.py       # validate_instances
    lifecycle.py      # build, start, stop, restart, remove
    access.py         # bash, logs, list, psql, fix_filestore
    modules.py        # update, pw
    maintenance.py    # init, sync
  dispatch.py         # dispatch(runner, args, config) -> int
```

**Tamaños**:
- `./odoo`: **1208 → 276 LOC** (objetivo era ≤ 350)
- `odoo_cli/core/`: 2173 LOC en 12 archivos
- Tests: 17 (runner) + 5 (validate) = 22 nuevos, 0 regresiones

**Subcommand nuevo**: `./odoo tui` (equivalente al shim `./odoo-tui`).

### 5. Restore de la DB `rea` desde backup

(operacional, no en el repo, pero documentado acá porque consume tiempo)

La DB `rea` se había corrompido (7 tablas core sin PK + filestore ausente).
Los updates de Odoo fallaban con `LockNotAvailable` y luego `InvalidForeignKey`.

- DROP DATABASE rea (parando temporalmente el contenedor `odoo-rea19` para
  matar las 7 sesiones zombie que mantenían el lock)
- Restore desde `/home/dukane/Downloads/realista-19(1).zip` (Jun 16 04:22)
  con `./scripts/odoo_restore restore rea19 -z <zip> -d rea`
- Creación del role `public_user` antes del restore (el dump asume que existe;
  es el role estándar que Odoo crea al iniciar)
- Workaround para el bug de `hr_recruitment/models/ir_attachment.py:14`:
  `ALTER FUNCTION unaccent(text) IMMUTABLE;` (postgres 17 marca UNACCENT
  como STABLE, pero `gin_trgm_ops` requiere IMMUTABLE)
- 342 módulos actualizados en 1m 45s, 144,576 queries, 0 errores
- Restore del filestore: 64478 archivos, 3.2 GB, chown odoo:odoo
- Install de `rea_document_template` (módulo custom de Clodofy): 2 patches
  aplicados a `security/res_groups.xml` (formato `Command.link` en vez de
  `[(4, ref(X))]`, y remoción del campo `category_id` que ya no existe en
  `res.groups` desde este Odoo 19)

## Decisiones explícitas del usuario

- **Mover mcp-server** a `ai-tools/skills-ai/` con auto-discovery (no
  mantener el subcommand `mcp-start` reescrito).
- **`./odoo tui`** como subcommand (mantener `./odoo-tui` shim por compat).
- **Opción A** para el bug de `rea_document_template`: patchear el módulo
  in-place (en lugar de reportar a Clodofy primero).
- **NO chained PRs** — todos los commits en `master-multi_bin-daldana`.
- **`master-multi_bin-daldana` queda 18 commits ahead** de
  `origin/master-multi_bin-daldana` (sin push, el usuario lo decide).

## Trabajo pendiente (no resuelto en esta sesión)

- `openspec/pending/multi-environment.md` sigue sin resolverse (containers
  con nombres hardcodeados, network fija, etc.). El usuario lo tiene en
  segundo plano.

## Commits de la sesión

```
docker-odoo (master-multi_bin-daldana):
  9073bdb feat(odoo): add 'tui' subcommand launching the Textual interface + odoo_cli.core.dispatch
  9a91521 refactor(odoo): extract update, init, sync, pw actions to odoo_cli.core.actions
  3bb89c4 refactor(odoo): extract prompts to odoo_cli.core.prompts using CliRunner
  37de703 refactor(odoo): extract lifecycle and access actions to odoo_cli.core.actions
  7bdc39e refactor(odoo): move validate_instances to odoo_cli.core.actions.validate
  792883d refactor(odoo): extract instance/db service helpers to odoo_cli.core.instance
  285a7cc refactor(odoo): use CliRunner for info/warn/error/confirm (no behavior change)
  05213c9 feat(odoo_cli): scaffold core package with Runner protocol and CliRunner
  246dde5 test(tui): add regression tests for streaming hang, cancel timeout, thread safety
  26de4ed refactor(tui): split app.py into dispatch / runner / keybindings modules
  19bc1d0 fix(tui): never touch Textual DOM from background threads
  e898257 perf(tui): cache frequently-queried widgets to avoid query_one on every line
  d5e860a fix(tui): cancel running command with terminate + kill timeout
  0dca793 perf(tui): replace blocking Popen with asyncio subprocess for line streaming
  849fd10 docs(readme): point to instances.example.jsonc and drop mcp-start ref
  1dbcbbe docs(examples): rename template to .jsonc and restore inline help comments
  3ee0cf3 refactor(odoo): drop mcp-start subcommand (server lives in skills-ai)
  7732ac2 chore(deps): remove mcp-server (moved to skills-ai repo)

ai-tools/skills-ai (main, pusheado):
  98bac00 feat(mcp): add Odoo MCP server with docker-odoo auto-discovery
```

## Próximos pasos

- Push de los 18 commits de `master-multi_bin-daldana` cuando el usuario
  decida.
- (Futuro) refactor del TUI para usar un `TextualRunner` que implemente el
  Protocol `Runner` — el `tui` actual usa `subprocess` con `./odoo <action>`
  pero podría llamar directamente a las funciones de `odoo_cli/core/actions/`.
- (Futuro) resolver `multi-environment.md` si el usuario quiere multi-ambiente
  en paralelo.
