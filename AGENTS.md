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
        ├── skills/                    ← Skills del proyecto (30 skills)
        ├── commands/                  ← Comandos del proyecto (6 commands)
        ├── docs/                      ← Documentación Odoo 19 (654 .md)
        ├── plans/                     ← Planes de migración
        ├── goals/                     ← Goal tracking
        ├── 17.0/                      ← Skills y docs Odoo 17.0
        ├── opencode.json              ← Config workspace (override global)
        └── package.json               ← Plugin dependencies (@opencode-ai/plugin)
```

## Odoo Version

**Versión principal: 19.0** — todos los skills y patrones usan Odoo 19 a menos que se indique explícitamente otra versión.

## Skills del Proyecto

### Core Odoo 19 (`.opencode/skills/`)

| Skill | Descripción |
|-------|-------------|
| `odoo_owl_backend-19.0` | OWL backend: views, components, registry, 92 widgets |
| `odoo_owl_website-19.0` | OWL website: interactions, builder, e-commerce, themes |
| `odoo-owl-frontend-templates-19.0` | **NUEVO** — Templates OWL en `static/src/xml/`, `renderToString()`, module context |
| `odoo_orm_backend-19.0` | ORM: BaseModel, fields, Domain, Command, cache |
| `odoo_security_api_ai-19.0` | Security: XSS, SQL injection, auth, access control |
| `odoo_reports_papermuncher-19.0` | PDF reports: Flexbox, QWeb, barcodes, watermarking |
| `odoo_tools_core-19.0` | Core tools: SQL, safe_eval, cache, config, translate |
| `odoo_documentation-19.0` | Full Odoo 19 docs (654 files) |
| `odoo_devops-19.0` | Module system, CLI, deployment, DB management |
| `odoo-migration-19` | Migration guide 17→19 (45 lessons) |
| `odoo-performance-19` | Performance: N+1, batch-first, indexes |
| `odoo-code-review-19.0` | Code review checklist (36 rules incl. recordset safety, scope creep, security) |
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
| `binaural-stock-barcode` | Barcode picking con fake lines |

### Workflows (`.opencode/skills/`)

| Skill | Descripción |
|-------|-------------|
| `coverage-workflow` | Ejecutar, analizar y mejorar cobertura |
| `sdd-workflow` | Spec-Driven Development: spec → plan → tasks |
| `odoo-testing-workflow` | Flujo de tests Odoo |
| `workspace-structure` | Estructura del workspace, pre-commit, instancias |

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

## Plugins (opencode.jsonc)

| Plugin | Propósito |
|--------|-----------|
| `@tarquinen/opencode-dcp` | Disciplined Code Process |
| `WakaTime` | Time tracking de desarrollo |
| `websearch-cited` | Web search con citas |
| `opencode-conductor-plugin` | Metodología Conductor (tracks, workflow) |
| `opencode-goal-plugin` | Goal tracking y seguimiento |
| `md-table-formatter` | Formateo de tablas Markdown |

## Conductor Methodology

Agente global `conductor` (mode: primary) con metodología alternativa al SDD:
- `~/.config/opencode/agent/conductor.md` — Definición del agente
- `src/conductor/` — Product definition, tracks, workflow, tech stack

**Diferencia con SDD**: Conductor usa tracks/features management. SDD usa spec→plan→tasks.
Ambas metodologías coexisten. Elegir según el contexto del trabajo.
