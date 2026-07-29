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
    ├── reports/coverage/              ← Reportes de coverage
    └── .opencode/                     ← OpenCode config
        ├── agents/                    ← Agentes SDD (7 agentes)
        ├── skills/                    ← Skills del proyecto Odoo 19 base (14 skills)
        ├── commands/                  ← Comandos del proyecto (6 commands)
        ├── docs/                      ← Documentación Odoo 19 (654 .md)
        ├── plans/                     ← Planes de migración
        ├── goals/                     ← Goal tracking
        ├── 17.0/                      ← Skills y docs Odoo 17.0 (80 skills)
         ├── 19.0/                      ← Skills Odoo 19.0 (104 skills base + 20 nuevos = 124)
        ├── opencode.json              ← Config workspace (override global)
        └── package.json               ← Plugin dependencies (@opencode-ai/plugin)
```

## Odoo Version

**Versión principal: 19.0** — todos los skills y patrones usan Odoo 19 a menos que se indique explícitamente otra versión.

## Inventario General

| Categoría | Cantidad |
|-----------|----------|
| skills/19.0/skills/ (99 skills base + 20 nuevos) | **119** |
| skills/.opencode/skills/ (19.0 base + OpenRAG) | 43 |
| **Total skills 19.0** | **162** |
| skills/17.0/skills/ (160 skills) | 160 |
| skills/global (~/.config/opencode/skills/) | ~116 |
| **TOTAL WORKSPACE** | **358** |
| Archivos documentación (.opencode/docs/) | 647 |
| Chunks indexados en OpenSearch | ~2,211 |

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
| `odoo-performance-19` | Performance: N+1, batch-first, indexes |
| `odoo-code-review-19.0` | Code review checklist (41 rules incl. recordset safety, scope creep, security, dead assets, start() lifecycle, ES2020, RPC error handling, focus restoration) |
| `odoo-context-keys-19` | **NUEVO** — Context keys: warehouse_id, location, stock filtering |

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
| `cadipa-sale-suscription-payment` | **NUEVO** — Portal payment flow + VES conversion + l10n_ve bug fix para cadipa_sale_suscription |
| `binaural-stock-barcode` | Barcode picking con fake lines |

### Workflows (`.opencode/skills/`)

| Skill | Descripción |
|-------|-------------|
| `coverage-workflow` | Ejecutar, analizar y mejorar cobertura |
| `sdd-workflow` | Spec-Driven Development: spec → plan → tasks |
| `odoo-testing-workflow` | Flujo de tests Odoo |
| `workspace-structure` | Estructura del workspace, pre-commit, instancias |
| `guia_precommit_odoo` | **NUEVO** — Guía completa del sistema pre-commit: script, hooks, troubleshooting |
| `openrag` | OpenRAG RAG: ingestión, búsqueda semántica, chat MCP |

### Globales (`~/.config/opencode/skills/`)

| Skill | Descripción |
|-------|-------------|
| `git-workflow` | **NUEVO** — Branch strategy, cherry-pick, separación de ramas, verificación post-cherry-pick |

### SDD Multi-Agent System (`.opencode/skills/`)

| Skill | Agente | Responsabilidad |
|-------|--------|-----------------|
| `sdd-lead-agent` | Lead | Orquestación, detección versión, quality gates, escalación |
| `sdd-explore-agent` | Explore | Investigación read-only: patrones, relaciones, contexto |
| `sdd-spec-agent` | Spec | Crear spec.md con requisitos EARS |
| `sdd-architect-agent` | Architect | Crear plan.md con research de codebase |
| `sdd-pm-agent` | PM | Crear tasks.md con trazabilidad EARS |
| `sdd-builder-agent` | Builder | Implementar código con TDD + worktree |
| `sdd-qc-agent` | QC | Verificar calidad, qc-report.md, FAIL→BUG loop |

**Flujo**: Lead → Explore → Spec → Architect → Explore → PM → Builder → Explore → QC → Lead (cierre)
**Versiones**: 19.0 (principal) + 17.0 (secundario) — detectado de `__manifest__.py`

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
| `odoo-code-review-17.0` | Checklist code review (FIX-001 a FIX-036) |
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

### Referencia Global (`~/.config/opencode/skills/`)

| Skill | Relevancia para Odoo 19 |
|-------|------------------------|
| `translation-i18n-patterns` | **ACTUALIZADO** — incluye JS `_t()` transpiler, QWeb templates |
| `qweb-template-patterns` | QWeb server-side syntax |
| `assets-bundling-patterns` | Asset bundles, SCSS, lazy loading |
| `guia_precommit_odoo` | Guía de pre-commit para módulos |
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
- **Skills indexados**: 324 skills, 2,211 chunks en OpenSearch
- **Ver skill**: `openrag`

### Postgres-DB MCP
- **Config**: `~/.config/opencode/opencode.jsonc` como `type: "local"`
- **Tools**: query, execute, list_databases, list_tables, describe_table, search_tables, explain
- **DB URL**: `postgresql://odoo:odoo@localhost:5432/`

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

## Plugins (opencode.jsonc)

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
