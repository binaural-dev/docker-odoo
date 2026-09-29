# AGENTS.md — docker-multi

Punto de referencia central para el workspace `docker-multi`. Odoo 19 (principal) y 17.

## Workspace Structure

```
/home/binlp011/sources/docker-multi/
├── AGENTS.md                          ← Este archivo
├── instances.json                     ← Configuración de instancias Docker
├── scripts/                           ← Scripts de operaciones
│   ├── precommit                      ← Pre-commit para módulos Odoo
│   ├── coverage                       ← Cobertura de tests
│   └── migrate                        ← Migración entre versiones
└── src/                               ← RAÍZ DE TRABAJO
    ├── odoo-19.0/                     ← Fuente Odoo 19 (core)
    ├── enterprise-19.0/               ← Módulos Enterprise
    ├── integra-addons-19.0/           ← Módulos custom Binaural
    ├── odoo-venezuela-19.0/           ← Localización venezolana
    ├── third-party-addons-19.0/       ← Addons de terceros
    ├── custom/                        ← Personalizaciones por instancia
    ├── stub_modules/                  ← Stubs enterprise para tests
    ├── scripts/                       ← Scripts de la instancia
    │   └── run_tests.sh               ← Tests con coverage
    ├── reports/coverage/              ← Reportes de coverage
    └── .opencode/                     ← OpenCode config
        ├── agents/                    ← Agentes SDD + Binaural (13 agentes)
        ├── skills/                    ← Skills del proyecto (108 dirs)
        ├── commands/                  ← Comandos del proyecto (12 commands)
        ├── docs/                      ← Documentación Odoo 19 (654 .md)
        ├── plans/                     ← Planes de migración
        ├── goals/                     ← Goal tracking
        ├── 17.0/skills/               ← Skills Odoo 17.0 (326 dirs)
        ├── 19.0/skills/               ← Skills Odoo 19.0 (161 dirs)
        ├── 16.0/skills/               ← Skills Odoo 16.0 (100 dirs)
        ├── opencode.json              ← Config workspace (override global)
        └── package.json               ← Plugin dependencies (@opencode-ai/plugin)
```

## Odoo Version

**Versión principal: 19.0** — todos los skills y patrones usan Odoo 19 a menos que se indique explícitamente otra versión.

## Inventario General

| Categoría | Cantidad |
|-----------|----------|
| skills/19.0/skills/ (161 dirs) | **161** |
| skills/.opencode/skills/ (project: 118 dirs) | **118** |
| skills/17.0/skills/ (325 dirs) | **325** |
| skills/16.0/skills/ (100 dirs) | **100** |
| skills/global (~/.config/opencode/skills/, 169 dirs) | **169** |
| **TOTAL WORKSPACE (unique)** | **~873** |
| Claude symlinks (~/.claude/skills/) | **~854** |
| Archivos documentación (.opencode/docs/) | 654 |
| Chunks indexados en OpenSearch | **5,738** (855 skills) |

## Skills del Proyecto

### Core Odoo 19 (`.opencode/skills/`)

| Skill | Descripción |
|-------|-------------|
| `odoo_owl_backend-19.0` | OWL backend: views, components, registry, 92 widgets |
| `odoo_owl_website-19.0` | OWL website: interactions, builder, e-commerce, themes |
| `odoo-owl-frontend-templates-19.0` | Templates OWL en `static/src/xml/`, `renderToString()`, module context, ARIA modal pattern, guard pattern, publicWidget lifecycle |
| `odoo_orm_backend-19.0` | ORM: BaseModel, fields, Domain, Command, cache |
| `odoo_security_api_ai-19.0` | Security: XSS, SQL injection, auth, access control |
| `odoo_reports_papermuncher-19.0` | PDF reports: Flexbox, QWeb, barcodes, watermarking |
| `odoo_tools_core-19.0` | Core tools: SQL, safe_eval, cache, config, translate |
| `odoo_documentation-19.0` | Full Odoo 19 docs (654 files) |
| `odoo_devops-19.0` | Module system, CLI, deployment, DB management |
| `odoo-migration-19` | Migration guide 17→19 (45 lessons) |
| `odoo-migration-audit-methodology` | **NUEVO** — Metodología de 8 pasos para auditar migraciones de módulos Odoo |
| `odoo-19-breaking-changes-checklist` | **NUEVO** — Checklist consolidado de breaking changes 17→19 (Python, XML, JS, SQL) |
| `odoo-migration-classification-taxonomy` | **NUEVO** — Taxonomía de clasificación: MIGRADO-VIGENTE, EN-PROGRESO-CON-BUG, etc. |
| `odoo-19-pos-js-migration` | **NUEVO** — Guía completa de migración JS del POS: imports, APIs removidas, patrones de patch |
| `odoo-cross-repo-module-tracking` | **NUEVO** — Cómo rastrear módulos across repos: integra-addons, odoo-venezuela, custom checkouts |
| `odoo-performance-19` | Performance: N+1, batch-first, indexes |
| `odoo-code-review-19.0` | Code review checklist (58 rules incl. recordset safety, scope creep, security, dead assets, start() lifecycle, ES2020, RPC error handling, focus restoration, compute-group-visibility, button-xpath) |
| `odoo-context-keys-19` | **NUEVO** — Context keys: warehouse_id, location, stock filtering |
| `odoo-compute-group-visibility` | **NUEVO** — `depends_context('uid')` + `has_group()` pattern, 4 anti-patterns, Odoo core reference |
| `odoo-button-xpath-patterns` | **NUEVO** — 6 safe patterns for `//header/button` xpath, 5 anti-patterns (incl. text()-based selectors breaking translated views), decision tree |
| `odoo-payment-transaction-architecture` | **NUEVO** — M2M table `account_invoice_transaction_rel`, ORM vs raw SQL, payment flow diagrams |
| `skill-sync-daemon` | **NUEVO** — Daemon systemd user service: sync OpenCode→Claude vía symlinks, polling 30s, 5 fuentes, name-collision protection |
| `agents-md-maintenance` | **NUEVO** — Protocolo de mantenimiento de AGENTS.md: cuándo actualizar, qué secciones, formato de reglas |
| `skills-inventory-protocol` | **NUEVO** — Inventario maestro de skills: ubicaciones, conteos, naming conventions, estructura de directorios |
| `odoo-approval-workflow-patterns` | **NUEVO** — Approval workflows: state machine, write guards, self-approval blocking, dual notification, mail.activity lifecycle, security groups, testing patterns, 10 anti-patterns |
| `odoo-dual-notification-patterns` | **NUEVO** — Dual-channel notifications: message_notify + forced second channel, mt_note subtype, customer exclusion, verification queries, 7 anti-patterns |
| `odoo-currency-convert-mandatory` | **NUEVO** — Regla: SIEMPRE usar `res.currency._convert()` para conversiones de moneda. API completa, anti-patterns (multiplicación manual), short-circuit same-currency. Aplica a 17+ |
| `odoo-vendor-override-patterns` | **NUEVO** — Patrones para override de módulos vendor: full-copy vs inheritance, template ID naming (module prefix), PresenceIndicator collisions, defensive field checks, barcode fallback paths |
| `openrag` | **NUEVO** — OpenRAG RAG system: architecture (OpenSearch/Ollama/MCP), ingestion workflow, knowledge filters, backend source management, verification commands |
| `openrag-embedding-fix` | **NUEVO** — OpenRAG embedding model fix + batch ingestion: nomic-embed-text:latest naming, _is_exact_token_query bug, batch ingest script pattern, filter update via HTTP |
| `skills-inventory-protocol` | **NUEVO** — Inventario maestro de skills: ubicaciones (5 dirs), naming conventions, OpenRAG ingestion policy, version detection protocol |
| `claude-opencode-port-protocol` | **NUEVO** — Protocolo de sincronización OpenCode→Claude: unidireccional via symlinks, format adaptation, post-port checklist |

### Módulos Binaural (`.opencode/skills/`)

| Skill | Descripción |
|-------|-------------|
| `binaural-farming` | Gestión ganadera (stock.lot, especies, razas) |
| `binaural-farming-website` | Catálogo web de ganadería (/agro) |
| `binaural-website` | Website base (portal, profile, checkout) |
| `binaural-website-sale` | E-commerce (shop, checkout, carrito) |
| `binaural-website-sale-delivery` | Métodos de envío, OWL patching |
| `binaural-website-sale-transit` | Stock en tránsito, mail templates |
| `l10n-ve-accountant` | Localización contable venezolana |
| `l10n-ve-currency-rate-live` | Sincronización BCV en vivo, multi-moneda (USD/EUR/CNY/TRY/RUB), retry programado vía `ir.cron.trigger`, TLS hardening, aislamiento de fallos por compañía, logging, cron window, tests. Incluye lecciones de merge conflicts (SyntaxError, pérdida silenciosa de retry logic) del PR #1060. Vive en `src/.opencode/skills/` + ingerida en `openrag` (no en `~/.claude/skills`) |
| `odoo-combo-product-validation-19.0` | **NUEVO** — Bug recurrente: validaciones custom de "impuesto único" (taxes_id/supplier_taxes_id) que no exceptúan `type='combo'`. 2 módulos afectados (`l10n_ve_accountant`, `binaural_purchase`), checklist de code review, constraints CORE relacionadas (combo_ids/combo_item_ids) |
| `cadipa-sale-suscription-payment` | **NUEVO** — Portal payment flow + VES conversion + l10n_ve bug fix para cadipa_sale_suscription |
| `cadipa-sale-suscription-testing` | **NUEVO** — Testing helpers, coverage patterns y anti-patterns para cadipa_sale_suscription (Odoo 17.0): _setup_ves_company, mock parent via __mro__[1], l10n_ve constraint patterns |
| `odoo-l10n-ve-test-patterns` | **NUEVO** — Patrones de testing para modulos que dependen de l10n_ve_* (Odoo 17.0): currency_foreign_id setup, action_post con move_action_post_alert, product_id en lineas de factura, correlative conflicts, VES/VEF currency, enterprise constraints. 6 anti-patrones (L1-L6) |
| `binaural-stock-barcode` | Barcode picking con fake lines |
| `binaural-checker-kiosk` | **NUEVO** — Kiosko de precios: vendor extension pattern, barcode fallback paths, pricelist resolution via sh_pricelist_ids, res.currency._convert(), PresenceIndicator collision, test fixtures (allowed_company_ids, raw SQL for foreign_currency_id) |
| `binaural-openupgrade-simulation` | **NUEVO** — Simulación de upgrade con OpenUpgrade: metodología 17→18→19, gotchas operativos del cluster docker-multi, scripts de migración pre/post/end |
| `odoo-analytic-distribution-limit-pattern-19.0` | **NUEVO** — Patrón completo: límite 100% distribución analítica por plan. Boolean en res.company + related settings + xpath analytic block + constraint @api.constrains agrupando por root_plan_id + float_compare + .format() translations. 12 tests TDD, 100% coverage. Caso real: TI-15326 |
| `odoo-19-boolean-setting-pattern` | **NUEVO** — Patrón reutilizable setting boolean Odoo 19: campo res.company + related res.config.settings + xpath en block (analytic/invoicing/tax/etc). Convenciones naming, grupos, CSS classes. Caso real: TI-15326 |
| `odoo-constraint-module-test-pattern-19.0` | **NUEVO** — Estructura tests para módulos @api.constrains: 12 tests (reject/allow, boundary, single, no-dist, multi-plan, multi-key, precision, multi-company). Helper parametrizado, post_install tag. Caso real: TI-15326 |
| `odoo-e2e-verification-playwright-rpc-19.0` | **NUEVO** — Verificación E2E híbrida: Playwright (login, settings UI) + JSON-RPC (crear records, validar constraints). Formato analytic_distribution dict, buscar account IDs reales, toggle setting via RPC. Caso real: TI-15326 |

### Workflows (`.opencode/skills/`)

| Skill | Descripción |
|-------|-------------|
| `coverage-workflow` | Ejecutar, analizar y mejorar cobertura. Incluye SDD validation cycle, anti-patterns C1-C15 |
| `sdd-workflow` | Spec-Driven Development: spec → plan → tasks. Incluye post-implementation validation cycle |
| `odoo-testing-workflow` | Flujo de tests Odoo. Incluye coverage validation post-implementation, anti-patterns C1-C14, pytz mock, time-window guards, parent_id immutability |
| `workspace-structure` | Estructura del workspace, pre-commit, instancias. Incluye container↔instance mapping |
| `guia_precommit_odoo` | Guía completa del sistema pre-commit: script, hooks, warnings catalog, troubleshooting |
| `openrag` | OpenRAG RAG: ingestión, búsqueda semántica, chat MCP |
| `gh-pr-workflow` | **NUEVO** — GitHub CLI (`gh`) para PRs: crear, ver, listar, checkout, leer y responder comentarios de review (`gh api .../pulls/{n}/comments`), safety protocol (nunca merge/approve/force-push sin confirmación del usuario). Disponible en Claude Code (symlink) y OpenCode. |
| `binaural-submodule-maintenance-merge` | **NUEVO** — Workflow para actualizar submódulos de un repo cliente (`integra-addons`/`odoo-venezuela`/`third-party-addons`) a su rama de mantenimiento: detección de línea divergente vs simplemente atrasada, naming inconsistente de rama de mantenimiento por repo, resolución masiva de conflictos aceptando lo entrante, verificación de integridad por tipo de archivo (no solo `.py`), separación commit-feature/commit-submódulos, workaround `gh pr edit` + GraphQL Projects-classic. |
| `binaural-odoo-shell-live-verification` | **NUEVO** — Protocolo para reproducir/verificar en vivo un bug contra la BD de staging real de un cliente vía `odoo shell`, con la regla dura de terminar SIEMPRE con `env.cr.rollback()` (nunca `commit()`). Incluye patrón de múltiples escenarios en una sola sesión (try/except/finally con rollback), invocación no-interactiva vía `docker cp` + stdin, y gotchas de invalidación de cache. |
| `l10n-ve-website-sale` | Patrones de moneda alterna y tasa BCV en checkout venezolano (`binaural_website_sale`, `binaural_website_sale_delivery`): mixin `ForeignRateCommon`, detección pricelist-aware de moneda alterna, AJAX de delivery, template inline con `t-set`. |

### Testing & Browser Automation Skills

| Skill | Ubicación | Descripción |
|-------|-----------|-------------|
| `playwright-mcp-usage` | `~/.config/opencode/skills/` | **NUEVO** — Playwright MCP tools: navigate, snapshot, click, type, mock, assert, trace. Automatización de browser agentic. |
| `odoo-website-testing-mcp-19.0` | `src/.opencode/19.0/skills/` | **NUEVO** — Testing de portales/websites Odoo 19.0 con Playwright MCP: login, shop, checkout, e-commerce, responsive, evidencia. |
| `odoo-backend-testing-mcp-19.0` | `src/.opencode/19.0/skills/` | **NUEVO** — Testing de formularios backend Odoo 19.0 (no portal) con Playwright MCP: dirty-tracking OWL del botón Guardar, diagnóstico de guardado silencioso vía `.o_field_invalid`, confirmación de que el save llegó al backend. |
| `e2e-testing` | `~/.config/opencode/skills/` | Playwright test framework: POM, config, CI/CD, flaky tests. Archivos `.spec.ts` con `@playwright/test`. |

### Globales (`~/.config/opencode/skills/`)

| Skill | Descripción |
|-------|-------------|
| `git-workflow` | **NUEVO** — Branch strategy, cherry-pick, separación de ramas, verificación post-cherry-pick |

### Terminal Productivity Tools (`.opencode/skills/`)

**27 herramientas instaladas** en Debian 13 (trixie), x86_64. Instalación 2026-09-01.

| Skill | Ubicación | Descripción |
|-------|-----------|-------------|
| `terminal-productivity-tools` | `src/.opencode/skills/` | Referencia completa: file managers (yazi/ranger/nnn/lf), image viewers (chafa/timg), replacements (bat/eza/fd/rg/delta), navigation (zoxide/fzf), monitoring (btop/ncdu/dust/duf), git TUI (lazygit/gitui), multiplexers (tmux/zellij), utilities (jq/yq/httpie/tokei), editor (neovim). Aliases en ~/.bashrc, symlinks bat→batcat, fd→fdfind. |

**Aliases configurados en `~/.bashrc` (lines 144-182):**
- `cat` → `bat --paging=never`, `ls` → `eza --icons --git`, `ll`/`la`/`lt`
- `grep` → `rg`, `find` → `fd`, `du` → `dust`, `df` → `duf`
- `fm` → `yazi`, `lg` → `lazygit`, `gu` → `gitui`, `zz` → `z`
- `img` → `chafa`, `imgt` → `timg`

**Symlinks:** `/usr/local/bin/bat` → `/usr/bin/batcat`, `/usr/local/bin/fd` → `/usr/bin/fdfind`

### DevOps & Systemd Tooling (`.opencode/skills/`)

| Skill | Ubicación | Descripción |
|-------|-----------|-------------|
| `devops-systemd-tooling` | `src/.opencode/skills/` | **NUEVO** — Patrones DevOps: systemd user services (service+timer), bash/curl scripting para Odoo JSON2 API (Bearer auth, /json/2/ endpoints), bashrc modification safety (sed+backup+validate), key masking, locking patterns, error handling. Incluye templates completos para scripts, anti-patrones (6), troubleshooting. |
| `docker-filesystem-cleanup` | `src/.opencode/skills/` | **NUEVO** — Metodología completa de limpieza Docker (imágenes/volúmenes huérfanos vía instances.json, build cache) y filesystem (Downloads, .cache, .local/share, custom/ dirs huérfanos). Incluye: detección de huérfanos, 5 fases de limpieza, umbrales de disco, Playwright reinstall post-purge, 7 anti-patrones. Referencia: R254-R259. |

### SDD Multi-Agent System (`.opencode/skills/`)

| Skill | Agente | Responsabilidad |
|-------|--------|-----------------|
| `sdd-lead-agent` | Lead | Orquestación, detección versión, quality gates, escalación |
| `sdd-explore-agent` | Explore | Investigación read-only: patrones, relaciones, contexto |
| `sdd-spec-agent` | Spec | Crear spec.md con requisitos EARS |
| `sdd-architect-agent` | Architect | Crear plan.md con research de codebase |
| `sdd-pm-agent` | PM | Crear tasks.md con trazabilidad EARS |
| `sdd-builder-agent` | Builder | Modo Manual: delega TDD a `binaural-fn-programador:senior-dev` y verifica tests/coverage/guardrails; Modo Delegación (OpenCode): implementa directamente |
| `sdd-qc-agent` | QC | Modo Manual: delega Gate 0 (code review) a `binaural-fn-programador:code-reviewer`; corre tests/coverage/trazabilidad EARS él mismo; genera qc-report.md, FAIL→BUG loop |
| `sdd-opencode-delegate-agent` | (Claude, sdd-opencode-runner) | **NUEVO** — Protocolo de delegación del pipeline SDD completo a `opencode run --agent sdd-lead --auto`, para ahorrar tokens de Sonnet |
| `sdd-opencode-guardrails` | — | **NUEVO** — Guardrails técnicos (permission `deny` por glob en `src/.opencode/agents/*.md`) para que OpenCode corra headless con `--auto` sin poder tocar `odoo-*.0/`/`enterprise-*.0/` ni autocommitear |
| `sdd-judge-agent` | (Claude, sdd-judge) | **NUEVO** — Verificación final independiente (Haiku) del resultado de OpenCode; no confía en el auto-reporte de `qc-report.md`, veredicto PASS/FAIL con hasta 3 reintentos (R5) |
| `sdd-openspec-bridge` | — | Puente hacia adelante entre el motor SDD y OpenSpec (`Fission-AI/openspec`, adoptado por el plugin de empresa `binaural-dev/IA-stack`); mapea spec.md/plan.md/tasks.md/QC ↔ proposal.md/Requirements-Scenarios/tasks.md/`/opsx:archive`. No migra las ~60 specs existentes en `src/specs/` |

**Plugins de empresa instalados** (marketplace `binaural-dev/IA-stack`, **actualizado 2026-08-17** tras el
breaking change v2.0.0 del stack — el modelo pasó de "un plugin por rol" a **función × departamento**):
`core@binaural` + `binaural-fn-programador@binaural` + `binaural-depto-producto@binaural`. Los nombres viejos
(`binaural-rol-programador-impl`, `binaural-depto-implementacion`) **ya no existen en el marketplace remoto**
y fueron desinstalados — si aparecen en `enabledPlugins` de algún `settings.json` hay que reemplazarlos o
Claude Code falla al resolverlos. Si en algún momento se necesita también el ángulo Implementación (en vez de
o junto a Producto), el plugin equivalente ahora es `binaural-depto-implementacion@binaural`.
`binaural-depto-producto` (con la skill `producto-flujo`) **ya existe** desde v2.0.0 — antes no. `core` trae
`flujo-programador`/`docker-odoo`/`odoo-testing`/`senior-dev`/`code-reviewer` vía `binaural-fn-programador` —
un flujo ligero humano-en-el-loop, independiente del SDD (no lo reemplaza). Nota de postura organizacional: el
propio changelog del stack descartó explícitamente traer una capa "sdd-\*" externa por considerarla "ceremonia
paralela a OpenSpec, que ya es la convención del stack" — no invalida este motor SDD (que ya trata OpenSpec
como interfaz pública y `src/specs/` como workspace interno, diseño compatible), pero es la posición oficial:
para IA-stack, OpenSpec solo alcanza.
Colisión de nombres a tener presente: `core` trae skills `odoo-base`/`odoo-security`/`odoo-repo-routing`/
`odoo-localization-flow`/`contexto-empresa`/`ciclo-y-gates`/`convenciones-git`/`escribir-en-chatter`/
`odoo-cloud`/`buscar-conocimiento` — usar con prefijo `core:` para convenciones organizacionales/Onyx/Odoo-vivo;
las skills sueltas del mismo nombre (sin prefijo) son la profundidad técnica Odoo 17.0/19.0 de este repo.
`core:convenciones-git` (nueva) trae la fórmula de nombre de rama, tags de commit por tipo de rama y el
esquema de versión `[Odoo].[A].[B].[C]` — contrastar contra `crear-texto-conventional-commit` de este repo.
`core:escribir-en-chatter` (nueva) trae la mecánica exacta de MCP para publicar en el chatter de Odoo
(`body_is_html=True`, `subtype="note"`, sumar a `github_pr_ids` sin reemplazar) — completa el detalle que
`sdd-openspec-bridge` da por hecho en su Gate 6. El agente `code-reviewer` de `binaural-fn-programador` ahora
contrasta contra el requerimiento (lee la tarea desde el nombre de la rama, baja imágenes de la descripción)
antes de mirar el diff — mejora aplicable al criterio de `sdd-judge`/`sdd-qc`.
OpenSpec (`openspec init --tools claude`) ya corre en los 5 repos de addons con git propio
(`integra-addons-{17.0,19.0}`, `odoo-venezuela-{17.0,19.0}`, `integra-addons-l10nve_17.0`); vertical `nomina`
ya tenía historial real. `docs-as-code/verticals.yaml` del stack remoto (2026-08-17) solo registra `nomina`
formalmente — `website` no está ahí todavía aunque este repo ya lo trata como vertical activo; verificar si
falta registrarlo del lado de IA-stack. La adopción de OpenSpec sigue siendo **progresiva, vertical por
vertical** — confirmado sin cambios contra lo que ya documenta `sdd-openspec-bridge`.

**Plugins oficiales instalados** (`claude-plugins-official`, 7 de 12 evaluados): `playwright` (MCP e2e,
complementario para el vertical `website`), `code-review` y `pr-review-toolkit` (revisión genérica — para
Odoo mandan `odoo-code-review-17.0/19.0` + `binaural-fn-programador:code-reviewer`; ojo con la
colisión de nombre `code-reviewer` entre `pr-review-toolkit` e IA-stack), `code-simplifier` (segunda opinión
tras `/simplify`), `claude-md-management` (**usar solo manualmente** — no conoce el diseño deliberado de
"Skills: where to look" de este `CLAUDE.md`, verificar que esa sección quede intacta tras usarlo),
`frontend-design` (complementario a las skills OWL Odoo-específicas), `claude-code-setup` (asesor, sin
fricción). **Descartados a propósito**: `explanatory-output-style`, `learning-output-style`,
`security-guidance`, `commit-commands` (sin Gate 6 ni formato de commit en español), `feature-dev`
(compite con `sdd-lead`). Detalle completo en `src/Agents.md`.

**Flujo Modo Manual**: Lead → Explore → Spec → Architect → Explore → PM → Builder → Explore → QC → Lead (cierre)
**Flujo Modo Delegación (default)**: `sdd-lead` (Sonnet) → `Task(sdd-opencode-runner, dispatch)` → `scripts/sdd_opencode_run.sh` lanza `opencode run --agent sdd-lead --auto` (pipeline completo) dentro de una **sesión tmux detached** y retorna de inmediato (`status:"running"`, no bloquea) → `sdd-lead` repite `Task(sdd-opencode-runner, status-check)` con el `job_id` hasta estado terminal (`done`/`failed`/`orphaned`, vía `scripts/sdd_opencode_status.sh`) → `sdd-judge` (Haiku) → PASS/reintento/escalación. `scripts/sdd_opencode_cleanup.sh` reapea jobs/sesiones tmux con TTL (default 6h).
**Versiones**: 19.0 (principal) + 17.0 (secundario) — detectado de `__manifest__.py`
**Plugin instalado**: `swarm-code@swarm-code` (marketplace `apoapps/swarm-code-plugin`) — provee el patrón relay Haiku→CLI (dispatch bloqueante) del que partió `sdd-opencode-runner`; `scripts/sdd_opencode_run.sh` es un wrapper propio, ya no basado en el pipe foreground de `oc-run.sh` del plugin.

**tmux + handoffs tipados (adaptado de `unclebob/swarm-forge`, 2026-08-06/07)**: el pipe foreground original
(`opencode | while read ... > $OUT`, sin `&`/`nohup`/tmux) moría cuando el pipeline SDD completo excedía el
timeout del tool Bash — el harness mataba el proceso a mitad de camino, sin checkpoint. swarm-forge resuelve
esto en su propio dominio (agentes CLI persistentes por rol en tmux, con un daemon `handoffd.bb` que entrega
mensajes vía outbox/inbox) — se adaptó solo la pieza necesaria: `sdd_opencode_run.sh` ahora lanza `opencode`
dentro de una sesión tmux detached (`/tmp/sdd-tmux/sdd.sock`, una sesión por `job_id`) que sobrevive tanto a la
llamada Bash que la creó como al subagente Haiku completo que la disparó — validado experimentalmente con dos
subagentes independientes sin contexto compartido. Cada job vive en `/tmp/sdd-jobs/<job_id>/` con
`dispatch.handoff`/`result.handoff` (mensajes tipados con headers `type/from/to/job/status/exit_code`, estilo
swarm-forge) + `status`/`exit_code`/`output.log`. **No** se adoptó el daemon de swarm-forge ni su topología de
git-worktree-por-rol: el polling lo hace `sdd-lead` mismo, repitiendo `Task(sdd-opencode-runner, status-check)`
— no hay tty interactivo que despertar ni múltiples roles concurrentes escribiéndose entre sí.

**Ventana tmux visible (opcional, 2026-08-25)**: la sesión tmux detached de arriba es invisible por defecto —
solo se monitorea por polling de texto (`sdd_opencode_status.sh`). `scripts/sdd_opencode_view.sh <job_id>`
abre una **ventana de terminal del sistema operativo aparte** (no la que tiene la conversación con Claude
Code) adjuntada a ese tmux, para ver al agente trabajar en vivo. El emulador es configurable: fuerza uno con
`SDD_TMUX_TERMINAL=<binario>` (env var, sin nuevo formato de config), o déjalo autodetectar el primero
disponible en PATH entre `gnome-terminal`, `konsole`, `xfce4-terminal`, `kitty`, `alacritty`, `wezterm`,
`foot`, `terminator`, `xterm`. Sin `DISPLAY`/`WAYLAND_DISPLAY` o sin ningún emulador conocido, no falla:
responde `"status":"skipped"` con el `attach_cmd` manual (`tmux -S /tmp/sdd-tmux/sdd.sock attach -t <job_id>`).
`sdd_opencode_run.sh` la invoca automáticamente al dispatchar solo si `SDD_TMUX_AUTO_VIEW=1` está seteada en
el entorno del usuario — por defecto queda desactivado para no abrir ventanas en corridas headless/CI.

### SudoLang Cache Engine (`.opencode/skills/`)

Skills del plugin `sudolang-cache-engine` portado de Claude Code a OpenCode (septiembre 2026).
Define la gobernanza de cache de agentes: Frente Estable/Fondo Volátil, Context{} block conventions,
y las 6 reglas SudoLang para optimizar uso de contexto de LLMs.

| Skill | Descripción |
|-------|-------------|
| `sudolang-cache-architecture` | Layout Frente Estable/Fondo Volátil, sizing guidance, authoring checklist |
| `sudolang-temporal-layering` | Forbidden/required in stable vs dynamic blocks, relay-fidelity fix |
| `sudolang-stigmergic-coordination` | Shared state via file refs, SDD artifact table, Context{} stage field |
| `sudolang-fork-agent-patterns` | Fork vs fresh subagent decision, two-phase fan-out rejected |
| `sudolang-progressive-disclosure` | Keep stable prompt small, load on demand via Skills |
| `sudolang-ttl-management` | TTL mechanics (5min/1hr), append-only state, model-gated exception |
| `sudolang-cache-engine` | **Umbrella skill** — tying all rules together, token reduction, anti-patterns |

Agentes asociados: `cache-analyzer` (read-only), `cache-optimizer` (read+write).
Comandos: `/cache-audit`, `/cache-optimize`, `/cache-test`.
Ver skill `sudolang-cache-engine-governance` para gobernanza completa en OpenCode.

### IA-Stack Business Skills (`.opencode/skills/`)

Skills de negocio de Binaural portados desde los plugins IA-stack de Claude Code (septiembre 2026).
Cubren flujos departamentales, gestión de clientes, requerimientos, release notes y QA.

| Skill | Departamento | Líneas | Descripción |
|-------|-------------|--------|-------------|
| `atencion-cliente-flujo` | ATC | 215 | Triage, 3 verticales (soluciones/nuevos desarrollos/migraciones), clasificación |
| `consultar-para-decidir` | Gerencia | 149 | Queries MCP Odoo, decision-first, reliability reporting |
| `estado-cola` | Coordinación | 157 | Queue status, señales por costo, preparación de triaje |
| `levantamiento-requerimiento` | Consultoría | 104 | GIVEN/WHEN/THEN, 7 secciones, reusable vs custom |
| `proyectos-especiales-flujo` | Especiales | 105 | "Mini Binaural", co-dirigido, flujo independiente |
| `release-notes` | Producto | 131 | Formato release, versionado (línea+trimestre+estado), 🔴/🟣 |
| `solicitud-vs-alcance` | Consultoría | 127 | 8 veredictos, 5 fuentes ordenadas, formato basado en evidencia |
| `validar-entrega-vs-spec` | QA | 193 | 3 roles QA, validación spec→alcance→comportamiento |
| `implementacion-flujo` | Implementación | 354 | Flujo completo: kickoff, gaps, producción, handoff ATC |
| `producto-flujo` | Producto | 329 | Verticales, licencias, versionado, catálogo de niveles |
| `auditar-documentacion` | Producto | 116 | Gap detection código vs artículos Knowledge |
| `configurar-cliente-nuevo` | Implementación | 118 | Clasificación modelo negocio, reuso de clientes similares |
| `construir-solucion` | Consultoría | 116 | Auto-construcción con matriz rojo/amarillo/verde |
| `historial-decisiones` | Producto | 93 | Timeline de decisiones desde Drive+Odoo+git+specs |
| `documentar-funcionalidad` | Producto | 130 | Pipeline código→spec→artículo Knowledge |

**NO portados** (genéricos Claude-specific): docx, pdf, pptx, xlsx, morning, docs, import-memory.

### Binaural Agents — OpenCode (`.opencode/agents/`)

Agentes Binaural definidos para OpenCode, portados desde plugins Claude (septiembre 2026).
Todos usan `opencode-go/mimo-v2.5`.

| Agente | Archivo | Modelo | Descripción |
|--------|---------|--------|-------------|
| `senior-dev` | `senior-dev.md` | mimo-v2.5 | Desarrollo Odoo: routing departamento/repo, checklist validación, gate protocol |
| `code-reviewer` | `code-reviewer.md` | mimo-v2.5 | Review requirement-first (Paso 0: leer tarea+imágenes antes del diff), 7 prioridades |
| `sdd-metrics-reporter` | `sdd-metrics-reporter.md` | mimo-v2.5 | Observer read-only: agrega metrics.jsonl, escribe reportes en src/.sdd/reports/ |
| `cache-analyzer` | `cache-analyzer.md` | mimo-v2.5 | Scanner read-only: detecta pollution risks en prompts de agentes |
| `cache-optimizer` | `cache-optimizer.md` | mimo-v2.5 | Rewriter: reestructura templates en layout stable+dynamic |

**Agentes SDD** (pre-existentes): sdd-lead, sdd-spec, sdd-architect, sdd-pm, sdd-builder, sdd-qc, explore, sdd-audit-writer.
Ver sección `SDD Multi-Agent System` para detalles de los agentes SDD.

### Commands — OpenCode (`.opencode/commands/`)

| Comando | Descripción |
|---------|-------------|
| `cache-audit` | Escanea agentes .md para pollution risks de cache |
| `cache-optimize` | Reestructura un agente en layout stable+dynamic |
| `cache-test` | Verifica estabilidad byte-for-byte entre variantes |
| `pre-commit` | Pre-commit para módulos Odoo (Binaural) |
| `tests` | Ejecución de tests con coverage |
| `test_coverage` | Coverage de tests |
| `index-17` | Indexación de skills Odoo 17.0 |
| `index-19` | Indexación de skills Odoo 19.0 |
| `re-index` | Re-indexación de skills |
| `ejecutar-flujo` | Ejecución de flujos SDD |
| `crear_actualiza_documentacion` | Crear/actualizar documentación |
| `actualiza_ambiente_staging` | Actualizar ambiente de staging |

### Odoo 17.0 Skills (`.opencode/17.0/skills/`)

| Skill | Descripción |
|-------|-------------|
| `odoo_orm_backend-17.0` | ORM: CRUD, search, fields, api decorators (media) |
| `odoo_owl_backend-17.0` | OWL backend views, widgets, registry (media) |
| `odoo_owl_website-17.0` | OWL website snippets, portal, e-commerce (media) |
| `odoo_security_api_ai-17.0` | XSS, SQL injection, auth, access control (media) |
| `odoo_tools_core-17.0` | SQL, safe_eval, cache, config, translate (media) |
| `odoo_reports-17.0` | QWeb reports, PaperMuncher (media-baja) |
| `odoo_devops-17.0` | CLI, deployment, DB management (media-baja) |
| `odoo_documentation-17.0` | Documentación oficial Odoo 17 (raw) |
| `odoo-code-review-17.0` | Checklist code review (FIX-001 a FIX-070) |
| `odoo-performance-17` | N+1, batch-first, CRUD optimizado, índices |
| `owl-framework-v2-17.0` | Referencia pura OWL 2.x (hooks, useState) |
| `odoo-design-patterns-creational-17.0` | **NUEVO** — Patrones GoF creacionales: Singleton, Factory, Builder, Prototype aplicados a Odoo 17.0 |
| `odoo-design-patterns-structural-17.0` | **NUEVO** — Patrones GoF estructurales: Adapter, Decorator, Composite, Proxy, Bridge, Facade aplicados a Odoo 17.0 |
| `odoo-behavioral-patterns-17.0` | **NUEVO** — Patrones GoF comportamiento: Observer, Command, Strategy, Template Method, State, Chain, Iterator, Visitor, Mediator, Memento aplicados a Odoo 17.0 |
| `odoo-solid-srp-ocp-17.0` | **NUEVO** — SOLID I: SRP (Single Responsibility) y OCP (Open/Closed) aplicados a Odoo 17.0. Mixins, _inherits, controladores delgados, _build_model, herencia de vistas, naming convention, anti-patrones |
| `odoo-solid-lsp-isp-dip-17.0` | **NUEVO** — SOLID II: LSP (Liskov Substitution), ISP (Interface Segregation), DIP (Dependency Inversion) aplicados a Odoo 17.0. MRO chain, super() contracts, mixins pequeños vs fat interfaces, Environment como Service Locator, Registry como DI Container, anti-patrones de imports directos |
| `odoo-layered-architecture-17.0` | **NUEVO** — Arquitectura de 5 capas de Odoo 17.0: HTTP/Controller, Service/Business, ORM/Persistence, Presentation/Views, Security. Patrones Bridge (ir.http), Pipeline (search→_search→_fetch_query), Template Method, Strategy, Visitor. Violaciones: layer skipping, sudo() wholesale, direct SQL bypass. 12 referencias a archivos fuente 17.0. |
| `odoo-event-driven-17.0` | **NUEVO** — Arquitectura Event-Driven de Odoo 17.0: bus.bus (Pub-Sub + PostgreSQL NOTIFY), Mail Notifications (3-channel dispatch), Automated Actions (base_automation + trigger taxonomy), Webhooks (inbound + outbound), Precommit/Postcommit hooks (transacciones), ORM Event System (modified() + _field_triggers), @api.onchange (UI events). 28+ bloques de código verificados contra codebase real. |
| `odoo-owasp-injection-xss-17.0` | **NUEVO** — OWASP Injection & XSS Prevention para Odoo 17.0: SQL Injection (ORM parameterized, SQL() helper, cr.execute seguro), XSS (t-out auto-escape, Markup, t-raw deprecado), Command Injection (safe_eval opcodes), Path Traversal (attachment validation), SSTI (QWeb compile seguro), XXE (etree parsing). 18 referencias a archivos fuente. Anti-patrones con severidad. |
| `odoo-event-driven-17.0` | **NUEVO** — Arquitectura Event-Driven de Odoo 17.0: bus.bus (Pub-Sub + PostgreSQL NOTIFY), Mail Notifications (3-channel dispatch), Automated Actions (base_automation + trigger taxonomy), Webhooks (inbound + outbound), Precommit/Postcommit hooks (transacciones), ORM Event System (modified() + _field_triggers), @api.onchange (UI events). 28+ bloques de código verificados contra codebase real. |
| `oca-17-contributing-guidelines` | **NUEVO** — OCA Contributing Guidelines aplicadas a Odoo 17.0: naming de módulos, estructura de directorios, file naming, XML/Python/JS/CSS convenciones, SQL seguras, tests (flaky prevention), Git commits, code review. 1,160 líneas. |
| `oca-module-lifecycle` | **NUEVO** — OCA Module Lifecycle: 4 niveles de madurez (Alpha/Beta/Stable/Mature), requisitos por nivel, maintainer role y responsabilidades, política de repositorios OCA, incubación de módulos. 1,078 líneas. |
| `oca-contribution-workflow` | **NUEVO** — OCA Contribution Workflow: Git commit format y tags, PR lifecycle y merge criteria, code review checklist, CI/testing, debugging en Runbot, documentación readme/. 478 líneas. |
| `odoo-17-subscription-invoice-currency` | **ACTUALIZADO** — Conversión de moneda en facturas de suscripción con localización venezolana (Odoo 17.0): `_prepare_invoice()` override forzando currency_id a VES + recalculación de moneda alterna (AC) con `company.currency_foreign_id` y `_get_conversion_rate()`; `_prepare_invoice_line()` con `price_unit` convertido via `_convert()` + `foreign_price`/`foreign_subtotal` hacia moneda alterna; `_recompute_subscription_rates()` con sync de `foreign_currency_id`; `_recompute_foreign_rates()` + onchange integration; rate semantics USD vs non-USD; constraint `_check_currency_id` de `l10n_ve_accountant`; MRO chain; tests 280-312; code review rules FIX-SIC-001 a 010. Skill en `.opencode/17.0/skills/odoo-17-subscription-invoice-currency/SKILL.md`. |
| `odoo-17-subscription-validation-patterns` | **NUEVO** — Patrones de validación en suscripciones (Odoo 17.0): dependencia circular `is_sale_order` vs `is_subscription`, `action_confirm()` vs `@api.constrains`, `required` condicional con contexto, XPath en fields duplicados por groups. 5 anti-patrones, 4 reglas RQ-FIX, código de referencia del fix implementado en `cadipa_sale_suscription`. Skill en `.opencode/17.0/skills/odoo-17-subscription-validation-patterns/SKILL.md`. |

### PostgreSQL/BD Skills (`.opencode/17.0/skills/` — 20 skills, ~9,550 líneas)

Ciclo de automejoramiento de 20 loops para PostgreSQL/BD en Odoo 17.0. Analiza `odoo-17.0/odoo/sql_db.py`, `odoo/models.py`, `odoo/fields.py`, `odoo/tools/sql.py`, `odoo/modules/registry.py`, y addons custom. Base de datos estudio: `cadipa1_db_study` (437 tables, 28 MB, PG 16.14).

| # | Skill | Área | Líneas |
|---|-------|------|--------|
| 001 | `odoo-db-architecture-17.0` | ConnectionPool, Cursor, Savepoint, Registry singleton | 698 |
| 002 | `odoo-ddl-schema-17.0` | DDL functions, `_auto_init()`, column/constraint evolution | 924 |
| 003 | `odoo-orm-type-mapping-17.0` | 18 field types → PG types, 4-stage conversion pipeline | 632 |
| 004 | `odoo-indexing-strategies-17.0` | Index types, `check_indexes()`, trigram/GIN, naming | ~450 |
| 005 | `odoo-explain-analyze-17.0` | Query timing, execution plans, table tracking | ~400 |
| 006 | `odoo-window-functions-17.0` | ROW_NUMBER, SUM OVER, LAG, FIRST_VALUE (33 usages) | ~350 |
| 007 | `odoo-cte-recursive-17.0` | 45 CTE usages, recursive view inheritance, parent_path | ~400 |
| 008 | `odoo-aggregation-grouping-17.0` | `_read_group()`, 10 aggregates, 6 time granularities | ~400 |
| 009 | `odoo-jsonb-array-17.0` | Json/Properties fields, translation JSONB, 8 JSONB functions | ~400 |
| 010 | `odoo-datetime-interval-17.0` | timezone(), date_trunc(), INTERVAL, UTC storage | ~400 |
| 011 | `odoo-connection-pooling-17.0` | ConnectionPool, worker architecture, LISTEN/NOTIFY | ~400 |
| 012 | `odoo-vacuum-statistics-17.0` | @api.autovacuum, TransientModel GC, pg_stat views | ~350 |
| 013 | `odoo-lock-management-17.0` | FOR UPDATE, SKIP LOCKED, NOWAIT, savepoint patterns | ~350 |
| 014 | `odoo-batch-bulk-17.0` | INSERT_BATCH_SIZE=100, IN_MAX=1000, execute_values() | ~500 |
| 015 | `odoo-table-partitioning-17.0` | Logical partitioning: _table_query, _auto=False, _inherits | ~500 |
| 016 | `odoo-db-security-17.0` | 6-layer security: ACL, Record Rules, SQL class, sudo() | ~500 |
| 017 | `odoo-backup-pitr-17.0` | pg_dump, restore, duplicate, neutralization, obfuscation | ~450 |
| 018 | `odoo-db-monitoring-17.0` | Profiler, query counters, cache stats, PerfFilter | ~450 |
| 019 | `odoo-custom-module-db-17.0` | Custom SQL patterns, hooks, migrations, PL/pgSQL | ~500 |
| 020 | `odoo-db-master-reference-17.0` | **SÍNTESIS** — Cross-reference 19 skills, decision trees, top 30 anti-patterns | ~500 |

### OWL Framework Skills

| Skill | Versión OWL | Versión Odoo | Contenido |
|-------|-------------|-------------|-----------|
| `owl-framework-v3-19.0` | OWL 3.x (master) | Odoo 18+ (NOT 19!) | Referencia pura OWL 3: signals, plugins, scopes, proxies, ErrorBoundary, Suspense, computed, effects, types system. ⚠️ Odoo 19 usa OWL 2.8.2, no OWL 3. Este skill es referencia futura. |
| `owl-framework-v2-17.0` | OWL 2.x (owl-2.x) | Odoo 16/17 | Referencia pura OWL 2: hooks, useState, reactive, lifecycle, templates, environment, input bindings. 27 archivos de documentación oficial. |

**Diferencia clave**: Los skills `odoo_owl_backend-*` y `odoo_owl_website-*` describen **componentes de Odoo** que usan OWL internamente. Los skills `owl-framework-v3-19.0` y `owl-framework-v2-17.0` contienen la **referencia pura del framework OWL** (descargada del repo oficial). **Odoo 19 usa OWL 2.8.2, no OWL 3.x** — `owl-framework-v3-19.0` es solo referencia para futura migración.

### Skills 19.0 Especializados (`.opencode/19.0/skills/` — 100 skills: 80 originales + 20 nuevos Context/DRY)

| # | Skill | Área |
|---|-------|------|
| 1 | `hoot-hands-on-19.0` | HOOT hands-on |
| 2 | `hoot-testing-framework-19.0` | HOOT framework |
| 3 | `odoo-anti-patterns-19.0` | Anti-patrones |
| 4 | `odoo-batch-queue-19.0` | Batch/Queue |
| 5 | `odoo-behavioral-patterns-19.0` | Patrones GoF comportamiento |
| 6 | `odoo-code-examples-19.0` | Snippets/cookbook |
| 7 | `odoo-coding-standards-19.0` | **NUEVO** — Coding standards |
| 8 | `odoo-connect-device-19.0` | **NUEVO** — IoT Box/Drivers |
| 9 | `odoo-context-keys-19` | Context keys |
| 10 | `odoo-controllers-19.0` | Controllers |
| 11 | `odoo-controller-testing-19.0` | Controller testing |
| 12 | `odoo-data-api-19.0` | Export/Import |
| 13 | `odoo-design-patterns-creational-19.0` | Patrones creacionales |
| 14 | `odoo-design-patterns-structural-19.0` | Patrones estructurales |
| 15 | `odoo-documentation-guidelines-19.0` | **NUEVO** — Documentación RST |
| 16 | `odoo-enterprise-ai-19.0` | Enterprise AI |
| 17 | `odoo-enterprise-ai-deep-19.0` | Enterprise AI deep |
| 18 | `odoo-enterprise-approvals-19.0` | Approvals |
| 19 | `odoo-enterprise-barcode-19.0` | Barcode |
| 20 | `odoo-enterprise-document-19.0` | Documents |
| 21 | `odoo-enterprise-iot-19.0` | Enterprise IoT |
| 22 | `odoo-enterprise-security-19.0` | Enterprise security |
| 23 | `odoo-enterprise-sign-19.0` | Sign |
| 24 | `odoo-enterprise-studio-19.0` | Studio |
| 25 | `odoo-enterprise-views-19.0` | Enterprise views |
| 26 | `odoo-event-driven-19.0` | Event-driven architecture |
| 27 | `odoo-external-api-19.0` | **NUEVO** — External API /json/2 |
| 28 | `odoo-extract-api-19.0` | **NUEVO** — OCR/Extract API |
| 29 | `odoo-frontend-assets-19.0` | Asset bundling |
| 30 | `odoo-http-controllers-advanced-19.0` | HTTP controllers advanced |
| 31 | `odoo-icons-ui-19.0` | Icons/UI |
| 32 | `odoo-integration-patterns-19.0` | Integration |
| 33 | `odoo-layered-architecture-19.0` | 5-layer architecture |
| 34 | `odoo-meta-learning-19.0` | **NUEVO** — Meta-learning |
| 35 | `odoo-mixins-19.0` | Mixins |
| 36 | `odoo-mobile-19.0` | Mobile/PWA |
| 37 | `odoo-multicompany-19.0` | Multi-company |
| 38 | `odoo-odoo-editor-19.0` | WYSIWYG editor |
| 39 | `odoo-odoo-sh-19.0` | Odoo.sh |
| 40 | `odoo-on-premise-19.0` | On-premise |
| 41 | `odoo-orm-advanced-19.0` | ORM advanced |
| 42 | `odoo-orm-new-features-19.0` | ORM new features |
| 43 | `odoo-owasp-auth-session-19.0` | OWASP auth/session |
| 44 | `odoo-owasp-injection-xss-19.0` | OWASP injection/XSS |
| 45 | `odoo-owl-component-patterns-19.0` | OWL component patterns |
| 46 | `odoo-owl-deep-dive-19.0` | OWL deep dive |
| 47 | `odoo-owl-integration-19.0` | OWL integration |
| 48 | `odoo-owl-services-19.0` | OWL services |
| 49 | `odoo-passkey-webauthn-19.0` | Passkey/WebAuthn |
| 50 | `odoo-performance-profiling-19.0` | Performance/profiling |
| 51 | `odoo-python-best-practices-19.0` | Python best practices |
| 52 | `odoo-quick-create-edit-19.0` | Quick create/edit |
| 53 | `odoo-qweb-directives-19.0` | QWeb directives |
| 54 | `odoo-qweb-inheritance-19.0` | QWeb inheritance |
| 55 | `odoo-qweb-server-19.0` | QWeb server |
| 56 | `odoo-reports-19.0` | Reports |
| 57 | `odoo-scss-architecture-19.0` | SCSS architecture |
| 58 | `odoo-scss-theming-19.0` | SCSS theming |
| 59 | `odoo-security-complete-19.0` | **NUEVO** — Security síntesis |
| 60 | `odoo-security-hardening-19.0` | Security hardening |
| 61 | `odoo-sequences-19.0` | Sequences |
| 62 | `odoo-solid-lsp-isp-dip-19.0` | SOLID LSP/ISP/DIP |
| 63 | `odoo-solid-srp-ocp-19.0` | SOLID SRP/OCP |
| 64 | `odoo-standard-models-19.0` | Standard models |
| 65 | `odoo-tdd-owl-javascript-19.0` | JS/OWL testing |
| 66 | `odoo-tdd-python-19.0` | Python testing |
| 67 | `odoo-architecture-complete-19.0` | **NUEVO** — Arquitectura completa |
| 68 | `odoo-translations-19.0` | i18n/translations |
| 69 | `odoo-upgrade-guide-19.0` | **NUEVO** — Migración 17→19 |
| 70 | `odoo-upgrade-scripts-19.0` | Upgrade scripts |
| 71 | `odoo-view-attributes-19.0` | View attributes |
| 72 | `odoo-website-theming-19.0` | Website theming |
| 73 | `odoo-websocket-19.0` | WebSocket |
| 74 | `odoo-wsgi-middleware-19.0` | WSGI middleware |
| 75 | `odoo-xml-form-deep-19.0` | XML form deep |
| 76 | `odoo-xml-graph-pivot-calendar-19.0` | XML graph/pivot/calendar |
| 77 | `odoo-xml-list-view-19.0` | XML list view |
| 78 | `odoo-xml-search-kanban-19.0` | XML search/kanban |
| 79 | `odoo-xml-views-advanced-19.0` | XML views advanced |
| 80 | `odoo-xml-views-basic-19.0` | XML views basic |
| 81 | `odoo-core-guardrails-19.0` | **NUEVO** — Core modification guardrails: prohibición de modificar odoo-19.0/ y enterprise-19.0/, alternativas legales, detección CI |
| 82 | `oca-19-contributing-guidelines` | **NUEVO** — OCA Contributing Guidelines aplicadas a Odoo 19.0: naming de módulos, estructura de directorios, XML/Python/JS/CSS convenciones, Domain.AND/OR, models.Constraint, @api.ondelete, HOOT testing, ES2020+. 1,128 líneas. |
| 83 | `odoo-19-boolean-setting-pattern` | **NUEVO** — Patrón reutilizable setting boolean Odoo 19: campo res.company + related res.config.settings + xpath en block (analytic/invoicing/tax/etc). Convenciones naming, grupos, CSS classes. Caso real: TI-15326 |

### Referencia Global (`~/.config/opencode/skills/`)

| Skill | Relevancia para Odoo 19 |
|-------|------------------------|
| `translation-i18n-patterns` | **ACTUALIZADO** — incluye JS `_t()` transpiler, QWeb templates |
| `qweb-template-patterns` | QWeb server-side syntax |
| `assets-bundling-patterns` | Asset bundles, SCSS, lazy loading |
| `guia_precommit_odoo` | Guía de pre-commit para módulos |
| `odoo-translation-precommit-patterns` | **NUEVO** — Patrones de traducción que pasan precommit: W8301/W8120/W8303, `.format()` como único patrón válido, mandatory vs optional checks |
| `odoo-development-skills` | Universal dev skill (14-19) |

## Pre-commit

```bash
cd /home/binlp011/sources/docker-multi
python3 scripts/precommit <instancia> -m <modulo1,modulo2>
```

**Third-party addons están excluidos** del pre-commit (config rama `19`).

Ver skill `workspace-structure` para instancias disponibles y validaciones.

## Docker Instances

| Instancia | Odoo | Puerto | Estado |
|-----------|------|--------|--------|
| `qa-consultoria-19-tests` | 19.0 | 8073 | Principal para desarrollo |

```bash
# Actualizar módulo
docker exec odoo-qa-consultoria-19-tests odoo -d odoo19_clean_cart -u <modulo> --load-language=es_VE --http-port=8099 --stop-after-init
```

## Reglas Clave

1. **Detectar versión Odoo** antes de generar código (leer `__manifest__.py`)
2. **Buscar módulos existentes** antes de crear nuevos (Odoo core → OCA → custom)
3. **JS `_t()`**: usar `require()`, NO `import` (transpilador Odoo 19)
4. **Templates UI**: usar `static/src/xml/`, NO `innerHTML` con `_t()`
5. **Pre-commit** antes de commit: `python3 scripts/precommit <instancia> -m <modulo>`
6. **Tests** después de pre-commit verde
7. **Traducciones**: generar `.po`, llenar `msgstr`, cargar con `--load-language`
8. **Context keys**: SIEMPRE usar `warehouse_id` (con `_id`), NUNCA `warehouse` para stock
9. **Tests**: NUNCA hacer `req.env = self.env(user=...)` — borra context HTTP (`lang`, etc.)
10. **Float compare**: SIEMPRE usar `float_compare()` en comparaciones de stock/cantidades
11. **Recordset safety**: SIEMPRE verificar `if recordset:` antes de `recordset[0]` — vacíos lanzan `IndexError`
12. **Move IDs Odoo 19**: NUNCA usar `move_ids_without_package` — usar `move_ids` (LESSON #10, FIX-032)
13. **Config parameters**: `get_param()` retorna strings — comparar con `== 'True'`, NUNCA usar en `t-if` directo (FIX-033)
14. **Dead controllers**: Import comentado en `__init__.py` = controller muerto — eliminar directorio `controllers/` (FIX-034)
15. **HTML security**: `<a target="_blank">` SIEMPRE con `rel="noopener noreferrer"` — reverse tabnabbing (FIX-035)
16. **Module scope**: Assets en `__manifest__.py` DEBEN corresponder a la funcionalidad declarada — no scope creep (FIX-036)
17. **Dead assets + PO cleanup**: Archivos en `static/` NO declarados en manifest son dead; al eliminar JS, limpiar entradas PO `#. odoo-javascript` asociadas (FIX-037)
18. **JS `start()` return `this._super()`**: En `publicWidget.Widget.extend()`, `start()` DEBE retornar `this._super(...arguments)` — `attachTo()` lo espera como Promise (FIX-038)
19. **ES2020 optional chaining**: `?.` y `??` son seguros en Odoo 19 (Chromium 90+); usar `?.focus()` para focus management seguro (FIX-039)
20. **RPC Error Handling**: `await rpc()` en event handlers DEBE estar dentro de `try/catch`. No ocultar modales/UI antes de que el RPC termine. En catch, mostrar error y permitir reintento. (FIX-040)
21. **Focus Restoration**: Al abrir un modal, guardar `document.activeElement` en variable de instancia. Al cerrarlo, restaurar el foco con `?.focus?.()` y limpiar la referencia con `= null`. Sigue el patrón de Odoo core `dropdown.js:346-352`. (FIX-041, WCAG 2.1)
22. **Onchange + batch**: NUNCA llamar métodos `@api.model` batch desde `@api.onchange`. Los métodos batch operan sobre BD, no sobre cache. Usar métodos que asignen en cache: `_recompute_foreign_rates()`, `_recompute_portal_fields()`. (FIX-030/17.0, FIX-041/19.0)

23. **Portal fields plain + `copy=False`**: Campos de portal display DEBEN ser `store=True` planos (sin compute), con `copy=False`. Usar `_convert()` directo (NUNCA `foreign_rate`). Sin freeze ni cache-skip. (FIX-031/17.0, FIX-042/19.0, Skill `odoo-17-subscription-portal-rate`)

24. **Singleton Registry Odoo 17**: `Registry` es singleton por DB vía `__new__` + LRU. Usar `self.env['modelo']` como Service Locator, nunca acceder a `self.env.registry` directamente. Cachear con `@ormcache` es seguro per-registry pero inconsciente de contexto multi-compañía. (Patrones Creacionales 17.0)
25. **Factory vs Abstract Factory**: Odoo 17 usa Simple Factory y Factory Method (MetaField.by_type, _build_model). NO implementa Abstract Factory — la familia de productos (modelo+vista+acción) se define declarativamente en XML, no programáticamente. (Patrones Creacionales 17.0)
26. **_prepare_* sin side effects**: Los métodos `_prepare_invoice()`, `_prepare_move_line_vals()` DEBEN ser puros — retornar dict sin mutar `self` ni los argumentos. Usar copia defensiva: `values = dict(values or {})` al inicio. (Patrones Creacionales 17.0)
27. **Mixin como Adapter**: `mail.thread`, `portal.mixin`, `rating.mixin` son Adapters GoF. 77+ modelos se adaptan via `_inherit`. Los mixins usan `self._name` para determinar dinámicamente qué modelo concreto están adaptando. (Patrones Estructurales 17.0)
28. **Decorator chain via _inherit**: Cada módulo con `_inherit` apila una capa Decorator en el MRO de la clase registry. TODO método base DEBE llamar a `super()` al final para mantener la cadena Decorator. Métodos como `stock.picking.action_confirm()` que NO llaman a `super()` rompen la cadena para todos los módulos decoradores. (Patrones Estructurales 17.0)
29. **Proxy stacking consciente**: `sudo()`, `with_company()`, `with_context()`, y `with_user()` son Proxys stackeables via `with_env()`. Cada proxy debe tener un comentario explicando por qué es necesario. `sudo()` sin documentación viola Principle of Least Privilege. (Patrones Estructurales 17.0)
30. **Domain expressions con AND/OR**: Preferir `expression.AND([...])` y `expression.OR([...])` sobre notación de prefijo polaco directa. Dominios con 4+ niveles de `['&', '|', ...]` son ilegibles y propensos a errores. `AND()` maneja identity element (TRUE_LEAF) y absorbing element (FALSE_LEAF) correctamente. (Patrones Estructurales 17.0)
31. **Self-Implementing Bridge**: `BaseModel` actúa como Abstraction e Implementor simultáneamente, diferenciado por flags (`_auto`, `_abstract`, `_transient`, `_register`). `MetaModel` es el Bridge builder que captura definiciones en tiempo de import, y `_build_model()` con `type()` crea los ConcreteImplementors dinámicos. (Patrones Estructurales 17.0)
32. **Observer trigger tree**: El ORM usa un trigger tree (`Registry._field_triggers`) para notificaciones cross-model. `modified()` recorre el árbol y marca en `Transaction.tocompute`. Usar `protecting()` para evitar ciclos de recomputación. (Patrones Comportamiento 17.0)
33. **Command con factory methods**: Usar SIEMPRE `Command.create()`, `Command.update()`, etc. sobre tuplas raw `(0, 0, vals)`. Las tuplas raw son opacas y propensas a errores. `write_batch()` normaliza formatos implícitos (tuplas, recordsets, None, int lists) a Command explícitos. (Patrones Comportamiento 17.0)
34. **Template Method con super() obligatorio**: Los métodos `_prepare_*()`, `default_get()`, `create()`, `write()` son skeletons con hooks. Toda subclase DEBE llamar a `super()` para mantener la cadena. Los métodos `_prepare_*` DEBEN ser puros (sin side effects) — usar `dict(values or {})` como copia defensiva. (Patrones Comportamiento 17.0)
35. **Visitor dispatch en vistas**: El procesamiento de vistas XML usa Visitor vía `getattr(self, f'_postprocess_tag_{tag}')`. Para extender, definir `_postprocess_tag_<tag>()` — no modificar `_postprocess_view()`. Nuevos tag handlers se descubren automáticamente. (Patrones Comportamiento 17.0)
36. **3-phase action methods**: Los métodos `action_*()` DEBEN separarse en 3 fases: `_pre_action` (validaciones, notificaciones), `_do_action` (escritura, lógica pura), `_post_action` (efectos secundarios: emails, locks, logging). Cada fase en método separado y overridable. `stock.move._action_done()` viola SRP con 10+ responsabilidades mezcladas. (SRP 17.0)
37. **Controladores delgados**: Los controladores (`@http.route`) DEBEN limitarse a routing y rendering. Toda lógica de negocio DEBE delegarse a métodos del modelo. Si un controlador tiene más de 3 llamadas a modelos o condicionales de negocio, refactorizar a métodos `_prepare_*`. (SRP 17.0)
38. **position="replace" solo como último recurso**: En herencia de vistas XML, preferir `position="after"`, `"before"` o `"inside"` con xpath específico. `position="replace"` destruye el elemento original y rompe extensiones de otros módulos que usan ese elemento como referencia. Solo usar replace cuando el elemento original es inherentemente incompatible. (OCP 17.0)
39. **LSP: super() obligatorio en toda la cadena MRO**: TODO método que sobreescribe via `_inherit` DEBE llamar a `super()` para preservar la cadena Decorator. `stock.picking.action_confirm()` y `stock.picking._action_done()` violan LSP al no llamar a `super()`. Usar Template Method pattern (`_prepare_*` hooks) para extensión limpia. (LSP 17.0)
40. **ISP: mixins pequeños y enfocados**: Preferir composición de mixins pequeños via `_inherit` (portal.mixin, utm.mixin, rating.parent.mixin, image.mixin) sobre un mixin grande tipo mail.thread (4690 líneas, 90+ métodos). `rating.parent.mixin` (71 líneas) fue creado para evitar la dependencia transitiva de mail.thread que tiene `rating.mixin`. (ISP 17.0)
41. **DIP: usar `self.env['model']`, nunca import de clases concretas**: Siempre obtener modelos via `self.env['account.move']` — NUNCA `from odoo.addons.account.models.account_move import AccountMove`. El Registry actúa como DI Container, Environment como Service Locator. Los imports directos crean acoplamiento concreto a concreto. Para server actions, usar naming convention `_run_action_{type}_multi`. (DIP 17.0)
42. **DIP: extraer constantes de dominio a módulos compartidos**: Constantes como `WARNING_MESSAGE`, `PROCUREMENT_PRIORITIES`, `OPERATION_TYPES` NO deben vivir dentro de módulos de modelo. Extraer a `constants.py` o `exceptions.py` en el módulo. Los imports cruzados (`from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES`) crean dependencias frágiles que se rompen al refactorizar. (DIP 17.0)
43. **Layer skipping: no bypass del ORM**: En Odoo 17, la comunicación entre capas DEBE ser unidireccional (Controller → Service → ORM → DB). NO hacer SQL directo en controladores ni métodos de negocio. Si es inevitable (SELECT FOR UPDATE, CTE recursivo), justificar con comentario y agregar check_access explícito. (Layered Architecture 17.0)
44. **Bridge pattern: ir.http como única puerta**: ir.http es el bridge oficial entre HTTP y ORM en Odoo 17. Los controladores DEBEN pasar por ir.http._dispatch() para routing, autenticación y pre/post procesamiento. NO instanciar modelos ORM directamente en el constructor de la aplicación. (Layered Architecture 17.0)
45. **sudo() scoped, no wholesale**: `sudo()` DEBE aplicarse solo a operaciones específicas, no a `self = self.sudo()` al inicio del método. Usar `self.sudo().field_name` o `self.sudo().write(vals)` en lugar de reemplazar self. (Layered Architecture 17.0)

## Reglas Clave (continuación)

### Core Modification Guardrails

46. **NUNCA modificar archivos en `odoo-17.0/`, `enterprise-17.0/`, `odoo-19.0/`, `enterprise-19.0/`** — viola licencias, se pierde en upgrades, rompe compatibilidad OCA.
47. **Alternativas legales**: herencia de vista (`inherit_id` + xpath), herencia de modelo (`_inherit`), JS patching (`@web/core/utils/patch`), QWeb extension (`t-extend`).
48. **Detectar en CI**: `git diff --cached --name-only | grep -E '^(odoo-17\.0|enterprise-17\.0|odoo-19\.0|enterprise-19\.0)/'` — bloquear commit si hay cambios.
49. **Excepciones**: Solo PR oficial a upstream Odoo, o security hotfix temporal con aprobación del lead técnico.
50. **SettingsBlock 'slots' error**: En Odoo 17.0, `slots: Object` es requerido en SettingsBlock pero `compileBlock()` nunca lo pasa. Solución: asegurar que `<block>` y `<setting>` tengan children con contenido renderizable. NO modificar `odoo-17.0/addons/web/`.
51. **App `string` duplicado en settings**: Si dos módulos definen `<app>` con el mismo `string`, aparecen tabs indistinguibles en la UI. El usuario puede estar viendo el tab equivocado sin settings. Solución: cada `<app>` debe tener `string` único. Usar `name` (atributo de `<app>`) para identificar programáticamente, `string` para UI.
52. **`<block>` vacío como anchor**: Si un `<block>` se usa como anchor para herencia xpath y no tiene contenido, en Odoo 17.0 dispara el error SettingsBlock 'slots'. Siempre dejar al menos un `<div>` o texto estático como contenido base. El atributo `name` se preserva como referencia xpath.

## MCP Servers

### OpenRAG MCP
- **Config**: `~/.config/opencode/opencode.jsonc` como `type: "local"`
- **Tools** (10): openrag_chat, openrag_search, openrag_ingest, openrag_delete_document, openrag_update_settings, openrag_create_knowledge_filter, openrag_search_knowledge_filters, openrag_update_knowledge_filter, openrag_delete_knowledge_filter, openrag_delete_chat
- **Skills indexados**: 855 skills, 5,738 chunks en OpenSearch
- **Ingest tool BUG**: `openrag_ingest` retorna HTTP 422 — usar script directo `ingest_document.py` (ver skill `openrag`)
- **Knowledge filter**: `odoo-skills-long-tail` (id: `94ecfff6-a584-4772-a8df-cdae572ad5e2`), 855 entries
- **Ver skill**: `openrag`

### Postgres-DB MCP
- **Config**: `~/.config/opencode/opencode.jsonc` como `type: "local"`
- **Tools**: query, execute, list_databases, list_tables, describe_table, search_tables, explain
- **DB URL**: `postgresql://odoo:odoo@localhost:5432/`

### codebase-memory-mcp
- **Config**: `~/.config/opencode/opencode.jsonc` como `type: "local"`
- **Tools**: search_graph, trace_path, get_code_snippet, query_graph, get_architecture, index_repository, detect_changes, list_projects, search_code, manage_adr, ingest_traces, get_graph_schema, index_status, delete_project
- **Repos indexados**: 22 repos across 16.0-19.0 (integra-addons, odoo-venezuela, third-party-addons + maintenance + l10nve)
- **Project IDs**: `home-binlp011-sources-<repo-name>` pattern
- **Indexing mode**: `moderate` (filtered files + similarity/semantic)
- **Re-index after git pull**: `codebase-memory-mcp cli detect_changes '{"project":"<name>"}'` then `index_repository` if changed_count > 0

### Playwright MCP
- **Config**: `~/.config/opencode/opencode.jsonc` como `type: "local"`
- **Command**: `npx @playwright/mcp@latest --browser=chrome --executable-path=/usr/bin/google-chrome-stable --caps=vision,pdf,devtools`
- **Tools** (40+): navigate, snapshot, click, type, fill_form, screenshot, evaluate, console_messages, network_requests, tabs, handle_dialog, file_upload, run_code, wait_for, resize, mouse_*, route, cookie_*, localstorage_*, sessionstorage_*, storage_state, verify_*, generate_locator, start_tracing, stop_tracing, start_video, stop_video, pdf_save
- **Browser**: Google Chrome Stable (headed, display `:0.0`)
- **Skills**: `playwright-mcp-usage` (global), `odoo-website-testing-mcp-19.0` (proyecto)
- **Diferencia con e2e-testing**: MCP es para automatización en vivo (agentic); `e2e-testing` es para archivos `.spec.ts` con `@playwright/test` (CI)
- **Instalado**: 2026-08-21. Referencia: AGENTS.md Rule #144

### MCP de Odoo — dos integraciones distintas, no confundir

Ambas apuntan al mismo Odoo (`binaural.odoo.com`) pero son transportes y configuraciones separadas:

| | `mcp__plugin_core_odoo__*` | `mcp__claude_ai_Binaural_MCP__*` |
|---|---|---|
| Usado por | Claude Code local (ej. agente `binaural-fn-programador:code-reviewer`) | Claude en claude.ai / Cowork |
| Transporte | stdio, `uvx mcp-server-odoo` | MCP remoto sobre HTTP, OAuth 2.1 (`https://binaural.odoo.com/mcp/rpc`) |
| Módulo Odoo requerido | ninguno (paquete genérico `mcp-server-odoo`) | `binaural_mcp_oauth` (depende de `mcp_server`) |
| Config | `userConfig` del plugin `core@binaural` (`odoo_url`, `odoo_db`, `odoo_api_key`, `onyx_api_key`) — se completa vía `/plugin` | Conector a nivel de organización, dado de alta una vez por el Owner en claude.ai |
| Tools | search_records, get_record, list_models, list_fields, create_record, update_record, post_message | los mismos + `ping` |

`plugin_core_odoo` requiere que las 4 variables de `userConfig` estén completadas — si no lo están, el
servidor `odoo` (stdio) falla al arrancar sin aviso visible. Verificar con un `search_records` de humo
(ej. `res.partner`, `limit=1`) tras configurar.

### Stack Tercerizado
OpenRAG usa stack externo que **no se despliega con docker-multi**:

| Servicio | Puerto | Propósito |
|----------|--------|-----------|
| Ollama (host) | 11434 | LLM local + embeddings |
| OpenSearch (Docker) | 9200 | Vector DB |
| Langflow (Docker) | 7860 | Workflows RAG |
| Docling Serve (host) | 5001 | Parseo de documentos |

## Reglas Clave — OpenRAG & RAG

53. **Docker env propagation**: Usar `docker compose up -d` (NO `restart`) para que cambios en `.env` tomen efecto en contenedores.
54. **litellm `provider/model_name`**: Modelos no-OpenAI DEBEN usar formato `provider/model_name` (ej: `ollama/llama3.2:1b`). Sin prefijo, litellm asume OpenAI.
55. **Chunking nomic-embed-text**: Máximo 2048 tokens (~3600 chars) por chunk. Skills grandes (>3600 chars) DEBEN dividirse por headings markdown con overlap.
56. **Langflow flow patching**: Los flujos pre-instalados usan OpenAI. Migrar a Ollama requiere: cambiar `model` + `api_key` a placeholder + `base_url=http://host.docker.internal:11434/v1` en nodos Agent y EmbeddingModel.
57. **Backend Python model patching**: `/app/src/agent.py` en `openrag-backend` hardcodea `gpt-4.1-mini`. Cambiar a `ollama/llama3.2:1b`. No persiste en recreación — parchear via entrypoint si es necesario.

58. **XPath `locate_node()` solo afecta al primer match**: `locate_node()` en `odoo/tools/template_inheritance.py` retorna `nodes[0]` — si el xpath matchea múltiples nodos, solo el primero recibe la modificación. Usar SIEMPRE selectores específicos (`[@groups=...]`, `[@name=...]`, etc.) para que cada xpath matchee exactamente un nodo. Documentado en FIX-027 (17.0) y FIX-050 (19.0).

59. **Exception Narrowing + Logging**: NUNCA usar `except Exception: pass/return True/return False` sin logging. Capturar solo las excepciones esperadas (`KeyError`, `ValueError`, `TypeError`, `ValidationError`, etc.) y loguear con `_logger.warning(...)`. `except Exception` genérico oculta bugs reales. Ejemplo: `except (KeyError, ValueError, TypeError) as exc: _logger.warning("Failed X for %s: %s", record.id, exc)`

### Reglas — Pago Multi-Moneda & l10n_ve

60. **`action_post()` bug en `l10n_ve_accountant`**: `action_post()` retorna wizard dict SIN llamar `super()` para `out_invoice/out_refund` cuando `move_action_post_alert` no está en context. SIEMPRE inyectar `move_action_post_alert=True` al llamar `action_post()` desde código automático (pagos, suscripciones). Bug en `l10n_ve_accountant/models/account_move.py:939-970`.

61. **`foreign_currency_id` en `account.payment`**: `l10n_ve_accountant` defaulta `foreign_currency_id` a `company.currency_foreign_id` (USD), NO a la moneda real del pago. Para pagos EUR, esto genera tasa incorrecta y error "La tasa debe ser superior a cero". Override en `account.payment.create()` para forzar la moneda desde la transacción.

62. **ORM Cache post-`action_post()`**: `parent_state` en `account.move.line` es un stored related field (`related='move_id.state'`). Después de `action_post()`, el ORM puede tener cache stale con `parent_state='draft'`. Usar `invalidate_recordset()` o `self.env.invalidate_all()` si se necesita leer `parent_state` inmediatamente después de postear.

63. **`is_sale_order` vs `is_subscription`**: Cuando se necesite validar si un registro pertenece al módulo Suscripciones, usar `is_sale_order` (stored field plano, `store=True`, set por defecto en `create()`). `is_subscription` es un computed field de enterprise que se setea a `False` cuando `plan_id` está vacío — usar `is_subscription` para validaciones post-eliminación de `plan_id` crea dependencia circular. (RQ-FIX-001, Skill `odoo-17-subscription-validation-patterns`)

64. **`action_confirm()` vs `@api.constrains`**: `@api.constrains` se dispara en `create()` y `write()` (bloquea la creación del registro). Para validaciones que solo deben ejecutarse al confirmar la orden (no al guardar), override `action_confirm()` directamente. `@api.constrains` para validación de confirmación bloquea la creación de la suscripción. (RQ-FIX-002, Skill `odoo-17-subscription-validation-patterns`)

65. **XPath en fields duplicados**: Si un field aparece múltiples veces en una vista (ej: `[@groups="..."]` y `[@groups="!..."]`), `locate_node()` (Rule 56) solo modifica el primer match. Crear xpaths separados usando selectores `[@groups=...]` para alcanzar cada field individualmente. (RQ-FIX-004, Skill `odoo-17-subscription-validation-patterns`)
66. **Alternate currency en suscripciones**: `_prepare_invoice()` DEBE recalcular `foreign_inverse_rate`/`foreign_rate`/`foreign_currency_id` usando `company.currency_foreign_id` y `_get_conversion_rate()`, no la tasa del tarifario, cuando se factura una suscripción con pricelist extranjero. `_prepare_invoice_line()` DEBE usar `_convert()` para foreign_price/foreign_subtotal hacia la moneda alterna. (FIX-SIC-006/007, Skill `odoo-17-subscription-invoice-currency`)
67. **SO foreign_currency_id sync**: `_recompute_subscription_rates()` DEBE actualizar `foreign_currency_id` a la moneda del tarifario en el UPDATE SQL. Usar `company_rate` (1/stored_rate) para non-USD, mantener lógica inversa para USD. Invalidar caché post-update. (FIX-SIC-008/009, Skill `odoo-17-subscription-invoice-currency`)
68. **Onchange pricelist → foreign sync**: `_onchange_pricelist_id()` DEBE invocar `_recompute_foreign_rates()` para sincronizar `foreign_currency_id` con el pricelist. Si pricelist está en moneda base, limpiar `foreign_*` y setear `manually_set_rate=False`. (FIX-SIC-010, Skill `odoo-17-subscription-invoice-currency`)

69. **`@api.model_create_multi` sobre `@api.model`**: Preferir `@api.model_create_multi` para `create()` porque recibe `vals_list` (batch) en lugar de un solo `vals`. El ORM llama `create()` una sola vez para todos los registros. Referencia: FIX-032 (17.0), FIX-053 (19.0).

70. **`cr.savepoint()` para operaciones SQL+flush**: Envolver operaciones que combinan raw SQL con `flush()` en `with self.env.cr.savepoint():`. El flush puede disparar stored computed recomputation que aborte la transacción. El savepoint aísla el error. Referencia: FIX-033 (17.0), FIX-054 (19.0).

71. **Multi-company SQL filter**: Batch SQL UPDATEs multi-compañía DEBEN filtrar por `company_id` en SELECT y UPDATE. `AND so.company_id = %s` evita corrupción cross-company. Referencia: FIX-034 (17.0), FIX-055 (19.0).

72. **Double re-apply pattern SQL**: Cuando SQL UPDATE directo modifica stored computed fields, el flush posterior los sobrescribe. Patrón: (1) SQL UPDATE, (2) flush, (3) re-aplicar SQL UPDATE, (4) invalidate_recordset. Referencia: FIX-035 (17.0), FIX-056 (19.0).

73. **`_prepare_*` pureza**: Los métodos `_prepare_invoice()`, `_prepare_invoice_line()` DEBEN ser puros (sin side effects). No mutar `self` ni argumentos. Usar copia defensiva `dict(vals or {})`. Referencia: FIX-036 (17.0), FIX-057 (19.0).

### Compute Group Visibility & Button XPath Patterns

74. **`has_group()` en compute DEBE tener `depends_context('uid')`**: Cualquier método `_compute_*` que llame a `self.env.user.has_group()` DEBE declarar `depends_context='uid'` en el campo. Sin esto, el ORM cachea el resultado por (model, field, record_id) sin considerar el usuario → **cache pollution**. Todos los usuarios ven el mismo resultado. Context key válida: `'uid'`, NUNCA `'user'`. Referencia: FIX-051 (19.0), FIX-038 (17.0), Skill `odoo-compute-group-visibility`. Bugs reales: `binaural_credit_limit/res_partner.py:14-18`, `binaural_club_socios/res_partner.py:388-392`.
75. **Context key `'user'` NO es válida**: Usar `'uid'` en `depends_context()`. `'user'` no es una context key estándar de Odoo y no invalida el cache correctamente. Referencia: Skill `odoo-compute-group-visibility`. Bug real: `binaural_last_cost/product_template.py:43`.
76. **`has_group()` NO funciona en XML `invisible`**: Las expresiones `invisible` se evalúan con `safe_eval` que NO tiene `has_group()` en sus builtins. Crear un campo Boolean compute con `depends_context('uid')` y usarlo en la expresión. Patrón: `<field name="user_has_group_xxx" invisible="1"/>` + `invisible="not user_has_group_xxx"`. Referencia: FIX-052 (19.0), FIX-039 (17.0), Skill `odoo-compute-group-visibility`, Odoo core `account/models/res_partner_bank.py:42,94-98`.
77. **`position="replace"` en `//header/button` DESTRUYE el botón original**: Si otro módulo hace `position="after"` o `position="before"` sobre el mismo elemento, su extensión se pierde. Usar `position="attributes"` para modificar atributos, `position="after"/"before"` para agregar nuevos botones. Solo usar `replace` cuando el elemento original es inherentemente incompatible. Referencia: FIX-054 (19.0), FIX-041 (17.0), Skill `odoo-button-xpath-patterns`. Anti-patrón `binaural_memberships/views/action_partner.xml:23`.
78. **N+1 en `_compute_*` con `search_count()`/`browse()` por registro**: Dentro de un loop en `_compute_*`, cada `search_count()` o `browse()` genera 1 SQL query. Para N registros = N queries. Usar raw SQL batch (`SELECT ... WHERE invoice_id = ANY(%s)`) o `search_count` con dominio que cubra todos los IDs. Referencia: FIX-055 (19.0), FIX-042 (17.0), Skill `odoo-payment-transaction-architecture`.
79. **XPath frágil con índice `[2]` o `[last()]`**: Los selectores XPath basados en índice son frágiles ante cambios en core o en otros módulos. Preferir selectores específicos: `[@name=...][hasclass(...)]`, `[@name=...][@groups=...]`, `[@name=...][@class=...]`. Referencia: FIX-053 (19.0), FIX-040 (17.0), Skill `odoo-button-xpath-patterns`.
80. **Tabla M2M `account_invoice_transaction_rel`**: La relación Many2many entre `account.move` y `payment.transaction` usa la tabla `account_invoice_transaction_rel` con columnas `invoice_id` y `transaction_id`. Para queries batch, usar raw SQL con `WHERE invoice_id = ANY(%s)` en vez de ORM `search_count` por registro. Referencia: Skill `odoo-payment-transaction-architecture`, `account_payment/models/account_move.py:12-15`.

### Testing Infrastructure & Dependencies

81. **`run_tests.sh` bug: `--db_name` siempre agrega timestamp**: `src/scripts/run_tests.sh` línea 65 ejecuta `DB_NAME="${DB_BASE}_$(date +%s)"` — si `--db_name=tests_custom` se pasa, el DB real es `tests_custom_1722500000`. **Workaround**: usar `scripts/coverage` (root) que NO tiene este bug, o pasar `--keep-db` y crear la DB manualmente. El script `scripts/run_tests.sh` (root) sí respeta `--db_name` directamente. Referencia: `src/scripts/run_tests.sh:43,65`.
82. **`l10n_ve` dependency para tests de contabilidad**: Módulos que dependen de `l10n_ve_accountant` necesitan que `l10n_ve` (chart of accounts) esté instalado en la DB de tests. Sin él, no existen cuentas `asset_receivable` → constraint `_check_payable_receivable` falla: "Any journal item on a receivable account must have a due date". **Fix**: agregar `invoice_date_due` + `invoice_payment_term_id` en tests, o instalar `l10n_ve` explícitamente. Cadena: `l10n_ve_accountant` → `l10n_ve_tax` (NO `l10n_ve`). Referencia: `cadipa_sale_suscription/tests/test_cancel_draft_invoices.py:139-157`.
83. **Estructura documentación OCA**: Módulos Odoo DEBEN seguir estructura OCA: `readme/DESCRIPTION.rst` (descripción + features), `readme/USAGE.rst` (instalación + uso + casos), `static/description/index.html` (HTML para Odoo Apps). Agregar `i18n/<lang>.po` con traducciones. Referencia: Skill `oca-contribution-workflow`, `odoo-documentation-guidelines-19.0`.

### Portal Fields Recomputation & copy() Flow

84. **`force=True` en `_recompute_portal_fields()` desde onchange/create**: Métodos que invocan `_recompute_portal_fields()` desde `_onchange_pricelist_id()` o `create()` DEBEN pasar `force=True`. Sin `force=True`, solo se recalculan suscripciones con `display_late=True` (state∈[3_progress,4_paused] AND next_invoice_date<today) — draft subscriptions y las con future next_invoice_date quedan con portal fields (`amount_to_invoice_bs`, `current_bcv_rate`) en 0.0. `create()` ya usa `force=True` (line 64). `_onchange_pricelist_id()` DEBE usar `force=True` (line 416). Referencia: Skill `cadipa-sale-suscription-payment`, FIX-PAY-006/007.
85. **`copy()` → `create()` gateway**: Odoo `copy()` invoca internamente `copy_data()` → `create()`. Custom `create()` override IS invoked during copy. Enterprise `copy_data()` copia `is_subscription=True` (stored computed) al vals dict. NO crear override de `copy()` para lógica que ya cubre `create()`. Portal fields con `copy=False` se resetean a 0.0 en copy, luego `create()` los recalcula con `force=True`. Referencia: Skill `cadipa-sale-suscription-payment`, FIX-PAY-007/008/009.

### Combo Products & Custom Tax Validations (2026-08-03)

86. **Validaciones de "impuesto único" DEBEN exceptuar `type='combo'`**: Cualquier `@api.constrains`/override de `create()`/`write()` que valide cardinalidad de `taxes_id`/`supplier_taxes_id` en `product.template` bloquea el guardado de productos combo si no exceptúa `type == 'combo'` — no tienen impuestos propios. Bug encontrado en **dos módulos independientes**: `l10n_ve_accountant._enforce_single_tax_vals` (fix en `src/specs/fix-product-combo-tax-validation/`) y `binaural_purchase._check_taxes_id` (fix previo por `purchase_ok`, commit `696cb8fd6`). Tratar como clase de bug recurrente. Referencia: FIX-059 (19.0), Skill `odoo-combo-product-validation-19.0`.
87. **`purchase_ok=False` en combo solo vía onchange de UI**: El fix de `binaural_purchase` exceptúa por `purchase_ok` en vez de `type` directamente — pero `purchase_ok=False` para combo solo lo setea el onchange del formulario (`_onchange_type` core), NO la creación programática (API/import/server action), que deja `purchase_ok=True` (default) y sigue disparando la validación. Preferir chequear `type` directamente en validaciones nuevas. Referencia: Skill `odoo-combo-product-validation-19.0`.
88. **`product.combo` requiere `combo_ids`/`combo_item_ids` no vacíos (constraint CORE)**: Todo `type='combo'` necesita ≥1 `product.combo` (`combo_ids`), y todo `product.combo` necesita ≥1 `product.combo.item` (`combo_item_ids`) — independiente de cualquier validación custom de impuestos. Al testear productos combo, crear el fixture completo primero o falla con `ValidationError: A combo product must contain at least 1 combo choice.`, fácil de confundir con el bug que se está probando. Referencia: Skill `odoo-testing-workflow` Anti-Pattern 11.
89. **Context sticky de `create()` filtra `write()` posterior sobre el mismo objeto**: Un override de `create()` que usa `self.with_context(ctx)` antes de `super().create()` produce un recordset que HEREDA ese contexto (incluyendo flags de skip-validation). Un `write()` posterior sobre ESE MISMO objeto en memoria (sin volver a `browse()`) hereda el flag silenciosamente y salta la validación sin error visible — produce falsos negativos en tests. Referencia: Skill `odoo_orm_backend-19.0`, `odoo-testing-workflow` Anti-Pattern 12.

### Workspace: Client Checkouts & Docker Infra (2026-08-03)

90. **`src/custom/<client>/<repo>` son checkouts git independientes, NO se sincronizan solos**: `src/custom/<client>/integra-addons`, `.../odoo-venezuela`, etc. son submodules git separados del pool compartido (`src/integra-addons-19.0/`, `src/odoo-venezuela-19.0/`). Un fix aplicado al repo compartido NO se propaga automáticamente — verificar con `diff -rq` (recursivo, sobre el árbol completo del módulo, no solo archivos puntuales) antes de asumir que un cliente específico ya tiene un fix, y sincronizar con `./odoo sync <client>` si diverge. Caso real: `binaural_purchase` fix (commit `696cb8fd6`) presente en `src/integra-addons-19.0/` pero ausente en `src/custom/19-homologacion-julio-2026-2/integra-addons/`. Referencia: Skill `workspace-structure`.
91. **Docker: referencia de nombre de contenedor corrupta en el daemon**: Si `./odoo start <instancia>` falla con "Conflict. The container name ... already in use by container `<hash>`" pero ese hash NO existe en `docker ps -a` ni `/var/lib/docker/containers/`, es un índice corrupto del daemon (bug Moby) — `docker rm -f`/`prune` NO lo resuelven. Requiere `sudo systemctl restart docker`. Antes de escalar, verificar y matar procesos `docker compose up` colgados. Referencia: Skill `workspace-structure`.

139. **`db-pg16` es un clúster Postgres compartido con bases reales de otros clientes**: casi todas las instancias del workspace comparten el mismo contenedor Postgres (`db-pg16`, `odoo-17-pg16`, etc.), donde conviven bases de datos de test desechables (`tests_binaural_ws_*`, patrón de `scripts/run_tests.sh`) junto a bases REALES de clientes/proyectos (ej. `countryclub-stg`, `josehern19.0`). Antes de borrar cualquier base en este clúster: listar todas, clasificar explícitamente cuáles son de test vs reales, y confirmar el alcance exacto con el usuario antes de ejecutar `DROP DATABASE` — nunca asumir "borra todo lo que matchee un patrón" sin esa confirmación. Detener los contenedores Odoo activos primero (libera conexiones), y reactivarlos después del borrado. Referencia: comando `/delete-test-bds` (corregido), incidente real en migración `binaural_pos_website`.

### Migración `l10n_ve_*` → `binaural_*` & Política de Commits SDD (2026-08-04, ticket 14303)

92. **Migración entre módulos hermanos: verificar huecos de cobertura entre agentes paralelos**: al dividir un build de migración (ej. `l10n_ve_tax`/`l10n_ve_invoice` → `binaural_tax`/`binaural_invoice`) por módulo/archivo entre agentes en paralelo, un campo/override que "naturalmente" pertenece a un módulo distinto del que cada agente tiene asignado puede quedar sin cubrir — cada agente asume que el otro lo hace. Caso real: el override de `_get_computed_taxes()` para producto exento de compra internacional debía ir en `binaural_tax/models/account_move_line.py` (paridad con `l10n_ve_tax`), no en `binaural_invoice`, y quedó sin implementar hasta detección manual post-build. Verificar explícitamente el mapa de dependencias cruzadas entre módulos antes de pasar a tests, no asumir "cada agente cubrió su parte". Referencia: Skill `odoo-lve-to-binaural-migration-17.0`.
93. **Campo de configuración sin consumidor real = bug silencioso**: agregar un booleano/Many2one nuevo a `res.company`/Settings y verificar solo que "existe y persiste" no es suficiente — si el método que debería leerlo (ej. una sección condicional de un wizard de reporte, como `_get_purchase_book_field_groups()`) no lo consulta, el campo no tiene ningún efecto visible aunque los tests de "el campo existe" pasen. Requiere un test que ejercite el flujo de negocio completo (generar el reporte real y verificar el efecto), no solo la existencia/persistencia del campo. Referencia: Skill `odoo-lve-to-binaural-migration-17.0`.
94. **`field.related` es un string punteado, NO una tupla**: `env['modelo']._fields['campo'].related` retorna `"company_id.campo"` (string), confirmado por `assert isinstance(self.related, str)` en `odoo/fields.py`. Tests que comparen contra una tupla `('company_id', 'campo')` fallan siempre, aunque el campo `related` esté correctamente definido. Referencia: Skill `odoo-lve-to-binaural-migration-17.0`.
95. **`binaural_tax`/`binaural_accountant` exigen `company.currency_foreign_id` configurado, y `account.move.currency_id` no puede diferir de la moneda de la compañía**: cualquier `account.move` creado en una compañía con `binaural_tax` instalado dispara `_prepare_tax_totals` → `ValidationError("No foreign currency configured in the company")` si `currency_foreign_id` no está seteado, incluso en tests que no prueban nada de moneda extranjera — todo `setUpClass` que cree facturas debe configurarlo primero. Además, `binaural_accountant._check_currency_id` prohíbe que `move.currency_id` difiera de la moneda base de la compañía — el patrón multi-moneda de este proyecto es `company.currency_foreign_id` + columnas `foreign_*` computadas, nunca cambiar `currency_id` del propio documento. Referencia: Skill `odoo-lve-to-binaural-migration-17.0`.
96. **Ciclo SDD: NUNCA commitear automáticamente al terminar Build/QC**: el cierre técnico del flujo SDD (tests + QC en verde) no implica autorización para commitear — el usuario decide cuándo y cómo se agrupa el commit en el historial. Tras un caso donde el flujo generó 5 commits intermedios que hubo que rehacer a mano en uno solo (ticket 14303), `sdd-builder-agent` y `sdd-lead-agent` (nuevo Gate 6: Commit Authorization) documentan explícitamente que ningún agente del flujo SDD ejecuta `git commit`/`git merge`/`git push` por su cuenta — el commit final sigue el formato de `crear-texto-conventional-commit.md` y solo se ejecuta cuando el usuario lo autoriza de forma explícita. Referencia: Skill `sdd-builder-agent`, `sdd-lead-agent`.

### Migración `l10n_ve_*` → `binaural_*`: gap real vs funcionalidad nueva, wizard tests y config de anticipos (2026-08-07, ticket 14303 Fase 3)

109. **Antes de asumir que algo es un gap de migración pendiente, verificar contra el PR/commit de origen que introdujo la feature relacionada — no solo contra el estado actual del checkout**: cuando el usuario describe un comportamiento que "debería" existir tras una migración `l10n_ve_*` → `binaural_*` (o cualquier migración entre módulos hermanos), el código destino puede no tenerlo simplemente porque el ORIGEN tampoco lo tuvo nunca — no es un gap de migración, es una funcionalidad nueva a construir en ambos lados. Verificar con `gh pr view <n> --repo <org>/<repo> --json body,commits,files` + `gh pr diff <n> --repo <org>/<repo>` contra el PR que introdujo la feature relacionada en origen, antes de planificar la implementación como "portar código existente". Caso real: se pidió excluir del libro de compras las líneas marcadas `international_purchase_exempt_product=True`; ni el destino (`binaural_invoice`) ni el origen (`l10n_ve_invoice`, confirmado contra el diff completo de `binaural-dev/odoo-venezuela#812`) tuvieron jamás esa lógica — era funcionalidad nueva, cambiando el spec (EARS nuevos) y el plan (sin código de referencia que portar). Referencia: Skill `odoo-lve-to-binaural-migration-17.0` §"Cómo diferenciar un gap de migración real de una funcionalidad nueva".
110. **`wizard.accounting.reports.currency_system` default `False` en compañías no-VEF hace que los tests que comparan montos absolutos lean el grupo de moneda equivocado**: `_determinate_amount_taxeds()` decide entre `tax_totals["groups_by_subtotal"]` (compañía) y `["groups_by_foreign_subtotal"]` (VEF) según `self.currency_system`, cuyo default (`_default_check_currency_system()`) es `True` solo si `company.currency_id.name == "VEF"`. Un test en una compañía USD que cree el wizard sin forzar `currency_system=True` y compare un `assertEqual` contra `price_unit`/`price_subtotal` de la línea falla con un valor incorrecto (ej. `-500.0` en vez de `0.0`), porque lee el grupo "foreign" (vacío/sin tasa en el fixture), no el de la compañía. Cualquier test nuevo que compare montos absolutos del wizard (no solo el wizard contra sí mismo) DEBE pasar `currency_system=True` explícitamente al crearlo. Referencia: Skill `odoo-lve-to-binaural-migration-17.0` §3, FIX-043 `odoo-code-review-17.0`.
111. **`binaural_advance_payment`: `res.company.advance_customer_account_id`/`advance_supplier_account_id` exigen tipos de cuenta (`liability_current`/`asset_current`) que un chart of accounts de QA puede no tener**: si al postear una factura/pago con anticipos aparece `UserError: "You must configure the advance customer account and the advance supplier account in the company settings"`, verificar primero si existe algún `account.account` del tipo requerido (`env['account.account'].search([('account_type','=','liability_current')])`) antes de intentar configurar el campo — el chart of accounts venezolano de una BD de QA puede no tener ningún `liability_current`, y hay que crear una cuenta nueva de ese tipo explícitamente. El dominio del campo es solo de vista (un `write()` directo no lo valida), pero no reutilizar por comodidad una cuenta de tipo incorrecto (ej. `asset_current` para el campo de cliente) — invierte la semántica contable del anticipo. Referencia: Skill `odoo-lve-to-binaural-migration-17.0` §4 "Gotcha: advance_customer_account_id/advance_supplier_account_id".

### Code Review de PR #2461: DRY entre módulos dependientes, override de hook con `None` semántico y `addons_path` anidado (2026-08-07)

112. **DRY entre módulos dependientes: si B depende de A, mixear/heredar la lógica de A — nunca reimplementarla**: cuando un módulo B (`binaural_website_sale_delivery`) ya depende de un módulo A (`binaural_website_sale`) y necesita lógica que A ya expone como mixin (`ForeignRateCommon._get_foreign_display_values()`), el controller de B DEBE mixear ese mixin y llamar al helper — nunca copiar el bloque de cálculo "porque son solo unas líneas". Caso real: `_order_summary_values()` en `binaural_website_sale_delivery/controllers/website_sale.py` reimplementaba manualmente la detección de `is_pricelist_foreign`/`alternate_currency`/`alternate_total`, duplicando byte a byte el bloque de `common.py` — detectado en review de PR #2461 (`manuelgc1201`) como riesgo de divergencia silenciosa entre el render de página y el AJAX de delivery sobre la misma orden. Fix: `class BinauralWebsiteSaleDelivery(ForeignRateCommon, Delivery)` + `self._get_foreign_display_values(order)`. Referencia: Skill `l10n-ve-website-sale` §8.6, spec `binaural_website_sale/specs/pricelist-aware-multicurrency/`.
113. **Override de un método core con parámetro `=None` semánticamente válido (no "ausente") debe manejar explícitamente el caso `None`**: si el método padre documenta que `param=None` dispara un comportamiento propio (ej. "resetear"), un override que solo actúa `if param:` dentro de la rama truthy deja sin ejecutar ese comportamiento en el caso `None` — viola el contrato LSP del método que sobrescribe. Caso real: `WebsiteSale._apply_pricelist(pricelist=None)` (Odoo core) usa `None` para resetear el pricelist a su default (ruta `/shop/pricelist` sin código promo, llamada real en `website_sale/controllers/main.py:964`); el override de `BinauralWebsiteSale._apply_pricelist()` solo llamaba `self._compute_foreign_rate(order)` `if pricelist and (order := request.cart)`, dejando la tasa/total alterno stale tras un reset. Fix: quitar la condición sobre `pricelist`, recalcular siempre que exista `request.cart`. Referencia: Skill `odoo-solid-lsp-isp-dip-19.0` (LSP: honrar todo el contrato del padre), spec `binaural_website_sale/specs/pricelist-aware-multicurrency/`.
114. **`addons_path`/`INSTANCE_ADDONS` no recorre subcarpetas anidadas — cada entrada debe apuntar directamente a la carpeta que contiene los módulos**: si `INSTANCE_ADDONS` lista `src/custom/<X>` pero los módulos corregidos viven en `src/custom/<X>/<subcarpeta>/<modulo>`, Odoo NUNCA los encuentra — `.resources/entrypoint.d/400-auto-detect-addons` agrega cada entrada de `INSTANCE_ADDONS` tal cual como una única carpeta de addons_path, sin recursión. Síntoma combinado: si el módulo compartido "de respaldo" (encontrado en otra entrada de `addons_path`, ej. `src/odoo-venezuela-19.0/l10n_ve_sale`) tiene un manifest con `version` de una serie Odoo distinta (ej. `"17.0.x"` en un stack 19.0), Odoo lo marca `installable=False` ("incompatible version") — bloqueando la instalación de cualquier módulo que dependa de él, aunque el código en sí esté correcto. Antes de asumir un bug de dependencias, verificar: (1) qué copia del módulo realmente resuelve `addons_path` (`docker exec <container> env | grep INSTANCE_ADDONS`), (2) si hay una copia corregida en una subcarpeta no alcanzada, (3) el `version` del manifest de la copia que sí se carga. Caso real: instancia `odoo-binaural-consultoria-migr-sitio-web-v19-tests`, PR #2461 — el override 19.0 correcto de `l10n_ve_sale`/`l10n_ve_stock` vivía en `src/custom/MIGR-SITIO-WEB-V19/odoo-venezuela/`, inalcanzable porque `INSTANCE_ADDONS` solo listaba `src/custom/MIGR-SITIO-WEB-V19`. **Chequeo adicional antes de bumpear versiones a mano**: si la copia "de respaldo" que resuelve el `addons_path` tiene manifests con versión de otra serie, verificar primero `git branch --show-current` (y `git status`) dentro del repo de addon-pool compartido (ej. `src/odoo-venezuela-19.0`) — el repo completo puede estar checked-out en la rama git equivocada (ej. `17.0` en un directorio nombrado `-19.0`), lo que explica que TODOS sus manifests tengan versión de la serie vieja. En ese caso el fix es `git checkout <serie> && git pull` en ese repo, **nunca** editar manifests a mano uno por uno — es un síntoma de checkout, no un typo de versión. Caso real: `src/odoo-venezuela-19.0` (PR #2435, `binaural_website_sale`) estaba en rama `17.0`; 11 módulos `l10n_ve_*`/`od_journal_sequence` marcaban `installable=False` en cascada, bloqueando `binaural_website_sale` (depende de `l10n_ve_sale`/`l10n_ve_stock`). Referencia: Skill `docker-odoo` (plugin `binaural-fn-programador`).

115. **Al hacer override de un método heredado decorado con `@http.route`, redeclarar TODOS los kwargs del padre — no solo los que cambian**: Odoo NO combina los kwargs del decorador entre la ruta del padre y la del override; cada `@http.route` en la subclase reemplaza la definición completa. Omitir un kwarg del padre no lo "hereda" con su valor por defecto real — cae al default genérico del decorador, que puede ser peligroso: `sitemap=False` (default) borra la URL de `sitemap.xml` para TODOS los websites que instalen el módulo (regresión de SEO silenciosa, nadie la nota hasta que cae el tráfico orgánico), y sin `handle_params_access_error` un producto/registro sin acceso o borrado devuelve 403/500 en vez de un redirect/404 limpio. Antes de escribir un override de una ruta core, leer el decorador COMPLETO del método padre (`grep -n "@route\|@http.route" -A15` en el archivo del core) y copiar cada kwarg que no se esté cambiando intencionalmente. Nota adicional para `website_sale.controllers.main`: helpers como `sitemap_products`/`sitemap_shop` están definidos DENTRO del cuerpo de la clase `WebsiteSale` (no a nivel de módulo) — se referencian como `WebsiteSale.sitemap_products`, `from ... import sitemap_products` da `ImportError`; y existe la constante `SHOP_PATH` en `odoo.addons.website_sale.const` para no hardcodear `/shop` en las rutas del override. Caso real: PR #2435 (`binaural_website_sale.controllers.website_sale.BinauralWebsiteSale.product()`), review de `manuelgc1201`. Referencia: Skill `binaural-website-sale` §2.x "Herencia de decorador `@http.route`".

116. **`scripts/odoo-test` (y por lo tanto `./odoo test <instancia> <modulo>`) no pasa `--http-port` — falla en instancias con servidor Odoo ya corriendo en 8069**: a diferencia de `scripts/run_tests.sh` (que sí usa `--http-port=19999` explícito en todas sus invocaciones), el comando interno de `scripts/odoo-test` corre con `--workers 0 --no-http` pero SIN override de puerto. En una instancia cuyo contenedor ya tiene su propio servidor Odoo escuchando en 8069 (el caso normal de cualquier instancia levantada con `./odoo start`), el subproceso de test choca con "Address already in use / Port 8069 is in use" y nunca llega a instalar ni correr ningún test — el síntoma es engañoso: reporta 0% de cobertura y "no data was collected" en vez de un error de tests, como si el módulo no tuviera código ejecutado. Para instancias con servidor vivo, usar `scripts/run_tests.sh` (o `scripts/coverage`) en vez de `./odoo test`, o verificar primero que la instancia esté detenida. Referencia: Skill `docker-odoo` (plugin `binaural-fn-programador`).

### Testing Infrastructure & Scripts (2026-08-05)

97. **Ciclo de validación SDD: pre-commit → tests no-cov → tests con coverage → comparar**: después de completar implementación SDD, ejecutar en orden: (1) `scripts/precommit` para validar código, (2) tests sin coverage con `--no-cov --keep-db` para confirmar que pasan, (3) tests con coverage sobre la misma DB con `python3 -m coverage run` manual, (4) `scripts/coverage` o equivalente para obtener reporte. **NUNCA saltarse un paso** — cada paso valida un aspecto diferente. Referencia: Skill `coverage-workflow`, validación `binaural-mig-international-purchase` (2026-08-05).

98. **`-i` vs `-u` flag en Odoo: `-i` reinstala XML data, `-u` solo actualiza**: el flag `-i` (install) ejecuta `load_data()` que re-procesa todos los XML del módulo — si hay `unique` constraints en tablas de datos (ej: `payment_concept_line_unique_code`), falla con `IntegrityError` al re-insertar. El flag `-u` (update) NO re-ejecuta XML data a menos que el archivo haya cambiado. Para re-ejecutar tests sobre DB existente, usar `-u` o ejecutar sin flag de install/update. `scripts/coverage` línea 88 usa `-i` que falla con constraints existentes. `run_tests.sh` Pass 2 línea 164 usa `-i` con el mismo problema. Referencia: `scripts/coverage:88`, `src/scripts/run_tests.sh:164`.

99. **`scripts/coverage` línea 81: `docker exec -it` falla sin TTY**: el script usa `docker exec -u root -it` que requiere terminal interactiva. Cuando se ejecuta desde CI, pipelines, o sesiones no-interactivas, falla con `the input device is not a TTY`. **Workaround**: ejecutar el equivalente manual sin `-it`: `docker exec -u root <container> bash -c "pip3 install coverage && python3 -m coverage erase && python3 -m coverage run ... && python3 -m coverage report -m"`. Referencia: `scripts/coverage:81`.

100. **Interpretación de coverage: SDD-specific vs total**: el coverage total de un módulo incluye código pre-existente NO modificado por la migración SDD. Ejemplo: `binaural_invoice` tiene 65% total, pero los archivos tocados por SDD (`res_company.py`, `account_journal.py`) tienen 100%. **Al reportar coverage SDD, desglosar**: (1) archivos modificados por SDD, (2) código pre-existente no cubierto. El SDD-specific coverage suele ser 95%+ aunque el total sea bajo por código legacy. Referencia: validación `binaural-mig-international-purchase` (2026-08-05).

 101. **`run_tests.sh` Pass 2 grep filter oculta fallos de coverage**: el script pasa la salida por `grep -E "(Starting|FAILED|ERROR|passed|failed|error\(s\)|TOTAL|Name|Stmts|Miss)"`. Si el paso de coverage falla antes de imprimir el reporte (ej: `pip3 install coverage` falla, o `coverage run` aborta), el grep no muestra ningún error visible — el log simplemente termina sin sección de coverage. **Verificar manualmente**: `docker exec -u root <container> python3 -m coverage report -m --include='*/<module>/*'`. Si dice "No data to report", el `coverage run` no llegó a ejecutarse. Referencia: Skill `coverage-workflow` Anti-Pattern C11.

102. **Vals mutation en write()**: NUNCA mutar el dict `vals` dentro de un override de `write()` o de un helper llamado desde `write()` si ese mismo `vals` se reutiliza en `super().write(vals)`. La mutación se aplica a TODOS los registros del recordset, incluyendo los que fueron excluidos de la validación. Usar `dict(vals)` (copia superficial) al pasar vals a helpers que puedan inyectar valores por defecto. Si el helper inyecta un default, aplicarlo solo al subconjunto via `records_to_validate.write(injection)`. Referencia: FIX-060, skill `odoo-vals-mutation-safety-19.0`, PR #14405.

103. **Trigger de validación incompleto en write()**: Cuando un override de `write()` ejecute validación condicional basándose en la presencia de campos en `vals`, incluir TODOS los campos que alteren el estado de validación en la condición. Si la validación depende de `type`, agregar `'type' in vals` a la condición `if`. El filtro de records debe usar `vals.get('type', r.type)` para detectar cambios de type en vals, no solo `r.type`. Referencia: FIX-061, skill `odoo-write-trigger-completeness-19.0`, PR #14405.

104. **Context `skip_*` propagado desde create()**: NUNCA retornar un recordset de `create()` con un flag de contexto `skip_*_on_write=True` activo — limpiar el contexto antes de retornar: `super().create(vals_list).with_context(skip_*=False)`. El recordset hereda el contexto y cualquier `write()` posterior sobre ese objeto en memoria se salta la validación silenciosamente. En tests, si se necesita hacer `product.with_context(skip_*=False)` después de `create()`, es code smell del create(). Referencia: FIX-062, PR #14405.

105. **TLS hardening en HTTP requests**: NUNCA usar `requests.get(url, verify=False)` directamente en código de negocio. Crear un helper que intente TLSVerification=True primero y haga fallback a `verify=False` solo en `SSLError`. El `disable_warnings(InsecureRequestWarning)` SIEMPRE debe estar dentro del helper, no en el call-site. Referencia: T17, skill `l10n-ve-currency-rate-live` §5, FIX-064.

106. **Logging en omisiones silenciosas (empty if/else)**: TODOS los `if`/`else` que determinen si un rate/proceso se ejecuta DEBEN tener `else` branch con `_logger.warning()` al menos. Nunca fallar silenciosamente — un `if` sin `else` que no loggea oculta bugs reales. Aplica a rates, conversiones, validaciones de datos externos. Referencia: T18, skill `l10n-ve-currency-rate-live` §6, FIX-063.

107. **Aislamiento de fallos en loops de entidades**: Cuando un loop itera entidades independientes (compañías, registros, transacciones), CADA iteración DEBE estar envuelta en `try/except` + `self.env.cr.savepoint()` para aislar fallos. Un error en una entidad NO debe detener el procesamiento de las demás. Aplica a crons, `_process_job`, métodos batch. Referencia: T19, skill `l10n-ve-currency-rate-live` §7, FIX-065.

108. **`parent_id` immutability en `res.company.write()`**: Odoo 17+ lanza `UserError("The company hierarchy cannot be changed.")` si se intenta cambiar `parent_id` después de la creación. En tests, NUNCA hacer `company.parent_id = False` después de `create()` — crear sin `parent_id` desde el inicio (el default es `False`). Referencia: T19, skill `l10n-ve-currency-rate-live` §8.1.

### Code Review: Merge Conflicts, Retry Logic & CI Stale (l10n_ve_currency_rate_live, 2026-08-10)

Lecciones del PR #1060 (backport multi-moneda BCV a 17.0): un merge conflict mal resuelto dejó el
módulo sin compilar y borró silenciosamente lógica de retry, sin que la descripción del PR lo
mencionara ni un reporte de CI desactualizado lo detectara. Reglas 117-122 son genéricas (aplican
a cualquier módulo/versión); revisar `l10n-ve-currency-rate-live` §8.5-8.9 para el detalle
completo del caso.

117. **Verificar `py_compile` tras resolver un conflicto de merge**: Odoo no valida sintaxis hasta que intenta importar el módulo en runtime — un merge mal resuelto puede dejar un `SyntaxError` (ej. un `try:` sin `except`/`finally`, un `continue` fuera de cualquier loop) sin que ningún linter local lo detecte de inmediato. SIEMPRE correr `python3 -m py_compile <archivo>` sobre archivos `.py` tocados por un merge antes de dar la resolución por buena o reportar tests en verde. Referencia: FIX-044 (17.0)/FIX-066 (19.0), skill `l10n-ve-currency-rate-live` §8.5.

118. **Diff contra ambas ramas padre al resolver un merge que combina dos features**: Cuando un conflicto ocurre en un método que dos ramas modificaron por razones distintas (ej. aislamiento por `savepoint()` + retry programado), tomar "el lado que compila" sin verificar el otro puede descartar lógica de negocio completa de forma silenciosa. Diffear explícitamente contra ambas ramas padre (`git diff <base>...<rama>`) y confirmar con `grep` que cualquier helper tocado sigue teniendo caller real tras la resolución. Referencia: FIX-045 (17.0)/FIX-067 (19.0), skill `l10n-ve-currency-rate-live` §8.6.

119. **Cambiar el contrato de un método privado exige auditar TODOS los call-sites**: Cambiar el tipo esperado de un parámetro (ej. lista plana → recordset, agregando `.mapped(...)`) rompe silenciosamente cualquier caller con la convención vieja, incluidos tests preexistentes fuera del diff que introdujo el cambio. `grep` TODOS los call-sites (producción y tests) antes de mergear — no asumir que "ya se migraron todos". Referencia: FIX-046 (17.0)/FIX-068 (19.0), skill `l10n-ve-currency-rate-live` §8.7.

120. **Ubicación de un guard/early-return debe ceñirse al bloque que pretende saltar**: Un early-return para optimizar/saltar un caso especial (ej. "no scrapear en fin de semana") debe envolver ÚNICAMENTE el bloque específico al que aplica esa justificación — ubicarlo antes de un cálculo principal no relacionado puede saltárselo también, rompiendo comportamiento existente. Correr la suite COMPLETA de la función (no solo tests nuevos) tras agregar un guard. Referencia: FIX-047 (17.0)/FIX-069 (19.0), skill `l10n-ve-currency-rate-live` §8.8.

121. **No confiar en un reporte de CI sin verificar contra qué commit corrió**: Un comentario de bot/CI de "tests exitosos" solo es válido para el commit contra el que corrió. Si el PR recibió commits nuevos después (fixes, merges) sin que el bot vuelva a correr, ese reporte no dice nada del HEAD actual — comparar el commit/fecha evaluado contra el HEAD antes de asumir que la suite pasa, especialmente si el HEAD más reciente pudiera no compilar (regla 117). Referencia: FIX-048 (17.0)/FIX-070 (19.0), skill `l10n-ve-currency-rate-live` §8.9.

122. **Gap de migración conocido: `l10n_ve_currency_rate_live` 19.0 va detrás de 17.0**: El módulo en `odoo-venezuela-19.0` es una versión mínima (~104 líneas, solo `_parse_bcv_data`) sin retry programado, aislamiento por `savepoint()`, TLS hardening ni soporte multi-moneda (EUR/CNY/TRY/RUB). Al portar esta funcionalidad a 19.0, aplican los mismos riesgos de merge de las reglas 117-121. Referencia: skill `l10n-ve-currency-rate-live` (nota de paridad 19.0), skill `odoo-lve-to-binaural-migration-17.0` (patrón general de gaps de migración).

### Skills Infrastructure & Sharing (2026-08-10)

Reglas para la infraestructura de skills, sharing entre herramientas, y mantenimiento de AGENTS.md.

123. **Skill Naming Convention**: Patrón: `{domain}-{topic}-{scope}-{version}`. Ej: `odoo-context-fundamentals-17.0`, `binaural-stock-barcode`, `sdd-builder-agent`. Para skills SDD: `sdd-{role}-agent`. Para skills Binaural: `binaural-{module}`. Para skills OCA: `oca-{phase}-{topic}`. Referencia: skill `skills-inventory-protocol`.

124. **Skill Directory Structure**: Cada skill = 1 directorio con `SKILL.md` dentro. Max 500 líneas archivo principal, referencias externas para más contenido. Front-matter: Trigger, Descripción, Contenido principal, Referencias. Referencia: skill `skills-inventory-protocol`.

125. **Skills Sharing Protocol**: OpenCode sources → Claude symlinks (unidireccional vía daemon). 5 fuentes: project (66), 17.0 (326), 19.0 (161), 16.0 (100), global (156). Primera fuente gana en caso de nombre duplicate. **Curado desde 2026-09-25** (~250 symlinks, antes 878): de 16.0/17.0/19.0 solo se enlaza lo listado en `src/scripts/skill-sync-versioned-allowlist.txt`, y nada de lo que matchee `src/scripts/skill-sync-exclude.txt`; la fase 4 borra los symlinks que dejan de calificar. Daemon: `src/scripts/skill-sync-daemon.sh`. Service: `~/.config/systemd/user/skill-sync.service`. Referencia: skill `skill-sync-daemon`.

126. **OpenRAG Ingestion Policy**: Skills del proyecto, versionadas (16.0/17.0/19.0), y documentación se ingieren a OpenRAG. Chunking: max 2048 tokens (~3600 chars) por chunk. Re-ingestion: post-cambio de skill, post-V-cycle. Credenciales: admin/OpenRag2026!Secure, index documents. Referencia: skill `openrag`.

127. **AGENTS.md Maintenance Protocol**: Quién: lead dev o SDD lead. Cuándo: post V-cycle, post cambio de infra. Qué: actualizar inventarios (conteos reales), agregar reglas (numeración secuencial), actualizar secciones de skills. NO incluir contenido completo de skills — solo referencias. Referencia: skill `agents-md-maintenance`.

128. **16.0 Skills Scope**: Odoo 16.0 tiene 100 skills en `src/.opencode/16.0/skills/`: Core ORM (10), GoF Patterns (10), SOLID+Architecture (10), OWASP (10), TDD (10), Performance (10), XML Views (10), Controllers/Mixins (10), Context/DRY (10), Translations/Tools (5), Migration/Best Practices (5). Total: ~5,500 líneas, 100+ anti-patrones. Referencia: `src/.opencode/16.0/PLAN-MASTER-100-LOOPS.md`.

129. **skill-sync Daemon Lifecycle**: Iniciar: `systemctl --user start skill-sync.service`. Verificar: `systemctl --user status skill-sync.service`. Logs: `journalctl --user -u skill-sync.service -f`. One-shot: `src/scripts/skill-sync-daemon.sh --once`. Intervalo: 30s default (configurable vía `SKILL_SYNC_INTERVAL`). Referencia: skill `skill-sync-daemon`.

130. **Version Detection Protocol**: SIEMPRE detectar versión Odoo antes de crear/modificar skills o código. Revisar `__manifest__.py` → campo `version`. Formato: `16.0.x.x.x`, `17.0.x.x.x`, `19.0.x.x.x`. Para skills: incluir versión en nombre si es version-specific. Referencia: skill `skills-inventory-protocol`.
131. **Un compute field corregido en backend puede seguir roto en portal/controller si estos reimplementan la misma comparación inline (PORTALRENEW)**: al sobreescribir un compute boolean/estado (ej. `_compute_display_late`), `grep` el mismo patrón de comparación en TODOS los templates QWeb (`views/*_templates.xml`) y controllers (dominios de búsqueda hardcodeados) del módulo enterprise dueño del campo — no asumir que leen el compute solo porque "deberían". Preferir hacer que esos puntos lean el compute field en vez de reimplementar la condición. Referencia: Skill `odoo-subscription-freeze-pattern` Sección 12, `country_sale_subscription` sección `PORTALRENEW`.
132. **Side-effects de preparación cron-only deben replicarse en overrides custom del mismo método público; un filtro de una capa MRO ajena al dominio puede silenciar una decisión correcta de una capa más especializada (CYCLE2)**: si un método solo-cron (ej. `_reset_subscription_qty_to_invoice()`) prepara estado inmediatamente antes de llamar a un método público reusable (`_create_invoices()`) alcanzable por otras rutas (botón manual, portal, API), ese reset debe vivir en el override más externo del método público que ya está en la cadena MRO para TODAS las rutas — no asumir que solo el cron necesita facturar. Al depurar "nada que facturar" en suscripciones, revisar TODA la cadena de `_get_invoiceable_lines()` (`grep` el método en cada módulo instalado), incluyendo localizaciones ajenas al dominio de suscripciones. Referencia: Skill `odoo-subscription-freeze-pattern` Sección 13, `country_sale_subscription` sección `CYCLE2`.
133. **`run_tests.sh` también oculta el traceback completo de un test que falló, no solo fallos de coverage**: el mismo grep-filter de la Regla 101 (`grep -E "(Starting|FAILED|ERROR|passed|failed|error\(s\))"`) deja pasar la línea `FAIL: Clase.metodo` pero descarta el `AssertionError`/traceback real. Para depurar, re-ejecutar sin el grep apuntando solo al test que falló: `docker exec -u root <container> odoo -d <db> --test-tags "/modulo:Clase.metodo" --stop-after-init --workers 0 --http-port=<puerto libre> --log-level=test`. Referencia: Skill `coverage-workflow` Anti-Pattern C15.
134. **Verificación en vivo de un bug reportado: `odoo shell` contra staging del cliente, `env.cr.rollback()` siempre**: antes de implementar un fix basado en una hipótesis de causa raíz no confirmada por ejecución real (especialmente en cadenas MRO de 3+ niveles), reproducir el flujo real vía `odoo shell -d <db_cliente>`, terminando SIEMPRE con `env.cr.rollback()` (nunca `commit()`), incluso dentro de bloques except. Referencia: Skill `binaural-odoo-shell-live-verification`.

135. **Multi-currency company setup en tests: `_setup_ves_company()` pattern**: cuando un módulo depende de `l10n_ve_accountant` y tests crean `account.payment` con moneda extranjera, el override de `account_payment.create()` verifica `payment_currency_id != company_currency_id`. Si la compañía es USD (default de test DB) y el pago también es USD, la condición es `False` → `foreign_rate` queda en 0.0 → assertion falla. Tests que verifican foreign_rate DEBEN cambiar la moneda base de la compañía a VES antes de crear pagos. Patrón: crear/activar VES, setear `company.currency_id = ves.id`, configurar `company.currency_foreign_id = USD`. Referencia: `cadipa_sale_suscription/tests/test_sale_order.py` helper `_setup_ves_company()`.

136. **Mock de super() vía `type(obj).__mro__[1]`**: cuando `unittest.mock.patch` no puede resolver la ruta de importación de una clase padre (ej. `odoo.addons.payment.models.payment_transaction.PaymentTransaction`), usar `type(instancia).__mro__[1]` para obtener la clase padre real. Pattern: `with patch.object(type(tx).__mro__[1], '_create_payment', ...)`. Aplica a cualquier test que necesite mockear el super() de un modelo que hereda vía `_inherit`. Referencia: `cadipa_sale_suscription/tests/test_sale_order.py` tests 940, 941, 950.

137. **COVERAGE.md en directorio del módulo**: después de ejecutar coverage sobre un módulo, crear/actualizar `COVERAGE.md` en la raíz del módulo documentando: resultados por archivo (stmts/miss/cover), líneas faltantes, comandos de coverage usados, y notas. Este archivo sirve como referencia rápida sin necesidad de re-ejecutar coverage. Convención del workspace para módulos con coverage > 90%. Referencia: `cadipa_sale_suscription/COVERAGE.md`.

138. **`--http-port` en tests contra instancia activa**: al ejecutar tests vía Docker exec contra una instancia que YA tiene un servidor Odoo corriendo en 8069, SIEMPRE pasar `--http-port=<puerto libre>` (ej. 8099, 19999) para evitar "Address already in use". `scripts/coverage` línea 81 y `scripts/odoo-test` NO pasan este flag → fallan silenciosamente reportando 0% coverage / "no data was collected". Preferir `src/scripts/run_tests.sh` o ejecución manual con `--http-port`. Referencia: AGENTS.md Rule #116, skill `odoo-testing-workflow` sección "Ejecución Directa en Docker".

140. **`at_install` corrido inline durante instalación en vivo (`../odoo test`) causa falsos negativos en tests que crean `account.move` directamente**: `../odoo test`/`scripts/odoo-test` siempre crea una base nueva y corre `-i <módulo>`, resolviendo toda la cadena de dependencias en un único proceso continuo — a diferencia de `scripts/run_tests.sh`, que instala primero y ejecuta los tests después contra una base ya completamente instalada. Un test tageado `at_install` (el default de `@tagged` si no se especifica explícitamente `post_install`) corre INLINE, intercalado con esa instalación en vivo — en ese punto el chart of accounts de la compañía puede no estar completamente asentado, y cualquier test que cree `account.move` directamente puede disparar `_check_payable_receivable` de forma no determinística ("Any journal item on a receivable account must have a due date and vice versa.", `account_move_line.py`) aunque el mismo test pase el 100% de las veces si se corre después de una instalación completa (ej. vía `scripts/run_tests.sh`). Esto no es específico de este repo: la propia clase base de Odoo `AccountTestInvoicingCommon` (`odoo-17.0/addons/account/tests/common.py`) tiene `assert 'post_install' in cls.test_tags` — rechaza correr `at_install` cualquier test que dependa de un CoA instalado. **Fix**: toda clase de test que cree `account.move`/facturas directamente debe taguearse `@tagged('post_install', '-at_install', ...)`, nunca dejarse en el default `at_install`, sin importar si el entrypoint de test normalmente usado (`run_tests.sh`) nunca expuso el bug por su diseño de dos fases (instalar, luego testear). Extiende la Rule #82 (que documentaba el síntoma de campo faltante, no esta causa de timing de instalación). Referencia: `cadipa_sale_suscription/tests/test_sale_order.py` y `test_cancel_draft_invoices.py` (ambas clases retagueadas de `at_install` a `post_install`), skill `odoo-testing-workflow` sección "Reglas para crear tests", skill `cadipa-sale-suscription-testing` anti-patrón T1.

### Sesión Traducciones es_VE, Cron Pricing Sync & Test Isolation (2026-08-21)

141. **NUNCA ejecutar `-u`/`./odoo test` con reinstalación de módulo contra una base de datos que el usuario tenga abierta activamente en el navegador**: actualizar/reinstalar un módulo (`docker exec ... odoo -u <modulo> -d <db>` o correr `./odoo test` apuntando directamente a la DB en uso) invalida y reconstruye el caché de vistas combinadas (`ir.ui.view._get_combined_arch`/`_get_view_cache`). Si la sesión del usuario pide una vista justo en ese instante, puede caer en una ventana de carrera donde el caché está momentáneamente inconsistente y el servidor devuelve un 500 real (`ValueError: can only parse strings` en `etree.fromstring(view.arch)`) — visible para el usuario, aunque el propio test/reinstalación termine en verde. Caso real: dos corridas de `./odoo test ... -u country_sale_subscription_fees` contra `countryclub-stg` (2026-08-21, 13:48-13:49) coincidieron con el usuario abriendo el menú de Ajustes, produciendo exactamente ese 500. Diagnóstico: reproducir `env['res.config.settings'].get_views([[view_id, 'form']], {})` (o el modelo/vista en cuestión) directamente en un shell de Python con el `lang` del usuario, para confirmar que el caché ya está consistente y que el código no tiene un bug real. **Fix/regla operativa**: SIEMPRE usar una base de datos temporal dedicada (`-d tests_<algo>`) para cualquier `-u`/test run, nunca la base que el usuario tiene abierta — `./odoo test <instancia> <modulo> -d tests_x ...` ya crea y destruye esa base automáticamente. Referencia: skill `odoo-testing-workflow` (Anti-Pattern 17).

142. **Patrón de cron "doble alcance": separar la sincronización incondicional de la condicional, y aplicar no-op write skip**: cuando un cron/batch tiene DOS efectos con condiciones de disparo distintas (ej. "actualizar el precio recurrente de un plan" vs. "actualizar el precio de línea de una orden vencida"), NO deben compartir el mismo filtro de candidatos solo porque comparten la misma fuente de datos — un filtro pensado para el caso condicional (ej. `display_late=True`) puede bloquear silenciosamente el efecto que debía ser incondicional. Extraer cada efecto a su propio método, con su propio scope de búsqueda, y llamar primero el/los incondicional(es). Además, antes de cada `write()` en batch, comparar el valor actual contra el valor objetivo y omitir el grupo/registro si ya coinciden — evita recomputes/tracking/`write_date` bumps innecesarios en corridas repetidas donde la mayoría de los candidatos ya está al día. Caso real: `country_sale_subscription_fees._cron_update_subscription_fee_lines()` sincronizaba `sale.subscription.pricing.price` (Fase 7) DENTRO del mismo bloque filtrado por `display_late` que `price_unit` — un tabulador nuevo publicado con cero órdenes vencidas nunca llegaba a actualizar el precio recurrente del plan. Fix: método separado `_sync_recurring_pricing_from_fee_table()`, sin filtro `display_late`, llamado antes del resto del cron. Referencia: spec `country_sale_subscription_fees/specs/fix-recurring-pricing-sync-decoupled-from-display-late.md`.

143. **`--i18n-export` de Odoo 17 blanquea `msgstr` cuando `msgid == msgstr` — NO es una traducción faltante real**: al exportar traducciones (`odoo --i18n-export=<path>.po -l <lang> --modules=<modulo>`) para auditar qué falta traducir, el exportador de Odoo 17 omite/deja vacío el `msgstr` de cualquier entrada donde el valor ya almacenado coincide exactamente con el `msgid` — típico en textos que ya están en español en el código fuente (nombres de grupo, labels de vista) o en traducciones ya cargadas idénticas al original. Comparar el `.po` exportado contra el repo puede reportar decenas de "faltantes" que en realidad ya están correctos en la base de datos. **Verificación correcta**: consultar directamente el campo JSONB en Postgres (ej. `select field_description from ir_model_fields where ...` o `select name from res_groups where id=...`) y confirmar que ambas claves de idioma (`en_US`/`<lang>`) existen con el valor esperado, antes de asumir un gap de traducción real. Referencia: skill `odoo-translations-17.0` §13.3.

### Playwright MCP & Browser Automation (2026-08-21)

144. **Playwright MCP para automatización de browser agentic**: Playwright MCP (`mcp.playwright`) provee herramientas `browser_*` para automatizar browsers desde agentes LLM — navigate, snapshot, click, type, screenshot, mock, assert. **NO confundir** con `@playwright/test` (archivos `.spec.ts` para CI). Para Odoo: usar `odoo-website-testing-mcp-19.0` para tests de portales/websites, `playwright-mcp-usage` para referencia general de tools. Skills en `~/.config/opencode/skills/` (global) y `src/.opencode/19.0/skills/` (proyecto). Referencia: AGENTS.md MCP Servers → Playwright MCP.

### Testing l10n_ve & Controllers (2026-08-21)

145. **`payment.transaction.create()` requiere `payment_method_id` (NOT NULL en Odoo 17.0)**: el campo `payment_method_id` en `payment.transaction` es `required=True` y no tiene default en Odoo 17.0. Cualquier test que cree transacciones de pago DEBE incluir este campo. Patrón: usar helper `_get_or_create_payment_provider()` que retorna `(provider, payment_method)` o buscar `env['payment.method'].search([], limit=1)` + crear si vacío. Referencia: skill `cadipa-sale-suscription-testing` anti-patrón T7, fix round 1-4 del proyecto `test-countryclub17`.

146. **`payment.method` tiene `provider_ids` (M2M), NO `provider_id` (FK)**: el campo `provider_id` NO existe en `payment.method` — la relación es M2M via `provider_ids`. Al crear `payment.method` en tests, usar `provider_ids=[(6, 0, [provider.id])]`, NO `provider_id=provider.id` que causa `ValueError: Wrong value`. Referencia: fix round 4 del proyecto `test-countryclub17`.

147. **`l10n_ve_invoice` requiere `product_id` en TODAS las líneas de factura**: el override de `account.move.create()` en `l10n_ve_invoice/models/account_move.py:125` valida que toda línea tenga `product_id`. Tests que creen facturas en DBs con `l10n_ve_invoice` instalado DEBEN incluir `product_id` + `account_id` en cada línea de `invoice_line_ids`. Skill `odoo-l10n-ve-test-patterns`. Referencia: fix round 2 del proyecto `test-countryclub17`.

148. **Campo de factura es `name`, NO `move_name`**: el campo en `account.move` se llama `name`. `move_name` aparece como alias SQL o variable local en algunos contexts pero NUNCA como campo ORM. Usar `invoice.name = ''` para limpiar el número correlativo, NO `invoice.move_name`. Referencia: fix round 5 del proyecto `test-countryclub17`.

149. **l10n_ve correlative bloquea re-posting después de `button_draft()`**: después de resetear una factura a draft con `button_draft()`, el número correlativo l10n_ve (ej. `00014`) persiste. Re-postear puede causar `ValidationError: An invoice already exists with the Control Number: XXXXX`. En tests, verificar solo que el estado vuelve a `draft` y `posted_before=False`, sin re-postear. Referencia: fix round 6 del proyecto `test-countryclub17`, skill `odoo-l10n-ve-test-patterns`.

150. **`convert_payment_currency_id` necesita VES/VEF activo en test DB**: el campo computado `convert_payment_currency_id` en `payment.provider` busca VES/VEF con `active=True`. Si la moneda no existe o está inactiva, `currency_id` en `payment.transaction` queda NULL. En setUpClass, buscar VES/VEF con `active_test=False` y setear `active=True` si existe, o crear si no existe. Referencia: fix round 7 del proyecto `test-countryclub17`, skill `odoo-l10n-ve-test-patterns`.

151. **Enterprise constraint `start_date <= next_invoice_date` en `sale_subscription`**: enterprise `sale_subscription` tiene constraint `sale_order_check_start_date_lower_next_invoice_date` que exige `start_date <= next_invoice_date`. Al setear `next_invoice_date` en el pasado en tests, también setear `start_date` a la misma fecha. Referencia: fix round 7 del proyecto `test-countryclub17`.

152. **Portal text depends on locale: check BOTH languages**: badges y textos en templates QWeb de portal dependen del idioma instalado. Tests que verifiquen texto (ej. "To Renew") DEBEN aceptar ambas variantes: `'To Renew' in row or 'Por Renovar' in row`. Skill `odoo-19-testing-translatable-labels`. Referencia: fix round 3 del proyecto `test-countryclub17`.

153. **Controller testing: `werkzeug.utils.redirect` para Response válido en `@http.route`**: el decorator `@http.route` valida el return via `Response.load()`. Un `SimpleNamespace` o `MagicMock` plano es rechazado. Usar `mock_req.redirect = MagicMock(side_effect=werkzeug.utils.redirect)` que retorna un objeto `Found` que `Response.load()` acepta. Skill `api-controller-testing` Patron F. Referencia: fix round 6 del proyecto `test-countryclub17`.
154. **XPath de vistas NUNCA debe seleccionar por texto traducible (`contains(text(), '...')`)**: `ir_ui_view.arch_db` es un campo JSONB traducido (una clave por idioma instalado); Odoo combina las vistas heredadas usando el arch del idioma ACTIVO del request, no siempre `en_US`. Un xpath que matchea un `<th>`/label por su texto en inglés se rompe SILENCIOSAMENTE en cualquier idioma donde ese texto ya esté traducido — y a diferencia de un `t-if` que simplemente evalúa `False`, un xpath sin match revienta la COMBINACIÓN COMPLETA de la vista con `ValueError: ... no se puede localizar en la vista principal`, tumbando toda la página (no solo el elemento afectado). Seleccionar SIEMPRE por un atributo estable e independiente del idioma (`t-if`, `t-field`, `name`, `id`, `class` propio del módulo) — NUNCA por `text()`/label. Distinta de la regla 152 (que es sobre leer texto YA renderizado en tests): esta regla es sobre CONSTRUIR el xpath que localiza el nodo a heredar. Bug real: `country_sale_subscription` (test-countryclub17) rompía `/my/subscriptions/<id>` completo en `es_VE` porque `sale_subscription.subscription_portal_content` (enterprise) traduce "Next Billing Date:" a "Fecha del siguiente cobro:". Referencia: FIX-056 (17.0), FIX-074 (19.0), skill `odoo-button-xpath-patterns` (Anti-pattern AP-XPATH-05).
155. **Delegaciones agente→agente (Task()/dispatch) usan un bloque `Context {}` fijo, no prosa libre, y referencian estado compartido por ruta en vez de pegarlo**: aplica tanto al dispatch `sdd-lead`→OpenCode (`scripts/sdd_opencode_run.sh` ya valida `Context{environment/odoo_version/repo/module/branch/allowed_files}`) como a las delegaciones Claude→Claude nuevas `sdd-builder`→`binaural-fn-programador:senior-dev` y `sdd-qc`→`binaural-fn-programador:code-reviewer` (`Context{task_id/ears_requirement/plan_ref/tasks_ref}` y `Context{module/spec_ref/diff_scope}` respectivamente). Motivo: un prompt de delegación con forma fija entre llamadas es lo que realmente permite que el system prompt del agente delegado (no el prompt de la task en sí, que varía por diseño) se sirva de caché de forma estable, y referenciar `plan.md`/`tasks.md` por ruta en vez de pegar su contenido evita pagar esos tokens dos veces. Ver skill `sdd-opencode-delegate-agent` y el plugin `sudolang-cache-engine` (regla `stigmergic-coordination.sudo.md`) — detalle completo en `src/Agents.md`, sección "Plugin local: `sudolang-cache-engine`". `sdd-lead.md` también cita explícitamente `stigmergic-coordination.sudo.md`/`ttl-management.sudo.md` en su propio bloque `Context{}` de dispatch a OpenCode y en la plantilla fija que usa para invocar el modo `wait` de `sdd-opencode-runner` (ver regla 181) — los tres agentes SDD-Claude (`sdd-lead`, `sdd-builder`, `sdd-qc`) quedan alineados con el plugin, no solo dos de los tres. Extendido 2026-09-05 a un cuarto: `Task(sdd-metrics-reporter)` también usa `Context{period_days/since/reconstruct_narrative}` fijo en vez de prosa libre (ver skill `sdd-metrics-reporter-agent`, sección "Contrato de invocación") — mismo motivo, ningún agente SDD-Claude nuevo debería quedar fuera de esta convención por default.
156. **Un comando lanzado dentro de una sesión tmux con `> archivo 2>&1` deja el pane vacío para cualquier terminal que se adjunte en vivo — usar `comando 2>&1 | tee archivo` + `ec=${PIPESTATUS[0]}`, nunca redirección plana, si el pane debe mostrar salida en vivo**: `scripts/sdd_opencode_run.sh` lanzaba `opencode` dentro del comando interno de su sesión tmux detached con `> "$OUT" 2>&1` — toda la salida iba directo al archivo de log del job, dejando el pane de tmux literalmente en blanco durante toda la ejecución, aunque la sesión mostrara `(attached)` desde una ventana abierta por `scripts/sdd_opencode_view.sh` (visor tmux opcional, ver arriba "Ventana tmux visible"). Fix aplicado: `"$OC_BIN" ... 2>&1 | tee "$OUT"` seguido de `ec=${PIPESTATUS[0]}` (no `$?`, que capturaría el exit code de `tee`, no el del comando real). Aplica a cualquier comando futuro lanzado dentro de una sesión tmux que deba ser visible en vivo Y loggeado a archivo a la vez — redirección plana (`>`) y visibilidad en vivo del pane son mutuamente excluyentes, `tee` es el único punto medio. Referencia: skill `sdd-opencode-delegate-agent` sección "Manejo de errores".
157. **OpenCode se autoimpone "modo plan" en dispatches de un solo turno sin directiva explícita de ejecución**: el agente `sdd-lead` de OpenCode puede interpretar un dispatch con lenguaje de restricción pesado como "solo generar un plan", haciendo preguntas aclaratorias y deteniéndose sin ejecutar ninguna herramienta real — fatal en un dispatch headless donde nadie puede responder. Todo dispatch de un solo turno debe abrir con una directiva de ejecución inequívoca ("MODO EJECUCIÓN INMEDIATA — NO ES MODO PLAN...") y responder de antemano cualquier pregunta aclaratoria esperable. Skill `sdd-opencode-guardrails`. Referencia: verificación E2E Playwright del proyecto `test-countryclub17`.
158. **OpenCode reincide en `docker exec ... psql` pese a prohibición explícita, incluso de solo lectura**: una sola línea de "prohibido" en el prompt no es suficientemente persistente. Hay que restatear la prohibición justo antes del paso de verificación relevante, y monitorear el log del job matando la sesión tmux en la primera ocurrencia de `docker exec`/`psql`, sin esperar a evaluar si la query era "solo lectura". Skill `sdd-opencode-guardrails`. Referencia: proyecto `test-countryclub17`.
159. **Despachos paralelos de OpenCode contra el mismo repo deben aislarse en git worktrees separados (dentro de `src/`)**: jobs concurrentes sobre el mismo working tree colisionan por puerto de BD de test y por cambios cruzados entre módulos hermanos sin visibilidad mutua. Worktrees deben crearse DENTRO de `docker-multi/src/` para ser visibles al bind-mount del contenedor. Skill `sdd-opencode-delegate-agent`. Referencia: proyecto `test-countryclub17`.
160. **El juez (`sdd-judge`) debe verificar contra `git show HEAD:<archivo>` cualquier reclamo de "pre-existing failures" en un autoreporte de OpenCode**: una etiqueta de "no relacionado con esta ronda" puede ser falsa — si el test existía en el HEAD comiteado con la suite en verde, el fallo es una regresión real de la ronda actual, aunque la causa esté en un módulo hermano. Skill `sdd-judge-agent`. Referencia: proyecto `test-countryclub17`.
161. **`account.payment.register` con `l10n_ve_igtf` instalado necesita `active_id` (int) Y `active_ids` (lista) simultáneamente en el contexto**: el core de Odoo 17 exige `active_ids` en `default_get()` cuando `active_model='account.move'`, pero `l10n_ve_igtf.utils.get_moves_from_context()` solo maneja bien `active_id` (int) — con solo uno de los dos, falla con "nothing left to pay" o `MissingError` según cuál falte. Skill `odoo-l10n-ve-test-patterns`. Referencia: proyecto `test-countryclub17`.
162. **Cuentas de test para `property_account_receivable_id`/`payable_id` necesitan `reconcile=True` explícito**: sin esto, `account.payment.register` filtra esas líneas como no-conciliables y falla con "nothing left to pay" pese a residual > 0 — mismo síntoma que la regla 161, revisar ambas causas si el error persiste. Skill `odoo-l10n-ve-test-patterns`. Referencia: proyecto `test-countryclub17`.
163. **Un helper de test invocado como `cls.metodo()` desde `setUpClass` debe declararse `@classmethod`**: si no, el primer argumento posicional pasado se vincula como `self`, produciendo `AttributeError` sobre un atributo aparentemente no relacionado (ej. `'str' object has no attribute 'env'`) que confunde el diagnóstico. Skill `odoo-test-doubles-mocking-17.0`. Referencia: proyecto `test-countryclub17`.
164. **Agregar un chequeo de grupo/permiso a un método compartido (ej. `action_post()`) puede romper silenciosamente los fixtures de test de un módulo hermano DEPENDIENTE**: el síntoma aparece en el módulo dependiente, no en el módulo modificado, dificultando el diagnóstico. Antes de cerrar el cambio, revisar todos los módulos que dependan del modificado (`grep` sobre `depends` en manifests) y otorgar el grupo nuevo en sus fixtures de test también. Skill `odoo-anti-patterns-17.0` (AP-32). Referencia: `country_sale_subscription` → `country_sale_subscription_fees`, proyecto `test-countryclub17`.
165. **La BD real de un ambiente (ej. `countryclub-stg`) nunca recibe el esquema nuevo de `./odoo test` (que usa su propia BD efímera) — hace falta `./odoo update -u <módulos> -d <bd>` explícito antes de verificar funcionalmente contra ese ambiente**: sin esto, cualquier flujo que toque un campo/columna nueva falla con `psycopg2.errors.UndefinedColumn` aunque el código y los tests unitarios estén en verde. Skill `binaural-docker-odoo`. Referencia: proyecto `test-countryclub17`.
166. **Antes de comitear en un repo con submódulos, excluir punteros de submódulo ajenos al trabajo actual (`M <nombre-submódulo>` en `git status`, sin ruta de archivo)**: son el `Subproject commit` desactualizado por otra sesión/persona, sin relación con la tarea — un `git add -A` los mezcla sin querer en el commit. Confirmar con `git diff <submódulo>` que es solo el puntero (no contenido) y usar `git add <rutas específicas>` en vez de `-A`. Skill `workspace-structure`. Referencia: proyecto `test-countryclub17`.

167. **Nunca correr `--stop-after-init`/`--test-enable`/`-u` por CLI directamente contra una base de datos que tiene un servidor Odoo real corriendo (`--dev=all`)**: un segundo proceso Odoo choca por locks de `ir.cron` con el servidor real (`UserError: El registro no se puede modificar en este momento: esta tarea de cron se está ejecutando`). Antes de correr cualquier test automatizado, crear SIEMPRE una base nueva por copia (`CREATE DATABASE "<nombre>" WITH TEMPLATE "<base_origen>"` — ejecutado con `psql -d postgres`, NUNCA `-d odoo`, que no existe como base física), correr los tests ahí, y borrarla al terminar (`DROP DATABASE IF EXISTS "<nombre>"`, verificando el nombre exacto antes de borrar). Skill `sdd-opencode-guardrails`. Referencia: proyecto `countryclub-copy` (bases `countryclub-copy`/`countryclub-copy-2`).

168. **El orden de merge de `extra_create_values` en overrides encadenados de `payment.transaction._create_payment()` varía por módulo — verificar cada uno antes de asumir que una pre-inyección "gana"**: algunos overrides hacen `{**defaults, **extra_create_values}` (los valores ya presentes en `extra_create_values` ganan sobre los defaults calculados después), pero otros hacen `extra_create_values | nuevos_valores` (los valores nuevos, a la derecha, ganan SIEMPRE, sin importar qué traiga `extra_create_values`) — en ese segundo caso, pre-inyectar el valor deseado ANTES de llamar a `super()` no sirve de nada, hay que corregirlo DESPUÉS de que `super()._create_payment()` retorne. Skill `odoo-payment-transaction-architecture`. Referencia: `country_basic_payments` Addendum B11 (`country_sale_subscription`, extra gana) vs B12 (`binaural_payment`, nuevos valores ganan).

169. **Un `t-value` de QWeb con encadenamiento `and`/`or` de Python colapsa al fallback final ante CUALQUIER intermedio falsy (`0.0`, `None`, `''`), no solo cuando "faltan datos"**: el patrón `a and b and c and (calculo) or 'fallback'` es frágil porque en Python `X and Y` retorna `Y` si `X` es truthy, así que si `calculo` mismo evalúa a `0`/`0.0`/`''` (un resultado válido pero falsy), la cadena completa colapsa al `fallback`, perdiendo un valor legítimo — usar SIEMPRE una estructura explícita (`t-if`/`t-set` anidados) cuando el resultado intermedio pueda ser legítimamente falsy. Skill `qweb-template-patterns` (global). Referencia: `country_basic_payments` Addendum #14.

170. **Un `<input type="number" step="0.01">` prefileado con un float sin redondear explícito puede fallar `checkValidity()` por `stepMismatch` pese a verse "lleno"**: ruido de punto flotante en una conversión de moneda (ej. `currency._convert()`) puede producir un valor como `78506.93000000001` que el navegador rechaza contra `step="0.01"` — el campo se ve con un número normal en el HTML, pero `element.validity.stepMismatch === true`. Redondear explícitamente (`round(valor, 2)`) antes de asignarlo al `value`. Skill `qweb-template-patterns` (global). Referencia: `country_basic_payments` Addendum #14/#15 (verificado con Playwright).

171. **Verificar con `git stash`/`git stash pop` si una falla de test reportada por OpenCode es realmente preexistente, no confiar solo en la etiqueta "no relacionado"**: correr la MISMA suite con los cambios propuestos revertidos temporalmente (`git stash`) contra una base de test igualmente fresca — si la falla persiste idéntica, es preexistente; si desaparece, es una regresión real introducida por el cambio. Complementa la regla 160 (verificar contra `git show HEAD:<archivo>` cuando el HEAD ya tiene la suite en verde). Skill `sdd-qc-agent`. Referencia: proyecto `countryclub-copy`.

172. **Al pollear `scripts/sdd_opencode_status.sh` justo después de un dispatch, el directorio del job nuevo puede no existir todavía — un poll inmediato devuelve el resultado CACHEADO del job anterior, no un error**: `sdd_opencode_run.sh` retorna casi inmediato con el `job_id`, pero el directorio `/tmp/sdd-jobs/<job_id>/` puede tardar unos segundos en crearse; si se lanza un status-check demasiado rápido apuntando al `job_id` equivocado (ej. reusando el más reciente de `ls -t` antes de que el nuevo exista), el script reporta el estado del job ANTERIOR sin ningún indicio de error — hay que esperar/reintentar hasta confirmar un `job_id` genuinamente nuevo (no visto antes) antes de interpretar el resultado. Skill `sdd-opencode-guardrails`. Referencia: proyecto `countryclub-copy`, múltiples dispatches de esta sesión.

173. **El `__init__.py` raíz de un módulo Odoo NUNCA debe hacer `from . import tests`**: Odoo descubre y corre los tests de `<módulo>/tests/` de forma independiente vía su propio test loader (`odoo.tests.loader`), sin pasar por el import chain normal del módulo — agregar ese import a `__init__.py` no es necesario para que los tests corran, y SÍ tiene un costo real: carga dependencias de test (`unittest`, mocks, helpers de `PaymentCommon`, etc.) en CADA arranque normal del servidor, no solo al testear. Skill `sdd-opencode-guardrails`. Referencia: proyecto `countryclub-copy`, corregido en QC de un dispatch de OpenCode.

174. **Patrón: escribir un campo que otro módulo (no declarado como dependencia formal) pudo haber agregado, de forma defensiva**: `if 'campo' in modelo._fields: modelo.campo = valor` — permite que un módulo aproveche un campo de otro (ej. `pay_soon` de `binaural_club_socios` sobre `account.move`) sin crear una dependencia dura en el manifest; el módulo sigue funcionando (no-op silencioso) en cualquier entorno donde el campo no exista. Skill `odoo-payment-transaction-architecture`. Referencia: `country_basic_payments` (`foreign_rate` de `l10n_ve_accountant`), `country_sale_subscription_fees` (`pay_soon` de `binaural_club_socios`).

175. **`environment` en el `Context{}` de dispatch a OpenCode nunca debe inferirse por el patrón "termina en `-tests`"**: ese sufijo es la convención real únicamente para módulos de los pools compartidos (`integra-addons-*`/`odoo-venezuela-*`/`third-party-addons-*`, que versionan fuera del repo del cliente y llevan la versión en el nombre del directorio) — los ambientes de cliente (`src/custom/<client>/`) varían de nombre y no siguen ese patrón. `scripts/sdd_opencode_run.sh` deja un warning (no bloqueante) en el log si detecta ese patrón contra un repo que no es un pool compartido. Skill `sdd-opencode-delegate-agent`. Referencia: sesión de guardrails SDD/OpenCode, 2026-08-27.

176. **Toda corrida de tests dentro del pipeline SDD delegado a OpenCode usa SIEMPRE una base de datos nueva por copia (`CREATE DATABASE ... WITH TEMPLATE ...`), nunca reutiliza una BD existente por nombre literal**: ni siquiera si el usuario/`sdd-lead` mencionó un nombre de BD en la solicitud — ese nombre, si existe, es el `TEMPLATE` de partida, nunca el target de escritura. Regla específica de tests; no aplica a otras operaciones que sí necesiten apuntar a una BD real (Gate 6 sigue rigiendo esas). Skills `sdd-opencode-delegate-agent`, `sdd-opencode-guardrails`, `workspace-structure`. Referencia: AGENTS.md #139/#167, sesión de guardrails SDD/OpenCode, 2026-08-27.

177. **El `cwd`/`WORK_DIR` pasado a `scripts/sdd_opencode_run.sh` (4º argumento) ahora se valida mecánicamente contra el `repo` declarado en `Context{}`**: si no coincide (ej. sigue apuntando al `src/` amplio por default en vez del repo acotado), el dispatch se rechaza antes de lanzar tmux/opencode — deja de ser solo una instrucción de prompt que `sdd-lead` podía olvidar. Skill `sdd-opencode-delegate-agent`. Referencia: sesión de guardrails SDD/OpenCode, 2026-08-27.

178. **`"docker exec*": allow` sin restricción en el guardrail de bash de los agentes OpenCode era el hueco real que habilitó la reincidencia en `docker exec ... psql`**: se reemplazó por comandos explícitos necesarios (ej. `"docker exec*python3 -m coverage*": allow`) más `"docker exec*psql*": deny` explícito en `sdd-lead`, `sdd-qc` y `sdd-builder` de OpenCode — la última regla que matchea gana, así que el `deny` cierra el hueco sin importar cuán amplio sea cualquier `allow` de `docker exec*` anterior en la lista. Skill `sdd-opencode-guardrails`. Referencia: incidente `test-countryclub17` (2026-08-26), sesión de guardrails SDD/OpenCode, 2026-08-27.

179. **Contrato `NEEDS_HUMAN_INPUT` (regla R6 de `sdd-lead`)**: si `environment`/`branch`/`repo` no son resolubles con lo declarado en `Context{}` más `instances.json`, el `sdd-lead` interno de OpenCode debe detenerse y devolver `NEEDS_HUMAN_INPUT: <pregunta puntual>` en vez de adivinar o ampliar la búsqueda fuera de `allowed_files`/`--dir`. `sdd-judge` pasa ese veredicto sin tocarlo (tercera opción junto a PASS/FAIL); `sdd-lead` (Claude) escala de inmediato al usuario sin que cuente como iteración del bucle de reintento de la regla R5. Antes de escalar al usuario, `sdd-lead` intenta resolverlo con Onyx (`mcp__plugin_core_onyx__search_indexed_documents`/`search_web`). Skills `sdd-opencode-delegate-agent`, `sdd-lead-agent`, `sdd-judge-agent`. Referencia: sesión de guardrails SDD/OpenCode, 2026-08-27.

180. **Playwright (`mcp__plugin_playwright_playwright__*`) es la herramienta formalmente sancionada de `sdd-qc` para verificación manual/E2E, reemplazando el fallback ad hoc a `psql`**: todo dispatch que la requiera debe abrir con la directiva "MODO EJECUCIÓN INMEDIATA" y restatear la prohibición de `psql` inline antes del paso de verificación específico, no solo una vez al inicio del prompt. Skills `sdd-opencode-delegate-agent`, `sdd-qc-agent`, `playwright-mcp-usage` (global). Referencia: incidente `test-countryclub17` (2026-08-26), sesión de guardrails SDD/OpenCode, 2026-08-27.
181. **`sdd-lead` no debe pollear el estado de un job de OpenCode repitiendo `Task(sdd-opencode-runner, status-check)` uno por uno — cada invocación gasta un subagente Haiku completo solo para reportar "sigue corriendo"**: usar en cambio `scripts/sdd_opencode_wait.sh <job_id> [max_seconds=480] [poll_interval=15]` (modo `wait` de `sdd-opencode-runner`), que reusa la lógica de `sdd_opencode_status.sh` pero hace el loop de `sleep`+chequeo DENTRO de una sola llamada Bash de una sola invocación de subagente, cortando en estado terminal o al agotar la ventana. El status-check puntual queda solo para el primer chequeo inmediatamente después del dispatch. La instrucción de invocación del modo `wait` debe ser una plantilla fija (solo `job_id`/`max_seconds`/`poll_interval` variando al final, nunca intercalados en la oración) para no invalidar el caché del system prompt de `sdd-opencode-runner` entre invocaciones — ver plugin `sudolang-cache-engine`, reglas `ttl-management.sudo.md`/`cache-architecture.sudo.md`. Skills `sdd-opencode-delegate-agent`, `sdd-lead-agent`. Referencia: `scripts/sdd_opencode_wait.sh`, sesión de optimización de polling SDD/OpenCode, 2026-08-27.

182. **Un campo restringido por `groups=` en una vista, si es referenciado en la expresión `invisible`/`readonly`/`required` de OTRO elemento (campo o botón) de la MISMA vista, obliga a que ese otro elemento comparta el mismo grupo — si no, Odoo 17 rechaza la vista con `ParseError: Field '<campo>' used in modifier '<modifier>' ... is restricted to the group(s) <grupo>`**: pasa incluso si el elemento referenciador (ej. un botón) no debería estar restringido por ese permiso — la solución correcta NO es agregarle el mismo `groups=` (eso oculta el elemento a usuarios que sí deberían verlo por otras razones), sino evitar referenciar el campo restringido directamente: usar en su lugar un campo computado auxiliar sin restricción de grupo que ya encapsule la condición necesaria. Detectado en la interacción entre dos tareas del mismo lote (una restringe `is_debt_order` a un grupo nuevo; otra agrega un botón cuyo `invisible` lo referencia) — confirmado en producción (`countryclub-copy-2`) al intentar actualizar el módulo. Skill `odoo-xml-views-advanced-17.0` (y `-19.0`). Referencia: proyecto `countryclub-copy`, tareas 80755/80756.

183. **`sale.order._prepare_invoice()` (core) copia INCONDICIONALMENTE todas las `transaction_ids` históricas de la orden a cada factura nueva (`'transaction_ids': [Command.set(self.transaction_ids.ids)]`) — para una orden de SUSCRIPCIÓN (que reutiliza el mismo registro `sale.order` en cada periodo de facturación), esto arrastra transacciones/pagos de periodos anteriores ya liquidados a la factura del periodo nuevo, causando que el comprobante de un pago viejo se postee también en el chatter de la factura nueva**: si un módulo de suscripciones ya sobreescribe `_prepare_invoice()` por otra razón, agregar ahí (acotado a `self.is_subscription`) un filtro `self.transaction_ids.filtered(lambda tx: not tx.invoice_ids)` antes de asignar `transaction_ids` en los `vals` retornados — solo las transacciones que aún NO tienen factura asignada pertenecen genuinamente al periodo por facturar. El fix es estrictamente hacia adelante (no reprocesa facturas ya mal vinculadas antes del fix). Skill `odoo-payment-transaction-architecture` (global). Referencia: `country_sale_subscription`, tarea 80775, proyecto `countryclub-copy`.

184. **Al ejecutar VARIAS tareas de Odoo relacionadas en UN SOLO worktree/rama compartida (batch), correr SIEMPRE la suite completa del módulo tras CADA tarea agregada, no solo los tests nuevos de esa tarea — una tarea posterior puede romper silenciosamente una anterior ya dada por cerrada** (ej. una restricción de grupo agregada a un campo, referenciado luego por la vista de otra tarea): el síntoma solo aparece al validar la vista completa (instalación/upgrade real del módulo), no necesariamente en los tests unitarios aislados de cada tarea por separado. Skills `sdd-opencode-delegate-agent`, `sdd-opencode-guardrails`. Referencia: proyecto `countryclub-copy`, lote de 6 tareas (80720/80755/80771/80721/80775/80756), 2026-08-28.

185. **Revisión de un doc externo de arquitectura actor-model/TupleSpace (2026-08-31): se adoptó vocabulario y convenciones livianas, se descartó explícitamente todo lo que requería infraestructura nueva o no tenía dónde aplicarse en este repo.** Adoptado (sin nueva infra, solo docs/skills): vocabulario de restart-strategy (`one_for_one`) para la política de reintentos ya existente de `sdd-opencode-delegate-agent`/`sdd-lead-agent`; convención de "retry con diff parcial" (capturar `git diff` del worktree de un job muerto antes de reintentar, para no re-pagar trabajo LLM ya hecho); campo `stage` explícito en los bloques `Context{}` de `stigmergic-coordination.sudo.md`; ítem de checklist de grounding/prompt-injection en `sdd-judge-agent` para contenido externo (tickets, docs fetcheados) tratado como requisito. Descartado explícitamente, con motivo verificado (no re-evaluar sin nueva evidencia): fan-out en dos fases (el `Agent` tool no expone visibilidad de streaming al coordinador); breakpoints rotativos de 20 bloques, serialización determinística de tools y un middleware tipo `ClaudeCacheMiddleware` (los tres solo aplican a llamadas crudas al SDK de Anthropic — grep confirmó cero usos de `anthropic.Client`/`messages.create`/`cache_control` como código ejecutado en este repo, todo pasa por las CLIs `opencode`/`claude`); sandboxing WASM/Firecracker y votación por umbral Byzantine (over-engineering para un pipeline con verificación binaria PASS/FAIL vía `sdd-judge`, sin necesidad de consenso numérico). Skills `sdd-opencode-delegate-agent`, `sdd-opencode-guardrails`, `sdd-judge-agent`, `sdd-lead-agent`, plugin `sudolang-cache-engine` (reglas `fork-agent-patterns.sudo.md`, `stigmergic-coordination.sudo.md`, `ttl-management.sudo.md`). El protocolo genérico para evaluar futuros documentos externos de este tipo ahora vive en la skill `sdd-external-doc-review`.

186. **Terminal productivity tools: aliases en `~/.bashrc` y binarios en `/usr/local/bin/` — NO instalar sin verificar arquitectura y OS**: este workspace (Debian 13 trixie, x86_64) tiene 27 herramientas instaladas (skill `terminal-productivity-tools`). Al clonar esta config en otra máquina: (1) verificar `uname -m` y OS antes de descargar binarios — los `.deb` de yazi/dust son x86_64 específicos, (2) los binarios manuales (gitui, zellij) viven en `/usr/local/bin/` y NO se actualizan con `apt upgrade` — documentar versión instalada y verificar releases cada ~3 meses, (3) `bat` se instala como `batcat` en Debian/Ubuntu — crear symlink `ln -sf /usr/bin/batcat /usr/local/bin/bat`, (4) `fd-find` se instala como `fdfind` — symlink `ln -sf /usr/bin/fdfind /usr/local/bin/fd`, (5) los aliases en `~/.bashrc` (líneas 144-182) sobreescriben comandos estándar (`cat`, `ls`, `grep`, `find`, `du`, `df`) — si algo falla, verificar que el reemplazo esté instalado antes de asumir bug del sistema. Referencia: skill `terminal-productivity-tools`.

187. **Un override de `write()` que auto-rellena/normaliza un campo para satisfacer un `@api.constrains` debe replicarse en `create()`, o el registro puede persistir inválido**: `@api.constrains` es *triggered-only* — si la lógica de auto-relleno solo vive en `write()`, un `create()` directo con el campo disparador ya activo puede persistir sin el campo dependiente. Confirmado con evidencia real en producción (`countryclub-copy-2`): 3 órdenes de `country_sale_subscription_fees` con `is_debt_order=True` y `debt_period_date=NULL`, ya confirmadas, creadas directamente sin pasar por `write()`. Fix: replicar la misma lógica de resolución de origen (`vals` → `self.default_get([...])` → fallback) en un override de `create()` (`@api.model_create_multi`), sin mutar los dicts de `vals_list` en sitio. Skill `odoo-write-trigger-completeness-19.0` (aplica igual a 17.0). Referencia: `country_sale_subscription_fees`, tarea 81463, PR #232.

188. **El MCP `postgres-db` (`postgresql://odoo:odoo@localhost:5432/postgres`) falla con connection refused si el contenedor `db-pg16` no publica el puerto 5432 al host (`docker port db-pg16` vacío)**: para diagnóstico de solo lectura cuando el MCP no conecta, usar `docker exec db-pg16 psql -U odoo -d "<db_name>" -c "<SQL>"` (Claude directo — para OpenCode ese comando sigue denegado, ver regla 178). Para ESCRITURAS que deben respetar computes/constraints, usar `docker exec -i <contenedor_odoo> odoo shell -d "<db_name>" --no-http` por stdin, cerrando con `env.cr.commit()` explícito — a diferencia del protocolo de solo-verificación de `binaural-odoo-shell-live-verification` (siempre `rollback()`), este es un segundo modo de esa skill para escritura autorizada. El clasificador de auto-mode de Claude Code bloquea por defecto escrituras directas a BD real vía este mecanismo — requiere confirmación explícita del usuario. Skills `postgresql-db-work`, `binaural-odoo-shell-live-verification`. Referencia: `country_sale_subscription_fees`, tarea 81463.

189. **Un sub-agente `Task(sdd-opencode-runner, ...)` puede ignorar una instrucción explícita de correr un script de forma síncrona/bloqueante y lanzarlo con `run_in_background`, devolviendo un resultado prematuro o del job equivocado**: pedirle que "encuentre el job_id más reciente" por su cuenta es frágil. Mitigación: (1) pasar SIEMPRE el `job_id` exacto en el prompt del `Task`, nunca pedirle que lo busque; (2) si el resultado no corresponde al `job_id` esperado, relanzar reforzando "NUNCA uses run_in_background". Skill `sdd-opencode-delegate-agent`. Referencia: tarea 81463, PR #232.

190. **Atender un comentario de "Solicitar cambios" de un reviewer humano en un PR ya abierto es un tipo de dispatch distinto al ciclo inicial spec→build→qc de `sdd-lead`**: flujo verificado: (1) leer el comentario vía `gh api repos/<org>/<repo>/issues/<pr>/comments --jq 'select(.id==<id>)'`, (2) `Context{}` de dispatch listando CADA punto del review como tarea literal, branch = la misma del PR abierto, (3) verificar con `sdd-judge`, (4) commit ADICIONAL en la misma rama y push, (5) responder en el hilo del PR listando qué se corrigió. Nueva skill `sdd-pr-review-fix`. Referencia: PR #232, tarea 81463, review de @RogerVBinaural.

191. **`scripts/sdd_opencode_run.sh` falla silenciosamente para prompts de dispatch mayores a ~15-18KB**: la línea `tmux -S "$TMUX_SOCKET" new-session -d -s "$JOB_ID" bash -c "$INNER_CMD"` tiene un límite duro de tmux sobre la longitud del comando (confirmado por binary search: falla con "command too long" desde ~18000 caracteres) — el job queda `status: running` para siempre, sin `output.log`, sin `exit_code`, sin ningún error visible (el fallo ocurre antes de que la sesión tmux exista). Mitigación actual: dividir el prompt en varios dispatches más pequeños (2-3 cambios de archivo por envío). Fix de raíz aplicado 2026-09-05: `scripts/sdd_opencode_run.sh` ahora soporta `"@<ruta>"` como primer argumento, leyendo el prompt de un archivo en vez de pasarlo como argumento posicional — ver regla 192 para el motivo adicional (independiente del límite de tmux) que terminó de justificar este fix. Skills `sdd-opencode-delegate-agent`, `sdd-opencode-guardrails`. Referencia: sesión `/crea-skills`, tarea 81463, 2026-09-03; fix aplicado en sesión de supervisión SDD/OpenCode, 2026-09-05.

192. **Un relay LLM (`sdd-opencode-runner`, Haiku) puede truncar/parafrasear silenciosamente un prompt largo al retipearlo dentro de su propia llamada a la tool Bash, incluso con prompts modestos (~1-2KB, muy por debajo del límite de tmux de la regla 191)**: confirmado en sesión de supervisión SDD/OpenCode (2026-09-05) — un dispatch real terminó con `dispatch.handoff` conteniendo solo el bloque `Context{}`, con toda la descripción de la tarea después de eso desaparecida sin ningún error, y el job igual reportó `status:"done"`/`exit_code:0`. Es un problema distinto al de la regla 191 (allí el límite es mecánico/tmux; acá es el modelo relay eligiendo no reproducir el texto completo). Fix: quien despache (`sdd-lead`) escribe el prompt completo a un archivo de scratchpad con `Write` y pasa `"@<ruta>"` como primer argumento — el relay solo copia una ruta corta, sin nada que parafrasear. `scripts/sdd_opencode_run.sh` ya soporta esta forma. Skills `sdd-opencode-delegate-agent`, `sdd-opencode-guardrails`. Referencia: sesión de supervisión SDD/OpenCode, 2026-09-05.

193. **El `sdd-lead` interno de OpenCode se autoimpone una pausa Plan→Build específicamente en el pipeline SDD completo, distinta de la ya documentada en la regla 157 (caso Playwright)**: en un dispatch headless de Modo Delegación, el modelo puede narrar Spec+Plan+Tasks completos en el chat y terminar el turno preguntando si puede proceder a Build — sin haber llamado ninguna tool de edición. El job queda `status:"done"`/`exit_code:0`, indistinguible de un éxito real hasta inspeccionar manualmente que `specs/<module>/` está vacío. A diferencia del fix de la regla 157 (una directiva "MODO EJECUCIÓN INMEDIATA" repetida en cada dispatch — volátil, se puede olvidar), acá el fix quedó baked-in en el propio `src/.opencode/agents/sdd-lead.md` (bloque estable, se carga siempre): preferible cuando se puede editar la definición del propio agente. Skill `sdd-opencode-guardrails`. Referencia: sesión de supervisión SDD/OpenCode, 2026-09-05.

194. **`/tmp/sdd-jobs/` no sobrevive un reinicio del host, perdiendo el único rastro de cualquier dispatch anterior — migrado a `src/.sdd/logs/{jobs/,metrics.jsonl}` (persistente, overridable con `SDD_LOG_ROOT`)**: `scripts/sdd_opencode_run.sh`/`status.sh`/`cleanup.sh` actualizados; cada dispatch/resultado/huérfano ahora también se anexa como una línea JSON append-only en `metrics.jsonl` (nunca se reescribe una línea anterior). Nuevo agente de solo lectura `sdd-metrics-reporter` (Claude, haiku) agrega esos datos y escribe reportes de auto-mejora en `src/.sdd/reports/`. Skills `sdd-opencode-delegate-agent`, `sdd-metrics-reporter-agent`. Referencia: sesión de supervisión SDD/OpenCode, 2026-09-05.

195. **La delegación SDD completa usa exclusivamente `opencode-go/mimo-v2.5` para TODOS los roles (`sdd-lead/spec/architect/pm/builder/qc/explore`) — ya no hay split con `deepseek-v4-flash` para los roles mecánicos**: decisión explícita del usuario (consumo/previsibilidad, 2026-09-05), aplicada en `src/.opencode/opencode.json` (config del repo, la que realmente aplica dentro de `docker-multi`) y replicada en `~/.config/opencode/opencode.jsonc` (global) para que no diverjan — ambos archivos deben mantenerse alineados manualmente. Skill `sdd-opencode-guardrails`. Referencia: sesión de supervisión SDD/OpenCode, 2026-09-05.

196. **Un agente fresco de reporte (`sdd-metrics-reporter`) puede afirmar una tabla de "modelo esperado" desactualizada de memoria en vez de leer el archivo de config real, pese a una instrucción explícita de "verificar el estado real"**: un principio general ("verificá contra el filesystem") no basta para un modelo barato bajo presión de producir un reporte rápido — hace falta un comando literal obligatorio (`cat src/.opencode/opencode.json`) en el procedimiento, no solo la advertencia. Skill `sdd-metrics-reporter-agent`. Referencia: sesión de supervisión SDD/OpenCode, 2026-09-05.

197. **Auditoría de cumplimiento del plugin `sudolang-cache-engine` (2026-09-05) sobre los agentes SDD tocados esa sesión**: encontró violaciones reales de `temporal-layering.sudo.md` (narrativas de incidente con job-id/fecha literal incrustadas en el bloque estable/siempre-cargado de `src/.opencode/agents/sdd-lead.md` y `.claude/agents/sdd-opencode-runner.md`) — movidas a sus skills respectivas (carga on-demand). También corrigió referencias stale a `/tmp/sdd-jobs/` dentro de las propias reglas del plugin, y extendió la regla 155 (bloque `Context{}` fijo) a una cuarta delegación (`Task(sdd-metrics-reporter)`). Skills `sdd-opencode-guardrails`, `sdd-metrics-reporter-agent`, plugin `sudolang-cache-engine`. Referencia: sesión de supervisión SDD/OpenCode, 2026-09-05.

198. **Un módulo con código ya migrado a una versión mayor puede seguir teniendo un gap real de dato en el upgrade in-place, invisible desde una instalación limpia**: `binaural_club_socios` reemplazó `type_relation` (Selection, 17.0) por `beneficiary_classification_id` (Many2one a un modelo nuevo, 19.0), sembrado vía `post_init_hook` — que solo corre en instalación nueva, nunca en upgrade de un módulo ya instalado. Sin script de migración, cualquier base de cliente real que ya tenía el módulo en 17.0 quedaría con la clasificación nueva en `NULL` tras el upgrade. Patrón de fix: script `pre-*.py` que renombra la columna vieja a temporal antes de que el `_auto_init` cree la columna nueva, y `post-*.py` que siembra los datos semilla (reusando la función del hook, idempotente) y hace el backfill vía SQL directo desde la columna temporal. Al escribir el backfill, ojo con comparar contra campos `translate=True` (se almacenan como jsonb, requieren `->> 'en_US'`, no `=` directo — bug real cometido y corregido en el mismo script). Skills `odoo-migration-19` (lecciones 51-55), `binaural-openupgrade-simulation` (nuevo). Referencia: TA-82204, rama `19.0_mig_ta_82204_migration_scripts_club_socios`, 2026-09-08.

199. **Verificar un script de migración con un "smoke test" (invocar `migrate()` a mano) no prueba que Odoo realmente lo dispare en un upgrade real — hace falta simular el hop completo, y esa simulación tiene sus propios gotchas de infraestructura no relacionados al módulo que se está migrando**: en la simulación de 3 saltos (17.0→18.0→19.0) de TA-82204, el hop 18→19 crasheó con lo que parecía un bug de Core (`ir_model.state` cast a jsonb inválido) — causa real: faltaba el flag `--load=base,web,openupgrade_framework` en el comando del hop, sin el cual los parches propios de `openupgrade_framework` (que ya cubren exactamente ese caso) nunca se importan. Además: el paquete oficial `odoo/upgrade-util` no debe pinearse a `@master` (puede resolver a un commit dev roto), y clonar una base entre instancias en clusters Postgres DISTINTOS requiere `pg_dump`/`pg_restore`, no `CREATE DATABASE ... TEMPLATE` (que solo funciona dentro del mismo cluster). Nuevo skill `binaural-openupgrade-simulation` con la metodología completa y checklist. Referencia: TA-82204, 2026-09-08.

200. **Crear una `res.company` con `country_id` seteado dispara automáticamente `install_l10n_modules()` (sin wizard manual)**: en Odoo 19, `res.company.create()` (`base/models/res_company.py`) instala la localización del país y carga su chart template (`account.chart.template._load()` → `_post_load_data()`) en el mismo `create()` — cualquier validación custom sobre `product.template`/`account.tax` que se dispare por ese batch `write()` debe soportar un recordset multi-registro real, no solo el caso de un producto a la vez. Skill `l10n-ve-accountant` (sección TI-15065). Referencia: PR #1305, verificación E2E 2026-09-10.

201. **Crear una BD manualmente vía `docker exec -u root <container> odoo -d <db> -i <mod> --stop-after-init` deja el filestore con owner `root`, causando `PermissionError`/`500` al servir assets web cuando el worker normal (usuario `odoo`) intente generarlos**: correr `./odoo fix-files <instancia>` inmediatamente después, antes de cualquier verificación por UI (Playwright u otra). Skill `binaural-docker-odoo`. Referencia: verificación E2E TI-15065, 2026-09-10.

202. **En un formulario backend OWL de Odoo 19, `.o_form_button_save` puede quedar `disabled` pese a haber "escrito" un valor con `browser_fill_form`/`.fill()` de Playwright — ese método no siempre dispara el tracking de "dirty" de OWL**: usar `browser_type` con `slowly: true` (keystrokes reales) en su lugar, y verificar `disabled`/`.o_form_dirty` vía `browser_evaluate` antes de reintentar el guardado. Un guardado sin efecto y sin error visible casi siempre es un campo requerido vacío — diagnosticar con `document.querySelectorAll('.o_field_invalid')` antes de asumir un bug de la herramienta. Nueva skill `odoo-backend-testing-mcp-19.0`. Referencia: verificación E2E TI-15065, 2026-09-10.

203. **Widget JS legacy (`Class.include()`) con método `async`: `this._super()` llamado después de un `await` lanza `TypeError`** — el mixin restaura `_super` de forma síncrona al retornar la promesa (primer `await`, no cuando se resuelve); capturar `const _super = this._super.bind(this, ...arguments)` como primera línea del método, antes de cualquier `await`, y usar esa variable en vez de `this._super(...)` después. Nueva entrada FIX-057 (`odoo-code-review-17.0`) / FIX-075 (`odoo-code-review-19.0`). Referencia: PR #247 (countryclub), bloqueante N4, 2026-09-11.

204. **Al batchear un loop per-registro con `try/except` para arreglar un N+1 (FIX-042), verificar que el método interno invocado ya capture los MISMOS tipos de excepción antes de eliminar el except externo** — de lo contrario se pierde aislamiento de errores y una excepción de un solo registro puede tumbar todo el batch, y a callers que dependían de ese aislamiento (ej. `cr.savepoint()` por-lote). Nueva entrada FIX-058 (`odoo-code-review-17.0`) / FIX-076 (`odoo-code-review-19.0`). Referencia: countryclub, ronda de mejora proactiva ciclo 3→5, regresión detectada por un ciclo de descubrimiento abierto posterior, 2026-09-12.

205. **El guardrail de `sdd-opencode-guardrails` bloqueaba `docker exec*psql*` pero no `docker exec*odoo*-d <BD real>*` — un job de OpenCode instaló/testeó un módulo directamente contra la BD real `countryclub` (`docker exec -u root odoo-countryclub odoo -d countryclub -i country_basic_payments --stop-after-init`) en vez de usar `./odoo test`** — se refuerza el bloque de ejemplo bash allow/deny de la skill con una entrada explícita por cliente conocido; no confundir con la regla 201 (crear una BD NUEVA vía el mismo comando es válido, el problema es apuntar contra el nombre de una BD real preexistente). Seguimiento técnico pendiente: replicar el deny real (no solo el ejemplo de la skill) en `src/.opencode/agents/*.md`/`opencode.json`. Referencia: countryclub, ronda de mejora proactiva ciclo 4 (primer intento), 2026-09-12.

206. **Nueva metodología: ronda de N ciclos de mejora proactiva con ciclo final de descubrimiento abierto** — en vez de reaccionar a un solo comentario de review humano, correr N ciclos sucesivos (cada uno con su propio review→spec/tasks acotado→build TDD→QC vía `sdd-judge`), donde el ÚLTIMO ciclo revisa el diff acumulado completo del round buscando específicamente regresiones introducidas por los ciclos anteriores del mismo round (caso real: el ciclo 5 encontró y corrigió una regresión que el ciclo 3 había introducido, ver regla 204). Nueva skill `sdd-proactive-improvement-rounds`. Referencia: countryclub, 2026-09-12.

207. **Odoo 19.0 removió la clase `Product` del frontend JS del POS — se dividió en
`ProductTemplate`/`ProductProduct`, y `get_price` pasó a `getPrice` con 7 parámetros** — cualquier
override/`patch()` de pricing en el POS portado desde 16.0/17.0 (que usaba
`odoo.define(...)`/`Registries.Model.extend` sobre `Product`, o `pricelist.items?.[0]`) necesita
reescribirse contra la API real de 19.0: import desde `@point_of_sale/app/models/product_template`
(no `@point_of_sale/app/store/models`, que ya no existe en código 19.0-nativo), `patch()` sobre
`ProductTemplate.prototype`, y resolución de reglas vía
`pricelist.getRulesByProductId/getRulesByTmplId/getCategoryRulesIds/getGlobalRulesIds/findBestRule`
(no `pricelist.items`). No existe un punto de extensión de una sola línea para un `base` custom de
pricelist — hay que sobrescribir `getPrice` completo, copiando fielmente (no de memoria) el ajuste
de cantidad por lote y la resolución de reglas del core, sin duplicar el `push` sobre
`related_lines` (se pasa por referencia — duplicar el push allí infla la cantidad usada para
resolver la regla). Ver skill `odoo-pos-pricelist-getprice-19.0` y `odoo-code-review-19.0`
FIX-077/FIX-078/FIX-079/FIX-080 para el detalle completo y el caso real (`binaural_brand_pos`,
`binaural_pos_last_cost`, TA-15107, PR
https://github.com/binaural-dev/integra-addons/pull/2802).

208. **Un prompt de dispatch a OpenCode muy grande puede matar la sesión tmux en silencio
(`orphaned`), aunque el dispatch reporte `"status":"running"`** — `scripts/sdd_opencode_run.sh`
embebe el prompt completo (ya escapado) dentro del comando `tmux new-session ... bash -c
"$INNER_CMD"`; con un prompt de ~16KB (ej. citando bloques de código extensos del core textual para
darle contexto exacto a OpenCode) la sesión murió inmediatamente sin error visible en el resultado
del dispatch — solo se detecta revisando `sdd_opencode_status.sh <job_id>` y viendo
`"status":"orphaned"`. Mitigación confirmada: no pegar bloques de código extensos dentro del
prompt — apuntar a la ruta/rango de líneas del archivo real e indicarle a OpenCode que lo lea él
mismo. Ver skill `sdd-opencode-delegate-agent`, sección de límite de tamaño del prompt.

209. **Un contador `Integer` incrementado manualmente en un controlador (ej. `partner.appointments_count += 1` al crear una cita) y sin decremento equivalente en el camino de cancelación/archivado (`action_archive()`, que solo pone `active=False`) queda desincronizado indefinidamente — el único fix robusto es convertirlo en `compute(store=False)` sobre `search_count()`/`One2many`, no agregar un decremento puntual**: además, si el compute se extiende entre módulos vía un hook con parámetro (`_get_x_domain(member=False)`), verificar SIEMPRE que el call-site real (no solo los tests, que pueden invocar el hook directo con el parámetro) propague ese parámetro — y que la ventana de fecha resultante tenga cota inferior Y superior, no solo inferior. Ver FIX-059/060/061 en `odoo-code-review-17.0` y skill `cadipa-appointment-membership-limits`. Referencia: ticket helpdesk #13019 (mail.message 879732), PR #233 (`cadipa1`) — 3 rondas delegadas a OpenCode con hallazgos reales de `sdd-judge`/`code-reviewer` antes del fix final.

### Port Protocol & Cross-Tool Sync (2026-09-17)

Reglas para sincronizar conocimiento entre Claude Code y OpenCode.

210. **OpenCode es la fuente de verdad para skills/proyecto; Claude consume via symlinks**: `src/.opencode/skills/` → `~/.claude/skills/` (unidireccional via `skill-sync-daemon.sh`). NUNCA editar directamente un symlink en `~/.claude/skills/` — siempre editar el archivo fuente en `src/.opencode/skills/` y ejecutar `skill-sync-daemon.sh --once`. Referencia: skill `claude-opencode-port-protocol`.

211. **Agentes OpenCode requieren DOS artefactos**: (1) archivo `.md` en `src/.opencode/agents/` con frontmatter (model, mode, permission) + instrucciones, Y (2) entry en `src/.opencode/opencode.json` → sección `agent`. Sin ambos, `Task(subagent_type: "<name>")` falla silenciosamente. OpenCode usa `opencode-go/mimo-v2.5` para TODOS los agentes (no split Haiku/Sonnet/Opus como Claude). Referencia: skill `claude-opencode-port-protocol`.

212. **Plugins Claude → OpenCode: adaptar formato, no copiar**: Claude rules (`.sudo.md`) → OpenCode skills (`SKILL.md` con frontmatter). Claude agents (`.md` con tools/model) → OpenCode agents + opencode.json. Claude hooks (`.sh`) → función en `scripts/precommit`, NUNCA como hook standalone. NO portar plugins genéricos (docx, pdf, pptx, xlsx, morning, docs, import-memory). Referencia: skill `claude-opencode-port-protocol`.

213. **Secret-scan integrado en pre-commit, no como hook**: `_check_secrets()` en `scripts/precommit` con 8 patrones regex (AWS, GitHub PATs, private keys, Slack, Google, Stripe, Anthropic + generic). Corre ANTES del pre-commit real. NO implementar como PreToolUse hook de Claude ni como standalone. Referencia: `scripts/precommit:53-109`, skill `claude-opencode-port-protocol`.

214. **Post-port: SIEMPRE ejecutar sync + actualizar AGENTS.md**: Después de portar skills/agents/commands de Claude→OpenCode: (1) `skill-sync-daemon.sh --once`, (2) actualizar inventarios en AGENTS.md (líneas 27-29, 44-56, 1600-1612), (3) agregar sección si es categoría nueva, (4) agregar regla si el port revela patrón repetible. Referencia: skill `claude-opencode-port-protocol`.

215. **Odoo Version Detection: NUNCA asumir versión, SIEMPRE detectar**: Leer `__manifest__.py` → campo `version` (formato `MAJOR.MINOR.PATCH.MODULE.BUILD`). La versión MAJOR.MINOR es la que importa. Si no hay manifest, detectar desde contexto (directorio, branch, instance name). Skills version-specific van en `src/.opencode/<version>/skills/`, skills version-agnósticos en `src/.opencode/skills/`. NUNCA usar skill de 17.0 para código 19.0 sin verificar BREAKING changes. Referencia: skill `odoo-version-detection`.

216. **Cache Engine Governance: Context{} block fijo ~80 tokens, Skills on demand**: Todo agente SDD invocado via `Task()` debe tener bloque `Context{}` fijo (task_id, ears_requirement, plan_ref, tasks_ref, branch, repo, module, stage). Máximo ~80 tokens. Skills se cargan via tool `skill` cuando el agente las necesita (Fondo Volátil). Usar `cache-analyzer` para auditar prompts, `cache-optimizer` para reestructurar. Referencia: skill `sudolang-cache-engine-governance`.

### Translation & Precommit Rules

217. **Translation patterns that pass OCA precommit mandatory**: The ONLY `_()` format that passes `translation-not-lazy` (W8301) in mandatory precommit is `.format()`. Patterns like `_('...%s...') % (value)` and `_('...%(name)s...') % {'name': value}` both FAIL. The "lazy" second-argument pattern `_('...%s', value)` also FAILS. Only `.format()` works. Reference: skill `odoo-translation-precommit-patterns`, PR `cadipa1#235`.

218. **Cherry-pick to release branch workflow**: When cherry-picking a commit from staging to release, create a NEW branch from release (`rls_<description>`), apply the fix, update submodule pointers by creating a branch from release's submodule hash, cherry-pick the fix there, then update the parent repo's submodule reference. NEVER push directly to release. Reference: skill `workspace-structure`, PR `cadipa1#235`.

219. **Guard de aprobación: proteger también el campo de estado, no solo las líneas que condiciona** — un `write()` guard que bloquea `price_unit`/`discount` en base a un campo Selection (`*_approval_state`) es cosmético si ese mismo campo no está protegido contra escritura directa: cualquier usuario puede `write({"approval_state": "approved"})` por RPC y auto-desbloquearse sin aprobador. Declarar un set explícito de "campos protegidos del workflow" y bloquear su escritura salvo un context flag interno que solo las acciones oficiales seteen. Nueva entrada FIX-068 (`odoo-code-review-17.0`) / FIX-087 (`odoo-code-review-19.0`). Referencia: PR #254 (countryclub), TA-82205, ronda 2.

220. **Guard de x2many commands: cubrir los 6 ops, no solo delete/unlink** — un guard que bloquea remoción/reemplazo de líneas vía comandos x2many (`invoice_line_ids`, etc.) debe revisar explícitamente los 6 ops de Odoo (`CREATE=0, UPDATE=1, DELETE=2, UNLINK=3, LINK=4, CLEAR=5, SET=6`), no asumir que delete/unlink (2/3) agota "quita/reemplaza registros" — `Command.clear()`/`Command.set()` (5/6) logran el mismo bypass. Nueva entrada FIX-069 (`odoo-code-review-17.0`) / FIX-088 (`odoo-code-review-19.0`). Referencia: PR #254 (countryclub), TA-82205, ronda 2.

221. **Guard de "no tocar el monto": enumerar TODOS los campos económicamente equivalentes** — bloquear `price_unit`/`discount` bajo un lock de aprobación sin cubrir `quantity` deja un bypass con el mismo efecto económico. Al definir el set de campos protegidos, preguntar "¿qué otro campo, combinado con los ya cubiertos, logra el mismo resultado?" en vez de limitarse a lo mencionado literalmente en el ticket. Replicar el set en el guard Python (modelo padre Y modelo hijo) y en el `readonly` de la vista. Nueva entrada FIX-070 (`odoo-code-review-17.0`) / FIX-089 (`odoo-code-review-19.0`). Referencia: PR #254 (countryclub), TA-82205, ronda 2.

222. **Testing mail_notification: `message_ids` excluye `user_notification` por diseño — no basta para detectar regresión de `message_type`** — el dominio del campo `message_ids` en `mail.thread` excluye `message_type='user_notification'` siempre, sea el código correcto o buggy (`'notification'` en vez de `'user_notification'` también queda fuera). Verificar contra `mail.message` directamente, con un dominio acotado (ej. `subject`) — un dominio amplio (`model`+`res_id`+`message_type`) también captura el mensaje automático de field-tracking (`tracking=True` en el campo) que Odoo postea con `message_type='notification'` por defecto, dando falsos positivos/negativos no relacionados al código bajo prueba. Skill `mail-notification-patterns` §Testing Gotchas. Referencia: PR #254 (countryclub), test `test_dual_channel_followup_not_in_chatter`.

223. **Reconciliar STATE.md/tasks.md/checklists locales contra el diff real antes de cerrar una ronda de review** — un ítem marcado "DEFER"/pendiente en un tracking doc puede llevar implementado desde una ronda anterior sin que el archivo lo refleje (o viceversa), confundiendo a un revisor futuro que confía en el checklist en vez de en el código. Antes de reportar un punto como "aplicado"/"diferido", `grep` el código real por la palabra clave y actualizar el tracking doc para que coincida. Skill `sdd-pr-review-fix`. Referencia: PR #254 (countryclub) — `openspec/changes/ta-82205-.../STATE.md` marcaba "Fix 7: DEFER" sobre código ya shippeado.

224. **El daemon Docker puede quedar contendido por sesiones concurrentes**: si otra sesión (agente u otra terminal) está construyendo una imagen pesada de Odoo al mismo tiempo, comandos básicos como `docker ps`/`docker images` pueden colgarse varios minutos sin fallar — no asumir que el daemon está caído. Skill `binaural-docker-odoo`. Referencia: PR #2691 (integra-addons), setup de instancia de test aislada, 2026-09-21/22.

225. **El orden de salida de `scripts/precommit`/`scripts/run_tests.sh` puede aparecer invertido al redirigir a archivo o `| tail`**: mezclan `print()` de Python (bufferizado cuando stdout no es TTY) con subprocesos (`docker exec`, `pre-commit`) que heredan el stdout sin buffer — el output del subproceso puede salir ANTES que los `print()` del wrapper. No diagnosticar fallos por el orden visual; confiar en el exit code y, si hace falta, capturar el output completo sin `tail` intermedio. Skill `binaural-docker-odoo`. Referencia: PR #2691 (integra-addons).

226. **Una corrida verde de `scripts/precommit` reportada por el bot no garantiza que siga verde después**: el script re-clona/actualiza `precommit-config-files` desde el remoto en cada corrida, así que la config puede endurecerse sin que el código del PR cambie. Re-ejecutar localmente antes de dar un PR por listo, sobre todo si estuvo abierto varias semanas. Skill `guia_precommit_odoo`. Referencia: PR #2691 (integra-addons) — 4 corridas previas del bot en verde, `W0404 reimported` (triple import idéntico) detectado recién al re-ejecutar localmente.

227. **Un review de bot IA puede reportar falso positivo sobre una dependencia/infra que vive en un archivo gitignored** (ej. `instances.json`) que el bot no ve en el diff del PR: verificar contra el estado real del workspace antes de aceptar el hallazgo como válido, en vez de "corregir" algo que ya funciona. Skill `sdd-pr-review-fix`. Referencia: PR #2691 (integra-addons) — `binauralbot` marcó `odoo.upgrade.util` como no verificado sin ver el pin ya existente en `instances.json`.

228. **Antes de publicar en el chatter de una tarea/ticket de Odoo, SIEMPRE seguir la skill `core:escribir-en-chatter`** (gate de confirmación humana antes de publicar, vínculo de PRs como registros `github_pr_ids` en vez de mencionarlos en prosa, mention real vía `data-oe-model`/`data-oe-id` resolviendo homónimos por `res.users`) — un `post_message` directo sin mostrar el borrador ni linkear los PRs, aunque publique, no cumple el gate y deja de proveer la trazabilidad esperada (los PRs no vinculados como registro son indistinguibles de "no hecho" para quien audite el ticket después). El conector que esa skill necesita para mentions/HTML reales (`mcp__plugin_core_odoo__post_message`, con `body_is_html`/`partner_ids`) devolvió `Invalid credentials or insufficient permissions` en una sesión (confirmado también con `get_current_context`) — verificar con esa tool ANTES de asumir que funciona; si sigue roto, avisar al usuario en vez de degradar silenciosamente a `mcp__claude_ai_Binaural_MCP__post_message` (funciona, pero solo texto plano, sin `partner_ids` ni acceso a `mail.followers`). Referencia: sesión TA-82204, 2026-09-22 — comentario publicado en `project.task` 82204 sin draft/confirmación ni `github_pr_ids`, detectado retroactivamente al revisar la skill.

229. **Workarounds no disruptivos para 3 problemas de infraestructura Docker compartida detectados en TA-82204 (2026-09-21)**: (a) el bug conocido de índice nombre→ID corrupto (ver `workspace-structure`) se puede evitar SIN reiniciar el daemon compartido — renombrar la instancia en `instances.json` y reconstruir solo ese servicio; (b) `./odoo build` compila TODAS las instancias en una sola invocación de `docker compose build` — el fallo de red de una instancia ajena (ej. un `curl` roto para una imagen 17.0 de otro cliente) aborta la build completa con `[exited with code 0]` engañoso; regenerar config vía los generadores Python directamente y correr `docker compose build <servicio>` acotado evita depender de instancias ajenas; (c) `docker compose` serializa invocaciones concurrentes del mismo proyecto entre sesiones distintas — un `./odoo start`/`build` propio puede parecer colgado mientras espera el lock de otra sesión; verificar procesos vivos y evidencia de trabajo real antes de matar nada (matar a mitad de un `docker compose up` es justamente lo que puede producir (a)). Ver skill `workspace-structure` para el detalle completo y los comandos exactos.

230. **El worktree de un review-fix puede (y a veces debe) crearse con ORIGEN en un clon externo fuera de `docker-multi`** (ej. `/home/binlp011/sources/<repo>`, un checkout personal del usuario) cuando el checkout de `docker-multi/src/<repo>` está sucio o en otra rama y no se lo quiere tocar — el DESTINO del worktree sigue teniendo que caer dentro de `docker-multi/src/` (mount único de los contenedores), pero `git worktree add <destino-en-docker-multi/src> <branch>` se corre parado en el repo origen externo. Patrón ya existente en el workspace (`integra-addons-19.0-wt-pr2691`). Ver skill `workspace-structure`.

231. **Un script de migración que asigna un campo con `UPDATE` SQL crudo (por rendimiento) y LUEGO necesita que un campo calculado-y-almacenado (`store=True`) que depende de ese campo se recalcule, debe invalidar la cache de la transacción ANTES de leer/recomputar** — si el mismo cursor tuvo actividad ORM previa sobre esos registros en la misma transacción (ej. un test que los creó, u otro hook), el `env` fresco creado dentro del script de migración comparte esa cache (es por-transacción, no por-instancia de `Environment`) y lee el valor viejo aunque el `UPDATE` crudo ya haya cambiado la fila en la base. Fix: `env.invalidate_all()` antes de `browse()`+recompute+`flush_recordset()`. Nueva entrada FIX-090 (`odoo-code-review-19.0`), lección #56 (`odoo-migration-19`). Referencia: `binaural_club_socios/migrations/19.0.1.1.3/post-migrate_beneficiary_classification.py`, TA-82204, detectado por un test propio antes de mergear (no en producción).

232. **Un mismo ticket puede generar reviews de IA en más de un PR de repos distintos, sobre ramas con el mismo nombre** — se resuelve con un worktree por repo (posiblemente en un mismo ambiente Docker nuevo para correr ambos test suites) pero SIEMPRE un commit y una respuesta de PR separados por repo; si ambos PRs referencian la misma tarea de Odoo, un solo comentario consolidado (siguiendo `core:escribir-en-chatter`, no un `post_message` directo) cubre ambos. Nueva sección en skill `sdd-pr-review-fix`. Referencia: TA-82204, PRs `integra-addons#2766` + `odoo-venezuela#1293`, 2026-09-21/22.

233. **Teardown de worktree + instancia de test Docker: 4 gotchas confirmados (PR #2691, 2026-09-22)** — (a) `__pycache__` owned por `root` (dejado por el contenedor Odoo corriendo como root sobre `./src` montado) bloquea `rm -rf`/`git worktree remove` con `Permission denied`; sin `sudo`, resolver con un contenedor descartable (`docker run --rm -v <path>:/target alpine sh -c "find /target -name __pycache__ -type d -exec rm -rf {} +"`); (b) `git worktree remove` puede desregistrar el worktree pero dejar el directorio físico si el permiso falla a mitad de camino — verificar con `find <ruta> -not -user "$USER"` después, no confiar en el mensaje; (c) `git branch -d` sobre la rama de un worktree de PR abierto falla con "not fully merged" porque compara contra el HEAD del checkout LOCAL, no contra origin — confirmar `git rev-parse <rama>` == `git ls-remote origin <rama-remota>` antes de forzar con `-D`; (d) `./odoo remove <instancia>` no borra la imagen Docker ni garantiza que los volúmenes nombrados desaparezcan — verificar y limpiar con `docker volume rm`/`docker rmi` explícitos. Skill `workspace-structure` §"Teardown de un worktree + instancia de test".

234. **2 gotchas adicionales de teardown no cubiertos por la regla 233 (TA-82204, 2026-09-22)**: (a) el índice nombre→ID corrupto de Docker (ver regla de `workspace-structure` sobre "referencia de nombre de contenedor corrupta") puede resolverse SOLO con el tiempo — un contenedor fantasma invisible en un momento dado puede volverse visible y borrable normalmente más tarde sin reiniciar el daemon; re-chequear `docker ps -a` antes de escalar al restart/rename; (b) al limpiar el propio ambiente, NUNCA correr `docker system prune`/`builder prune`/`volume prune` sin acotar — el build cache compartido (decenas de GB) es usado por TODAS las instancias de TODAS las sesiones activas en el host; limpiar solo por nombre exacto de la propia instancia (contenedor, imagen, volúmenes). Ver skill `workspace-structure`.

235. **Reconciliar un PR marcado `CONFLICTING` contra su rama base es un modo de trabajo distinto al pipeline spec→build→qc y a `sdd-pr-review-fix`** — nueva skill `sdd-pr-conflict-reconcile`. Tres lecciones confirmadas: (a) un clon local shallow rompe `git merge-base` con exit 1 y sin mensaje, indistinguible de "historias no relacionadas" — siempre `git fetch --unshallow` antes de analizar un conflicto en un clon de origen incierto; (b) `git merge-tree --write-tree --merge-base=<X>` enumera los conflictos reales sin tocar el working tree, y puede revelar que el conflicto real es mucho menor que "todo el PR" (4 de 5 módulos sin ningún conflicto en el caso real); (c) cuando el conflicto es porque el mismo módulo fue migrado dos veces en paralelo (la rama base lo migró de forma independiente después de que la rama del PR divergiera), NO hay que confiar en el autoreporte de OpenCode sobre qué se resolvió — verificado dos veces en la misma tarea: reportó "tests corridos" habiendo solo hecho `python3 -m py_compile`, y reportó "docs ya completos" cuando un `grep` directo mostraba 16 menciones de una feature ya eliminada. Referencia: PR #2731 (integra-addons), tarea 81271/81283, 2026-09-22.

236. **Teardown de un ambiente Docker/worktree renombrado a mitad de tarea deja huérfanos bajo el nombre viejo si solo se limpia por el nombre actual** — dos gotchas confirmados (PR #2731, integra-addons, 2026-09-22): (a) el teardown estándar (`./odoo remove`, `docker volume rm`/`docker rmi` por nombre) solo encuentra recursos bajo el nombre vigente en `instances.json` — si la instancia fue renombrada en algún momento de su vida (ej. workaround del bug de índice corrupto de Docker), hay que repetir la búsqueda explícitamente con el nombre pre-rename; (b) un contenedor fantasma del bug de índice corrupto puede estar realmente `Up` (no solo `Created`) por horas sin aparecer en ninguna consulta directa — el disparador confiable para descubrirlo es un error de `docker volume rm`/`docker rmi` ("volume is in use - [hash]"/"must be forced") durante el propio teardown, que revela el hash real. Skill `workspace-structure` §"Teardown de un worktree + instancia de test" y §"Docker Troubleshooting", nueva sección "Teardown" en `sdd-pr-conflict-reconcile`.

237. **Un módulo base que rediseña una vista rompe el `-u` desde versiones viejas si un puente tenía una vista heredada con otro xmlid anclada a lo eliminado** (Odoo 19.0, tarea 82676, 2026-09-23): `_process_end` borra los huérfanos recién al final, y la vista vieja sigue activa al validar la nueva (`ParseError ... no se puede localizar en la vista principal`). Solución: `pre-migrate.py` en el módulo base que desactiva esas vistas por xmlid. Solo se detectó restaurando una base real de cliente; `./odoo test` con base limpia no lo ve. Skills `odoo-upgrade-scripts-19.0` §6.4 y `binaural-product-catalog-19.0`.

238. **Odoo 19 hace commit después de cada módulo durante `-u`** (`odoo/modules/loading.py:273`): si la actualización falla a mitad de camino, los módulos ya cargados quedan con su `latest_version` nueva y sus scripts de migración no vuelven a correr en el reintento. Para validar una migración, restaurar la base desde cero y actualizar una sola vez; no dar por probada una migración "porque el segundo intento pasó". Skill `binaural-restore-client-backup`.

239. **`./odoo update` (y cualquier comando del CLI que use `docker exec -it`) no hace nada, sin error, en sesiones sin TTY** (agentes, background): los módulos quedan sin instalar ni actualizar. Usar `docker exec -u root <container> odoo --stop-after-init -p 90 --workers=0 -u|-i <mods> -d <db>` sin `-it`, solo sobre bases propias. Relacionada con la regla 99 (`scripts/coverage`). Skill `binaural-docker-odoo` §Troubleshooting.

240. **Restaurar un backup de cliente en un ambiente de worktree**: preferir `scripts/odoo_restore`; neutralizar siempre (`odoo neutralize`); armar los addons con el mismo orden que la instancia del cliente, reemplazando solo su `integra-addons` por el worktree, y confirmar con `comm` que no falte ningún módulo instalado. Los backups `*_nofs` dan 500 en imágenes (esperable). `./odoo pw` puede no dejar entrar; usar `odoo shell`. Skill `binaural-restore-client-backup`.

241. **La rama `staging` de un repo cliente puede apuntar `integra-addons` a una rama de integración `<sha9>_<rama>` que junta varias features** (ej. posv19: SITEF + checker kiosk). Para llevar un PR a staging: rama de integración nueva desde ese commit + merge del PR (si la integración tiene copias viejas de los mismos commits, tomar la versión del PR por módulo y verificar con `git write-tree --prefix`), y un PR en el repo cliente que solo mueva el submódulo. Nunca apuntar el submódulo directo al commit del PR. Skill `binaural-submodule-maintenance-merge` §Paso 8.

242. **Un reclamo de "precio incorrecto" en un reporte que usa lista de precios se diagnostica con datos, no cambiando el código**: leer el snapshot con que se generó (moneda, lista, "precio sin IVA", que puede venir de preferencias guardadas), extraer el valor real del PDF (`pdftotext`), y comparar con `_get_product_price_rule` para cada `min_quantity` y con una orden de venta simulada en memoria. Los reportes calculan con cantidad 1, así que los escalones por volumen nunca aparecen. Antes de tocar código, preguntar de dónde sale el valor que espera el usuario. Skill `binaural-product-catalog-19.0`.

243. **Un core y sus puentes solo son independientes si el core no nombra a ningún puente ni lee sus campos** (Odoo 19.0, TA-82676): hooks genéricos extendidos con `super()`, cada puente dueño de su campo, vista y lógica, `auto_install` en los puentes "pegamento", y la lógica de un cliente en un puente del repo del cliente. Probar con `./odoo test` en el core solo, cada puente solo y todos juntos, y E2E progresivo. Skill `odoo-bridge-module-independence-19.0`.

244. **Hooks encadenados de "ámbito" deben intersectar y distinguir `None` (sin ámbito) de `[]` (ámbito sin coincidencias)**; `wizard.read()` entrega los Many2one como `(id, nombre)`. Uniones con `set(a + b)` o `or None` pasan los tests felices y fallan con dos puentes. `odoo-code-review-19.0` FIX-092/FIX-093.

245. **Un `required=True` en un asistente bloquea sus botones auxiliares** ("Faltan algunos campos obligatorios" antes de llamar al método): validar el dato en la acción final, no en el campo. `odoo-code-review-19.0` FIX-091.

246. **`-u` no sobrescribe traducciones de vista ya guardadas en la base**: para que un cambio de `.po` llegue a clientes existentes, `post-migrate` que recargue solo ese módulo con `_load_module_terms(..., overwrite=True)`. Verificar con `arch_db` en `with_context(lang=...)`. Skill `odoo-translations-19.0` §14.

247. **OpenCode no es confiable para lógica de código aunque reciba el código exacto** (TA-82676: 3 rondas sin aplicar una intersección, validación marcada como hecha sin tests, alcance inventado). Para código, usar payload literal (`cp` + `diff -r`) o aplicarlo directamente; siempre verificación propia y code-review por ronda. Y el heredoc del prompt SIEMPRE entre comillas (`<<'EOF'`). Skill `sdd-opencode-delegate-agent`.

248. **Si el MCP de Playwright se desconecta, seguir con Playwright de Node** (`npx --no-install playwright --version`, `npm i playwright@<versión>` en scratch, script propio con descargas). Skill `playwright-mcp-usage` §Troubleshooting.

249. **Archivar OpenSpec**: `MODIFIED`/`REMOVED` sobre requisitos que no existen en el spec principal abortan el archivado; un requisito nuevo va en `ADDED`. En repos de cliente el OpenSpec es a nivel de repo y el archivado es mover la carpeta. Skill `sdd-openspec-bridge`.

### Reglas — Vendor Override & Currency (Ticket 15386)

250. **Currency conversion: SIEMPRE usar `res.currency._convert()`** — NUNCA multiplicar/dividir manualmente por `company_rate` o cualquier tasa. `_convert()` maneja short-circuit same-currency, redondeo, inverse rate (USD en sistema VEF), y caching. Signature: `source_currency._convert(from_amount, to_currency, company=None, date=None, round=True)`. Skill `odoo-currency-convert-mandatory`. Referencia: ticket 15386, fix commit `8b152b2`.
251. **Full-copy template override: eliminar sub-templates sin prefijo de módulo** — Si el vendor define `<t-name="Foo">` (sin module prefix), nuestra copia NO debe incluirlo. Odoo registra `t-name` globalmente → duplicado = `"Template already exists"` → bundle completo muere → página en blanco. Skill `odoo-vendor-override-patterns` Patrón 1. Referencia: ticket 15386, commit `6e7ef03`.
252. **Vendor barcode fallback path: verificar datos faltantes antes de setear** — Vendors de POS/kiosko tienen DOS paths (configured-fields vs barcode fallback). El fallback típicamente NO resuelve pricelist, stock, ni weight. Override DEBE verificar `if "key" not in res:` antes de compute cada campo. Skill `binaural-checker-kiosk` §Barcode Fallback Path. Referencia: ticket 15386, commits `8ae24b0` + `db9d6f0`.
253. **`_get_product_price()` kwargs-only en Odoo 19** — positional args después de `products` causan `TypeError`. Usar `quantity=1.0, uom=..., date=...`. Skill `odoo-19-breaking-changes-checklist`. Referencia: ticket 15386.
254. **Defensive field check para campos de vendor** — `if "field" in model._fields and model.field:` — necesario porque versiones viejas del vendor no tienen campos nuevos. Skill `odoo-vendor-override-patterns` Patrón 2. Referencia: ticket 15386, Rule #174.
255. **`allowed_company_ids` en tests para vendor code** — Vendor modules que usan `env.context.get('allowed_company_ids')` fallan con `TypeError` en tests. Pattern: `cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[company.id]))`. Skill `odoo-l10n-ve-test-patterns`. Referencia: ticket 15386.
256. **`foreign_currency_id` ORM write trigger** — Escribir `foreign_currency_id` via ORM dispara `l10n_ve_rate` → busca `account.move.line.foreign_currency_id` que puede no existir en test DB. Usar raw SQL: `UPDATE res_company SET foreign_currency_id = %s WHERE id = %s` + `invalidate_all()`. Skill `odoo-l10n-ve-test-patterns`. Referencia: ticket 15386.
257. **`db_name` vs `db_filter` en `instances.json`** — `db_name` define la BD exacta. `db_filter` es regex para selection. Usar `db_name` (override) para instancias de testing, no `db_filter`. El entrypoint regenera `odoo.conf` en cada restart — fixes via `sed` no persisten. Skill `binaural-docker-odoo`. Referencia: ticket 15386.

258. **`groups=` en la definición Python de un campo bloquea el campo ENTERO a nivel ORM (`check_field_access_rights`), no solo la UI** — a diferencia de `groups=` en la vista XML (solo oculta), el atributo en el campo Python hace que cualquier usuario sin ese grupo reciba `AccessError` al leer/escribir el campo, incluso si nunca lo toca en su flujo. Si ya existe un guard runtime (`has_group()` + `UserError`) protegiendo el uso real del campo, el `groups=` Python es redundante y debe quitarse, dejando la restricción solo en la vista + el guard. Gotcha de testing: un test con `TransactionCase` sin `.with_user()` corre como superusuario (`env.su=True`) y NO detecta este bug — usar `new_test_user()` + `.with_user()` + `invalidate_recordset()`. Referencia: ticket #15446 (countryclub, 2026-09-28), FIX-073 (17.0)/FIX-097 (19.0) en `odoo-code-review-17.0`/`-19.0`.

259. **`sdd-judge`: forense de mtime para descartar falsos positivos de SCOPE, y checklist de tests huecos en dispatches de coverage** — cuando `allowed_files.txt` no explica un archivo flaggeado (ediciones directas de `sdd-lead` fuera de cualquier dispatch), comparar el mtime del archivo contra la ventana de ejecución del job (timestamp en el propio `job_id` + `completed_at` de `result.handoff`) en vez de asumir violación. Además, para dispatches de "cerrar gap de coverage", releer el contenido real de los tests nuevos buscando antipatrones de padding (aserciones que pasarían igual sin el fix, fixtures que evitan la rama bajo prueba, mocks innecesarios de descriptores, fechas relativas al día de ejecución, tests tautológicos) — el número de coverage solo no es evidencia suficiente. Referencia: ciclo #15446 (countryclub, 2026-09-28). Skill `sdd-judge-agent`.

## Plugins (opencode.jsonc)

Ver `src/Agents.md` (sección "Plugins" y subsección "Plugin local: `sudolang-cache-engine`") para el
detalle actualizado de plugins instalados — este archivo raíz no duplica esa lista para no desincronizarse.

## Conductor Methodology

Agente global `conductor` (mode: primary) con metodología alternativa al SDD:
- `~/.config/opencode/agent/conductor.md` — Definición del agente
- `src/conductor/` — Product definition, tracks, workflow, tech stack

**Diferencia con SDD**: Conductor usa tracks/features management. SDD usa spec→plan→tasks.
Ambas metodologías coexisten. Elegir según el contexto del trabajo.

### 17.0 Skills Creados (18 nuevos + 3 versionados = 21 total)

Todos en `.opencode/17.0/skills/`. Skills versionados pre-existentes: `odoo-code-review-17.0`, `odoo-performance-17`, `owl-framework-v2-17.0`.

| # | Skill | Loop | Descripción |
|---|-------|------|-------------|
| 001 | `odoo-design-patterns-creational-17.0` | 001 | Singleton/Factory: Registry, Environment, MetaModel, _build_model |
| 002 | `odoo-design-patterns-structural-17.0` | 002 | Adapter/Decorator/Composite/Bridge/Facade/Proxy |
| 003 | `odoo-behavioral-patterns-17.0` | 003 | Observer/Command/Strategy/TemplateMethod/State/Chain/Iterator/Visitor/Mediator/Memento |
| 004 | `odoo-solid-srp-ocp-17.0` | 004 | SRP mixins, _inherits, controladores delgados, OCP _inherit, xpath |
| 005 | `odoo-solid-lsp-isp-dip-17.0` | 005 | LSP super(), ISP mixins pequeños, DIP env[] no imports |
| 006 | `odoo-layered-architecture-17.0` | 006 | 5 capas (HTTP→Service→ORM→Views→Security), interacciones, violaciones |
| 007 | `odoo-event-driven-17.0` | 007 | bus.bus, mail notifications, automated actions, webhooks, precommit/postcommit |
| 008 | `odoo-owasp-injection-xss-17.0` | 008 | SQL Injection, XSS, Command Injection, Path Traversal, SSTI, XXE |
| 009 | `odoo-owasp-auth-session-17.0` | 009 | Auth modes, Session, MFA/TOTP, OAuth2, LDAP, CSRF, API keys |
| 010 | `odoo-tdd-python-17.0` | 010 | Test framework, TransactionCase/HttpCase, assertions, mocking |
| 011 | `odoo-tdd-owl-javascript-17.0` | 011 | QUnit, makeTestEnv, MockServer, tours, patch, helpers |
| 012 | `odoo-orm-advanced-17.0` | 012 | Prefetching, search_fetch, Cache, flush, _inherits, StackMap |
| 013 | `odoo-batch-queue-17.0` | 013 | ir.cron, batch search, flush batching, ormcache, GC |
| 014 | `odoo-python-best-practices-17.0` | 014 | Recordset safety, float_compare, Command, _prepare_* purity |
| 015 | `odoo-owl-deep-dive-17.0` | 015 | OWL 2 lifecycle, reactivity, templates, services, env |
| 016 | `odoo-anti-patterns-17.0` | 016 | 25 anti-patrones CRITICAL/HIGH/MEDIUM con fixes |
| 017 | `odoo-security-hardening-17.0` | 017 | Checklist práctica: ACL, record rules, XSS, SQLi, sudo audit |
| 018 | `odoo-code-examples-17.0` | 018 | 43 snippets cookbook: models, security, views, tests, OWL |
| 019 | `odoo-integration-patterns-17.0` | 019 | JSON-RPC, XML-RPC, REST-like, webhooks, payment APIs |
| 020 | `odoo-meta-learning-17.0` | 020 | Lecciones del proceso, fabricated code problem, futuro |

### Nuevas Reglas 17.0 (34-43, skills 004-009)
- **34.** 3-phase action methods: _pre_action → _do_action → _post_action
- **35.** Controladores delgados: solo routing+rendering, negocio delegado a modelos
- **36.** position="replace" solo como último recurso (preferir after/before/inside)
- **37.** LSP: super() obligatorio en toda cadena MRO
- **38.** ISP: mixins pequeños y enfocados (portal.mixin 136ln, no mail.thread 4690ln)
- **39.** DIP: usar self.env['model'], nunca import de clases concretas
- **40.** DIP: extraer constantes de dominio a módulos compartidos
- **41.** Layer skipping: no bypass del ORM
- **42.** Bridge pattern: ir.http como única puerta
- **43.** sudo() scoped, no wholesale

### V2: 20 Nuevos Skills 17.0 (Ciclo de Automejoramiento V2)

| Skill | Loop | Descripción |
|-------|------|-------------|
| `odoo-controllers-17.0` | 001 | Sistema de Controllers: Controller base, @route, ir.http bridge, Http/Json Dispatchers, WebSocket, anti-patrones |
| `odoo-wsgi-middleware-17.0` | 002 | WSGI Application, ProxyFix, servidores Threaded/gevent/PreFork, señalización, session store |
| `odoo-mixins-17.0` | 003 | Mixins AbstractModel: mail.thread (4690ln), portal (136ln), rating, utm, image, composición |
| `odoo-translations-17.0` | 004 | Sistema i18n: JSONB fields, _() Python, _t() JS, PO files, update_field_translations |
| `odoo-xml-views-basic-17.0` | 005 | Vistas form/tree/kanban/search/graph/pivot/calendar, widgets, default views |
| `odoo-xml-views-advanced-17.0` | 006 | Herencia inherit_id, CTE recursivo, xpath, 6 positions, _combine, RNG validation |
| `odoo-sequences-17.0` | 007 | ir.sequence (standard/no_gap), sequence.mixin, date_range, secure sequences, PG signaling |
| `odoo-qweb-server-17.0` | 008 | QWeb server-side: compile pipeline, _render(), 11 directivas, herencia, reports, layouts |
| `odoo-frontend-assets-17.0` | 009 | Asset bundling: ir.asset, 8 bundle types, SCSS pipeline, debug mode, minification |
| `odoo-view-attributes-17.0` | 010 | 28 atributos de vista: field, button, tree, form, search, calendar, graph/pivot |
| `odoo-scss-theming-17.0` | 011 | SCSS theming: $o-* variables, Bootstrap 5 overrides, website themes |
| `odoo-mobile-17.0` | 012 | Mobile framework: PWA, responsive UI, barcode, offline, push notifications |
| `odoo-odoo-editor-17.0` | 013 | Odoo Editor WYSIWYG: arquitectura, plugins, Powerbox, sanitización, integración OWL |
| `odoo-icons-ui-17.0` | 014 | Iconos FontAwesome 5+ y UI: Dropdown, Tooltip, Dialog, Popover, OWL components |
| `odoo-multicompany-17.0` | 015 | Multi-company: allowed_company_ids, with_company, company-dependent fields, record rules |
| `odoo-enterprise-views-17.0` | 016 | Enterprise views: Cohort, Grid, Map, Activity, Gantt, Studio |
| `odoo-standard-models-17.0` | 017 | Modelos estándar: res_partner, res_users, ir.model, ir.actions, ir.config_parameter |
| `odoo-upgrade-scripts-17.0` | 018 | Upgrade scripts: pre/post/end, version numbering, migration utils |
| `odoo-data-api-17.0` | 019 | Export/Import: ir.exports, base_import, ir.model.data, XML data noupdate |
| `odoo-architecture-complete-17.0` | 020 | Arquitectura completa: síntesis de 47 skills, 5-capas, master index |

### V3: 2 Nuevos Skills 17.0 (Guardrails + SettingsBlock Fix)

| Skill | Descripción |
|-------|-------------|
| `odoo-core-guardrails-17.0` | **NUEVO** — Política de guardarraíles: prohibición absoluta de modificar archivos en odoo-17.0/ y enterprise-17.0/. Alternativas legales (herencia, patch, xpath). Cómo detectar cambios ilegales en CI/pre-commit. |
| `odoo-settings-block-slots-error-17.0` | **NUEVO** — Diagnóstico y resolución del error OWL "Invalid props for component 'SettingsBlock': 'slots' is missing" en res.config.settings de Odoo 17.0. Root cause, fix a nivel de vista XML, anti-patrones. Incluye Causa 3: tabs duplicados con mismo `string` que muestran el tab incorrecto. |

### V4: 2 Nuevos Skills 17.0 (Automejoramiento Testing — Loops 001-002)

| Skill | Descripción |
|-------|-------------|
| `odoo-unit-testing-deep-17.0` | **NUEVO** — Deep unit testing: 10 secciones cubriendo error boundary testing (ValidationError/UserError/AccessError/IntegrityError), float precision edge cases (banking rounding, 2.675→2.68, ±0.005 threshold), recordset boundaries (empty/multi/deleted/negative IDs), security matrix testing (@users + with_user + with_company), time-dependent logic (freeze_time, UTC boundaries), parameterized testing (subTest matrices), performance guards (assertQueryCount + @warmup), mocking patterns (self.patch, mute_logger, call counting), cache management, input validation boundaries (Unicode, emoji, CRLF, zero/negative). 41+ source annotations verificadas contra código real. 8 anti-patrones (DEEP-001 a DEEP-008). |
| `odoo-regression-testing-17.0` | **NUEVO** — Regression testing: 12 secciones cubriendo sistema @tagged (at_install/post_install, personalizados, localización, external, standalone), aislamiento TransactionCase/SingleTransactionCase, reproducibilidad (DISABLED_MAIL_CONTEXT, flush_tracking, bloqueo HTTP externo, CryptContext/Random patch), query count regression (assertQueryCount multi-usuario, @warmup, SQL pattern assertQueries), fixtures (new_test_user, RecordCapturer, jerarquía Common classes), CI (TagsSelector, ODOO_TEST_MAX_FAILED_TESTS, retry automático, @no_retry, is_query_count auto-detección). 46+ source annotations, 12 anti-patrones (REG-001 a REG-008). |

### V5: 1 Nuevo Skill 17.0 (Automejoramiento Testing — Loop-003)

| Skill | Descripción |
|-------|-------------|
| `odoo-performance-benchmark-17.0` | **NUEVO** — Performance testing & benchmarking: 11 secciones cubriendo assertQueryCount avanzado (single-user, per-user multi-user), SQL pattern verification (assertQueries), @warmup cold/hot cache strategy, @users multi-user parameterization, wall-time + query count dual measurement (time.perf_counter), SQL profiling (self.profile, Profiler, Nested, PeriodicCollector), HTTP performance (UtilPerf, _get_url_hot_query, _check_url_hot_query, _enable_table_tracking table-level budgets), fixture setup for benchmarks (batch creates, EMPLOYEES_COUNT raw SQL seeding, flush_tracking, registry ready patching), tag-based organization (module_perf tags), CI-level stats collection (Stat, collectStats, log_stats, OdooSuite, ODOO_TEST_MAX_FAILED_TESTS), deterministic patterns (freeze_time, mute_logger, self.patch call counting, mock_mail_gateway, RecordCapturer). 35+ source annotations, 12 anti-patrones (PERF-001 a PERF-012). |

### V6: 1 Nuevo Skill 17.0 (Automejoramiento Testing — Loop-004)

| Skill | Descripción |
|-------|-------------|
| `odoo-test-doubles-mocking-17.0` | **NUEVO** — Test doubles, mocking & patching: 12 secciones cubriendo Odoo-native helpers (self.patch, startPatcher, classPatch), unittest.mock core (autospec, wraps spy pattern, side_effect, PropertyMock), Mail mocking subsystem (mock_mail_gateway con 5 patches, mock_mail_app, mock_bus, assertPostNotifications, MockSmtplibCase), SMS mocking (mockSMSGateway con 3 patches IAP v0/v2/v3), RecordCapturer, BlockedRequest external HTTP blocking, context-based disabling (DISABLED_MAIL_CONTEXT), decorators (@users, @warmup, @mute_logger), framework-level patching (_crypt_context, enter_test_mode), time mocking (freeze_time, cr.now, mock_datetime_and_now), enterprise patterns (manual call counting stock_barcode, cron patching sale_subscription). 49+ source annotations, 12 anti-patrones (MOCK-001 a MOCK-012). |

### V7: 4 Nuevos Skills 17.0 (Automejoramiento Testing — Loops 005-008)

| Skill | Descripción |
|-------|-------------|
| `odoo-security-testing-17.0` | **NUEVO** — Security testing: 12 secciones cubriendo taxonomía de seguridad Odoo 17.0 (ACL+record rules+field-level+company), test user creation (new_test_user, @users, with_user, with_env), ACL testing (assertRaises AccessError/UserError, assertRaisesRegex, CRUD Complete Matrix con 96+ assertions), record rule testing (check_access_rule, ir.rule programmatic, _filter_access_rules_python, domain validation), multi-company security (with_company, allowed_company_ids, branch testing), portal/public access (5-level: public/portal/user/manager/admin), controller security (HttpCase.url_open, access_token, CSRF), hierarchy/inheritance (_inherits ACL propagation, follower-based, subtype-based), XSS sanitization (html_sanitize, SANITIZE_TAGS, group_sanitize_override), IntegrityError (triple nesting: mute_logger + assertRaises + savepoint), mass matrix regression (@warmup + @users + assertQueryCount), mocking (patch(check_access_rights), mock_void_external_calls). 38+ source annotations, 12 anti-patrones (S1-S12). |
| `odoo-testing-flows-workflows-17.0` | **NUEVO** — Flow/workflow testing: 10 secciones cubriendo linear action chaining (stock.move lifecycle, sale.order lifecycle, create→confirm→done), state machine transitions (leave lifecycle: confirm→approve→validate→refuse→draft, re-entry idempotency, UserError on invalid transitions), wizard/TransientModel testing (button_validate return dict → Form wizard → process, multi-step backorder wizards, account.payment.register), cross-module orchestration (SO→PO→Stock MTO, sale_purchase_stock_flow, cancel propagation), automated actions (base_automation triggers: on_create_or_write, on_stage_set, on_state_set, filter_domain, trigger_field_ids, recursion protection), payment flow parameterization (_test_flow unified method, direct/redirect/token flows, subTest matrices), time-sensitive flows (freeze_time for allocations, payslips, reconciliations), multi-entity flows (backorder chains, Command.link mid-flow, multi-backorder), security matrix in flows (per-step with_user, mute_logger, @users isolation, timing markers). 37+ source annotations, 12 anti-patrones (FLOW-001 a FLOW-012). |
| `odoo-testing-computed-fields-17.0` | **NUEVO** — Computed field testing: 10 secciones cubriendo fundamentos (store=True vs store=False, lazy recomputation, @api.depends syntax), testing patterns (assertEqual after create, direct _compute_*() call, invalidate_recordset(fnames=[]) pattern, flush_all() for pending recomputations, action flow verification), advanced patterns (chain dependencies @api.depends on computed fields, recursive=True, multi-field compute, compute_sudo=True, precompute=True, inverse method), monetary/float (assertRecordValues, float_compare, multi-currency), recompute triggers (M2M store trigger, cross-model modified(), negative testing), tracking (tracking=True on stored vs non-stored computed), automation (recompute-triggered server actions, trigger_field_ids, filter_domain, compute_on_create), edge cases (empty recordset, deleted dependency, multi-company, zero/negative, inverse unlink), Form() + computed (triggers, protected fields). 51+ source annotations, 8 anti-patrones (COMP-001 a COMP-008). |
| `odoo-testing-constraints-onchanges-17.0` | **NUEVO** — Constraint & onchange testing: 12 secciones cubriendo @api.constrains fundamentals (ValidationError+savepoint, create vs write, assertRaisesRegex message matching, UserError from action chains), constraint types (float range boundary, date/time overlap 5 scenarios, cross-model archiving, multi-company, _sql_constraints+IntegrityError+mute_logger, aggregation >100%), _check_* method patterns (direct via create, via action_* chain, context-controlled skipping), edge cases (boundary dates, multi-record aggregation, _inherits propagation, inverse unlink), onchange fundamentals (model.onchange() direct API con fields_spec, invalidate_all(), _get_fields_spec()), Form()-based onchange (basic, .new() for one2many, .edit() + with_context defaults), side effects (warning dict pattern, block field reset, domain updates, Command propagation), edge cases (dirty-field detection, onchange-once guarantee, default_get interaction), integration (Form().save() → @api.constrains full chain). 34+ source annotations, 12 anti-patrones (AP-001 a AP-012). |

### V8: 2 Nuevos Skills 17.0 (Automejoramiento Testing — Loops 009-010)

| Skill | Descripción |
|-------|-------------|
| `odoo-testing-security-advanced-17.0` | **NUEVO** — Advanced security testing: 10 secciones cubriendo advanced record rule testing (domain composition global AND vs group OR, dual-path validator _filter_access_rules_python vs _filter_access_rules, check_access_rule/rights dual check, _inherits multi-model rule propagation), field-level security (check_field_access_rights con operations, fields_get/fields_view_get security context, user_has_groups con negation !, _read_group_check_field_access_rights override, NO_ACCESS sentinel), security view/UI (invisible+groups, modifiers, tours con visibilidad por grupo), multi-company (with_company cross-access, domain patterns: in, parent_of, +[False], related field, _eval_context), security inheritance (_compute_domain recursion, parent_field any wrapping), automated actions (context preservation, no privilege escalation), password/API key (_crypt_context.verify, key generation/revocation, KEY_CRYPT_CONTEXT), report security (_render_qweb_pdf multi-company isolation), performance (per-user assertQueryCount, raise_exception=False baseline), advanced matrix (patch.object(check_access_rights) conditional side_effect, 7-category mass matrix, cross-model access, implied_ids hierarchy, programmatic ir.rule). 55+ source annotations, 12 anti-patrones (S1-S12). |
| `odoo-testing-multi-company-isolation-17.0` | **NUEVO** — Multi-company isolation testing: 10 secciones cubriendo fixture setup (test companies, single/multi-company users, warehouses per company, new_test_user con company_ids), context managers (allow_companies, switch_company, sudo con nesting patterns, restore en finally), @users decorator (_activate_multi_company, with_company dentro de @users, cache invalidation entre users), cross-company isolation (assertRaises UserError/AccessError/QWebException, Deny→Allow dual path, sudo baseline), flow testing (SO→Invoice company propagation, Task→SO→Invoice FSM, inter-company stock transfers push/pull), company-dependent fields (property_* per company, is_kits computed per company, standard_price, no-leakage verification), HTTP tests (cids URL parameter, portal cross-company, redirect preservation, authentication switching), branch company (parent_of operator, branch user setup, shared accounts/journals, branch currency), inter-company operations (push/pull rules, lot isolation by company, transit location), performance (allowed_company_ids impact, record rule N+1 avoidance, assertQueryCount multi-company). 65+ source annotations, 10 anti-patrones (S1-S10). |

### V9: 3 Nuevos Skills 17.0 (Automejoramiento Testing — Loops 011-013)

| Skill | Descripción |
|-------|-------------|
| `odoo-testing-controllers-17.0` | **NUEVO** — Controller testing: 12 secciones cubriendo HttpCase infrastructure (url_open, authenticate, make_jsonrpc_request, start_tour, browser_js, assertURLEqual), authentication testing (public/portal/internal, session switching), JSON-RPC testing (make_jsonrpc_request, JsonRpcException assertion, _assertNotFound helper), access token testing (portal_ensure_token, valid/invalid/missing, share URL tokens), redirect testing (allow_redirects=False, assertURLEqual, 301/302/303/308), form POST & file upload (CSRF token via http.Request.csrf_token, files= parameter, multipart), response assertion (.json(), .content, .headers, lxml.html parsing), error handling (mute_logger, JsonRpcException, 403/404), controller patching (patch.object, MockRequest, _get_error_html), multi-user session switching (cookie manipulation via opener.cookies), CORS & multi-website (guest tokens, company context routing), multi-step payment flows (_test_flow, share URL simulation, _json_url_open). 77+ source annotations, 12 anti-patrones. |
| `odoo-tdd-owl-javascript-17.0` | **EXPANDIDO** — De 479 a 2,630 líneas (+2,151). 21 nuevas secciones: makeView() — factory de componentes de vista, lifecycle verification con assert.step()/assert.verifySteps(), makeDeferred() async flow control, mount() internals, triggerEvent type system completo (12+ constructores de evento), browser.setTimeout immediate patching, component composition (padres/hijos/slots), onError() error boundaries OWL, useSubEnv() env propagation, patchDate()/patchTimeZone() deterministic time, registry isolation, hushConsole, useEffect() reactive widgets, error service testing, PseudoWebClient, drag/drop, createWebClient()+doAction(), makeWithSearch(), useLogLifeCycle(). 60 source annotations, 16 anti-patrones. |
| `odoo-testing-integration-api-17.0` | **NUEVO** — Integration & API testing: 18 secciones cubriendo fundamentos de mocking (taxonomía 6 niveles: protocolo→HTTP→framework→librería→modelo→aplicación), PATCH-GLOBAL (mock requests.post/requests.get con routing por URL), SESSION-MOCK (MockedSession con verificación XML via assertXmlTreeEqual), SOAP-ZEEP (patch zeep.transports.requests.Session), BUSINESS-METHOD (patch.object a nivel de método de negocio), FRAMEWORK-REQ-HANDLER (_request_handler classmethod con routing por env.context), IAP-MOCK (mockSMSGateway multi-versión API v1/v2/v3), MAIL-GATEWAY (mock completo 5 patches), SOCIAL-AGGREGATE (ExitStack multi-plataforma), HTTP-CONTROLLER (PaymentHttpCommon + HttpCase), WEBSOCKET-INTEG (websocket-client real ws://), WEBHOOK-NOTIF (webhooks con HMAC signature), EDI-FLOW (assertRecordValues + estados to_send→sent→to_cancel→cancelled), OAUTH-LDAP (patch.object ldap + HttpCase login flow), EXCEPTION-SIM (timeout/4xx/SOAP Fault/InsufficientCredit), ENV-CONTEXT-ROUTING (_set_context + env.context.get), anti-patterns (INT-001 a INT-012). 21+ file references, 12 anti-patrones. |

### V10: 7 Nuevos Skills 17.0 (Automejoramiento Testing — Loops 014-020 — COMPLETED ✅)

| Skill | Líneas | Descripción |
|-------|--------|-------------|
| `odoo-testing-e2e-tours-17.0` | 836 | E2E tour testing: 17 secciones cubriendo start_tour API, browser_js low-level, tour step interface (trigger, run, isCheck, timeout), tour registration patterns (registry, wTourUtils, POS), run command patterns (click, text, drag_and_drop, keydown), stepUtils helpers, website tour utils (dragNDrop, clickOnSnippet), POS screen helpers, e-commerce shop flow, enterprise mock+tour pattern, multi-tour sequencing, JS-level vs Python-level assertions, ClickBot crawler, tour data setup. 17+ file references, 10 anti-patrones (E2E-001 a E2E-010). |
| `odoo-testing-hybrid-js-python-17.0` | 1,546 | Hybrid JS+Python testing: 14 secciones cubriendo tour + Python post-assertions, mock+tour+assertRecordValues triple pattern, JS-level assertions via TourError, Python data→JS verification, JS state→Python assertion, hybrid QUnit+Python, payment flow hybrid, enterprise mock+tour+assertions, POS hybrid, website builder tours, ClickBot + Python. 37 annotations, 9 anti-patrones. |
| `odoo-testing-cron-batch-17.0` | 1,572 | Cron/batch testing: 17 secciones cubriendo method_direct_trigger, cron state management, _process_job matrix, batch processing patterns, enter_test_mode, cron with mock, multi-company, error handling, time-dependent, queue jobs, enterprise patterns. 23 annotations, 10 anti-patrones. |
| `odoo-testing-flaky-prevention-17.0` | 1,258 | Flaky prevention: 13 secciones cubriendo taxonomía 7 categorías, time-dependent flakiness, database state isolation, async race conditions, test ordering independence, randomness control, HTTP isolation, cache pollution, CI stabilization, non-determinism detection, enterprise patterns. 19 annotations, 9 anti-patrones. |
| `odoo-testing-coverage-metrics-17.0` | 1,280 | Coverage/metrics: 14 secciones cubriendo coverage fundamentals, running coverage, .coveragerc, minimum thresholds, coverage analysis, uncovered path detection, regression prevention, gap analysis, query count metrics, test suite metrics, metrics dashboard, CI integration. 12 annotations, 7 anti-patrones. |
| `odoo-testing-data-migrations-17.0` | 1,393 | Data/migration testing: 14 secciones cubriendo migration fundamentals, script structure, pre/post/end hooks, data integrity, version numbering, rollback verification, data transformation, model/field changes, multi-module, enterprise patterns, noupdate data. 10 annotations, 7 anti-patrones. |
| `odoo-testing-best-practices-17.0` | 1,179 | **SÍNTESIS FINAL** — Best practices sintetizando los 20 skills: 14 secciones cubriendo organización, jerarquía de clases, fixtures, assertions, mocking, coverage, seguridad, performance, flaky prevention checklist (10-punto), code review checklist (15-punto), anti-pattern catalog (top 15), test decision matrix, reference index de los 20 skills. 15 anti-patrones cross-referenciados. |

### Resumen Final del Plan de Automejoramiento (20 Loops)

| Fase | Loops | Skills | Estado |
|------|-------|--------|--------|
| **Fase I** (Unit/Regression/Performance/Doubles/Security) | 001-005 | `odoo-unit-testing-deep`, `odoo-regression-testing`, `odoo-performance-benchmark`, `odoo-test-doubles-mocking`, `odoo-security-testing` | ✅ COMPLETED |
| **Fase II** (Flows/Computed/Constraints/Security-Adv/Multi-Company) | 006-010 | `odoo-testing-flows-workflows`, `odoo-testing-computed-fields`, `odoo-testing-constraints-onchanges`, `odoo-testing-security-advanced`, `odoo-testing-multi-company-isolation` | ✅ COMPLETED |
| **Fase III** (Controllers/OWL/Integration/E2E/Hybrid) | 011-015 | `odoo-testing-controllers`, `odoo-tdd-owl-javascript` (expanded), `odoo-testing-integration-api`, `odoo-testing-e2e-tours`, `odoo-testing-hybrid-js-python` | ✅ COMPLETED |
| **Fase IV** (Cron/Flaky/Coverage/Migrations/Best-Practices) | 016-020 | `odoo-testing-cron-batch`, `odoo-testing-flaky-prevention`, `odoo-testing-coverage-metrics`, `odoo-testing-data-migrations`, `odoo-testing-best-practices` | ✅ COMPLETED |

**Total 20 skills**: 31,334 líneas, 640+ source annotations, 200+ anti-patrones

### V11: 2 Nuevos Skills 17.0 (Patrones de Visibilidad e Inverse)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-view-invisible-patterns` | **NUEVO** — Odoo 17: `attrs`/`states` deprecated, `invisible` como expresión Python con `context`/`user`/`time`/`record`, `position="parent"` no soportado (usar `xpath`), visibilidad por contexto, campos en modificadores deben estar en la vista. |
| `odoo-17-computed-field-inverse` | **NUEVO** — Patrón `inverse` en stored computed fields para prevenir recomputación durante flush. Doble capa `create()` override + `inverse`. Anti-patrones: solo `create()`, solo `inverse`, condicional en vals. |

### V12: 1 Nuevo Skill 17.0 (Automejoramiento Context/DRY — Loop-001)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-context-fundamentals` | **NUEVO** — Sistema de Context de Odoo 17.0: arquitectura HTTP→Controller→ORM→SQL, frozendict, with_context/with_env/split_context, context_get(), @api.depends_context(), 50+ context keys oficiales en 6 categorías, makeContext() client-side, context en record rules, 10 anti-patrones, diferencias 17→19. 15 archivos fuente referenciados con líneas exactas. |

### V13: 1 Nuevo Skill 17.0 (Automejoramiento Context/DRY — Loop-002)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-context-views` | **NUEVO** — Context en vistas XML de Odoo 17.0: `ir.actions.act_window.context` (Char con expresión Python, safe_eval server-side, makeContext client-side), `default_<campo>` para valores por defecto, `search_default_<filter>` para pre-activar filtros (extracción en SearchModel + defaultRank), `group_by` para agrupación dinámica, `*_view_ref` para vistas hijas en fields relacionales, `context.get()` en atributos (invisible/column_invisible/readonly), herencia de context (NO merge de dict en XML, merge client-side via makeContext), `active_id`/`active_ids`/`active_model` (deprecados en Odoo 17), `active_test` para registros archivados, keys personalizadas (flags de UI), flujo completo BD→Server→Client→Sub-vistas, 7 anti-patrones. 19 archivos fuente verificados. |

### V14: 1 Nuevo Skill 17.0 (Automejoramiento Context/DRY — Loop-003)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-context-python` | **NUEVO** — Context en Python de Odoo 17.0: `@api.depends_context` (definición, registro en field_depends_context, cache_key con sub-llaves, invalidación multi-context, dirty fields, flush con context_none), `default_get()` (prioridad de defaults: context→ir.default→field.default→parent), `onchange()` y flujo de context, `_search`/`_name_search` con `active_test`, `copy_data()`/`copy_translations()` (mecanismo `__copy_data_seen`), `fields_view_get`/`get_view` y dependencias de context, `clean_context()` (definición y usos), server actions eval context, context managers (protecting, clear, with_context sticky), 6 anti-patrones, diff 17→19. 45+ referencias a código fuente. |

### V15: 1 Nuevo Skill 17.0 (Automejoramiento Context/DRY — Loop-004)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-context-js` | **NUEVO** — Context client-side (JS/OWL) de Odoo 17.0: `makeContext()` (algoritmo de merge acumulativo, evaluación secuencial, orden de precedencia), `evaluateExpr()` (evaluador Python-in-JS via py.js), `evalPartialContext()` (evaluación key-by-key para fieldspec), `user_service.context` (construcción desde session.user_context, API updateContext/removeFromContext), `orm_service` (inyección de user context en kwargs de todo RPC), `action_service` (multi-capa: doAction, doActionButton, _loadAction, _preprocessAction), `CTX_KEY_REGEX` (filtrado de default_*/search_default_*/group_by/active_id/*_view_ref al navegar entre acciones), `search_default_*` (extracción en SearchModel + eliminación del globalContext + activación por defaultRank), `getFieldContext()` (construcción de context para sub-vistas con filtrado de default_*/search_default_*/*_view_ref), `getBasicEvalContext()` (variables uid/context/allowed_company_ids/current_company_id + active_id/active_ids/active_model deprecados), `Record.evalContext` (serialización de datos por tipo, _computeDataContext, _setEvalContext), `*_view_ref` (extracción via regex en FormController + merge en loadViews), context en botones (view_button clickParams + view_button_hook evaluateExpr con evalContext), deshabilitación de acciones view (create/edit/delete via context flag), ActionMenus activeIdsContext, 6 anti-patrones CRITICAL/HIGH/MEDIUM, diff 17→19. 17 archivos fuente verificados, 15+ fragmentos de código. |

### V16: 1 Nuevo Skill 17.0 (Automejoramiento Context/DRY — Loop-005)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-context-advanced` | **NUEVO** — Context avanzado de Odoo 17.0: seguridad (`sudo()`, `with_user()`, `with_env()`, stackeabilidad, `clean_context()` en sudo), multi-compañía (`allowed_company_ids`, `env.company`, `with_company()`, `force_company` deprecado, sticky behavior), idiomas (`lang`, `prefetch_langs`, `edit_translations`, `check_translations`, `context_get()`), timezone (`tz`, `context_today()`, `_read_group` tz conversion), importación (`import_file`, `import_compat`, `import_skip_records`), instalación (`install_mode`, `MODULE_UNINSTALL_FLAG`), copia (`__copy_data_seen`, `__copy_translations_seen`), tests (`DISABLED_MAIL_CONTEXT`, `tracking_disable`, `mail_notrack`, `no_reset_password`), reportes (`bin_size`, `landscape`, `force_report_rendering`, `webp_as_jpg`), website/portal/email context, context managers (`Environment.protecting()`, `Environment.clear()`, `Transaction.clear()`), clean context avanzado, 8 anti-patrones con severidad, diff 17→19. 20+ archivos fuente verificados con líneas exactas. |

### V17: 5 Nuevos Skills 17.0 (Automejoramiento Context/DRY — Loops 006-010)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-utilities-core` | **NUEVO** — Utilidades core de `odoo.tools` de Odoo 17.0: `tools.misc` (clean_context, frozendict, StackMap, formatLang), `tools.float_utils` (float_round 5 métodos, float_compare, float_is_zero, float_repr), `tools.sql` (SQL class parameterizado, make_identifier, create_index, increment_fields_skiplock), `tools.safe_eval` (opcodes, builtins, wrapped modules), `tools.func`/`tools.cache` (lazy_property, ormcache, ormcache_context), `tools.date_utils` (start_of/end_of, get_month/quarter, add/subtract, date_range), `tools.config` (configmanager, crypt_context), `tools.image` (ImageProcess, image_data_uri), `tools.barcode`/`tools.json` (check_barcode_encoding, scriptsafe), `tools.mail` (html_sanitize, SANITIZE_TAGS, email_split), `tools.view_validation` (valid_view, IGNORED_IN_EXPRESSION), `tools.profiler` (Profiler, ExecutionContext). 15 secciones, 8 anti-patrones, 14+ referencias verificadas contra source real. |
| `odoo-17-utilities-orm` | **NUEVO** — Utilidades del ORM de Odoo 17.0: Recordset utils (ensure_one, exists, filtered, filtered_domain, mapped, sorted), Search utils (search, search_read, search_count, search_fetch, name_search, name_create, _name_search, browse, ref), Read Group (read_group, _read_group_groupby, _read_group_postprocess_groupby, _read_group_expand_full, _read_group_fill_results), CRUD (create con @api.model_create_multi, write pipeline, unlink con @api.ondelete, read, copy_data, copy, load/export_data), Field Metadata (fields_get, _fields, get_metadata), View/Access (get_view reemplaza fields_view_get, get_formview_action, _get_access_action, default_get prioridad 4-nivel, onchange stub+web), Security (check_access_rights 4 ops, check_access_rule, check_field_access_rights, has_group con ormcache), Cache/Compute (compute_value, recompute, flush_model/recordset, invalidate_recordset, add_to_compute, modified), 10 anti-patrones (4 HIGH/4 MED/2 LOW). 41+ referencias verificadas contra source real. |
| `odoo-17-utilities-views` | **NUEVO** — Utilidades de vistas y templates de Odoo 17.0: Pipeline rendering ir.ui.view (render, _get_combined_arch, _combine, _get_view_cache, postprocess_and_fields con Visitor dispatch), Motor QWeb ir.qweb (25 directivas de compilación, _compile_expr, _compile_format, _prepare_environment), 21 Field Converters (MonetaryConverter, ImageConverter, BarcodeConverter, etc. con Template Method pattern), View Inheritance (apply_inheritance_specs, 6 positions, CTE recursiva), View Validation (valid_view, @validate, 8 RNG schemas, 16 _validate_tag_*), ir.actions.* system (_for_xml_id, _get_runner, 6 run_action_*), ir.ui.menu (load_menus con @ormcache_context), ir.filters (get_filters, create_or_replace), Assets (ir_asset.py, AssetsBundle, t-call-assets, lazy loading), Widget y SCSS utilities (viewWidgetRegistry, 30+ $o-* variables). 25 anti-patrones con severidad, 10 patrones GoF. 14+ referencias a archivos fuente. |
| `odoo-17-utilities-javascript` | **NUEVO** — Utilidades JavaScript de Odoo 17.0: Core utils (arrays 11 fn, strings 8 fn, objects 5 fn, numbers 8 fn), Concurrency (Mutex, KeepLast, Race, Deferred), Timing (debounce con animationFrame, throttleForAnimation, batched), RPC/ORM (jsonrpc, ORM.call/create/read/search/write, x2ManyCommands), Registry (Registry class + global, category/sub-registries), Patch (patch/unpatch con _super()), Browser wrapper (browser setTimeout/fetch/localStorage wrappers + feature detection), Localization (_t/_lt, formatDate/formatDateTime/formatDuration, formatCurrency, unaccent), Assets (loadJS/loadCSS/loadBundle, LazyComponent), Hooks OWL (useService, useBus, useAutofocus, useChildRef), Test helpers (makeTestEnv, click, mockRPC, MockServer, makeDeferred, patchDate). 14 secciones, 8 anti-patrones HIGH/MEDIUM/LOW. 19+ referencias verificadas. |
| `odoo-17-utilities-testing` | **NUEVO** — Utilidades de testing de Odoo 17.0: Clases base (TransactionCase, SingleTransactionCase, HttpCase, BaseCase), Decoradores (@tagged, @users, @warmup, @no_retry), Assertions (assertRecordValues, assertQueries, assertQueryCount con multi-user, assertRaises savepoint), Mock system (self.patch, startPatcher, RecordCapturer, BlockedRequest, with_user), Mail/SMS mocks (mock_mail_gateway 5 patches, mockSMSGateway, mock_smtplib_connection), Mail/SMS assertions (assertSentEmail, assertMailMail, assertSMS, assertMailNotifications), Form() wizard (__init__, save(), O2MProxy, M2MProxy), Fixtures (new_test_user, DISABLED_MAIL_CONTEXT, BaseCommon), Testing tools (Savepoint, TestCursor, profile, try_report, TagsSelector, OdooSuite), JS testing (patchDate, makeTestEnv, MockServer), 15 anti-patrones, diffs 17→19. 30+ referencias verificadas. |

### V18: 4 Nuevos Skills 17.0 (Automejoramiento Context/DRY — Loops 011-014)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-tricks-orm` | **NUEVO** — Trucos ORM de Odoo 17.0 (1,032 ln): Search Domain Mastery (operadores avanzados, expression.AND/OR, TRUE_LEAF/FALSE_LEAF), Recordset Patterns (filtered_domain, concat, mapped profundo, grouped), Cache Tricks (invalidate_recordset, ormcache/ormcache_context, env.cache), SQL Tricks (SQL(), increment_fields_skiplock, FOR UPDATE SKIP LOCKED, CTE), Write/Create Optimizations (@api.model_create_multi, batch patterns), Field Tricks (compute_sudo, precompute, depends_context, auto_join, fields.Json), Environment Tricks (active_test=False, sudo(False), env.ref), Onchange Patterns (BREAKING: domain return removed), Advanced Query (_where_calc override, _as_query, _order_field_to_sql), Trigger & Recompute (modified, _field_triggers, protecting), Command API (8 commands), Security Decorators (@api.ondelete, @api.returns), Performance Patterns (search_count, browse vs search). 14 secciones. 40+ archivos fuente. |
| `odoo-17-tricks-views` | **NUEVO** — Trucos de vistas de Odoo 17.0 (1,299 ln, 60+ patrones): Dynamic Views (Visitor dispatch, grupos condicionales, attrs deprecado), XPath Avanzado (locate_node first-match, parent/ancestor axis, 6 posiciones, add/remove), Field Widgets (14 widgets con options), Invisible Patterns (context.get(), negación, modifiers JSON), Tree Views (editable, multi_edit, 7 decoration-*, column_invisible), Form Views (header buttons, web_ribbon, collapsible groups), Kanban (ProgressBar, QWeb templates, ribbons), Search Views (default_period, SearchPanel enable_counters, Group By granular), QWeb (t-attf-*, t-call slots, t-inherit), Mobile/Responsive, Context en Vistas (avanzado), 16 Anti-patrones (5 CRITICAL). 30+ archivos fuente. |
| `odoo-17-tricks-performance` | **NUEVO** — Trucos de performance de Odoo 17.0: N+1 Prevention (search_fetch, prefetch_fields=False, mapped optimización), Batch Processing (@api.model_create_multi, search_count early exit), Index Strategy (index='trigram', 'btree_not_null', auto_join, create_unique_index), Cache Optimization (ormcache vs ormcache_context, log_ormcache_stats, invalidate_recordset, @warmup), Query Optimization (_where_calc override, _as_query, Expression class), Field Performance (compute_sudo, precompute, store trade-off, depends granular), ORM Write Optimizations (tracking_disable batch, sudo fuera de loop), SQL-Level (SKIP LOCKED, increment_fields_skiplock), Memory Management (load=False, batch chunking), Testing Performance (@warmup, assertQueryCount, profile), 15 Anti-patrones. 40+ archivos fuente. |
| `odoo-17-tricks-security-data` | **NUEVO** — Trucos de seguridad y datos de Odoo 17.0: ACL Patterns Avanzados (check(), _get_allowed_models, cache, groups), Record Rules Tricks (_eval_context, AND/OR, parent_of, NULL handling), Field-Level Security (groups, NO_ACCESS, related_sudo), Data File Tricks (noupdate, ref(), eval, search), Translation/i18n (translate modes, _()/_t()/_lt(), TRANSLATED_ATTRS), Security Context (env.su, _uid vs env.user, sudo stacking, _apply_ir_rules), Data Integrity (_sql_constraints, @api.constrains, ondelete), Password & Auth (password computed, hashing, API keys, session token), Server Actions Security (triple verification), ir.config_parameter (get_param cache), 8 Anti-patrones. 60+ trucos, ~70% no cubiertos en skills existentes. 19+ archivos fuente. |

### V19: 1 Nuevo Skill 17.0 (Automejoramiento — Loop-015)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-tools-development` | **NUEVO** — Herramientas de desarrollo de Odoo 17.0 (1,251 ln, 31 archivos): Odoo CLI (13 comandos: server/shell/scaffold/populate/db/deploy/neutralize/obfuscate/genproxytoken/tsconfig/cloc), Debug Mode (--dev=all/reload/qweb/xml, session.debug, FSWatcher), Debugger (breakpoint, t-debug, SUPPORTED_DEBUGGER), Logging (init_logger, 7 handlers, 10 flags, mute_logger/lower_logging), Profiling (Profiler, 4 collectors, Speedscope, ExecutionContext, ir.profile), Assets (IrAsset 14 métodos, AssetsBundle 12 métodos), i18n (trans_export/import, TranslationImporter/Exporter, 3 readers, 3 writers), Database (18 funciones, 14 flags, initialize), Scaffolding (3 templates), Server Management (4 server classes, start/restart/_reexec, 20 flags), 10 Anti-patrones. |

### V20: 4 Nuevos Skills 17.0 (Automejoramiento DRY — Loops 016-019)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-dry-models` | **NUEVO** — DRY en modelos de Odoo 17.0 (1,021 ln): AbstractModel (20 mixins catalogados), _inherit decorator (40+ archivos), _inherits delegation (11 modelos), Mixin Composition (mail.thread, portal, rating, image, utm), Prototype Pattern (13 modelos), related fields (63 en stock), company_dependent (43+), fields.Json/Properties (10 pares), super() chain (stock_picking/sale_order/account_move), default_get chain. 14 reglas DRY + 10 anti-patrones. 38 mixins AbstractModel. |
| `odoo-17-dry-views` | **NUEVO** — DRY en vistas de Odoo 17.0 (~1,100 ln, 25+ hallazgos): CTE recursiva _get_inheriting_views(), _combine() deque depth-first, priority escalonado (sale=20, purchase=25, account=30), position='attributes' con add/remove, position='replace' mode='inner', t-call+T_CALL_SLOT='0', t-call dinámico con fallback t-else, t-inherit-mode primary/extension, placeholder+inherit OCP, Field/View Widget Registry, _postprocess_access_rights groups, customize_show+priority, hasclass vs contains(@t-attf-class). |
| `odoo-17-dry-python` | **NUEVO** — DRY en Python de Odoo 17.0 (~1,000 ln): Decorators (depends/depends_context/ondelete/model_create_multi/returns, conditional/synchronized/locked, ormcache/ormcache_context, lazy_property), Utility functions (float_utils, date_utils, SQL(), clean_context, formatLang, ImageProcess, barcode, view_validation), Template Method _prepare_* (8 tablas: _prepare_invoice, _prepare_procurement_values, etc.), Monkey-patching (_inherit MRO, _register_hook+setattr, monkey_patch decorator, _unregister_hook), Metaclasses (MetaModel, MetaField.by_type, MetaCase, __init_subclass__), Code gen (_build_model(), ir.model._instanciate(), _setup_base(), _add_field). 15 anti-patrones. |
| `odoo-17-dry-javascript` | **NUEVO** — DRY en JavaScript de Odoo 17.0 (~900 ln): OWL Component Reuse (standardFieldProps, standardViewProps, ErrorHandler/WithEnv wrappers, useChildSubEnv), Patch System (patch/unpatch con _super, patchWithCleanup), Service Registry (14 servicios, useService hook), Registry System (10 categorías: services/fields/views/view_widgets/main_components/systray), JS Mixins/Composition (field registry resolution, view registry, wrapping/env injection), Utility functions (arrays 12 fn, strings 9 fn, objects 5 fn, numbers 8 fn, concurrency 4 classes, timing 5 fn+2 hooks, hooks 10 customs), LazyComponent, loadBundle/loadJS/loadCSS, Test helpers (mock_services 15 fakes, MockServer 2611 ln, makeTestEnv). 10 anti-patrones. |

### V21: 1 Nuevo Skill 17.0 (Síntesis Final — Loop-020)

| Skill | Descripción |
|-------|-------------|
| `odoo-17-master-reference` | **NUEVO** — Referencia maestra sintetizando los 20 skills de automejoramiento: Cross-reference index de 20 skills por fase (Context/Utilities/Tricks/DRY), 6 Decision Trees (extender modelo, manejar context, optimizar performance, seleccionar herencia de vistas, patrones de seguridad, utility functions), Anti-Pattern Catalog (top 50 organizados por severidad: 10 CRITICAL/20 HIGH/15 MEDIUM/5 LOW), Context Quick Reference (keys oficiales, stock, partner/base, test/dev, convención default_*), Utilities Cheat Sheet (odoo.tools, ORM, JS), DRY Checklist (modelos/vistas/Python/JS), Performance Tips (10 reglas), Security Checklist (10 checks), Testability Patterns (12 patrones), Migration Notes 17→19 (14 cambios clave), Directorio completo de 20 skills. |

### Skills totales 17.0: 113 (108 nuevos + 5 pre-existentes)

---

## 19.0 Testing Skills (Automejoramiento — 20 Skills, 31,403 líneas)

### Fase I (Loops 001-005): Unit/Regression/Performance/Doubles/Security

| Skill | Líneas | Descripción |
|-------|--------|-------------|
| `odoo-unit-testing-deep-19.0` | 1,453 | Error boundary testing, assertRecordValues/Approx/WhitespaceInsensitive/Like, assertQueriesContain, @users/@warmup first-class, freeze_time wrapper, add_to_registry, enter_registry_test_mode, BlockedRequest. 30 annotations, 10 anti-patterns. |
| `odoo-regression-testing-19.0` | 2,056 | @tagged, assertQueriesContain, @users/@warmup, new_test_user, RecordCapturer, ODOO_TEST_MAX_FAILED_TESTS, @no_retry, Savepoint class, _patchExecute, SoftFail, is_tour auto-detection. 42 annotations, 9 anti-patterns. |
| `odoo-performance-benchmark-19.0` | 1,690 | assertQueryCount per-user, @warmup, @users, assertQueriesContain, UtilPerf (profiler-based in 19.0), self.profile, HttpCase.profile() route profiling, Stat/collectStats, freeze_time, _patchExecute shared helper. 52 annotations, 12 anti-patterns. |
| `odoo-test-doubles-mocking-19.0` | 1,826 | self.patch/startPatcher, mock_mail_gateway (6 patches: +push_to_end_point vs 17.0), mockSMSGateway, RecordCapturer (domain=None), BlockedRequest, DISABLED_MAIL_CONTEXT, @users/@warmup. 19.0: IrMail_Server rename, _disable_send, _crypt_context on ResUsersPatchedInTest, debug_mode() _request_stack.push(). 53 annotations, 12 anti-patterns. |
| `odoo-security-testing-19.0` | 1,817 | check_access() unified API, has_access(), _filtered_access(), Domain class AST, _check_field_access(), html_sanitize conditional_comments. 19.0: @users flush_all(), with_user old_env restore, new_test_user Command.set(), Domain.AND/Domain.OR. 45 annotations, 12 anti-patterns. |

### Fase II (Loops 006-010): Flows/Computed/Constraints/Security-Adv/Multi-Company

| Skill | Líneas | Descripción |
|-------|--------|-------------|
| `odoo-testing-flows-workflows-19.0` | 2,053 | 50 patterns. 19.0: Form.from_action() (1 line vs 7 in 17.0), move_ids_without_package REMOVED, backorder_ids One2many, create_backorder tri-state ('ask'/'always'/'never'), assertRecordValues field_names=, E2E tour-first flow testing. 44 annotations, 14 anti-patterns. |
| `odoo-testing-computed-fields-19.0` | 2,062 | 10 sections + 19.0-specific: Registry consistency warnings for shared compute, recursive=True auto-detection, precompute enhanced (M2O, O2M, editable/readonly, required, batch, monetary), invalidate_recordset(flush=True), assertRecordValues auto-Approx, modified trigger zero-query tests, Form()+compute_sudo shared cache test. 68 annotations, 10 anti-patterns. |
| `odoo-testing-constraints-onchanges-19.0` | 1,490 | **Breaking**: _sql_constraints deprecated → models.Constraint/Index/UniqueIndex. **Breaking**: @api.onchange domain return removed (warning dict only). New: callable constraint messages (lambda env, diag:), CheckViolation/UniqueViolation, assertRecordValues match/case + auto Approx, Constraint naming rules enforced. 52 annotations, 14 anti-patterns. |
| `odoo-testing-security-advanced-19.0` | 1,612 | Advanced: check_access() unified API, has_access(), _filtered_access(), Domain AST (Domain.AND/OR/TRUE), _check_field_access() replacement, @users flush_all() between subtests, with_user() old_env restore, new_test_user() Command.set(), html_sanitize() conditional_comments parameter. 36 annotations, 13 anti-patterns. |
| `odoo-testing-multi-company-isolation-19.0` | 2,305 | Fixture setup, context managers, @users() with flush_all(), cross-company isolation, flow propagation (SO→Invoice), company-dependent fields, HTTP tests (cids), branch company (parent_of), inter-company operations, performance. 19.0: Domain.AND/OR replaces expression.AND/OR, check_access() unified, flush_all() mandatory between subtests. 69 annotations, 12 anti-patterns. |

### Fase III (Loops 011-015): Controllers/OWL/Integration/E2E/Hybrid

| Skill | Líneas | Descripción |
|-------|--------|-------------|
| `odoo-tdd-owl-javascript-19.0` | 562 | **Pre-existing** — OWL/JS TDD with QUnit + HOOT reference. |
| `odoo-testing-integration-api-19.0` | 1,594 | 21 sections: PATCH-GLOBAL, SESSION-MOCK, SOAP-ZEEP, BUSINESS-METHOD, FRAMEWORK-REQ-HANDLER, IAP-MOCK, MAIL-GATEWAY (6 patches in 19.0), SOCIAL-AGGREGATE, HTTP-CONTROLLER, WEBSOCKET-INTEG, WEBHOOK-NOTIF, EDI-FLOW, OAUTH-LDAP, EXCEPTION-SIM, ENV-CONTEXT-ROUTING. 19.0: IrMailServer→IrMail_Server, _build_email__, _connect__, push_to_end_point, debug_mode() _request_stack.push(), @users @wraps+flush_all(). 35 annotations, 15 anti-patterns. |
| `odoo-testing-e2e-tours-19.0` | 1,346 | 18 sections: start_tour/browser_js APIs, tour step interface (trigger, run, isCheck, timeout), registration patterns (direct, website, POS, backend+frontend), run commands (12 types), stepUtils, wTourUtils, POS screens, e-commerce utils, enterprise mock+tour, multi-tour, JS vs Python assertions, ClickBot crawler. 19.0: success_signal, debug param, cpu_throttling, delay_to_check_undeterminisms, expectUnloadPage, isActive context-aware steps, run() helpers with {queryFirst,click,edit}. 24 annotations, 12 anti-patterns. |
| `odoo-testing-hybrid-js-python-19.0` | 1,509 | 14 sections: Tour+ORM post-assertions, mock+tour+assertRecordValues triple, JS TourError assertions, Python→JS data flow, JS state→Python verification, payment flow hybrid, enterprise mock+tour, POS hybrid, website builder tours, ClickBot+Python. 19.0: start_pos_tour(), StockPicking class rename, Command.link() preferred. 33 annotations, 11 anti-patterns. |

### Fase IV (Loops 016-020): Cron/Flaky/Coverage/Migrations/Best-Practices

| Skill | Líneas | Descripción |
|-------|--------|-------------|
| `odoo-testing-cron-batch-19.0` | 1,706 | 18 sections: method_direct_trigger, cron state, _process_job() @classmethod, _run_job() loop (MIN_RUNS_PER_JOB=10), CompletionStatus enum, _commit_progress(), progress tracking (failure_count, MIN_FAILURE_COUNT_BEFORE_DEACTIVATION=5), batch processing, enter_registry_test_mode(), Savepoint class, queue jobs, enterprise patterns. 19.0: _acquire_one_job() CTE+SKIP LOCKED, ListLogHandler. 28 annotations, 10 anti-patterns. |
| `odoo-testing-flaky-prevention-19.0` | 1,503 | 13 sections: 7 flakiness categories, time-dependent, DB state isolation, async race conditions, test ordering, randomness control, HTTP isolation, cache pollution, CI stabilization, non-determinism detection. 19.0: freeze_time wrapper class (L2737), Savepoint class, ODOO_TOUR_DELAY_TO_CHECK_UNDETERMINISMS, @users flush_all(), @warmup on BaseCase(L321), TestCursor architecture, forbidden commit/rollback, enter_registry_test_mode(). 27 annotations, 10 anti-patterns. |
| `odoo-testing-coverage-metrics-19.0` | 1,322 | 14 sections: coverage fundamentals, running coverage, .coveragerc, minimum thresholds, analysis, uncovered path detection, regression prevention, gap analysis, query count metrics (assertQueryCount L604, @warmup L2668, @users L2637), test suite metrics (Stat L28, collectStats L285, log_stats L244), metrics dashboard, CI integration. 14 annotations, 9 anti-patterns. |
| `odoo-testing-data-migrations-19.0` | 1,639 | 13 sections: migration script structure, pre/post/end hooks, data integrity, version numbering, rollback verification, data transformation, model/field changes, multi-module, enterprise patterns, noupdate data. 19.0: models.Constraint replaces _sql_constraints in migration scripts, check_access() unified for migration data integrity. 13 annotations, 8 anti-patterns. |
| `odoo-testing-best-practices-19.0` | 1,389 | **SÍNTESIS FINAL** 19.0 — 14 secciones: organización, jerarquía de clases, fixtures, assertions (assertRecordValues auto-Approx, Form.from_action()), mocking (6-mail patch), coverage targets, security (check_access(), Domain.AND/OR), performance (@warmup, assertQueryCount), flaky prevention (10-punto), code review (15-punto), anti-pattern catalog (top 15), test decision matrix, reference index de todos los 20 skills. 27 annotations, 15 anti-patrones. |

### Resumen 19.0 Automejoramiento

| Fase | Loops | Skills | Líneas | Estado |
|------|-------|--------|--------|--------|
| **Fase I** (Unit/Regression/Performance/Doubles/Security) | 001-005 | 5 skills | 8,842 | ✅ COMPLETED |
| **Fase II** (Flows/Computed/Constraints/Security-Adv/Multi-Company) | 006-010 | 5 skills | 9,522 | ✅ COMPLETED |
| **Fase III** (Integration/E2E/Hybrid) | 011-015 | 3 skills | 4,449 | ✅ COMPLETED |
| **Fase IV** (Cron/Flaky/Coverage/Migrations/Best-Practices) | 016-020 | 5 skills | 7,559 | ✅ COMPLETED |
| **Pre-existing** (TDD-Python, TDD-OWL, HOOT) | — | 3 skills | 1,031 | ✅ PRE-EXISTING |
| **Total** | **001-020** | **20 skills** | **31,403** | **✅ COMPLETED** |

### Notas de Migración 17.0 → 19.0

| Cambio | Impacto |
|--------|---------|
| `check_access()` unified API | Reemplaza `check_access_rights()` + `check_access_rule()` |
| `Domain.AND/OR` class-based AST | Reemplaza `expression.AND/OR` y dominios raw |
| `models.Constraint/Index/UniqueIndex` | Reemplaza `_sql_constraints` (BREAKING) |
| `@api.onchange` domain return REMOVED | Solo warning dict soportado (BREAKING) |
| `_sql_constraints` deprecated | Usar `models.Constraint` con naming `_` prefix |
| `Form.from_action()` | 1 línea reemplaza 7 líneas de wizard handling |
| `move_ids_without_package` REMOVED | Usar `move_ids` |
| `@users`/`@warmup` first-class | Decoradores standalone, ya no en common.py |
| `freeze_time` wrapper class | Soporta class/method/context decorator, auto_tick_seconds |
| `assertRecordValues` auto-Approx | Float/monetary auto-wrapped con precisión digital/currency |
| `IrMailServer` → `IrMail_Server` | Mail module rename |
| `build_email` → `_build_email__` | Mail method rename |
| `_filtered_access()` | Reemplaza `_filter_access_rules_python()` |
| `check_field_access_rights()` → `_check_field_access()` | Field-level access rename |
| HOOT framework | JS testing con `expect().toBe()` (nuevo, reemplaza QUnit) |

### V22: 20 Nuevos Skills 19.0 (Context, Utilities, Tricks, Tools & DRY)

Ciclo de automejoramiento para Odoo 19.0. 20 loops siguiendo flujo SDD (Spec→Plan→Tasks→Builder→QC→Lead). Skills en `src/.opencode/19.0/skills/`. Fuentes: `odoo-19.0/` y `enterprise-19.0/`.

#### Fase I: Context Mastery (Loops 001-005)

| Skill | Descripción |
|-------|-------------|
| `odoo-19-context-fundamentals` | Sistema de context: Environment, frozendict, with_context(), clean_context(), @api.depends_context(), default_get() 4 niveles, _search active_test, context keys (5 categorías), diff 19.0 vs 17.0 (14 cambios). 8 anti-patrones. |
| `odoo-19-context-views` | Context en vistas XML: ir.actions.act_window (safe_eval), botones (doActionButton), fields (getFieldContext), search_default_* (SearchModel), default_*, group_by, *_view_ref (regex), CTX_KEY_REGEX, makeContext(). 12 ejemplos XML. |
| `odoo-19-context-python` | Context en Python: depends_context cache_key (lang NUEVO 19.0), auto-agregado de 'lang' en translate=True, default_get() 4 niveles, _search active_test, copy_data __copy_data_seen, clean_context usos, server actions _get_eval_context, protecting/clear/with_company managers. |
| `odoo-19-context-javascript` | Context client-side: makeContext() merge acumulativo, evalPartialContext() NUEVO 19.0, user.context getter, ORM service inyección, action_service 4 capas, CTX_KEY_REGEX, getFieldContext filtrado, getBasicEvalContext, HOOT tests. |
| `odoo-19-context-advanced` | Context avanzado: sudo/with_user stackeabilidad, clean_context en su, multi-company allowed_company_ids sticky, lang/prefetch_langs, tz/context_today, DISABLED_MAIL_CONTEXT/testing keys, protecting/clear managers, diff 19.0 vs 17.0 completo. |

#### Fase II: Utilities Deep Dive (Loops 006-010)

| Skill | Descripción |
|-------|-------------|
| `odoo-19-utilities-core` | Utilidades core odoo.tools: misc (clean_context, frozendict, formatLang), sql (SQL class, increment_fields_skiplock), safe_eval (_SAFE_OPCODES, wrap_module), float_utils (json_float_round NUEVO), func (lazy_property DEPRECATED), cache (ormcache, ormcache_context DEPRECATED), date_utils, config, image (image_process NUEVO), barcode, profiler (QwebTracker NUEVO), mail (email_anonymize NUEVO), view_validation. 80+ funciones, 8 anti-patrones. |
| `odoo-19-utilities-orm` | ORM utilities: Recordset (filtered acepta Domain NUEVO), Search (search_fetch público NUEVO), CRUD (7 Command types), Environment API (flush_query/execute_query NUEVOS, force_company DEPRECATED), Security (check_access/has_access/_filtered_access NUEVOS), Cache (cache_key lang NUEVO), Domain AST (6 subclases, _to_sql), Table Objects (Constraint/Index/UniqueIndex NUEVOS), Decorators (@api.ondelete/@api.deprecated NUEVOS, @api.returns ELIMINADO). 57 referencias, 8 anti-patrones. |
| `odoo-19-utilities-views` | Vistas/templates: ir.ui.view Pipeline (Visitor _postprocess_tag_*), QWeb Engine (20 directivas), 21 Field Converters (Template Method), View Inheritance (CTE recursiva, 5 posiciones), View Validation (RNG, 16 _validate_tag_*), ir.actions (7 types, webhook postcommit NUEVO), Assets (3-phase pipeline, 8 asset classes), Web Client Data (web_read specification dict NUEVO, formatted_read_grouping_sets NUEVO). 10 anti-patrones. |
| `odoo-19-utilities-javascript` | JS utilities: Core (slidingWindow/rotate/uuid/hashCode/deepMerge/invertFloat NUEVOS), Concurrency (Deferred extends Promise NUEVO), Timing (setRecurringAnimationFrame NUEVO), RPC/AES-GCM cache, Registry addValidation NUEVO, Patch System (2 args BREAKING NUEVO), Browser (BroadcastChannel/visualViewport NUEVOS), Localization, Assets, HOOT framework. 20+ NUEVO, 8 anti-patrones. |
| `odoo-19-utilities-testing` | Testing utilities: Base classes (BaseCase/TransactionCase/HttpCase), Decorators (@users/@warmup first-class NUEVO, freeze_time class wrapper NUEVO), Assertions (assertRecordValues auto-Approx NUEVO, assertQueriesContain NUEVO), Mock System, Mail/SMS Mocks (6 patches, push_to_end_point NUEVO), Form.from_action() NUEVO, Registry Test Mode (enter_registry_test_mode NUEVO), HOOT JS framework (@odoo/hoot). 12 anti-patrones. |

#### Fase III: Tricks & Tools (Loops 011-015)

| Skill | Descripción |
|-------|-------------|
| `odoo-19-tricks-orm` | ORM tricks: Domain.AND/OR class AST NUEVO, Recordset Patterns (filtered acepta Domain NUEVO), Cache (ormcache_context DEPRECATED), SQL (increment_fields_skiplock NUEVO), write/create optimizations (search_fetch público NUEVO), Field (compute_sudo, precompute, auto_join ELIMINADO), Environment (execute_query NUEVO), Onchange (domain REMOVIDO BREAKING), @api.ondelete/@api.deprecated NUEVOS. 17 diffs 17→19. |
| `odooe-19-tricks-views` | View tricks: Dynamic Views (Visitor dispatch), XPath avanzado (locate_node first-match), 6 positions (+move NUEVO 19.0), 14+ widgets, Invisible patterns, Tree/Form/Kanban/Search/QWeb/Mobile avanzados, Context en vistas (warehouse_id NUEVO). 16 anti-patrones (5 CRITICAL). |
| `odoo-19-tricks-performance` | Performance: N+1 (search_fetch público NUEVO), Batch (@api.model_create_multi), Index (auto_join ELIMINADO, Constraint/Index NUEVO), Cache (ormcache_context DEPRECATED), Query (Domain class AST optimize_full NUEVO), Field (compute_sudo), SQL (increment_fields_skiplock NUEVO), Testing (@warmup first-class, assertQueriesContain NUEVO). 15 anti-patrones. |
| `odoo-19-tricks-security-data` | Security/data: ACL (check_access unified NUEVO, has_access/_filtered_access NUEVOS), Record Rules (Domain.AND/OR), Field Security (_check_field_access NUEVO), Data files, Translation, Data Integrity (Constraint/Index NUEVO), Password/Auth (pbkdf2_sha512 600k rounds), ir.config_parameter, ir.actions.server. 26 diffs 17→19, 8 anti-patrones. |
| `odoo-19-tools-development` | Dev tools: Odoo CLI (13 commands), Debug Mode (--dev), Debugger (breakpoint, t-debug), Logging (7 handlers), Profiling (4 collectors, QwebTracker NUEVO), Assets (IrAsset 14 methods, AssetsBundle 12 methods), i18n, Database (18 functions), Scaffolding (3 templates), Server (4 classes, 20 flags). 10 anti-patrones. |

#### Fase IV: DRY & Synthesis (Loops 016-020)

| Skill | Descripción |
|-------|-------------|
| `odoo-19-dry-models` | DRY Models: AbstractModel (20+ mixins catalogados), _inherit (40+ extensiones), _inherits (11 models), Mixin Composition (mail.thread 82+ models), Prototype Pattern (13 models), related (63 en stock), company_dependent (43+), fields.Json/Properties (10+), super() chain, Constraint/Index/UniqueIndex NUEVO. 14 reglas DRY + 10 anti-patrones. |
| `odoo-19-dry-views` | DRY Views: CTE recursiva _get_inheriting_views(), _combine() DFS deque, priority escalonado, position='attributes' add/remove/move NUEVO, t-call+T_CALL_SLOT='0', t-inherit mode primary/extension, placeholder+inherit OCP, Field/View Widget Registry. 25+ hallazgos, 15 reglas DRY. |
| `odoo-19-dry-python` | DRY Python: Decorators (@api.ondelete/@api.deprecated NUEVOS, @api.returns ELIMINADO, ormcache_context DEPRECATED), Utility functions (clean_context, float_utils, SQL(), etc.), Template Method _prepare_* (8 tables), Monkey-patching (_inherit MRO, _register_hook+setattr), Metaclasses (MetaModel, MetaField.by_type, MetaCase, __init_subclass__), Code gen. 15 anti-patrones. |
| `odoo-19-dry-javascript` | DRY JavaScript: OWL Component Reuse (standardFieldProps, standardViewProps), Patch System (2 args BREAKING NUEVO), Service Registry (14 services, useService), Registry (10 categories, addValidation NUEVO), JS Composition (field/view registry resolution), Utilities (14+ arrays, 12 strings, 7 objects, 9 numbers), LazyComponent, HOOT test helpers. 10 anti-patrones. |
| `odoo-19-master-reference` | Referencia maestra: Cross-reference index 20 skills, Decision Trees (4), Anti-Pattern Catalog (30+ top), Context Quick Reference (70+ keys, 9 categorías), Utilities Cheat Sheet (80+ functions), DRY Checklist (49 reglas: 14 models+15 views+10 python+10 js), Tricks Collection (80+), Migration Notes 17→19 (35 items: 6 BREAKING+9 HIGH+20 NEW). |

### V23: 4 Nuevos Skills OCA (Contributing Guidelines + Module Lifecycle + Contribution Workflow)

Se crearon 4 skills basados en documentos oficiales de OCA: guías de contribución adaptadas a Odoo 17 y 19, ciclo de vida de módulos (Alpha/Beta/Stable/Mature), y workflow de contribución (PR/code review/CI). Skills guardados en `.opencode/17.0/skills/` y `.opencode/19.0/skills/`.

| Skill | Versión | Descripción | Líneas |
|-------|---------|-------------|--------|
| `oca-17-contributing-guidelines` | 17.0 | OCA coding guidelines completas adaptadas a Odoo 17.0: módulos, XML, Python, JS, CSS, SQL, tests, Git | 1,160 |
| `oca-19-contributing-guidelines` | 19.0 | OCA coding guidelines adaptadas a Odoo 19.0: incluye Domain.AND/OR, models.Constraint, @api.ondelete, HOOT, ES2020+ | 1,128 |
| `oca-module-lifecycle` | 17.0 | Ciclo de vida de módulos OCA: 4 niveles de madurez, requisitos, maintainer role, política de repositorios | 1,078 |
| `oca-contribution-workflow` | 17.0 | Workflow de contribución OCA: Git commits, PR lifecycle, code review checklist, CI/testing, Runbot debugging | 478 |

### V24: 1 Nuevo Skill 17.0 (Subscription Invoice Currency Conversion)

Se creó 1 skill documentando el patrón de conversión de moneda en facturas de suscripción para localización venezolana. Cubre: `_prepare_invoice()` override forzando currency_id a VES, `_prepare_invoice_line()` convirtiendo price_unit via `_convert()`, consulta de `res.currency.rate` via `_get_conversion_rate()`, constraint `_check_currency_id` de `l10n_ve_accountant`, MRO chain, y traducciones i18n. Skill guardado en `.opencode/17.0/skills/`.

| Skill | Versión | Descripción | Líneas |
|-------|---------|-------------|--------|
| `odoo-17-subscription-invoice-currency` | 17.0 | Conversión de moneda en facturas de suscripción con localización venezolana: _prepare_invoice() override forzando currency_id a VES + recalculación de moneda alterna (AC), _prepare_invoice_line() con price_unit convertido + foreign_price/foreign_subtotal hacia moneda alterna, _recompute_subscription_rates() con sync de foreign_currency_id, _recompute_foreign_rates() + onchange, rate semantics USD vs non-USD, _check_currency_id constraint, MRO chain, traducciones i18n, tests 280-312, code review rules FIX-SIC-001 a 010. | 726 |

### V25: 20 Nuevos Skills sale_subscription Views — sdd-improvement (COMPLETED ✅, 20/20)

Ciclo de 20 loops de automejoramiento para el módulo `sale_subscription` (enterprise-17.0).
Cada skill analiza, documenta y referencia patrones de vistas XML reales del módulo enterprise.
**⚠️ READ-ONLY**: No se modifica `enterprise-17.0/` ni `odoo-17.0/`.

| Skill | Loop | Descripción |
|-------|------|-------------|
| `sale-subscription-views-mode-inheritance` | 001 | **NUEVO** — Mode Inheritance Patterns: mode=primary vs extension, sistema priority (default 16), CTE recursiva `_get_inheriting_views()`, 4 cadenas de herencia de sale_subscription, 3 ejemplos ✅ (priority baja, base view, view_ids explícito) y 3 ❌ (primary auto-referencial, priority 999 competition, position=replace en calendar). 300+ líneas. |
| `sale-subscription-views-decoration-badge` | 002 | **NUEVO** — Decoration & Badge Patterns: 6 patrones documentados (tree-root decoration, widget badge en 3 trees, widget badge en form header, div badges Bootstrap, kanban progressbar, state_selection), 7 estados subscription_state mapeados, 9 ejemplos ✅ y 3 ❌ (decoration duplicado, kanban hardcoded, decoration-info ambigüedad), análisis DRY. 255 líneas. |
| `sale-subscription-views-invisible-expressions` | 003 | **NUEVO** — Invisible Expression Patterns: 5 patrones documentados (field dependencies `invisible="1"`, state-based simple, action-conditional, compound conditions, empty/zero check), 8 ejemplos ✅ (dependency fields agrupados, button resume, dynamic form sections, compound buttons, payment alert) y 4 ❌ (complex expression no mantenible, operator precedence sin paréntesis, DRY violation en árboles duplicados). 229 líneas. |
| `sale-subscription-views-tree-patterns` | 004 | **NUEVO** — Tree View Patterns: 8 patrones documentados (decoration-* en tree root y fields, badge widget multi-color para subscription_state, optional/column_invisible, inline trees editable, default_order, multi_edit/sample, close_reasons, priority 999 anti-patrón), 4+ ejemplos ✅ (decoraciones semánticas, protección NULL en decorations, mapeo completo subscription_state a colores, inline trees con domain) y 5+ ❌ (priority 999, DRY violation decoration, column_invisible sin groups, decoration-info con 4 significados, subscription_state sin readonly). ~340 líneas. |
| `sale-subscription-views-form-structure` | 005 | **NUEVO** — Form View Structure Patterns: 6 patrones documentados (header buttons visibility, stat button box, alert banners, subscription info group dual-entry, notebook page inline tree, primary form context duplication), 10 ejemplos ✅ (Resume button, Upsell compound, MRR stat, Alert banner, dual-group, plan layout, inline decoration, sale order template domain) y 7 ❌ (Close wizard ref, History hardcoded threshold, Banner position after, no_one groups, Optional products expression compleja, Context duplication DRY). 265 líneas. |
| `sale-subscription-views-kanban-patterns` | 006 | **NUEVO** — Kanban View Patterns: 5 patrones documentados (default_group_by con group_expand, progressbar activity_state con 3 colores, badges condicionales t-if con luxon.DateTime, rating display con 3 iconos semánticos, health state_selection field), 5 ejemplos ✅ (group_expand expande solo activos, progressbar colores semánticos, payment_exception badge con t-if simple, rating protegido con .length, health invisible cuando no es bad) y 3 ❌ (quick_create=false sin alternativa, t-if complejo sin extraer a computed, rating hardcoded 5/3/1 frágil). ~300 líneas. |
| `sale-subscription-views-search-filters` | 007 | **NUEVO** — Search View & Filter Patterns: 6 patrones documentados (filter_domain multi-campo, subscription_state filters organizados con separators, date filters con context_today(), activity filters invisible=1, 9 group_by options, extension search inheritance), 6 ejemplos ✅ (filter_domain con |, búsqueda en order_line, separators entre filters, date filter con atributo date, activity filters invisibles, group_by completo) y 2 ❌ (strftime + domain complejo con timezone, mixed naming convention en group_by). ~250 líneas. |
| `sale-subscription-views-calendar-patterns` | 008 | **NUEVO** — Calendar View Patterns: 3 patrones documentados (mode=primary sin priority en calendar, position=replace en amount_total y state con riesgos de romper extensiones, dependencia de date_start activity_date_deadline base), 2 ejemplos ✅ (color semántico a subscription_state, reuso del calendar en 4 acciones act_window) y 2 ❌ (position=replace en amount_total y state — rompe extensiones de otros módulos). ~280 líneas. |
| `sale-subscription-views-portal-templates` | 009 | **NUEVO** — Portal QWeb Template Patterns: 4 patrones documentados (dual strategy extension+primary, modal con CSRF+access_token, portal subscriptions list, sidebar composition via t-call), 5 ejemplos ✅ (primary True, extension sin primary, modal CSRF, dual close modal, template composition) y 3 ❌ (position=replace en sidebar rompe extensiones, t-if duplicado en close modals, customize_show priority=90). ~300+ líneas. |
| `sale-subscription-views-context-actions` | 010 | **NUEVO** — Context Patterns in Actions: 5 patrones documentados (default_*+search_default_* combinados, active_id deprecado, view_ids explícito vs implícito, 4 variantes de domain filtering, help HTML templates), 5+ ejemplos ✅ y 3 ❌ (active_id deprecado, domain duplicado entre acciones, help copiado en 4 actions). 5 acciones catalogadas con líneas exactas. ~300 líneas. |
| `sale-subscription-views-plan-pricing` | 011 | **NUEVO** — Plan & Pricing View Patterns: 10 patrones documentados (stat_button, web_ribbon, billing period dual-field inline, auto_close_limit dual-field, inline tree editable con control button, subscription_pricing page condicional, context múltiples defaults, help o_view_nocontent, duration dual-field con invisibles, many2many_tags con domain dinámico), 10 ejemplos ✅ (stat button con active_subs_count, billing period inline, auto_close limit, pricing inline tree, page invisible condicional, context compuesto, help pattern, duration condicional, M2M tags con domain) y 2 ❌ (inline tree duplicado sin shared template, options no_create inconsistente). ~300 líneas. |
| `sale-subscription-views-alert-automation` | 012 | **NUEVO** — Alert & Automation View Patterns: 7 patrones documentados (visibilidad constante `invisible="1"`, state-based por action/trigger, compuesta multi-factor con and/or, readonly condicional `readonly="id"` para inmutabilidad post-creación, required condicional frontend, layout grupos anidados + o_row, naming y convenciones), 12 ejemplos ✅ (company_id doble propósito, campos técnicos ocultos, triple patrón invisible+required+readonly, trigger filtra fecha, and lógico para condiciones cruzadas, calendario laboral compuesto, readonly en 9 campos, required simple y compuesto, panel izquierdo/derecho, o_row inline) y 6 ❌ (readonly en label sin efecto, colspan en em no-field, typo activitity_deadlines, lógica invertida ribbon sin comentario, required sin validación Python, colspan en elemento no-field). 232 líneas. |

| `sale-subscription-views-server-actions` | 013 | **NUEVO** — Server Action & Wizard Patterns: 7 patrones documentados (server action state='code', wizard launch via `_for_xml_id`, direct method call `.filtered()._action_cancel()`, modal wizard `target="new"`, button trigger via external ID, context passing `active_ids`, close reasons retention UI validation), 7 ejemplos ✅ (Cancel filtered, Pause guard, Change Customer wizard, Close Reason modal, Change Customer multi-company, Button external ID, Retention alert validation) y 5 ❌ (inline code sin test, contexto faltante en server action, sin web_ribbon en close reason, external ID sin fallback, expresión compleja sin paréntesis). ~300 líneas. |

| `sale-subscription-views-product-patterns` | 014 | **NUEVO** — Product Template View Patterns: 6 patrones documentados (recurring_invoice toggle inline, page subscription_pricing condicional con inline tree editable + control button, context con default+search_default combinados, template duration dual-field value+unit, template form extension con plan_id y company_id invisible, product_action_subscription con defaults), 4 ejemplos ✅ (recurring toggle, pricing page, context defaults, duration dual-field) y 2 ❌ (inline tree duplicado DRY, no_create inconsistente). 72 líneas de source, 2 archivos XML. ~250 líneas. |

| `sale-subscription-views-partner-account` | 015 | **NUEVO** — Partner & Account View Patterns: 5 patrones documentados (stat button cross-model en res.partner con groups protection, stat button condicional con count=0 hide en account.analytic.account, subscription_id injection en account.move.line/move via xpath después de analytic_distribution, pricelist Recurring Prices page con inline tree editable + domain filter y no_create, activity type action con domain `['|']` y default_res_model), 5 ejemplos ✅ (partner stat button, analytic conditional, subscription_id injection, pricelist inline tree con domain, activity type filter) y 3 ❌ (sin count=0 en partner, sin readonly en subscription_id, sin search_view_id personalizado). 4 archivos XML. ~250 líneas. |
| `sale-subscription-views-bridge-modules` | 016 | **NUEVO** — Bridge Module View Patterns: Catalog of 11 bridge modules (stock, website, project, POS, marketing, FSM, dashboard, localization, tax, commissions). Documents 8 view patterns: inherit_id standard (✅), position=attributes (✅), context passing (✅), server actions (✅), standalone views (✅), and ⚠️ l10n_br primary+replace (❌ — 3x position=replace rompe extensiones). 5 ✅ examples, 2 ❌ examples. Tabla comparativa de patrones por bridge. 300+ líneas. |
| `sale-subscription-views-code-organization` | 017 | **NUEVO** — Code Organization & Naming: file naming conventions (_views.xml vs _templates.xml vs sin sufijo), record ID naming (7 variantes identificadas con inconsistencias), field ordering (form/tree/search), group naming (name= attribute patterns), xpath targeting (6 patrones con niveles de anidamiento 1-6), priority management (5-22 extension, 50-90 portal, 999 primary). 6 categorías, 10 ejemplos ✅, 8 ejemplos ❌, 8 anti-patrones. Cross-file analysis de los 14 XML views. ~420 líneas. |
| `sale-subscription-views-anti-patterns` | 018 | **NUEVO** — Anti-Patterns Catalog consolidando los 25 anti-patrones descubiertos en los 17 loops anteriores. Clasificados por severidad: 4 CRITICAL (position=replace destruction, primary auto-referential), 8 HIGH (DRY violations, complex expressions, duplicated contexts), 9 MEDIUM (naming typos, readonly gaps, hardcoded values), 4 LOW (file naming, cosmetic). Cada uno con source file+line, fix difficulty, y priority fix roadmap. Referencias cruzadas a los 17 skills. ~450 líneas. |
| `sale-subscription-views-improvement-guide` | 019 | **NUEVO** — Cross-Cutting Improvement Guide: guía práctica para mejorar las vistas XML de sale_subscription basada en los 18 loops de automejoramiento anteriores. Incluye priority fix roadmap (22 fixes en 3 tiers: 9 Immediate, 7 Short-term, 6 Long-term), 8 pattern-specific improvements con before/after code examples, code standards (naming, DRY, security visibility), forward compatibility notes para Odoo 19.0 (9 cambios: position=move, attrs→invisible, models.Constraint, Domain.AND/OR, etc.), anti-pattern remediation checklist completa (25 APs), impact analysis por archivo, y cross-references a 15 skills anteriores. ~410 líneas. |

| `sale-subscription-views-master-reference` | 020 | **NUEVO** — Referencia maestra sintetizando los 19 skills anteriores. Incluye cross-reference index por pattern type y por XML file (14 archivos), 4 decision trees (inheritance mode, decoration, position replace, invisible fix), quick reference tables (subscription_state mapping, priority values, position=replace occurrences), meta-learning del proceso completo (6 learnings, 5 lessons, quality metrics), anti-pattern quick reference (top 10 de 25), notas de migración a Odoo 19.0 (15 patrones), y links completos a los 19 skills. Skill capstone del ciclo de 20 loops. ~530 líneas. |

<!-- END V25: sale-subscription-views-self-improvement (20/20 loops — COMPLETED ✅) -->

### V26: odoo-core-self-improvement — Odoo 17.0 Community Core Internals ✅ COMPLETED (7/7 loops)

Ciclo de 20 loops de automejoramiento para el core de Odoo 17.0 Community (`odoo-17.0/odoo/`).
Cada skill analiza, documenta y referencia la arquitectura interna del framework: ORM, Field System, HTTP, Tools, Module System, Views, Testing, y más.
**⚠️ READ-ONLY**: No se modifica `odoo-17.0/`.

| Skill | Loop | Descripción |
|---|---|---|
| `odoo-core-orm-lifecycle` | 001 | **NUEVO** — ORM Internals: BaseModel lifecycle, jerarquía MetaModel→BaseModel→Model, pipeline CRUD (create/write/unlink/read), sistema de cache field-first, lazy prefetch con PREFETCH_MAX=1000, proxy stacking via with_env(), trigger tree de recomputación con modified(), 4 extension points (_inherit/_inherits/_register_hook/_where_calc), 4 anti-patrones (write() monolítico, cache brute-force en unlink(), double modified frágil, TOFIX conocidos). 7,320 líneas analizadas de models.py. |
| `odoo-core-field-system` | 002 | **NUEVO** — Field System Internals: jerarquía de 18 Field subclases (Boolean→Many2many→Id), pipeline de conversión `convert_to_cache→convert_to_record→convert_to_column/read`, descriptor Python `__get__` con 5 estrategias de fetch, descriptor `__set__` con three-way dispatch, función `determine()` y su bug heurístico `__name__.find('__')`, sistema de triggers y árbol de recomputación, Command protocol para x2many (7 commands). 8✅ 6❌, 24 code blocks, 5,247 líneas analizadas de fields.py. |
| `odoo-core-api-decorators` | 003 | **NUEVO** — API Decorators (@api.*): attrsetter() como base de todos los decoradores, call_kw() como dispatcher central con 3 modos (model/model_create/multi), registro de @api.depends/_depends_context/@api.constrains/@api.ondelete/@api.onchange en el ORM, pipeline downgrade() para @api.returns, propagate() para herencia de decoradores. 10 patrones documentados (6✅ 5❌), referencias a api.py L85-484 y models.py L840-926. |
| `odoo-core-http-layer` | 004 | **NUEVO** — HTTP Layer (Request→Controller→Response): pipeline completo Application.__call__() WSGI entry → HTTPRequest → Request._post_init → _serve_db → _serve_ir_http → match → authenticate → pre_dispatch → dispatch → post_dispatch. Documenta Bridge pattern (ir.http↔dispatcher), Template Method (Dispatcher ABC), Strategy (Http vs JsonRPC dispatchers), FutureResponse pattern. 4✅ 4❌ ejemplos. Fuentes: http.py (2,444L), ir_http.py (326L). |
| `odoo-core-database-layer` | 005 | **NUEVO** — Database Layer (SQL, Cursors, Transactions): Savepoint (uuid, flush-before), Cursor (REPEATABLE READ, IN_MAX=1000), TestCursor (savepoint simulation), SQL class (parameterized composable), increment_fields_skiplock (FOR UPDATE SKIP LOCKED), ConnectionPool (MAX_IDLE_TIMEOUT=600s), BaseCursor (pre/post hooks). 7✅ 4❌. Fuentes: sql_db.py (838L), tools/sql.py (693L). |
| `odoo-core-module-system` | 006 | **NUEVO** — Module System (Registry, Loading, Lifecycle): Registry singleton con LRU(42), MetaModel auto-registration vía metaclass, 4-phase model setup, Graph/Node BFS dependency resolution, 9-step load_modules pipeline, PG sequence signaling, deferred constraints, TriggerTree recomputation. 7✅ 5❌. Fuentes: registry.py (1,014L), loading.py (643L), graph.py (199L), module.py (524L), migration.py (243L), db.py (186L), models.py (MetaModel L193-235, _build_model L695-770). |
| `odoo-core-views-templates` | 007 | **NUEVO** — Views & Templates: QWeb Engine & Inheritance Pipeline: CTE recursiva `_get_inheriting_views()` para resolución de cadenas de herencia, `_combine()` merge depth-first (extensions→primaries), 6 posiciones de herencia (replace/attributes/inside/after/before/move), Visitor dispatch en `_postprocess_view()` y `_validate_view()` (16 `_validate_tag_*`), motor QWeb completo (compile/render, static vs dynamic dispatch, 20+ directivas), validación dual RNG+Python, NameManager. 10✅ 6❌. Fuentes: ir_ui_view.py (3,063L), template_inheritance.py (274L), ir_qweb.py (2,772L), view_validation.py (317L). |

<!-- END V26: odoo-core-self-improvement (Loops 001-007 ✅) -->

### V27: account-views-self-improvement — Odoo 17.0 Account Views (COMMUNITY, LGPL)

Ciclo de 20 loops de automejoramiento para el módulo `account` (Odoo 17.0 Community — LGPL). Analiza patrones de vista XML en `odoo-17.0/addons/account/views/` (~37 archivos, 6,882 líneas) y módulos `account_*` relacionados (~20 módulos).
**⚠️ READ-ONLY**: NO se modifica `odoo-17.0/addons/account/`.

| Skill | Loop | Descripción |
|-------|------|-------------|
| `account-views-move-form-tree` | 001 | **NUEVO** — account.move Form, Tree & Action Patterns: 9 patrones (dual Post/Confirm button, state badge 4-colors, outstanding credits 4 alert variants, dual-field partner name, multi-field filter_domain, clean action definition, centralized invisible fields, section_and_note_one2many, activity template). 9✅ 8❌. Fuentes: account_move_views.xml (1,836L). |
| `account-views-tax-account-tag` | 002 | **NUEVO** — Account, Tax & Tag Views: 10 patrones (h1 Code+Name Layout, Stat Button Box, account_type_selection Widget, many2many_tags Domain+Context+Options, Tax Amount Display, Tax Repartition Line Editable Tree, Tax Kanban Minimal Design, Search Multi-field filter_domain, Tag Web Ribbon, Group & Incoterm Views). 10✅ 10❌. Fuentes: 5 archivos XML (645L). |
| `account-views-payment-bank` | 003 | **NUEVO** — Payment, Payment Term & Bank Statement Views: 10 patrones (Payment Header Workflow Buttons, Stat Button Box, Invoicing Legacy Ribbon, Dual Partner ID Fields, Amount o_row with Currency, Payment Tree Patterns, Early Discount Layout, Preview Section, Bank Statement Editable Tree, Payment Method Minimal Views). 10✅ 10❌. Fuentes: 4 archivos XML (768L). |
| `account-views-journal-dashboard` | 004 | **NUEVO** — Journal & Journal Dashboard Views: 12 patrones (Journal Tree with handle+optional, Form Header Stat Button+Ribbon+h1, Dual Default Account Labels 5-variant, Inbound/Outbound Palindrome Pages, Advanced Settings 3-group Alias, Search with Type Filters, Journal Group Editable Tree, Dashboard Kanban JS Class + 9 Sub-templates, Kanban-Menu View/New/Reports, Body Bank/Cash dual-pane, Body Sale/Purchase KPIs, Action with explicit view_ids). 12✅ 12❌. Fuentes: account_journal_views.xml (301L), account_journal_dashboard_view.xml (385L). |
| `account-views-reconcile-cash` | 005 | **NUEVO** — Reconciliation Models & Cash Rounding Views: 10 patrones (Rule Type Radio Widget, Match Amount 4-state, d-flex gap Layout, Payment Tolerance, Counterpart Entries Editable Tree, Partner Mapping Regex Tree, Search with 7 Filters, Reconcile Line Sub-form, Full Reconcile Minimal, Cash Rounding Views). 9✅ 9❌. Fuentes: account_reconcile_model_views.xml (280L), account_full_reconcile_views.xml (22L), account_cash_rounding_view.xml (64L). |
| `account-views-report-portal` | 006 | **NUEVO** — Report Action Registration, Portal QWeb Templates, Dashboard Setup Bar & Digest Extension patterns: ir.actions.report, portal breadcrumb/home/table/sidebar, js_class extension, digest KPI. 10 patrones, 10✅ 13❌. |
| `account-views-partner-company` | 007 | **NUEVO** — Partner, Company & Currency Views: 10 patrones (Fiscal Position Form Structure, Inline Button in Alert Banner, Tax Mapping Editable Tree with Complex Domains, Partner Stat Buttons Monetary+Statinfo, Partner Warning & Credit Limits Config, Partner Dual Invoicing Page split by is_company, Partner Search & Action Windows, Bank Account Trust UI with position="replace", Primary Mode with js_class + position="replace", Company Terms & Onboarding Standalone Forms). 10✅ 10❌. Fuentes: partner_view.xml (320L), res_partner_bank_views.xml (107L), res_company_views.xml (67L), res_currency.xml (24L). |
| `account-views-config-product` | 008 | **NUEVO** — Config Settings, Product & UoM Views: 15 patrones (App+Block+Setting OWL Hierarchy, Toggle→Conditional Content, upgrade_boolean Widget, company_dependent Settings, help+documentation+title Triple, Settings Without id/string Anti-patterns, Product Accounting Page Insertion, Product Tree many2many_tags, Reusable Tree via view_id, Category Property Defaults, Tax Insertions, fiscal_country_codes Cross-Cutting Field, Empty Setting, readonly Redundancy). 15✅ 15❌. Fuentes: res_config_settings_views.xml (396L), product_view.xml (101L), uom_uom_views.xml (14L). |
| `account-views-payment-module` | 009 | **NUEVO** — Account Payment Module Views: 10 patrones (Refund Workflow, Payment Token Fields, Authorized Transactions Guard, Capture/Void Buttons, Transaction Stat Buttons 3-variant, Payment Provider Inline Tree, Portal Pay Now 2-context, Transaction Status Badges 3-state, Payment Modal 3-way, Error/Success Templates 4-type). 10✅ 10❌. Fuentes: 7 archivos XML (313L) del módulo account_payment/. |
| `account-views-wizards` | 010 | **NUEVO** — Wizard Views: 10 patrones (Wizard Footer con btn-primary+special="cancel", Hidden Technical Fields invisible="1", force_save="1" en campos computados, Alert Banner informativo/warning 5 tipos, Radio Widget Selection 3 instancias, Live Preview Widget con account_resequence_widget/grouped_view_widget, Conditional Group Visibility por action type, Footer Dual Button con data-hotkey q/x, Sheet Onboarding Layout con h2+grid, Inline Editable Tree en setup wizards). 11✅ 10❌. Fuentes: 10 archivos XML (609L) en account/wizard/. |
| `account-views-edi-ubl` | 011 | **NUEVO** — EDI & UBL View Patterns: 11 patrones (Multiple Tree Inheritance DRY violation, 3-Tier Alert Banners by Blocking Level, EDI Document Tree Decoration 3-state, Nested Inline EDI Document Tree, Server Action with binding_view_types, PEPPOL Partner Extension triple-view, many2many_checkboxes Widget, EDI Proxy User Read-Only Form, Inline Toggle in Settings, Invisible Tax Fields by UBL Category, Search Filter EDI Processing). 14✅ 13❌. Fuentes: 8 archivos XML (457L) en account_edi, account_edi_ubl_cii, account_edi_ubl_cii_tax_extension, account_edi_proxy_client. |
| `account-views-peppol-self-billing` | 012 | **NUEVO** — PEPPOL & Self-Billing View Patterns: 10 patrones (Settings position="replace", State Machine UI 8 estados, Application Status Badge+Mode, Partner Validation Alert+Verify, Partner Tree Optional Fields, Dashboard Kanban Conditional Links, Move Header Button+State Display, 4 Tree Extensions with "to be removed", Search Filters Group By+Domain, Self-billing Button add+separator). 11✅ 10❌. Fuentes: 6 archivos XML (391L) en account_peppol y account_peppol_selfbilling. |
| `account-views-sepa` | 013 | **NUEVO** — SEPA Payment Views: 10 patrones (Conditional Field Visibility with `!=`, Nested Invisible Dependency, Dashboard Kanban `hasclass` Targeting, Plural QWeb Conditional, Compound `invisible`+`groups`, Tree `optional="hide"`, Settings Module Check, Row Layout `oe_inline`, Simple `position="after"` LEI Insertion). 10✅ 10❌. Fuentes: 7 archivos XML (152L) en enterprise-17.0/account_sepa/. |
| `account-views-followup-batch` | 014 | **NUEVO** — Follow-up & Batch Payment Views: 10 patrones (Dual Inverse-Invisible Buttons, 3-State Decoration Badge, Dual web_ribbon bg_color, Batch State Machine draft→sent→reconciled, force_save Many2many Domain, position="replace" Anti-pattern, XPath hasclass() Targeting, Missing confirm+groups, QWeb Template Composition, Mode=primary Popup). 10✅ 10❌. Fuentes: 8 archivos XML (796L) en enterprise-17.0/account_followup/ y account_batch_payment/. |
| `account-views-reports` | 015 | **NUEVO** — Account Reports Views: 12 patrones (Toggle Notebook por Booleana, Alert Banner + Button Inline, Field Invisible Constante, Dual-Column Group Layout, Stat Button en Partner, position="replace" en Dashboard, Settings company_dependent, Column_Invisible por Parent, Selector decoration-muted, Custom Widget x2many Jerárquico, Domain Widget, mode="primary" Tree Extension). 12✅ 10❌. Fuentes: 11 archivos XML (648L) en enterprise-17.0/account_reports/. |

| `account-views-budget-misc` | 016 | **NUEVO** — Budget & Miscellaneous Views: 12 patrones (Cross-Model Budget Widget, Stat Button Box Budget, Dual-Notebook Budget Lines, Alert Banner Blocking Level, Analytic Account Stat Button, Kanban Approval State Machine, Settings Budget Toggle, 3-Way Match Invoice Status, Journal Dashboard 3-Way Link, Check Printing Bank Rec Widget, Auto-Transfer Tree + Form State Draft/Sent/Done). 12✅ 12❌. Fuentes: 7 archivos XML (670L) en account_budget, account_3way_match, account_accountant_check_printing, account_auto_transfer (Enterprise). |
| `account-views-online-extract` | 017 | **NUEVO** — Online Synchronization & Invoice Extract Enterprise Views: 12 patrones (State-based sync workflow buttons, invisible guard field, statusbar+create=false, many2many_tags complex domain, dashboard CTA 3-state QWeb, position=replace anti-pattern, position=attributes conditional, dashboard field injection, portal QWeb dual-state, portal security notice, journal invisible cascade, hidden field form trigger). 12✅ 12❌. Fuentes: 7 XML (322L) en account_online_synchronization y account_invoice_extract (Enterprise). |
| `account-views-accountant` | 018 | **NUEVO** — Account Accountant Enterprise Views: 14 patrones (JS Class Custom Widget, Priority 999 Takeover, Multi-field filter_domain, Editable Tree+multi_edit, Technical Field Column Invisible, State-based Readonly Chain, Dashboard QWeb Conditional, Stat Button Box Injection, Footer data-hotkey, Settings position=replace, Kanban t-attf-* Dynamic, Decoration Semantic Mapping, company_dependent Settings, Dual Panel Layout). 14✅ 12❌. Fuentes: 12 XML (958L) en account_accountant (Enterprise). |
| `account-views-anti-patterns` | 019 | **NUEVO** — Anti-Patterns Catalog consolidando 22 anti-patrones descubiertos en los 18 loops anteriores. Clasificados: 4 CRITICAL (position=replace destructivo, DRY violation invisible, priority 999, mode=primary+replace), 6 HIGH (wizard sin confirm, settings replace sin id, decoration ambigua, expression compleja inline, hidden field trigger), 8 MEDIUM (filter_domain Polish notation, context duplicado, required+create=false, column_invisible, naming inconsistente), 4 LOW (missing ids, hardcoded styles, false negatives, typos). 22✅ 22❌. Remediation: 9 Immediate, 7 Short-term, 6 Long-term fixes. |
| `account-views-master-reference` | 020 | **NUEVO** — Master Reference sintetizando 19 loops. Cross-reference index de 19 skills, 5 árboles de decisión (Inheritance Mode, position=replace, invisible, decoration, widget), 3 tablas Quick Reference (Top 15 Anti-Patterns, 13 position=replace occurrences, 3 mode=primary), 17 notas de migración 17→19 consolidadas (3 BREAKING), 5 lecciones meta-learning, 15-item checklist, 6 sugerencias de trabajo futuro. |

<!-- END V27: account-views-self-improvement (Loops 001-020 ✅) -->

### V28: account-a-mods-self-improvement — Odoo 17.0 Core 'A' Modules (Community + Enterprise) ✅ COMPLETED

Ciclo de 15 loops de automejoramiento para todos los módulos que comienzan con 'A' en Odoo 17.0 (Community + Enterprise), excluyendo `account` y `analytic` ya cubiertos. Cubre **views + models + controllers + security** de ~60 módulos. READ-ONLY: no modificar `odoo-17.0/` ni `enterprise-17.0/`.

| Skill | Loop | Descripción |
|-------|------|-------------|
| `account-a-mods-analytic` | 001 | **NUEVO** — Analytic Accounting Patterns: módulos `analytic` (Community, LGPL) + `analytic_enterprise` (Enterprise). 10 patrones (Dynamic M2O Column Generation _sync_plan_column, mode=primary+priority Selection Tree, Stat Button Dual Pattern, JSON Distribution+GIN Index, Custom JSON Search, Notebook Toggle by parent_id, _read_group Computed Override, Enterprise Grid View js_class, View_ids Explicit Sequencing, editable=top+analytic_distribution Widget). 11✅ 10❌. Fuentes: 4 views XML (467L) + 8 models (1,057L) + 1 enterprise view (45L) + 1 enterprise model (12L) + 2 JS (58L). |
| `account-a-mods-approvals` | 002 | **NUEVO** — Approvals Module View Patterns: módulo `approvals` (Enterprise). 10 patrones (Dual Inverse-Invisible Buttons, Dynamic Form Sections with triple attribute, 4-State Decoration Mapping, t-set Dict for Dynamic CSS, Radio Widget Configuration Bank, Two Tree Views with Priority, Force_Save on Category/Approver, Validation Warning Pattern, Approver Inline Tree Multi-Mode, Header Button Extension). 10✅ 10❌. Fuentes: 5 views XML (630L) en enterprise-17.0/approvals/. |
| `account-a-mods-appointment` | 003 | **NUEVO** — Appointment Module View Patterns: módulo `appointment` (Enterprise, OEEL-1). 12 patrones (Dual-Mode Invisible Toggle schedule_based_on, Compound Invisible Guard 3+ conditions, Column Invisible with Parent Context, position="replace" in mode=primary ⚠️, Alert Banner Cascade, Web Ribbon Archived, Dynamic readonly with Expression, Hidden Input Portal QWeb, Gantt+Popover Template, Stat Button Box Conditional, QWeb Template Composition, Invisible Field Duplication). 12✅ 12❌. Fuentes: 16 views XML (2,174L) en enterprise-17.0/appointment/. |
| `account-a-mods-appointment-payment` | 004 | **NUEVO** — Appointment Account Payment Patterns: módulo `appointment_account_payment` (Enterprise). 8 patrones (Inline Tree Read-Only Booking Form, Payment Toggle Dynamic Invisible+Required, 6-State Alert Cascade, QWeb Monetary Widget Display, position="replace" Confirm Button, position="attributes" Cancel Condition, Portal Layout Composition, Payment Sub-template Composition). 12✅ 11❌. Fuentes: 8 views XML (307L) en enterprise-17.0/appointment_account_payment/. |
| `account-a-mods-small-community` | 007 | **NUEVO** — Combined Small Community Modules: 12 módulos Community (LGPL) — `auth_password_policy`, `auth_totp_mail`, `account_debit_note`, `account_audit_trail`, `account_add_gln`, `account_qr_code_emv`, `account_payment_term`, `account_check_printing`, `account_fleet`, `account_tax_python`, `account_test`, `account_update_tax_tags`. 8 patrones (Settings Inheritance, Wizard Form+Footer+Action, mode=primary View Override, Stat Button Injection, QWeb Dashboard Kanban, Multi-XPath Field Injection, Complex Compound Invisible, Standalone CRUD Views). 8✅ 8❌. Fuentes: 20 XML (~581L) en 12 módulos Community. |
| `account-a-mods-consolidation` | 008 | **NUEVO** — Consolidation Module Views: módulo `account_consolidation` (Enterprise). 12 patrones (Context-Driven Invisibility 74x, column_invisible with Context, Dual Read/Edit Sections, mode=primary Onboarding 3x, Grid+Graph+js_class, Stat Button Context Propagation, Compound domain time.strftime(), State Button Guards, Inline Tree Editable, Label+Div Rate Display, Kanban t-call, position="replace" Risk). 12✅ 10❌. Fuentes: 9 XML (1,285L). |
| `account-a-mods-intrastat` | 009 | **NUEVO** — Intrastat Module Views: módulo `account_intrastat` (Enterprise). 10 patrones (Declaration Layout, Computed Filter Domains, priority=7 Conflict 4x, position="replace" 6x, Date-Validity Domain Duplicated 3x, Declaration Amount Widget, Commodity Code Selector, Supplementary Units, Transport Mode Selection, Country of Origin). 10✅ 10❌. Fuentes: 9 XML (514L). |
| `account-a-mods-sepa-dd` | 010 | **NUEVO** — SEPA Direct Debit Views: módulo `account_sepa_direct_debit` (Enterprise). 10 patrones (Mandate State Machine, 4-State Tree Decoration, Search State Filter, Dual Alert Banners, Conditional Required+Invisible Batch, Dashboard Kanban SDD, Settings position="replace" ⚠️, Partner Stat Button, Invoice QWeb Notice, Raw SQL Search Method). 10✅ 8❌. Fuentes: 9 XML (389L). |
| `account-a-mods-remaining-combined` | 011 | **NUEVO** — Combined Remaining Enterprise: 15 módulos (Enterprise + Community account_base_import LGPL). 13 patrones (External Tax Compute Button, Alert Banner Before Sheet, External Tax Settings Avatax/TaxCloud, BACS DDI Workflow, priority=999 Injected Views, position="replace" Settings, Stat Button Cross-Model, fiscal_country_codes Visibility, Standalone CRUD Taxonomy, Portal QWeb Tax Hide, Client Action Import, Bank Statement File Uploader, Batch Payment Rejection Wizard). 13✅ 8❌. Fuentes: 39 XML (~1,217L). |
| `account-a-mods-anti-patterns` | 012 | **NUEVO** — Anti-Patterns Catalog consolidando todos los anti-patrones descubiertos en los 11 loops anteriores de account-a-mods-self-improvement. Clasificados por severidad: 7 CRITICAL (position=replace destruction), 13 HIGH (oe_highlight duplicado, priority conflict, security), 22 MEDIUM (DRY violations, truthy-ambiguous, missing groups), 18 LOW (cosmetic, HTML, FontAwesome). Incluye 13 ✅ fix examples, 25-item detection checklist, y referencias cruzadas a cada skill. ~600+ líneas. |
| `account-a-mods-improvement-guide` | 013 | **NUEVO** — Improvement Guide basada en los 14 skills de account-a-mods-self-improvement. Priority fix roadmap con 3 tiers (7 Immediate, 6 Short-term, 6 Long-term). 8 pattern-specific improvements con ejemplos before/after. Code standards compartidos para vistas XML en módulos 'A', position decision tree, decoration-* standard mapping, forward compatibility Odoo 19.0 checklist. ~250+ líneas. |
| `account-a-mods-master-reference` | 014 | **NUEVO** — Master Reference sintetizando los 15 skills de account-a-mods-self-improvement. Cross-reference index con métricas completas, 4 árboles de decisión (position=replace risk, mode=primary vs extension, invisible simplification, widget selection), quick reference tables (top anti-patterns, migration 17→19, pattern frequency heatmap), meta-learning (7 unique patterns, 7 enterprise/community differences, 7 methodology learnings), 16-item implementation checklist. ~350+ líneas. |

<!-- END V28: account-a-mods-self-improvement (Loops 001-015 ✅) -->

### V29: account-b-mods-self-improvement (Odoo 17.0 Modules 'B' — Loops 001-010)

| Skill | Loop | Descripción |
|---|---|---|
| `account-b-mods-settings-config` | 001 | **NUEVO** — Settings & Config Patterns para base_setup: App+Block+Setting OWL hierarchy, singular/plural labels, module toggle + save warning, company_dependent settings, target="blank" anti-pattern, groups protection. 8✅ 8❌. |
| `account-b-mods-automation` | 002 | **NUEVO** — Automation & Server Action Patterns para base_automation: trigger-based conditional visibility (35+ invisible), custom OWL widgets, mode=primary server action form, kanban t-att-class dict (10 tipos), webhook security banner, domain widget dual access. 8✅ 8❌. |
| `account-b-mods-address-geo` | 003 | **NUEVO** — Address & Geolocation View Patterns para base_address_extended + base_geolocalize: priority=900 standalone address form, dual-city field mutual exclusion (city_id/city), o_row street layout with flex, dual-button geo localization (Compute vs Refresh), position="replace" in settings, stat button with context propagation, city CRUD with editable=top, geo provider read-only form. 8✅ 8❌. |
| `account-b-mods-barcodes` | 004 | **NUEVO** — Barcode & GS1 Nomenclature View Patterns para barcodes + barcodes_gs1_nomenclature: inline x2many tree with handle widget, mutual exclusive fields by type selection, rich inline help text with HTML, o_view_nocontent empty-state pattern, column_invisible with parent reference, inherit_id + position=attributes, conditional field groups, context propagation in inline x2many, triple attribute (column_invisible+invisible). 8✅ 8❌. |
| `account-b-mods-vat-iban` | 005 | **NUEVO** — VAT & IBAN Validation View Patterns para base_vat + base_iban: position=move field relocation, VIES validation inline status display, company_dependent settings with full metadata, dual widget=iban injection via position=attributes. 4✅ 4❌. |
| `account-b-mods-import-module` | 006 | **NUEVO** — Module Import & Extension View Patterns para base_import_module: wizard state machine (init→done), file upload with accepted_extensions, dual Activate/Upgrade buttons with inverse invisible, module_type field injection across 4 view types (kanban/tree/form/search), context propagation, custom js_class. 6✅ 6❌. |
| `account-b-mods-remainder` | 007 | **NUEVO** — Combined Remainder View Patterns para board + base_sparse_field + base_install_request + base_automation_hr_contract: dashboard OWL template composition, board layout system, empty state o_view_nocontent, serialization field injection, module request button with t-if+invisible+groups negation, wizard with alert banner, resource field in automation triggers. 8✅ 8❌. |
| `account-b-mods-master-reference` | 008 | **NUEVO** — Master Reference sintetizando los 7 skills de account-b-mods-self-improvement. Cross-reference index, 3 árboles de decisión (settings visibility, invisible strategy, position selection), top 10 anti-patterns, pattern frequency heatmap, 10 meta-learning insights, 10-item checklist, migration notes 17→19. |

<!-- END V29: account-b-mods-self-improvement (Loops 001-008 ✅) -->

### V30: account-c-mods-self-improvement (Odoo 17.0 Modules 'C' — Loops 001-010)

| Skill | Loop | Descripción |
|---|---|---|
| `account-c-mods-calendar-event` | 001 | **NUEVO** — Calendar Event View Patterns: módulo `calendar` (Community, LGPL). 12 patrones (Calendar View Declaration con date_start/stop/delay/color, Dual-Field Daterange Toggle allday vs timed, Recurrence Rule Selection UI con rrule_type_ui proxy, Month-by-Byday Mutual Exclusion, End Type Mutual Exclusion count vs until, Alarm Type-Conditional Fields email/notification/sms, Attendee State Machine Buttons 3-way, Recurring Event Edit Banner, Videocall Management Triad set/clear/join, Calendar Icon Decorators, Quick Create Form lightweight, Event Type & Alarm Standalone CRUD). 12✅ 12❌. Fuentes: 1 archivo XML (545L). Sin position="replace", sin mode="primary". |
| `account-c-mods-calendar-templates` | 002 | **NUEVO** — Calendar Templates, SMS & Activity Patterns: módulos `calendar` + `calendar_sms` (Community, LGPL). 7 patrones (Portal QWeb Invitation con csrf_token+keep_query, Activity Category Routing en mail.activity con 5× position=attributes, SMS Alarm Integration con alarm_type conditional, Partner Stat Button con widget="statinfo", Calendar Settings Sync con app block Google/Outlook, Activity Wizard Schedule con 4× position=attributes, Partner Kanban Integration con badge condicional). 7✅ 7❌. Sin position="replace". |
| `account-c-mods-contacts` | 003 | **NUEVO** — Contacts & Contacts Enterprise View Patterns: módulos `contacts` (Community, LGPL) + `contacts_enterprise` (Enterprise, OEEL-1). 6 patrones (Action View Sequence Control con 3× act_window.view + view_id explícito, Context Default Propagation `default_is_company`, Multi-Group Menu Access comma-separated OR, Menu Hierarchy con 3 niveles + 14 menuitems, Parent-Only Grouping Nodes `menu_localisation`/`menu_config_bank_accounts`, Enterprise Map View Extension con sequence=3). 6✅ 6❌. Sin position="replace". |
| `account-c-mods-crm-lead-form-tree` | 004 | **NUEVO** — CRM Lead Form/Tree/Search View Patterns: módulo `crm` (Community, LGPL). Análisis de `crm_lead_views.xml` (1,328L). 14 patrones (Dual-Panel Conditional Visibility lead/opportunity, Header Button State Machine 6 botones, data-hotkey Keyboard Shortcuts w/v/x/l, Stat Button Box Meeting+Duplicates, Web Ribbon Won/Lost, Context Propagation 18+ default_*, Blacklist Warning UI triad, Address Format o_address classes, Tree optional/column_invisible 49 occurrences, Multi-edit Mode, filter_domain 5-pipe, Hidden Activity Filters, Conditional Group By month/day, Quick Create Preload 18 hidden fields). 14✅ 14❌. |
| `account-c-mods-crm-kanban` | 005 | **NUEVO** — CRM Lead Kanban/Board View Patterns: módulo `crm` (Community, LGPL). 3 vistas kanban en `crm_lead_views.xml` (L389-674). 12 patrones (Kanban Declaration con js_class/sample/default_group_by/on_create, Progressbar Activity State con colors+sum_field, Kanban Lost/Won Ribbon via t-set, Card Composition 5-capas, Priority Widget, Activity Widget, Color Picker, Monetary Display con t-if, Tags with color_field, Forecast Kanban mode=primary Override con 4× position="replace", User Avatar con domain, Kanban Menu condicional). 12✅ 10❌. |
| `account-c-mods-crm-team-stages-reports` | 006 | **NUEVO** — CRM Team, Stage & Report View Patterns: módulo `crm` (Community, LGPL). 4 archivos: `crm_team_views.xml` (347L), `crm_stage_views.xml` (73L), `report/crm_activity_report_views.xml` (119L), `report/crm_opportunity_report_views.xml` (225L). 10 patrones (Team Action Window Context Propagation con search_default_team_id, Help Empty State Templates o_view_nocontent_smiling_face, Stage CRUD multi_edit, Activity Report Graph/Pivot/Tree con interval=month, Activity Search Filters con 11 group_by, Opportunity Report mode=primary Override con 2x position="replace", Report Search group_by groups con typo "compaign", Team Dashboard Kanban QWeb con monetary/plural, Team Assignment Domain Widget foldable, Report Graph/Pivot Invisible Fields con groups negation). 10✅ 10❌. |
| `account-c-mods-crm-enterprise-wizards` | 007 | **NUEVO** — CRM Enterprise & Wizard View Patterns: módulo `crm_enterprise` (Enterprise, OEEL-1) + 5 wizards Community (LGPL). 10 patrones (Enterprise Graph/Pivot con invisible fields + groups negation, Enterprise Cohort mode=churn con date_start/date_stop/interval=week, Enterprise Map View res_partner, Dashboard Action view_ids Sequence con 4 act_window.view records, Enterprise Forecast simple position="after" Override, Lead Conversion Wizard con radio widget + conditional action, Wizard Footer Pattern data-hotkey q/x + btn-primary/special=cancel, Lost Reason Wizard con binding_model_id+dialog_size, Merge Wizard con inline tree, PLS Update Wizard con many2many_tags+o_field_highlight). 10✅ 8❌. |
| `account-c-mods-crm-iap-livechat-sms` | 008 | **NUEVO** — CRM IAP, Livechat, SMS & Mail Plugin View Patterns: módulos `crm_iap_enrich`, `crm_iap_mine`, `crm_livechat`, `crm_sms`, `crm_mail_plugin` (Community, LGPL). 12 XML files (489L). 10 patrones (IAP State Machine con statusbar+Submit/Retry+alert banners por error_type, Dual-Modal via context.get('is_modal'), Triple-Inheritance "Generate Leads" button en 4 vistas, Dual Enrich button by lead type con data-hotkey='g', SMS Composer Dual Actions con binding_view_types list vs form, Chatbot Stat Button con lead_count, Mail Plugin minimal button, QWeb Enrich Template con t-if sections, Minimal Standalone View). 10✅ 10❌. |
| `account-c-mods-crm-settings-currency` | 009 | **NUEVO** — CRM Settings & Currency Rate Live View Patterns: módulos `crm_iap_mine` settings, `crm_iap_enrich` settings, `currency_rate_live` (Enterprise OEEL-1). 4 patrones (IAP Buy Credits Widget injection via widget name="iap_buy_more_credits" en settings, Currency Rate Live Settings con row layout+manual update button, CRM Menu Hierarchy Extension, Cross-cutting Settings Modular Injection pattern). 4✅ 4❌. |
| `account-c-mods-master-reference` | 010 | **NUEVO** — Referencia maestra sintetizando los 9 skills de account-c-mods-self-improvement (V30). Cross-reference index de 9 skills, 3 árboles de decisión (inheritance mode, position strategy, widget selection), quick reference tables (top 10 anti-patterns, pattern frequency heatmap), meta-learning (5 insights sobre módulos 'C'), migration notes consolidadas, y 15-item implementation checklist. |

<!-- END V30: account-c-mods-self-improvement (Loops 001-010 ✅) -->

### V31: data-recycle-remanents-self-improvement (Odoo 17.0 Módulos 'D' y Remanentes)

| Skill | Loop | Descripción |
|---|---|---|
| `data-recycle-remanents` | 001 | **NUEVO** — Data Recycle View Patterns: módulo `data_recycle` (Community, LGPL). 4 XML (192L). 7 patrones (Stat Button + Run Now Header con oe_highlight, Radio Widget Horizontal options=\"{'horizontal': true}\", Domain Widget con options=\"{'model': 'res_model_name'}\", Conditional Info Alert con invisible=\"res_model_id\", Tree Inline Action Buttons Validate/Discard, Searchpanel Search View con icon, Multi-Level Menu con web_icon). 7✅ 7❌. |
| `data-delivery-views` | 002 | **NUEVO** — Delivery Module View Patterns: módulo `delivery` (Community, LGPL). 5 XML (325L). 10 patrones (Dual Inverse-Invisible Stat Buttons para toggle prod/test environment, Delivery Type Conditional Visibility, Destination Availability Cascade country→state→zip, Inline Formula Layout para price rules, Button Triad Shipping Workflow en sale.order, Order Line Decoration-Warning para recompute, Hidden Technical Fields, Column_Invisible vs Invisible, Web Ribbon Archived, Action Help HTML + Context Default). 10✅ 10❌. |
| `data-digest-views` | 003 | **NUEVO** — Digest Module View Patterns: módulo `digest` (Community, LGPL). 3 XML (201L). 7 patrones (Digest Form State Machine con 3 botones Send Now/Deactivate/Activate + statusbar, KPI Page con Group Composition extensible, Standalone Digest Tip CRUD con handle, Settings Block Toggle + Content-group con documentation, Portal Unsubscribe QWeb con alert-success, Search Default con search_default_filter_activated, Groups-Based Field Visibility con 4 niveles de grupo). 7✅ 7❌. |
| `data-documents-core` | 004 | **NUEVO** — Documents Core View Patterns: módulo `documents` (Enterprise, OEEL-1). 4 XML (576L). 12 patrones (Custom JS Class Views con 5 js_class, Custom OWL Widgets documents_many2many_tags/kanban_activity/boolean_favorite, Searchpanel Facet Group By con enable_counters, Kanban QWeb Complex Templates con t-set cascade para file type detection, Form Dual Lock/Unlock Buttons con inverse invisible, Stat Button Conditional Visibility por count, Notebook con Context Propagation para facet_ids, Footer btn-group Layout con data-hotkey, Web Ribbon "Moved to trash", Search uid-based Filters, Primary Mode Facet Form, Hidden Technical Fields + Action Patterns). 12✅ 12❌. |
| `data-documents-share` | 005 | **NUEVO** — Documents Share & Workflow View Patterns: módulo `documents` (Enterprise, OEEL-1). 6 XML (663L). 12 patrones (Share Form Dual-Variant con CopyClipboard URL + popup/compact, Workflow Rule Form Domain/Tags Toggle via condition_type, Tag Action Inline Editable Tree con dominio facet_id parent_of, Share Tree decoration-muted/badge state, Share Portal QWeb 4 templates con format_file_size utility, Workflow Action Minimal editable=bottom, Activity Type Extension 'upload_file' con folder_id, Activity Plan Domain filtrado). 12✅ 12❌. |
| `data-documents-settings-menu` | 006 | **NUEVO** — Documents Settings, Menu & Wizard Patterns: módulo `documents` (Enterprise, OEEL-1). 5 XML (152L). 8 patrones (Settings App+Block con group_documents_manager, Dual Settings Actions con context module=general_settings/documents, Partner Stat Button Cross-Model, Menu Hierarchy 3 niveles con web_icon, Wizard Request Form con many2one_avatar, Link to Record Dual resource_ref por groups admin/!admin, Wizard Footer data-hotkey, Tag IDs Domain by Folder). 8✅ 8❌. |

| `data-cleaning-merge` | 007 | **NUEVO** — Data Cleaning & Merge View Patterns: módulos `data_cleaning` + `data_merge` (Enterprise, OEEL-1). 10 XML (510L). 8 patrones (Tree js_class + groupby inline buttons Merge/Discard, mode=primary Search View priority=1000, ir.model Inheritance con Enable/Disable Merge buttons, Domain Widget con model dinámico, 3-Level Nested Invisible cleaning_mode→notify_user_ids→frequency, Dual Action Main + Notification con searchpanel_default, QWeb Notification Template con t-attf-href, Radio Widget Action Selector con invisible+required). 6/8 patrones únicos no vistos en A/B/C. 8✅ 8❌. |
| `delivery-enterprise-carriers` | 008 | **NUEVO** — Enterprise Delivery Carrier View Patterns: módulos `delivery_*` (Enterprise, OEEL-1). 36 XML (1,696L) en 14 carriers. 15 patrones (Carrier Config Page 14/14, Credential Fields 14/14, Return Label Triad 11/14, Package Type Domain 9/14, Label Format 12/14, Test Env Banner 3/14, Service Discovery Button 4/14, Shipping Wizard 3/14, QWeb SOAP Templates 2/14, Custom OWL Widgets 4/14, IoT Integration 1/14). Legacy vs Modern comparison. 15✅ 15❌. |
| `combined-d-remanentes` | 009 | **NUEVO** — Combined D Remaining Modules: 19 módulos (2 Community LGPL + 17 Enterprise OEEL-1). 45 XML (~1,219L). 12 patrones cross-cutting (Documents Settings Toggle, Stat Button Injection, Payroll Warning Banner x9 DRY violation, mode=primary+priority=999 CRITICAL, position="replace" QWeb, 4-Level Inheritance Chain, Manual stat_info Anti-Pattern, Standalone CRUD, Search Extension, Complex 6-condition Invisible, Placeholder Anchor OCP). 12✅ 12❌. |
| `v31-data-d-master-reference` | 010 | **NUEVO** — Referencia maestra sintetizando los 9 skills de V31 (data-recycle-remanents-self-improvement). Cross-reference index, top 20 anti-patterns (4 CRITICAL + 6 HIGH + 6 MEDIUM + 4 LOW), 4 árboles de decisión (position strategy, stat button, settings, invisible complexity), migration notes consolidadas 17→19, pattern frequency heatmap, meta-learning con 5 findings únicos de módulos 'D', implementation checklist de 15 items. 389 líneas. |

<!-- END V31: data-recycle-remanents-self-improvement (Loops 001-010 ✅) -->

### V32: event-modules-self-improvement — Odoo 17.0 Event Ecosystem (Loops 001-010)

Ciclo de 10 loops de automejoramiento para los 35 módulos del ecosistema de Eventos de Odoo 17.0 (28 Community LGPL + 7 Enterprise OEEL-1). Cubre views de event core, functional extensions, website_event portal, tracks, quizzes, enterprise modules (cohort/gantt/map/social), y mass_mailing bridges. Arquitectura 4-capas: Core → Functional → Website → Enterprise. **READ-ONLY**: No se modifica `odoo-17.0/` ni `enterprise-17.0/`.

| Skill | Loop | Descripción |
|---|---|---|
| `event-modules-core-event` | 001 | **NUEVO** — Event Core Views: 11 XML (~1,448L) del módulo event core. 10 patrones: state-based button triad, responsive dual-template kanban, mode=primary search+position=replace, daterange+hidden end date, decoration-badge triplet, context-driven group_by toggle, inline tree editable con hidden fields, kanban luxon date formatting, custom widget event_icon_selection, mode=primary ticket standalone views. 10✅ 10❌, 8 anti-patterns. |
| `event-modules-functional` | 002 | **NUEVO** — Event Functional Extension Views: 22 XML (~1,285L) en 6 módulos (event_booth, event_sale, event_crm, event_booth_sale, event_crm_sale, event core ext). 12 patrones: dual-mode architecture base+primary (8 mode=primary), position="replace" destructivo, stat button injection (10 instancias), decoration-badge (booth state, sale_status), dual web_ribbon (Sold/Not Sold), complex domain Polish notation+strftime, tree/form view ref in context, position=attributes add/separator, cross-module field unhiding, duplicate dict key bug AP-001, settings toggle cascade, 4-tier inheritance chain. 12✅ 10❌, 4 anti-patterns (2 HIGH). |

| `event-modules-website-core` | 003 | **NUEVO** — Website Event Core: 21 XML (~2,114L) del módulo website_event. 12 patrones: backend form extensions (website_id, question_ids), schema.org microdata (34 ocurrencias), dual-responsive filter architecture (desktop dropdown + mobile offcanvas), is_view_active() feature flags, JS-powered countdown widget (data-* + client-side), conditional t-cache optimization, position="move" field relocation, primary="True" QWeb search box override (HIGH risk), website builder snippet options (we-* elements con data-dependencies), QWeb template composition (35 t-call), conditional rendering state machine (91 t-if), Plausible analytics integration. 12✅ 12❌, 0 decoration-*, 6 position="replace". |

| `event-modules-website-core` | 003 | **NUEVO** — Website Event Core: 21 XML (~2,114L) del módulo website_event. 12 patrones: backend form extensions (website_id, question_ids), schema.org microdata (34 ocurrencias), dual-responsive filter architecture (desktop dropdown + mobile offcanvas), is_view_active() feature flags, JS-powered countdown widget (data-* + client-side), conditional t-cache optimization, position="move" field relocation, primary="True" QWeb search box override (HIGH risk), website builder snippet options (we-* elements con data-dependencies), QWeb template composition (35 t-call), conditional rendering state machine (91 t-if), Plausible analytics integration. 12✅ 12❌, 0 decoration-*, 6 position="replace". |
| `event-modules-booth-exhibitor` | 004 | **NUEVO** — Event Booth & Exhibitor Website Views: 19 XML (~1,370L) en 4 módulos (website_event_booth, website_event_booth_exhibitor, website_event_booth_sale, website_event_exhibitor). 10 patrones: multi-step wizard progress bar (3→4 steps), dual responsive filter architecture (desktop dropdown + mobile offcanvas/accordion), sponsor ribbon/badge system con display_ribbon_style, radio card selection UI con Sold Out overlay, conditional form injection via t-att-class, currency conversion + tax display con _convert(), state-based alert cascade (4 estados), t-call template composition, website builder snippet options (we-button/we-checkbox), standalone sponsor CRUD + kanban. 10✅ 10❌, 3 position="replace" LOW risk, 1 primary="True" QWeb. |
| `event-modules-meet-sale-crm` | 005 | **NUEVO** — Meet, Sale, CRM & Jitsi Views: 5 módulos (website_event_meet, sale, crm, jitsi, meet_quiz), 13 XML (~808L). 10 patrones: Jitsi integration via t-call with 8 params, 3-state room href logic, tax-aware dual monetary display, pricelist discount policy, QWeb composition (t-call chains), meeting room backend CRUD, state-based alert cascade, registration confirmation position="replace" (HIGH risk), quiz leaderboard with image_data_uri, cart integration with ticket hash. 2 bugs found: duplicate record ID, t-valuef typo. 10✅ 10❌. |
| `event-modules-tracks` | 006 | **NUEVO** — Track Session Views: 17 XML (2,034L) del módulo website_event_track. 12 patrones: My Agenda wishlist track filtering, agenda timeline table (rowspan/colspan), track proposal form con file upload, stage management kanban con progressbar, tag CRUD con inline editable tree, visitor wishlist bi-directional stat buttons, settings toggle cascade 4-nivel, feature flags via is_view_active(), **PWA offline CRITICAL: primary=True + position=replace** on div#wrap, dual card+list display, tag badge toggle links, reminder reusable widget con 8 combos. 17✅ 17❌. 1 CRITICAL risk. |
| `event-modules-track-live-quiz` | 007 | **NUEVO** — Track Live, Quiz & Gantt Views: 4 módulos, 16 XML (~691L). 8+ patrones: live streaming participation (YouTube embed, modal), quiz CRUD con leaderboard (image_data_uri, puntos, posición), quiz question management (radio/char/text question types), quiz integration in track pages (t-call in live page), enterprise gantt view for tracks (color, progress, js_class), live/quiz settings toggles cascade, quiz visitor tracking, leaderboard templates (top3 + full table). |
| `event-modules-enterprise-social` | 008 | **NUEVO** — Enterprise Event Views: 3 módulos Enterprise (event_enterprise, website_event_social, website_event_twitter_wall), 7 XML (~147L). Patrones: cohort/gantt/map views con js_class enterprise, social push notification stat buttons, twitter wall snippet integration per event type, whatsapp templates. |
| `event-modules-mass-mailing-bridges` | 009 | **NUEVO** — Mass Mailing Event Bridge Modules: 4 módulos mass_mailing_event* (2 Community con views + 2 sin views). 5 patrones: dual inverse-invisible buttons (btn-primary vs btn-secondary), hidden field as visibility dependency (event_registrations_open), same-anchor xpath composition (multi-module injection before stage_id), minimal override pattern (super→mutate view_id for SMS variants), priority 4 safe stacking. 0 position="replace", 0 mode="primary", 0 primary="True". 5✅ 5❌. |
| `event-modules-master-reference` | 010 | **NUEVO** — Referencia maestra sintetizando los 9 skills de análisis del ecosistema Eventos de Odoo 17.0 (V32, 35+ módulos, 90+ patrones). Cross-reference index, 4 árboles de decisión (inheritance strategy, position=replace risk, primary="True" vs extension, stat button placement), top 10 anti-patterns, 15+ notas de migración 17→19, meta-learning (5 lessons), implementation checklist (12 items). Arquitectura 4-capas (Core→Functional→Website→Enterprise) documentada. ~440+ líneas. |

<!-- END V32: event-modules-self-improvement (Loops 001-010 ✅) -->

### V33: fleet-frontdesk-self-improvement — Odoo 17.0 Fleet & Frontdesk (Loops 001-003 ✅)

Ciclo de 3 loops de automejoramiento para `fleet` (Community, LGPL) y `frontdesk` (Enterprise, OEEL-1). Cubre vehicle/model/cost views, fleet dashboard/settings + frontdesk completo, y master reference. **READ-ONLY**: No se modifica `odoo-17.0/` ni `enterprise-17.0/`.

| Skill | Loop | Descripción |
|---|---|---|
| `fleet-views-vehicle-model-costs` | 001 | **NUEVO** — Fleet Vehicle, Model & Cost Views: 3 archivos XML (1,330L), 14 patrones (tri-state service stat buttons, contract state machine 4-botón, decoration triple warning/danger/muted, vehicle_type conditional car/bike, kanban progressbar + icons, o_row unit display, kanban badge via JS indexOf() — NOVEDOSO, luxon.DateTime comparison — NOVEDOSO, multi-field filter_domain, remaining_days widget, o_view_nocontent empty-state). 0 position="replace", 0 mode="primary". 14✅ 12❌ 2⚠️. |
| `fleet-views-board-frontdesk` | 002 | **NUEVO** — Fleet Board, Settings & Frontdesk Views: 10 archivos XML (837L), 20 patrones (fleet dashboard pivot/graph/tree/search, settings OWL App+Block, frontdesk visitor decoration-danger datetime — 🔴 CRITICAL NOVEDOSO, label_selection widget — NOVEDOSO, Gantt+Calendar — NOVEDOSO, OWL component mount — NOVEDOSO, CopyClipboardChar — NOVEDOSO, inline tree buttons — NOVEDOSO, timezone-aware filters — NOVEDOSO, station kanban dashboard con KPIs, drinks CRUD, reports DRY violation, QR template, menu hierarchy). 0 position="replace", 0 mode="primary". 20✅ 15❌ 7⚠️. |
| `fleet-frontdesk-master-reference` | 003 | **NUEVO** — Referencia maestra del proyecto V33: 2 skills consolidados (34 patrones, 13 XML, ~2,167L). Cross-reference index, 14 anti-patrones (1 CRITICAL + 5 HIGH + 4 MEDIUM + 4 LOW), 3 decision trees (decoration-datetime risk, label_selection vs badge, position safety), pattern frequency heatmap, 18 notas de migración 17→19 (2 BREAKING), meta-learning con 9 hallazgos únicos (datetime.now() decoration — 🔴 CRITICAL primerizo, Gantt+Calendar, label_selection widget, luxon.DateTime, OWL kiosk component, .to_utc(), tree inline buttons, indexOf() badge, CopyClipboardChar), comparison con V25-V32 (7 patrones nuevos). Implementation checklist 18 items. 0 position="replace", 0 mode="primary". |

<!-- END V33: fleet-frontdesk-self-improvement (Loops 001-003 ✅) -->

### V34: google-gamification-self-improvement — Odoo 17.0 Google & Gamification (Loops 001-002 ✅)

| Skill | Loop | Descripción |
|-------|------|-------------|
| `google-gamification-gamification` | 001 | **NUEVO** — Gamification Views: 14 patrones analizando 10 archivos XML (971L) del módulo gamification de Odoo 17.0 Community. Cubre 4 patrones NOVEDOSOS: widget="gauge" (único en Odoo 17), widget="domain" en formulario, widget="progressbar" en tree, luxon.DateTime en kanban. State machines de challenge (draft→inprogress→done) y goal (draft→inprogress→reached/failed). Goal kanban ternary CSS classes, Badge rule authorization cascade, Karma tracking inline tree. 7 anti-patrones (2 MEDIUM + 5 LOW). 0 position="replace", 0 mode="primary". 419 líneas. |
| `google-gamification-google` | 002 | **NUEVO** — Google Module Views: 9 patrones analizando 7 archivos XML (210L) de google_calendar, google_gmail y google_recaptcha (Community). Cubre: Settings Block `position="replace"` (3 occurrences — HIGH risk), OAuth Credential Fields (Client ID/Secret con password=True), Gmail Auth Badge Triad en fetchmail+ir_mail servers (Token Valid badge + Connect button + Setup alert), OAuth Token Display readonly, reCAPTCHA API Key Fields, Hidden Technical Fields, Simple Field Injection, Documentation Links. 3 position="replace" documentados como HIGH risk. 6 anti-patrones (2 HIGH + 2 MEDIUM + 2 LOW). 210 líneas. |
| `google-gamification-master-reference` | MR | **NUEVO** — Referencia maestra sintetizando los 2 skills de V34: 23 patrones totales (14 gamification + 9 Google), cross-reference index, pattern frequency heatmap, 13 anti-patrones consolidados (2 HIGH + 4 MEDIUM + 7 LOW), 3 árboles de decisión (position=replace risk, widget selection, settings strategy), 10 notas de migración 17→19 consolidadas, meta-learning con 6 hallazgos únicos de V34, implementation checklist. |

<!-- END V34: google-gamification-self-improvement (Loops 001-002 ✅) -->

### V35: hr-core-self-improvement — Odoo 17.0 Core HR (Loops 001/005)

| Skill | Loop | Descripción |
|-------|------|-------------|
| `hr-core-employee` | 001 | **NUEVO** — HR Employee, Department & Job Views: 15 archivos XML (1,858L) del módulo `hr` Community (LGPL). 17 patrones incluyendo 7 NOVEDOSOS: Primary Mode 3-Level Chain (res_users.xml 3x mode=primary), 3-State Presence Stat Button con inverse-invisible, Dual-Template Kanban Image Triage (1024→128→SVG), Notebook Replacement with $0 Placeholder, 3 widgets únicos (work_permit_upload, hr_homeworking_radio_image, hr_department_chart), y split widget con position="replace". 0 decoration-*, 0 data-hotkey. 6 position="replace" ⚠️, 3 mode="primary". 14 anti-patrones (3 CRITICAL + 4 HIGH + 4 MEDIUM + 3 LOW). 12 migration notes. 663 líneas. |
| `hr-core-holidays` | 002 | **NUEVO** — HR Holidays Views: 9 archivos XML (2,707L) del módulo `hr_holidays` Community (LGPL). 14 patrones: Dual-Mode 3-Level Inheritance Chain (16 mode=primary), State Machine 6-Button (confirm/approve/validate/refuse/cancel/reset), Timezone Alert Triple-Span mutex (NOVEL), Dual-Render Request Date, Search 3-Way Architecture, Massive position="replace" en allocation manager (12 replaces, CRITICAL), Tree Decoration 4-State, Accrual Frequency 7-Way Mutex (NOVEL), Custom OWL accrual_levels_one2many (NOVEL), Department Kanban Cross-Model Injection (NOVEL), Kanban t-set Dict Dynamic CSS con fallback. 25+ widgets. 14 anti-patrones (3 CRITICAL + 5 HIGH + 4 MEDIUM + 2 LOW). 628 líneas. |
| `hr-core-attendance-contract` | 003 | **NUEVO** — HR Attendance & Contract Views: 10 archivos XML (1,162L) de `hr_attendance` + `hr_contract` Community (LGPL). 12 patrones incluyendo 2 bugs CRITICAL (copy-paste error out_ip_address L124-125, inverted plural logic L166-170), 3 NOVEDOSOS (dual-groups field rendering 6 field pairs, custom contract_warning_tooltip widget, kiosk OWL SPA bootstrap). 0 position="replace" en attendance, 5 en contract. 0 mode="primary". 15 widgets. 12 anti-patrones (2 CRITICAL + 4 HIGH + 4 MEDIUM + 2 LOW). 604 líneas. |
| `hr-core-skills-entry-bridges` | 004 | **NUEVO** — HR Skills, Work Entry & Bridges: 16 archivos XML (1,528L) de 5 módulos Community (LGPL). 20 patrones: expression-based invisible (recordset), cascading skill_type→skill→level visibility, custom OWL widgets (resume_one2many, skills_one2many), state-based readonly chains, guard field + priority=90, compound AND invisible, hierarchy views (3x), 6-clause Polish filter_domain, triple mode="primary" en hr_fleet, 5x position="replace" en hr_maintenance. 7 position="replace" total, 3 mode="primary". 12+ custom widgets. 9 anti-patrones (1 HIGH + 5 MEDIUM + 3 LOW). 799 líneas. |
| `hr-core-master-reference` | 005 | **NUEVO** — Master Reference sintetizando los 4 loops de V35. Cross-reference index de 10 módulos (50 XML, 6,955L, 63 patrones), top 24 anti-patrones consolidados (5 CRITICAL + 8 HIGH + 7 MEDIUM + 4 LOW), 2 bugs críticos documentados (copy-paste error inverted plural), 3 árboles de decisión (position=replace, mode=primary, decoration), meta-learning con 7 hallazgos únicos, implementation checklist por módulo. 424 líneas. |

<!-- END V35: hr-core-self-improvement (Loops 001-005 ✅) -->

### V36: hr-expense-recruitment-timesheet-self-improvement — Odoo 17.0 Community HR (Gastos, Reclutamiento, Timesheet) (Loops 001/004)

| Skill | Loop | Descripción |
|-------|------|-------------|
| `hr-expense-views` | 001 | **NUEVO** — Expense Module View Patterns: módulos `hr_expense` (7 XML, 1,452L) + `hr_homeworking` (2 XML, 73L). 14 patrones incluyendo 7 NOVEDOSOS: Dual-statusbar normal/refused, nb_attachment inverse-invisible buttons, triple conditional price input (has_cost/no_cost/multi-currency), `not is_editable` pervasive readonly (32×), searchpanel default_state filtering, cross-model stat buttons en account.move/payment, 3-tier mode=primary architecture (10×). 0 position="replace". 12 anti-patrones (2 HIGH + 5 MEDIUM + 5 LOW). 525 líneas. |
| `hr-recruitment-views` | 002 | **NUEVO** — Recruitment Module View Patterns: módulo `hr_recruitment` (12 XML, 1,593L) + bridges `hr_recruitment_skills`/`sms`/`survey` (5 XML, 227L). 14 patrones: applicant state machine dual-track (application_status + kanban_state), kanban recruitment pipeline, interviewer form mode=primary + position="replace" (⚠️ CRITICAL), header button state machine 4-botones con data-hotkey q/d/x, stat button box 3-way, stage management + hired warning, skills cascade 3-level, salary o_row + extra, survey interview integration, search view 6 filter groups, kanban progressbar + color, web_ribbons 3-state, kanban dual-template, department kanban hasclass() injection. 1 position="replace" 🔴. 8 anti-patrones (1 CRITICAL + 2 HIGH + 3 MEDIUM + 2 LOW). 592 líneas. |
| `hr-timesheet-views` | 003 | **NUEVO** — Timesheet Module View Patterns: módulo `hr_timesheet` (11 XML, 1,534L). 12 patrones: Dual-mode primary architecture (7× mode=primary), readonly guard field (`readonly_timesheet`), inline timesheet en task form, timesheet_uom widget variants (3 tipos), 9× position="replace" (7 en search — MEDIUM), decoration state machine para time validation (3 niveles), kanban badge t-set cascade (3 estados), portal QWeb template composition, dual avatar por groups (hr.employee vs hr.employee.public), dual is_uom_day branching, search specialization (3 variantes), settings toggle cascade. 9 NOVEDOSOS: task_with_hours widget, timesheet_uom_no_toggle, project_task_progressbar, 3-tier groups (user/approver/manager), dual-mode timers. 0 mode="primary" en vistas no-core, 0 data-hotkey. 8 anti-patrones (2 MEDIUM + 6 LOW). QC PASS. |

<!-- END V36: hr-expense-recruitment-timesheet-self-improvement (Loops 001-004 ✅ COMPLETED) -->

### V37: helpdesk-self-improvement — Odoo 17.0 Enterprise Helpdesk (Loops 001-002)

Ciclo de 2 loops de automejoramiento para el módulo `helpdesk` (Enterprise, OEEL-1) y sus 12 módulos bridge. Cubre tickets, stages, teams, SLA, portal, rating, y bridges (timesheet, sale, FSM, SMS, stock, repair). **READ-ONLY**: No se modifica `enterprise-17.0/helpdesk/`.

| Skill | Loop | Descripción |
|-------|------|-------------|
| `helpdesk-core-views` | 001 | **NUEVO** — Helpdesk Core Views: 13 archivos XML (2,585L), 18 patrones (Stat Button Box with Rating Icons — NOVEL, Dual-Field Conditional Visibility, SLA Deadline + Warning, Kanban Dashboard KPI Columns — NOVEL, Gallery of 12 Dashboard Actions — NOVEL, Team Form Settings Sections, Portal QWeb 7 templates, Cohort Analysis — NOVEL, 6 custom js_class registrations). 24 widget types. 13 position="replace" (6 HIGH en stage_id), 17 mode="primary", 0 data-hotkey. 12 anti-patrones (2 CRITICAL + 4 HIGH + 3 MEDIUM + 3 LOW). 610 líneas. |
| `helpdesk-bridge-views` | 002 | **NUEVO** — Helpdesk Bridge Views: 12 módulos bridge enterprise (29 XML, ~1,200L). 10 patrones (Stat Button Box Injection 7×, stage_id before-anchor row 5×, Two-Phase Priority Layering 45/50, Header Timer Buttons, Team Config Extension, Guard Fields use_*, Portal QWeb, Toggle Cascade, Hotkey Standardization, Thin Bridge). 3 position="replace" (only timesheet), 6 mode="primary" (only timesheet). 9 data-hotkey (1 collision: w). 5 anti-patrones (MEDIUM). 475 líneas. |
| `helpdesk-master-reference` | MR | **NUEVO** — Master Reference V37: 2 skills consolidados (28 patrones, 42+ XML, ~3,800L). Anti-pattern catalog (17 total), 2 decision trees, 10 migration notes, 5 meta-learning findings, 12-item checklist. 214 líneas. |

<!-- END V37: helpdesk-self-improvement (Loops 001-002 ✅) -->

### V38: odoo-db-skills-19.0 — Database/PostgreSQL Skills for Odoo 19.0 ✅ COMPLETED (20/20 loops)

Ciclo de 20 loops de automejoramiento para DB/PostgreSQL skills de Odoo 19.0. Cubre architecture, DDL/schema, type mapping, SQL class, database layer, indexing, EXPLAIN, window functions, CTE, aggregation, JSONB, datetime, locks, batch/bulk, table partitioning, security, monitoring, vacuum, custom SQL, y master reference. Source: `odoo-19.0/odoo/sql_db.py` (852L), `tools/sql.py` (781L), `orm/registry.py` (1269L), `orm/models.py`, `orm/fields.py`, `tools/profiler.py` (747L), `tools/query.py` (276L), `orm/table_objects.py` (205L), `orm/domains.py` (~400L). **READ-ONLY**: No se modifica `odoo-19.0/`.

| # | Skill | Loop | Descripción |
|---|-------|------|-------------|
| 1 | `odoo-db-architecture-19.0` | 001 | **NUEVO** — ConnectionPool, Cursor, Savepoint, Registry singleton (LRU 42), inter-process signaling (tables NOT sequences for logical replication). ~300L. |
| 2 | `odoo-db-schema-ddl-19.0` | 002 | **NUEVO** — _auto_init() pipeline, Constraint/Index/UniqueIndex (table_objects.py 205L), field.update_db(), DDL functions from tools/sql.py. ~350L. |
| 3 | `odoo-db-orm-type-mapping-19.0` | 003 | **NUEVO** — 18+ field types → PG types (Float→numeric NOT float8!, Char→varchar/text pg_varchar threshold 1024), conversion pipeline, convert_to_column_insert() batch optimization. ~300L. |
| 4 | `odoo-db-sql-class-19.0` | 004 | **NUEVO** — SQL class (tools/sql.py L46-201), Domain AST to_sql(), Query class (tools/query.py 276L), make_identifier() crc32 hash, DDL functions. ~300L. |
| 5 | `odoo-db-core-database-layer-19.0` | 005 | **NUEVO** — TestCursor (savepoint-based commit simulation), _FlushingSavepoint, ConnectionPool 3-phase borrow, Cursor lifecycle REPEATABLE READ. ~300L. |
| 6 | `odoo-db-indexing-strategies-19.0` | 006 | **NUEVO** — field.index (btree/btree_not_null/trigram), check_indexes() pg_index/pg_class/pg_am queries, auto_join REMOVED in 19.0, _condition_to_sql_company(). ~250L. |
| 7 | `odoo-db-explain-analyze-19.0` | 007 | **NUEVO** — EXPLAIN ANALYZE plan nodes, ORM search pipeline, SQLCollector (profiler.py), N+1 detection, assertQueryCount. ~250L. |
| 8 | `odoo-db-window-functions-19.0` | 008 | **NUEVO** — ROW_NUMBER(), SUM() OVER(), LAG/LEAD, read_group() with aggregates, _read_group_expand_full(). ~250L. |
| 9 | `odoo-db-cte-recursive-19.0` | 009 | **NUEVO** — Non-recursive/recursive CTE, parent_path (format "1/5/12/45/", LIKE patterns), ORM search with parent_path. ~250L. |
| 10 | `odoo-db-aggregation-grouping-19.0` | 010 | **NUEVO** — _read_group() pipeline, GroupBy class, aggregates (count/sum/avg/min/max/array_agg), read_group_expand(). ~250L. |
| 11 | `odoo-db-jsonb-properties-19.0` | 011 | **NUEVO** — Json field, Properties field, JSONB operations (->/->>/@>/?), GIN index, PropertiesDefinition schema. ~200L. |
| 12 | `odoo-db-datetime-interval-19.0` | 012 | **NUEVO** — UTC storage, AT TIME ZONE, INTERVAL, timedelta vs relativedelta, date_trunc, read_group time intervals. ~200L. |
| 13 | `odoo-db-lock-management-19.0` | 013 | **NUEVO** — FOR UPDATE/NOWAIT/SKIP LOCKED, increment_fields_skiplock(), lock_timeout, deadlock prevention. ~200L. |
| 14 | `odoo-db-batch-bulk-19.0` | 014 | **NUEVO** — execute_values(), batch create/write, UPSERT ON CONFLICT, page_size tuning, memory management. ~200L. |
| 15 | `odoo-db-table-partitioning-19.0` | 015 | **NUEVO** — _auto=True/False, _table_query, range/list/hash partitioning, partition pruning. ~200L. |
| 16 | `odoo-db-security-19.0` | 016 | **NUEVO** — check_access() unified API, has_access(), _filtered_access(), record rules, field-level security, parameterized queries. ~250L. |
| 17 | `odoo-db-monitoring-19.0` | 017 | **NUEVO** — Profiler system (SQLCollector/QwebCollector), sql_counter, pg_stat views, cache statistics, pg_badger. ~200L. |
| 18 | `odoo-db-vacuum-statistics-19.0` | 018 | **NUEVO** — VACUUM/ANALYZE, autovacuum tuning, table bloat detection, pg_stat_user_tables, scheduled maintenance. ~200L. |
| 19 | `odoo-db-custom-module-sql-19.0` | 019 | **NUEVO** — init() hook, raw SQL patterns, migration scripts, DDL functions, PL/pgSQL, batch operations. ~250L. |
| 20 | `odoo-db-master-reference-19.0` | 020 | **NUEVO** — Capstone: cross-reference 19 skills, 4 decision trees, 30 anti-patterns (5 CRITICAL/10 HIGH/10 MED/5 LOW), 7 key 19.0 changes. ~400L. |

**Key 19.0 Changes Documented:**
- check_access() unified (replaces check_access_rights + check_access_rule)
- Domain.AND/OR class-based AST (replaces expression.AND/OR)
- models.Constraint/Index/UniqueIndex (replaces _sql_constraints)
- auto_join REMOVED (must use explicit domain joins)
- SQL.__iter__() DEPRECATED (use SQL.identifier())
- flush_query()/execute_query() NEW on Environment
- ormcache_context DEPRECATED (use @ormcache)
- Inter-process signaling uses INSERT-only tables (NOT sequences) for logical replication

**Total: 20 skills, ~5,500+ líneas, 100+ anti-patterns, 30+ source files analyzed**

<!-- END V38: odoo-db-skills-19.0 (20/20 loops — COMPLETED ✅) -->

### Odoo 16.0 Skills (`.opencode/16.0/skills/`)

| Skill | Descripción |
|-------|-------------|
| `odoo-core-orm-16.0` | Core ORM: BaseModel, fields, CRUD, cache, prefetch |
| `odoo-core-fields-16.0` | Field system: 18 types, descriptors, triggers, compute |
| `odoo-core-api-16.0` | API decorators: @api, depends, constrains, onchange |
| `odoo-core-http-16.0` | HTTP layer: WSGI, controllers, dispatchers, routing |
| `odoo-core-db-16.0` | Database: cursors, transactions, SQL class, pooling |
| `odoo-core-modules-16.0` | Module system: registry, loading, graph, lifecycle |
| `odoo-core-security-16.0` | Security: ACL, record rules, access control |
| `odoo-core-cache-16.0` | Cache system: ormcache, invalidation, prefetch |
| `odoo-core-views-16.0` | Views engine: QWeb, inheritance, xpath, validation |
| `odoo-gof-creational-16.0` | GoF Creational: Singleton, Factory, Builder, Prototype |
| `odoo-gof-structural-16.0` | GoF Structural: Adapter, Decorator, Composite, Proxy |
| `odoo-gof-behavioral-16.0` | GoF Behavioral: Observer, Command, Strategy, State |
| `odoo-solid-srp-ocp-16.0` | SOLID: SRP mixins, OCP _inherit, xpath |
| `odoo-solid-lsp-isp-dip-16.0` | SOLID: LSP super(), ISP mixins, DIP env[] |
| `odoo-arch-layered-16.0` | Layered architecture: 5 capas, Bridge, Pipeline |
| `odoo-arch-event-16.0` | Event-driven: bus.bus, mail, webhooks, hooks |
| `odoo-owasp-injection-16.0` | OWASP: SQL injection, XSS, command injection |
| `odoo-owasp-auth-16.0` | OWASP: Auth, session, MFA, OAuth, CSRF |
| `odoo-owasp-crypto-16.0` | OWASP: Cryptography, password hashing |
| `odoo-owasp-hardening-16.0` | OWASP: Security hardening checklist |
| `odoo-tdd-python-16.0` | TDD Python: TransactionCase, assertions, mocking |
| `odoo-tdd-owl-16.0` | TDD OWL: QUnit, tours, patch, helpers |
| `odoo-tdd-unit-16.0` | Unit testing: error boundary, float precision |
| `odoo-tdd-regression-16.0` | Regression: @tagged, fixtures, CI |
| `odoo-tdd-performance-16.0` | Performance: assertQueryCount, profiling |
| `odoo-perf-n1-16.0` | Performance: N+1 prevention, batch-first |
| `odoo-perf-batch-16.0` | Performance: batch processing, queue_job |
| `odoo-perf-index-16.0` | Performance: PostgreSQL indexes, trigram |
| `odoo-perf-cache-16.0` | Performance: cache optimization, ormcache |
| `odoo-perf-query-16.0` | Performance: query optimization, EXPLAIN |
| `odoo-perf-cron-16.0` | Performance: cron jobs, batch scheduling |
| `odoo-xml-basic-16.0` | XML Views: form, tree, kanban, search |
| `odoo-xml-advanced-16.0` | XML Views: inheritance, xpath, positions |
| `odoo-xml-kanban-16.0` | XML Views: kanban, progressbar, QWeb |
| `odoo-xml-qweb-16.0` | XML Views: QWeb templates, directives |
| `odoo-xml-portal-16.0` | XML Views: portal templates, website |
| `odoo-xml-graph-16.0` | XML Views: graph, pivot, calendar |
| `odoo-xml-search-16.0` | XML Views: search filters, group by |
| `odoo-xml-invisible-16.0` | XML Views: invisible, attrs, modifiers |
| `odoo-xml-widgets-16.0` | XML Views: field widgets, options |
| `odoo-ctrl-http-16.0` | Controllers: @http.route, routing |
| `odoo-ctrl-portal-16.0` | Controllers: portal, website |
| `odoo-ctrl-middleware-16.0` | Middlewares: WSGI, session, auth |
| `odoo-mixin-mail-16.0` | Mixins: mail.thread, chatter, tracking |
| `odoo-mixin-portal-16.0` | Mixins: portal.mixin, website |
| `odoo-mixin-image-16.0` | Mixins: image mixin, binary |
| `odoo-ctx-fundamentals-16.0` | Context: Environment, frozendict, with_context |
| `odoo-ctx-views-16.0` | Context: XML views, default_*, search_default_* |
| `odoo-ctx-python-16.0` | Context: @api.depends_context, default_get |
| `odoo-dry-models-16.0` | DRY: AbstractModel, _inherit, mixins |
| `odoo-dry-views-16.0` | DRY: View inheritance, xpath, reuse |
| `odoo-dry-python-16.0` | DRY: Decorators, utilities, template method |
| `odoo-dry-js-16.0` | DRY: JS utilities, patch, registry |
| `odoo-util-core-16.0` | Utilities: odoo.tools (misc, sql, safe_eval) |
| `odoo-util-orm-16.0` | Utilities: ORM helpers (search, browse, read) |
| `odoo-util-views-16.0` | Utilities: view validation, inheritance |
| `odoo-util-js-16.0` | Utilities: JS core (arrays, strings, objects) |
| `odoo-util-testing-16.0` | Utilities: Test helpers, Form(), mock |
| `odoo-i18n-16.0` | Translations: _(), _t(), PO files, i18n |
| `odoo-sequences-16.0` | Sequences: ir.sequence, sequence.mixin |
| `odoo-devtools-16.0` | Dev tools: CLI, debugger, logging, profiling |
| `odoo-testing-tools-16.0` | Testing tools: base classes, decorators |
| `odoo-migration-15-16-16.0` | Migration 15→16: breaking changes, upgrade scripts |
| `odoo-migration-16-17-16.0` | Migration 16→17: breaking changes, upgrade scripts |
| `odoo-migration-16-19-16.0` | Migration 16→19: breaking changes, upgrade scripts |
| `odoo-testing-best-16.0` | Testing best practices: checklist, anti-patterns |
| `odoo-master-reference-16.0` | Master reference: cross-reference all 100 skills |

<!-- END Odoo 16.0 Skills (100 skills — COMPLETED ✅) -->

## Skill Sharing Infrastructure

### Daemon: skill-sync

Sincroniza skills de OpenCode → Claude vía symlinks (unidireccional).

```bash
# One-shot sync
src/scripts/skill-sync-daemon.sh --once

# Daemon (loop cada 30s)
src/scripts/skill-sync-daemon.sh

# Estado del servicio
systemctl --user status skill-sync.service

# Logs
journalctl --user -u skill-sync.service -f
```

Ver skill `skill-sync-daemon` para documentación completa.

### Fuentes de Skills (5 directorios)

| # | Fuente | Count | Prioridad |
|---|--------|-------|-----------|
| 1 | `src/.opencode/skills/` | 108 | 1 (primera fuente) |
| 2 | `src/.opencode/17.0/skills/` | 326 | 2 |
| 3 | `src/.opencode/19.0/skills/` | 161 | 3 |
| 4 | `src/.opencode/16.0/skills/` | 100 | 4 |
| 5 | `~/.config/opencode/skills/` | 155 | 5 |

### Target Claude

`~/.claude/skills/` — ~854 dirs (~851 symlinks + 3 real dirs)

### OpenRAG

Skills, versionadas y documentación se ingieren a OpenRAG para búsqueda semántica.
Ver skill `openrag` para política de ingestion y credenciales.

<!-- END Skill Sharing Infrastructure -->

### Migration Audit Skills (2026-09-18)

Skills creadas a partir de la auditoría de migración 17→19 (24 módulos auditados, 8 pasos por módulo).

| Skill | Scope | Ubicación | Descripción |
|-------|-------|-----------|-------------|
| `odoo-migration-audit-methodology` | Global | `~/.config/opencode/skills/` | Metodología de 8 pasos para auditar migraciones de módulos Odoo |
| `odoo-19-breaking-changes-checklist` | Global | `~/.config/opencode/skills/` | Checklist consolidado de breaking changes 17→19 (Python, XML, JS, SQL) |
| `odoo-migration-classification-taxonomy` | Global | `~/.config/opencode/skills/` | Taxonomía de clasificación: MIGRADO-VIGENTE, EN-PROGRESO-CON-BUG, SIN-MIGRAR, etc. |
| `odoo-19-pos-js-migration` | Project | `src/.opencode/skills/` | Guía completa de migración JS del POS: imports, APIs removidas, patrones de patch |
| `odoo-cross-repo-module-tracking` | Project | `src/.opencode/skills/` | Cómo rastrear módulos across repos: integra-addons, odoo-venezuela, custom checkouts |
| `odoo-approval-workflow-patterns` | Global | `src/.opencode/skills/` | Approval workflows: state machine, write guards, self-approval blocking, dual notification, activity lifecycle |
| `odoo-dual-notification-patterns` | Global | `src/.opencode/skills/` | Dual-channel notifications: message_notify + forced second channel, mt_note, customer exclusion |

### Migration Rules (R217-R231)

| # | Regla | Scope | Fuente |
|---|-------|-------|--------|
| R217 | **Migration Audit 8-Step Methodology** — SIEMPRE seguir los 8 pasos: manifest, gap 17→19, syntax+XML IDs, PR chain, i18n, CSS/assets, classification, write report | Global | 24 módulos auditados |
| R218 | **POS JS API Breaking Changes Odoo 19** — `@point_of_sale/app/store/models` REMOVIDO, `Product.get_pricelist_item()` REMOVIDO, `TicketScreen._onDoRefund()` REMOVIDO, `ErrorPopup`→`AlertDialog`, `DiscountButton`→`PosStore.applyDiscount`. Requiere reescritura completa (~8-16h por módulo). | Module | pos_commissions, pos_discount, subsidiary_pos_hr |
| R219 | **XML Inheritance tree→list Migration Risk** — Cuando una vista target renombra `<tree>` a `<list>`, el `inherit_id` que referencia el viejo XML ID (ej. `product_pricelist_item_tree_view`) ROMPE la herencia. SIEMPRE verificar que el target existe en 19.0. | Module | costs_matrix (CRITICAL) |
| R220 | **i18n PO Header Staleness Detection** — Archivos `.po` copiados de 17.0 sin re-export mantienen header `Odoo Server 17.0+e`. Regenerar con `odoo --i18n-export` contra base 19.0. | Module | Múltiples módulos |
| R221 | **Cross-Repo Module Tracking** — Módulos viven en repos distintos: `integra-addons-19.0` (Binaural), `odoo-venezuela-19.0` (l10n_ve_*), `custom/<client>/` (checkouts). Verificar existencia en TODOS los repos antes de asumir que un módulo "no existe". | Project | 239 módulos totales |
| R222 | **Migration Classification Taxonomy** — Usar clasificación estándar: MIGRADO-VIGENTE (CERO/deuda técnica/deuda CRÍTICA), EN-PROGRESO-CON-BUG, EN-PROGRESO-PR, SIN-MIGRAR, NO-REQUIERE, NO-EXISTE, NOT IN SHARED POOL. | Global | Taxonomía R4 |
| R223 | **Odoo 19 group_operator→aggregator** — `fields.Float(group_operator="avg")` DEBE ser `fields.Float(aggregator="avg")` en 19.0. Causa `ValueError` en registro de campos si no se migra. Aplica a TODOS los report models (sale.report, purchase.report, account.invoice.report). | Module | margin (6 fields), 3 report models |
| R224 | **Odoo 19 SQL() Class for Report Models** — `_select()` y `_group_by()` en report models DEBEN retornar objetos `SQL()`, NO strings. `from odoo.tools import SQL`. Sin esto, los reportes crash con TypeError. | Module | location_report, margin, 3+ report models |
| R225 | **Odoo 19 currency_table→account_currency_table** — El alias SQL para la tabla de tasas de cambio en `sale.report` y `purchase.report` cambió de `currency_table` a `account_currency_table`. Usar el viejo alias causa SQL error en pivot/graph views. | Module | margin (sale_report.py) |
| R226 | **Approval Workflow Pattern** — Flujo de aprobación con state machine (Selection: none→requested→approved/rejected), audit fields (requested_by, decided_by, dates), computed visibility booleans con `@api.depends_context("uid")`, y self-approval blocking. Aplica a CUALQUIER modelo Odoo que requiera aprobación humana antes de permitir una acción (editar precios, confirmar órdenes, publicar contenido). Skill: `odoo-approval-workflow-patterns`. | Global | TA-82205 country_invoice |
| R227 | **Write Guard Pattern** — Bloqueo de escritura vía `write()` override en AMBOS modelos (padre e hijo). El guard en el padre previene bypass vía `move.write({'line_ids': [(1, id, vals)]})`; el guard en el hijo previene bypass vía wizards/RPC directos. Usar context key `__approval_write__` para bypass del sistema. El guard DEBE examinar TODAS las operaciones Command (op=0 a op=6): op=0 (CREATE con locked field), op=1 (UPDATE con locked field), op=2/3 (DELETE/UNLINK remueven línea), op=5/6 (CLEAR/SET reemplazan todas las líneas). Ver R233 para detalle completo. Skill: `odoo-approval-workflow-patterns` Pattern 4-5. | Global | TA-82205 country_invoice |
| R228 | **Dual Notification Pattern** — Notificaciones que DEBEN llegar por AMBOS canales (Discuss inbox + email). Usar `message_notify()` para el canal preferido, luego `mail.message.create()` + `_notify_thread_by_inbox()`/`_notify_thread_by_email()` para forzar el otro canal. NUNCA usar `message_post()` para el follow-up (colisiona con auto-notificación de followers). Subtype `mt_note` para que nunca llegue al cliente. Skill: `odoo-dual-notification-patterns`. | Global | TA-82205 country_invoice |
| R229 | **Customer Exclusion en Notificaciones** — El partner externo (cliente) NUNCA debe recibir notificaciones de flujos internos (aprobaciones, cambios de estado, etc.). Tres capas de protección: (1) `message_notify()` solo con partners de usuarios internos, (2) `mt_note` subtype en follow-up messages, (3) `message_post()` sin `partner_ids`. Verificar con query SQL que el customer partner tiene 0 notificaciones en `mail_notification`. Skill: `odoo-dual-notification-patterns`. | Global | TA-82205 country_invoice |
| R230 | **mail.activity Lifecycle** — Para flujos con múltiples aprobadores: schedule UNA activity POR aprobador (cada uno ve su to-do), close TODAS las activities **del tipo aprobación** en approve/reject con `action_done()` (NO `action_unlink()`). **SIEMPRE filtrar por `activity_type_id`** en el dominio de búsqueda — sin este filtro, se cierran activities no relacionadas (meetings, calls, etc.) que existan en el mismo registro. Activity type: `mail.mail_activity_data_todo` (o el custom definido para el flujo de aprobación). Las activities complementan las notificaciones: son visibles en el Dashboard sin importar el `notification_type` del usuario. Skill: `odoo-approval-workflow-patterns` Pattern 10. | Global | TA-82205 country_invoice |
| R231 | **Dual Delivery Verification** — Para verificar que la notificación dual funciona: query `mail_notification` agrupando por `notification_type` por cada `mail_message_id`. Cada usuario interno DEBE tener exactamente 2 rows (inbox + email). Customer partner DEBE tener 0 rows. Subtype de los messages DEBE ser `mt_note` o `NULL`. Usar `docker exec db-pg16 psql` o el MCP `postgres-db` para verificación. Skill: `odoo-dual-notification-patterns` Verification Queries. | Global | TA-82205 country_invoice |
| R232 | **Bashrc Modification Safety** — CUALQUIER modificación programática de `~/.bashrc` (sed, awk, manual) DEBE seguir el patrón: (1) backup con timestamp (`cp "$BASHRC" "${BASHRC}.bak.$(date +%s)"`), (2) sed con pattern exacto (`^export VAR=`), (3) validación post-write con `grep -q`, (4) restore automático si falla. NUNCA ejecutar durante sesión interactiva (solo systemd/service). Nunca loggear valores completos de variables sensibles (API keys, passwords) — usar `${VAR: -8}` para masking. Skill: `devops-systemd-tooling`. | Global | odoo-apikey-renewal |
| R233 | **Write Guard Command Completeness** — Todo guard de escritura en x2many que valide campos bloqueados DEBE examinar TODAS las 7 operaciones Command (op=0 a op=6), no solo op=1 (UPDATE). Un guard que solo chequea op=1 se bypasea con: op=0 (CREATE con valor bloqueado), op=2 (DELETE remueve la línea con precio), op=5 (CLEAR reemplaza todas las líneas), op=6 (SET reemplaza todas las líneas). La función `_line_commands_touch_locked_field()` o equivalente DEBE iterar cada tupla de comando y verificar: op=0 → chequear `vals` por campos bloqueados; op=1 → chequear `vals`; op=2/3 → la línea eliminada tenía el campo bloqueado; op=5/6 → tratar como DELETE-all + CREATE-all. Skill: `odoo-approval-workflow-patterns` Pattern 4. | Global | PR #254 country_invoice |
| R234 | **reply_to=False con message_type no-thread** — Al crear `mail.message` directamente via `mail.message.create()` (NO `message_post()`) con `message_type` igual a `"user_notification"` o cualquier tipo no-thread, DEBE pasar `reply_to=False` explícitamente. `is_thread_message()` retorna False para tipos no-thread, causando que `_get_reply_to()` produzca un recordset vacío y lance `KeyError` al indexar `[res_id]`. El patrón dual-channel (`odoo-dual-notification-patterns`) con `message_type="notification"` (que SÍ es thread type) NO se afecta. Aplica a cualquier `mail.message.create()` custom con `message_type` fuera de `("notification", "comment")`. Skill: `odoo-dual-notification-patterns`. | Global | PR #254 country_invoice |
| R250 | **Odoo 19: type='product' eliminado** — En Odoo 19, `type='product'` ya NO existe. Tipos válidos: `consu` (Bienes), `service`, `combo`. Para productos almacenableables usar `type='consu'` + `is_storable=True` explícito al crear. El stock quant constraint verifica `product_id.is_storable`, NO `type='product'`. Tests que creen productos con stock DEBEN usar este patrón. `is_storable` default es `False` — el compute solo lo resetea a False para tipos no-consu, NO lo pone en True. Skill: `odoo-19-breaking-changes-checklist`. | Global | PR #2850 binaural_product_catalog |
| R251 | **Paridad de métodos de exportación en bridges** — Cuando el core define múltiples métodos de exportación/acción (PDF, XLS, etc.) y los puentes usan hook methods, verificar que TODOS los métodos reciban los mismos datos resueltos. Un puente que sobreescribe `_get_filter_product_sets()` resuelve productos para `print_report()` pero `print_report_xls()` puede no invocar la resolución. Patrón: si el core tiene `print_report()` + `print_report_xls()`, ambos DEBEN llamar `_resolve_products_from_filters()` cuando `product_ids` está vacío. Skill: `odoo-bridge-module-independence-19.0`. | Global | PR #2850 binaural_product_catalog |
| R252 | **Multi-company: búsquedas ORM con company_id** — Búsquedas ORM sobre modelos con campo `company_id` DEBEN incluir `('company_id', 'in', [self.env.company.id, False])` para backward compat con registros legacy sin company_id (NULL). Aplica a `stock.quant`, `product.catalog`, `ir.property`, y cualquier modelo multi-compañía. El patrón `[False, company_id]` es consistente con las record rules de Odoo (`multi_company_rules.xml`). Skill: `binaural-product-catalog-19.0`. | Global | PR #2850 binaural_product_catalog |
| R253 | **TransientModel: limitations de wizard_snapshot** — Los wizards TransientModel son vacuumed por sesión. `wizard_snapshot` (JSON) captura el estado completo para regeneración. Si un modelo base (ej. `product.catalog`) tiene `company_id` pero el wizard NO tiene ese campo, agregarlo requiere schema change (nuevo campo en el wizard). Mientras tanto, la búsqueda del wizard por `catalog_name` en `show_catalog()` NO puede filtrar por compañía — es una inconsistencia conocida de bajo riesgo (wizards son session-scoped, snapshot carry full state). Skill: `binaural-product-catalog-19.0`. | Project | PR #2850 binaural_product_catalog |

### Infrastructure Maintenance Rules (R254-R259)

| # | Regla | Scope | Fuente |
|---|-------|-------|--------|
| R254 | **Docker orphan detection via instances.json** — `instances.json` es la source of truth. Cualquier imagen Docker cuyo nombre NO matchee una instancia definida (pattern: `<instance_name>:<odoo_version>`) es huérfana y DEBE eliminarse. Volúmenes huérfanos siguen el pattern `docker-multi_<instance>-{data,py,py3,web}`. Antes de eliminar, verificar con `docker ps -a` que no haya contenedores stopped usando esa imagen. Skill: `docker-filesystem-cleanup`. | Global | Limpieza 133GB session |
| R255 | **custom/ orphan detection** — Directorios en `src/custom/` que NO tienen entrada correspondiente en `instances.json` son huérfanos. Clasificar antes de eliminar: (1) repos clonados sin instance → verificar si son source de alguna instance, (2) directorios vacíos o sin `.git` → eliminar, (3) worktrees de PRs cerrados → eliminar. Directorios con `__pycache__` owned by root requieren `sudo rm -rf`. Skill: `docker-filesystem-cleanup`. | Global | 23 directorios eliminados |
| R256 | **Filesystem cache cleanup hierarchy** — Limpiar en orden de mayor a menor impacto: (1) `.cache/uv/archive-v0/` (~19G, Python cache), (2) `.cache/codebase-memory-mcp/` (~7.6G, re-indexable), (3) `Downloads/*.zip` (~7.4G, backups temporales), (4) `.cache/ms-playwright/` (~1.3G, requiere reinstalación), (5) `.cache/google-chrome/` + `.cache/mozilla/` (~2.1G, browser cache), (6) `.local/share/claude/versions/` (~893M, old CLI), (7) `.npm/` (~1.5G, `npm cache clean --force`). NUNCA eliminar `~/.claude/skills/`, `~/.claude/agents/`, ni `~/.local/share/fonts/`. Skill: `docker-filesystem-cleanup`. | Global | Limpieza 70GB filesystem |
| R257 | **Playwright reinstall after cache purge** — Si se limpió `.cache/ms-playwright/`, DEBE ejecutarse `npx playwright install --with-deps chromium firefox webkit` para restaurar navegadores. Sin esto, Playwright MCP (`--browser=chrome --executable-path=/usr/bin/google-chrome-stable`) y tests E2E fallan silenciosamente. Verificar con `npx playwright --version` y `ls ~/.cache/ms-playwright/` post-reinstall. Skill: `docker-filesystem-cleanup`. | Global | Post-purge verification |
| R258 | **Disk space monitoring thresholds** — Monitorear `/home` partition periódicamente: <70% OK, 70-85% WARNING (revisar Downloads/.cache), 85-95% CRITICAL (ejecutar limpieza completa), >95% EMERGENCY (todo + considerar eliminar `docker-odoo/` si existe como directorio alternativo de ~6.9G). Usar `df -h /home` y `du -h --max-depth=1 ~/ 2>/dev/null | sort -rh | head -10`. Skill: `docker-filesystem-cleanup`. | Global | Monitoreo preventivo |
| R259 | **Stale docker-compose.generated.yml** — `docker-compose.generated.yml` en la raíz del workspace es generado por `./odoo build` y puede quedar stale referenciando instancias eliminadas. Si `instances.json` cambió y el compose no se regeneró, el compose puede causar confusiones al revisar el estado del sistema. Regenerar con `./odoo build` o eliminar manualmente si no se usa. Skill: `docker-filesystem-cleanup`. | Global | Post-cleanup detection |

### OpenRAG & codebase-memory-mcp Rules (R260-R264)

| # | Regla | Scope | Fuente |
|---|-------|-------|--------|
| R260 | **OpenRAG MCP ingest tool BROKEN (HTTP 422)** — `openrag_openrag_ingest` retorna `{'type': 'missing', 'loc': ['body', 'file'], 'msg': 'Field required'}` sin importar el formato de input. El tool espera contenido de archivo como bytes, no paths. **Workaround**: usar script directo `cat file.md \| python3 /home/binlp011/openrag/scripts/ingest_document.py --text - --name "odoo-skills/<cat>/<name>"`. Skill: `openrag`. | Global | Session 2026-09-25 |
| R261 | **OpenRAG embedding model name MUST include `:latest`** — `ingest_document.py` línea 37 usa `EMBEDDING_MODEL = "nomic-embed-text"` (sin `:latest`) pero Ollama tiene `nomic-embed-text:latest`. Embeddings se almacenan en campo `chunk_embedding_nomic_embed_text` (float) en vez de `chunk_embedding_nomic_embed_text_latest` (knn_vector, jvector, 768). El backend registry solo reconoce `nomic-embed-text:latest` → `UnknownEmbeddingProvider` → search degradado a solo-texto. **Fix**: cambiar default en `ingest_document.py` a `nomic-embed-text:latest`, o pasar `--embedding-model nomic-embed-text:latest`. Para docs existentes: `update_by_query` para fix `embedding_model` + copiar vectores al campo knn correcto. Skill: `openrag-embedding-fix`. | Global | Session 2026-09-25 |
| R262 | **OpenRAG `_is_exact_token_query()` kills queries with numbers** — `search_service.py` función `_is_exact_token_query()` retorna `True` para CUALQUIER query con letras Y dígitos. Queries con números de versión ("odoo 16 core ORM") siempre retornan 0 resultados. **Fix**: agregar word-count guard (`len(words) > 4` → False). Archivo: `/home/binlp011/openrag/src/services/search_service.py:27-42`, copiar a container vía `docker cp` + restart. Skill: `openrag-embedding-fix`. | Global | Session 2026-09-25 |
| R263 | **OpenRAG backend source NOT volume-mounted** — `/app/src/` en el container está baked into la imagen. Para aplicar cambios de código: (1) editar en host `/home/binlp011/openrag/src/`, (2) `docker cp` al container, (3) `docker restart openrag-backend`. Los cambios NO persisten en recreación del container. Skill: `openrag`. | Global | Session 2026-09-25 |
| R264 | **codebase-memory-mcp: 22 repos indexados across 16.0-19.0** — Repos indexados: integra-addons-{16.0,17.0,18.0,19.0}, integra-addons-l10nve-{17.0,18.0}, integra-addons-maintenance-{17.0,19.0,l10nve_17.0}, odoo-venezuela-{16.0,17.0,18.0,19.0}, odoo-venezuela-maintenance-{17.0,19.0}, third-party-addons-{16.0,17.0,18.0,19.0} + 3 worktrees. Project IDs: `home-binlp011-sources-<repo-name>`. Re-index after git pull: `codebase-memory-mcp cli detect_changes '{"project":"<name>"}'` then `index_repository` if changed_count > 0. Skills `codebase-memory-mcp-usage` para referencia completa. | Global | Session 2026-09-25 |
