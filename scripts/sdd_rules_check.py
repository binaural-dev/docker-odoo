#!/usr/bin/env python3
"""Indice de reglas de AGENTS.md con disposicion honesta por regla (P1-9).

Cada regla numerada de AGENTS.md recibe una disposicion:

  preserved             hay un oraculo en el repo (script, hook o config) que la hace cumplir
  intentional-difference la regla contradice otra regla o guardrail, y la contradiccion esta documentada
  bounded-external      el limite vive en un tercero (Odoo core/enterprise, Postgres, git, Docker)
  unknown               no se encontro evidencia de enforcement: la regla es prescriptiva

El indice vive en scripts/sdd-rules-index.json y se regenera con --write.
El gate (check) falla si el conjunto de reglas del indice no coincide con el de AGENTS.md,
si una evidencia declarada no existe en disco, si una regla "preserved" no declara evidencia
o si una regla "unknown" declara evidencia (seria una afirmacion sin respaldo).

Regla de honestidad: nunca se inventa enforcement. Un "unknown" es preferible a un
"preserved" sin oraculo real, y el reporte siempre cuenta los unknown.

Uso:
  python3 scripts/sdd_rules_check.py            # reporta el estado del gate
  python3 scripts/sdd_rules_check.py --write    # regenera scripts/sdd-rules-index.json
  python3 scripts/sdd_rules_check.py --strict   # ademas falla si hay reglas unknown
  python3 scripts/sdd_rules_check.py --verbose  # ademas lista las reglas por disposicion
"""

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = "AGENTS.md"
INDEX = "scripts/sdd-rules-index.json"
SCHEMA = "sdd-rules-index/v1"

PRESERVED = "preserved"
DIFFERENCE = "intentional-difference"
EXTERNAL = "bounded-external"
UNKNOWN = "unknown"

DISPOSITIONS = [PRESERVED, DIFFERENCE, EXTERNAL, UNKNOWN]

# --------------------------------------------------------------------------------------
# Oraculos de enforcement (todos verificados en disco antes de citarlos)
# --------------------------------------------------------------------------------------
GUARDRAILS = "scripts/sdd-guardrails.json"
TOOL_GUARD = "scripts/sdd_tool_guard.py"
PRECOMMIT = "scripts/precommit"
RUNNER = "scripts/sdd_opencode_run.sh"
WAITER = "scripts/sdd_opencode_wait.sh"
STATUS = "scripts/sdd_opencode_status.sh"
ODOO_CMD_GUARD = "scripts/sdd_odoo_cmd_guard.sh"
GUARD_PLUGIN = "scripts/opencode-plugins/sdd-odoo-guard.js"
VERDICT_GATE = "scripts/sdd_verdict_gate.sh"
GIT_HOOK = "scripts/sdd_install_git_hook.sh"
INVENTORY = "scripts/sdd_inventory_check.py"
TREE_PROOF = "scripts/sdd_tree_proof.sh"
JUDGE_EVENT = "scripts/sdd_judge_event.sh"
TOKEN_USAGE = "scripts/sdd_token_usage.py"
MODEL_SWITCH = "scripts/opencode_model_switch.sh"
CONFIG_SYNC = "scripts/sdd_opencode_config_sync_check.sh"
ODOO_UPDATE = "scripts/odoo-update"
ODOO_SHELL = "scripts/odoo-shell"
ODOO_TEST = "scripts/odoo-test"
RUN_TESTS = "scripts/run_tests.sh"
COVERAGE = "scripts/coverage"
SKILL_SYNC = "src/scripts/skill-sync-daemon.sh"
AGENT_LEAD = "src/.opencode/agents/sdd-lead.md"
OPENCODE_JSON = "src/.opencode/opencode.json"
ODOO_CLI = "odoo"
DOCKER_COMPOSE = "docker-compose.generated.yml"

ORM_MODELS = "src/odoo-19.0/odoo/orm/models.py"
ORM_FIELDS = "src/odoo-19.0/odoo/orm/fields.py"
ORM_DOMAINS = "src/odoo-19.0/odoo/orm/domains.py"
ORM_ENV = "src/odoo-19.0/odoo/orm/environments.py"
ORM_REGISTRY = "src/odoo-19.0/odoo/orm/registry.py"
TOOLS_TRANSLATE = "src/odoo-19.0/odoo/tools/translate.py"
TOOLS_MAIL = "src/odoo-19.0/odoo/tools/mail.py"
TOOLS_SAFE_EVAL = "src/odoo-19.0/odoo/tools/safe_eval.py"
TOOLS_TEMPLATE = "src/odoo-19.0/odoo/tools/template_inheritance.py"
TOOLS_VIEW_VAL = "src/odoo-19.0/odoo/tools/view_validation.py"
TOOLS_CONFIG = "src/odoo-19.0/odoo/tools/config.py"
TOOLS_JSTRANS = "src/odoo-19.0/odoo/tools/js_transpiler.py"
HTTP = "src/odoo-19.0/odoo/http.py"
SQL_DB = "src/odoo-19.0/odoo/sql_db.py"
LOADING = "src/odoo-19.0/odoo/modules/loading.py"
MIGRATION = "src/odoo-19.0/odoo/modules/migration.py"
RES_COMPANY = "src/odoo-19.0/odoo/addons/base/models/res_company.py"
RES_CURRENCY = "src/odoo-19.0/odoo/addons/base/models/res_currency.py"
ADDON_ACCOUNT_MOVE = "src/odoo-19.0/addons/account/models/account_move.py"
ADDON_STOCK_MOVE = "src/odoo-19.0/addons/stock/models/stock_move.py"
ADDON_MAIL_THREAD = "src/odoo-19.0/addons/mail/models/mail_thread.py"
ADDON_PRODUCT_TPL = "src/odoo-19.0/addons/product/models/product_template.py"
ADDON_PAYMENT_TXN = "src/odoo-19.0/addons/payment/models/payment_transaction.py"
ADDON_SALE_ORDER = "src/odoo-19.0/addons/sale/models/sale_order.py"
ADDON_WEB_MAIN = "src/odoo-19.0/addons/web/controllers/main.py"
WEB_CLASS_JS = "src/odoo-19.0/addons/web/static/src/legacy/js/core/class.js"
POS_PRODUCT_TPL = "src/odoo-19.0/addons/point_of_sale/static/src/app/models/product_template.js"

# --------------------------------------------------------------------------------------
# Clasificacion curada: numero de regla -> (disposicion, evidencia, razon)
# Lo que no aparece aqui queda "unknown" sin evidencia (regla prescriptiva, sin oraculo).
# La evidencia de varias rutas se separa con " + " (cada parte se verifica en disco).
# --------------------------------------------------------------------------------------
CLASSIFY = {
    321: (PRESERVED, "scripts/engram-env.sh + scripts/sdd_memory_common.py + scripts/sdd_memory_capture.py + scripts/opencode-plugins/sdd-memory.js + scripts/hooks/engram_claude_hook.py", "redaccion, lista blanca de cabeceras, plugin con lista de agentes y hooks; pruebas en scripts/test_sdd_memory_*.py"),
    3: (EXTERNAL, TOOLS_JSTRANS, "el transpilador JS de Odoo 19 es el que procesa `_t()`."),
    5: (PRESERVED, PRECOMMIT, ""),
    12: (
        EXTERNAL,
        ADDON_STOCK_MOVE,
        "`move_ids_without_package` ya no existe en Odoo 19; la API del core es el oraculo.",
    ),
    13: (EXTERNAL, TOOLS_CONFIG, "`config.get_param()` devuelve strings por contrato del core."),
    15: (EXTERNAL, TOOLS_MAIL, "el saneo de HTML vive en `odoo.tools.mail` del core."),
    24: (EXTERNAL, ORM_REGISTRY, "el Registry es singleton del core (`odoo.orm.registry`)."),
    25: (EXTERNAL, ORM_MODELS, "MetaField/`_build_model` son del core."),
    27: (EXTERNAL, ORM_MODELS, "los mixins (`mail.thread`, `portal.mixin`) son adapters del core."),
    28: (EXTERNAL, ORM_MODELS, "la cadena de `_inherit` la resuelve el core."),
    29: (EXTERNAL, ORM_ENV, "el apilado de proxies (`sudo`, `with_company`) lo implementa `Environment` del core."),
    30: (EXTERNAL, ORM_DOMAINS, "`expression.AND/OR` pertenece al core."),
    31: (EXTERNAL, ORM_MODELS, "MetaModel es el bridge del core."),
    32: (EXTERNAL, ORM_FIELDS, "el trigger tree de recomputacion vive en el core."),
    33: (EXTERNAL, ORM_MODELS, "`Command` es la API del core."),
    35: (EXTERNAL, TOOLS_TEMPLATE, "`locate_node()` del core solo afecta el primer match."),
    44: (EXTERNAL, HTTP, "`ir.http` y el dispatcher HTTP son del core."),
    46: (PRESERVED, GUARDRAILS + " + " + TOOL_GUARD, ""),
    58: (EXTERNAL, TOOLS_TEMPLATE, "`locate_node()` del core devuelve solo el primer nodo."),
    62: (EXTERNAL, ORM_MODELS, "la invalidacion de cache es del core (`Environment.invalidate_*`)."),
    64: (EXTERNAL, ORM_MODELS, "`@api.constrains` es triggered-only por diseno del core."),
    65: (
        EXTERNAL,
        TOOLS_TEMPLATE,
        "el primer match de `locate_node()` es del core; los selectores XPath son del modulo.",
    ),
    69: (EXTERNAL, ORM_MODELS, "`@api.model_create_multi` es la API del core."),
    70: (EXTERNAL, SQL_DB, "los savepoints los implementa `odoo.sql_db`."),
    74: (EXTERNAL, ORM_FIELDS, "`depends_context` y `cache_key` son del core."),
    75: (EXTERNAL, ORM_FIELDS, "las context keys validas las define el core."),
    76: (EXTERNAL, TOOLS_SAFE_EVAL, "`has_group()` no esta entre los builtins de `safe_eval` del core."),
    80: (EXTERNAL, ADDON_ACCOUNT_MOVE, "la tabla M2M de transacciones la crea el modulo `account` del core."),
    81: (PRESERVED, RUN_TESTS, ""),
    85: (EXTERNAL, ORM_MODELS, "`copy()` del core pasa por `copy_data()` -> `create()`."),
    88: (EXTERNAL, ADDON_PRODUCT_TPL, "el constraint de combo vive en `product` del core."),
    89: (EXTERNAL, ORM_MODELS, "el contexto propagado en `create()` es del core."),
    94: (EXTERNAL, ORM_FIELDS, "`related` es un string punteado en el core."),
    97: (PRESERVED, COVERAGE, ""),
    98: (EXTERNAL, LOADING, "la semantica de `-i`/`-u` la implementa el cargador del core."),
    99: (PRESERVED, COVERAGE, ""),
    108: (EXTERNAL, RES_COMPANY, "`res.company.parent_id` es inmutable en el core."),
    115: (EXTERNAL, ADDON_WEB_MAIN, "el decorador `@http.route` y sus kwargs son del core."),
    116: (PRESERVED, ODOO_TEST, ""),
    125: (PRESERVED, SKILL_SYNC, ""),
    129: (PRESERVED, SKILL_SYNC, ""),
    133: (PRESERVED, RUN_TESTS, ""),
    134: (PRESERVED, ODOO_SHELL, ""),
    138: (PRESERVED, RUN_TESTS, ""),
    143: (EXTERNAL, TOOLS_TRANSLATE, "el exportador de i18n del core omite `msgstr` cuando coincide con el `msgid`."),
    145: (EXTERNAL, ADDON_PAYMENT_TXN, "`payment_method_id` es required en el modelo del core."),
    146: (EXTERNAL, ADDON_PAYMENT_TXN, "`provider_ids` es M2M en el modelo del core."),
    148: (EXTERNAL, ADDON_ACCOUNT_MOVE, "`account.move.name` es el campo del core; `move_name` no existe."),
    152: (EXTERNAL, TOOLS_TRANSLATE, "las etiquetas traducidas dependen del locale cargado por el core."),
    153: (EXTERNAL, HTTP, "el contrato de `Response.load()` es del core."),
    154: (
        EXTERNAL,
        TOOLS_TEMPLATE,
        "`arch_db` es un campo traducido por idioma; el core combina vistas con el arch del idioma activo.",
    ),
    155: (PRESERVED, AGENT_LEAD, ""),
    156: (PRESERVED, RUNNER, ""),
    157: (PRESERVED, AGENT_LEAD, ""),
    158: (PRESERVED, GUARDRAILS, ""),
    159: (PRESERVED, RUNNER, ""),
    167: (
        PRESERVED,
        ODOO_CMD_GUARD + " + " + GUARD_PLUGIN + " + " + GUARDRAILS,
        "scripts/sdd_odoo_cmd_guard.sh:99-107 rechaza un `-d` igual a una instancia/BD real de instances.json "
        "(exit 1 en :107); scripts/opencode-plugins/sdd-odoo-guard.js:11-17 lo invoca en tool.execute.before y "
        "lanza error si el exit no es 0; scripts/sdd-guardrails.json:25-26 carga ese plugin. Alcance: solo runtime "
        "OpenCode (.claude/settings.json no lo invoca) y solo el binario `odoo -d`, no `./odoo test`.",
    ),
    172: (
        PRESERVED,
        STATUS,
        "el script de estado puede devolver la cache del job anterior: la regla vive en el script del repo.",
    ),
    175: (PRESERVED, RUNNER, ""),
    176: (
        DIFFERENCE,
        GUARDRAILS,
        "el protocolo exige `psql` (`CREATE DATABASE ... WITH TEMPLATE`) pero `scripts/sdd-guardrails.json` "
        "deniega `psql`: contradiccion documentada, se acepta el gap.",
    ),
    177: (PRESERVED, RUNNER, ""),
    178: (PRESERVED, GUARDRAILS, ""),
    179: (PRESERVED, AGENT_LEAD, ""),
    180: (PRESERVED, AGENT_LEAD, ""),
    181: (PRESERVED, WAITER, ""),
    182: (EXTERNAL, TOOLS_VIEW_VAL, "la validacion de `groups=` en vista es del core."),
    183: (
        EXTERNAL,
        ADDON_SALE_ORDER,
        "`sale.order._prepare_invoice()` es del core y copia `transaction_ids` sin filtro.",
    ),
    188: (
        EXTERNAL,
        DOCKER_COMPOSE,
        "db-pg16 no publica puerto al host en el compose generado (docker-compose.generated.yml:5-20); "
        "la conexion del MCP es frontera Docker/Postgres.",
    ),
    189: (PRESERVED, WAITER, ""),
    191: (PRESERVED, RUNNER, ""),
    192: (PRESERVED, RUNNER, ""),
    193: (PRESERVED, AGENT_LEAD, ""),
    194: (PRESERVED, RUNNER, ""),
    195: (PRESERVED, OPENCODE_JSON, ""),
    198: (EXTERNAL, MIGRATION, "los scripts de migracion solo corren en upgrade; `post_init_hook` es del core."),
    199: (EXTERNAL, MIGRATION, "el disparo de los scripts de migracion lo decide el core."),
    200: (EXTERNAL, RES_COMPANY, "`install_l10n_modules()` del core dispara la localizacion al crear la compania."),
    201: (
        EXTERNAL,
        ODOO_CLI,
        "el owner root del filestore lo fija Docker al correr el binario como root; la mitigacion es "
        "`./odoo fix-files` (odoo:1613-1614), fuera del control del indice.",
    ),
    203: (EXTERNAL, WEB_CLASS_JS,"el mixin `Class.include()` y `_super` son del frontend web del core."),
    205: (PRESERVED, GUARDRAILS, ""),
    207: (EXTERNAL, POS_PRODUCT_TPL, "el split `ProductTemplate`/`ProductProduct` y `getPrice` son del core del POS."),
    208: (PRESERVED, RUNNER, ""),
    210: (PRESERVED, SKILL_SYNC, ""),
    213: (PRESERVED, PRECOMMIT, ""),
    214: (PRESERVED, SKILL_SYNC, ""),
    217: (
        EXTERNAL,
        ".pylintrc-mandatory",
        "solo exigible donde pylint_odoo activa `translation-not-lazy`: verificado con pylint_odoo 9.1.3 "
        "que con la config 17.0 se reporta W8301 y con la 19.0 (`valid-odoo-versions=19.0`) no se reporta "
        "nada, asi que en 19.0 no hay gate mecanico. Misma salvedad para except-pass, "
        "method-required-super y test-folder-imported, aunque ninguna otra regla del indice depende de ellos.",
    ),
    222: (EXTERNAL, ADDON_MAIL_THREAD, "el dominio de `message_ids` excluye `user_notification` por diseno del core."),
    224: (
        EXTERNAL,
        DOCKER_COMPOSE,
        "el daemon Docker lo gestiona el host; la contencion por sesiones concurrentes no es verificable en el repo.",
    ),
    225: (PRESERVED, PRECOMMIT, ""),
    226: (PRESERVED, PRECOMMIT, ""),
    237: (EXTERNAL, LOADING, "el purgado de huerfanos (`_process_end`) es del core."),
    238: (EXTERNAL, LOADING, "el commit por modulo durante `-u` es del core."),
    239: (PRESERVED, ODOO_UPDATE, ""),
    246: (EXTERNAL, TOOLS_TRANSLATE, "`_load_module_terms(..., overwrite=True)` es del core."),
    247: (PRESERVED, RUNNER, ""),
    250: (EXTERNAL, RES_CURRENCY, "`res.currency._convert()` es la API del core."),
    253: (EXTERNAL, ORM_MODELS, "`_get_product_price()` es kwargs-only en el core."),
    258: (EXTERNAL, ORM_FIELDS, "el chequeo de acceso a campo (`check_field_access_rights`) es del core."),
    261: (
        EXTERNAL,
        ODOO_CLI,
        "los roles y el CONNECT de Postgres son del servidor; `./odoo provision-role` (odoo:110-116) los aplica "
        "y el mensaje de error de la instancia lo sugiere (odoo:170).",
    ),
    264: (PRESERVED, PRECOMMIT, ""),
    265: (PRESERVED, PRECOMMIT, ""),
    271: (PRESERVED, COVERAGE, ""),
    274: (PRESERVED, MODEL_SWITCH, ""),
    288: (PRESERVED, RUNNER, ""),
    294: (
        EXTERNAL,
        ODOO_CLI,
        "la caida por `role odoo is not permitted to log in` la produce el rol de Postgres en reposo; el CLI solo "
        "sugiere `provision-role` (odoo:170).",
    ),
    298: (PRESERVED, PRECOMMIT, ""),
    300: (PRESERVED, RUNNER, ""),
    301: (PRESERVED, GUARDRAILS + " + " + CONFIG_SYNC, ""),
    302: (PRESERVED, RUNNER, ""),
    303: (PRESERVED, JUDGE_EVENT + " + " + TOKEN_USAGE, ""),
    304: (PRESERVED, TOKEN_USAGE, ""),
    308: (PRESERVED, "scripts/sdd_inventory_check.py", ""),
    309: (PRESERVED, "scripts/sdd_rules_check.py", ""),
    311: (PRESERVED, "scripts/run_tests.sh + scripts/coverage", ""),
    315: (PRESERVED, "scripts/opencode-plugins/sdd-lean-ruleset.js + scripts/tests/test_sdd_lean_plugin.py", ""),
    316: (
        EXTERNAL,
        "scripts/tests/test_sdd_lean_plugin.py",
        "los hooks `experimental.*` dependen de la version de OpenCode; se reverifican al actualizar.",
    ),
    317: (PRESERVED, "scripts/sdd_inventory_check.py", ""),
}

RULE_RE = re.compile(r"^(\d+)\.\s+\*\*(.*)$")
HEADER_RE = re.compile(r"^(#{2,4})\s+(.*\S)\s*$")


def _rule_title(body):
    """Titulo de la regla.

    Algunos titulos de AGENTS.md cruzan varias lineas (el `**` de cierre queda en la
    linea siguiente), asi que se toma la primera linea del titulo sin exigir el cierre.
    """
    match = RULE_RE.match(body)
    if not match:
        return None
    title = match.group(2).strip()
    if title.endswith("**"):
        title = title[:-2].strip()
    return title


def _run(cmd, cwd=None):
    """Ejecuta un comando y devuelve su stdout (o "" si falla)."""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
    except OSError:
        return ""
    return proc.stdout if proc.returncode == 0 else ""


def _rule_lines(path):
    """Lineas de regla de AGENTS.md.

    Se leen con grep (el archivo supera los 100 KB) y, si grep no esta disponible,
    con un lector en streaming por lineas. Nunca se carga el archivo completo.
    """
    out = _run(["grep", "-nE", r"^[0-9]+\. \*\*", path])
    if out:
        rows = []
        for line in out.splitlines():
            # grep -n antepone "N:"; los titulos pueden contener ":" asi que se separa con regex.
            match = re.match(r"^(\d+):(.*)$", line)
            if not match:
                continue
            rows.append((int(match.group(1)), match.group(2)))
        return rows
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, body in enumerate(fh, 1):
            if _rule_title(body) is not None:
                rows.append((lineno, body.rstrip("\n")))
    return rows


def _header_lines(path):
    """Encabezados (familias) del documento con su numero de linea."""
    out = _run(["grep", "-nE", r"^#{2,4} ", path])
    rows = []
    if out:
        for line in out.splitlines():
            match = re.match(r"^(\d+):(.*)$", line)
            if not match:
                continue
            rows.append((int(match.group(1)), match.group(2)))
        return rows
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, body in enumerate(fh, 1):
            if HEADER_RE.match(body):
                rows.append((lineno, body.rstrip("\n")))
    return rows


def parse_rules(root=ROOT):
    """Devuelve (rules, gaps).

    rules: {numero: {"title", "family", "line"}} con la familia = encabezado mas cercano.
    gaps: numeros faltantes entre el minimo y el maximo de la numeracion.
    """
    agents = os.path.join(root, AGENTS)
    rules = {}
    if not os.path.exists(agents):
        return rules, []
    headers = _header_lines(agents)
    for lineno, body in _rule_lines(agents):
        title = _rule_title(body)
        match = RULE_RE.match(body)
        if title is None or match is None:
            continue
        num = int(match.group(1))
        family = ""
        for hline, hbody in headers:
            if hline < lineno:
                family = hbody.strip()
            else:
                break
        rules[num] = {
            "title": title,
            "family": family,
            "line": lineno,
        }
    if not rules:
        return rules, []
    numbers = sorted(rules)
    gaps = [n for n in range(numbers[0], numbers[-1] + 1) if n not in rules]
    return rules, gaps


def disposition_for(num):
    """Disposicion curada de una regla; unknown cuando no hay oraculo identificado."""
    return CLASSIFY.get(num, (UNKNOWN, "", ""))


def build_index(root=ROOT, previous=None):
    """Construye el indice completo a partir de AGENTS.md y la clasificacion curada.

    previous: indice anterior (dict). Sus clasificaciones manuales (disposicion distinta de
    unknown) para reglas que NO estan en CLASSIFY se conservan; CLASSIFY siempre gana.
    Sin esta conservacion, un --write pisaria cualquier edicion a mano del JSON.
    """
    rules, gaps = parse_rules(root)
    manual = (previous or {}).get("rules", {}) or {}
    entries = {}
    for num in sorted(rules):
        prev = manual.get(str(num), {})
        if num not in CLASSIFY and prev.get("disposition", UNKNOWN) != UNKNOWN:
            disp = prev.get("disposition")
            evidence = prev.get("evidence", "")
            reason = prev.get("reason", "")
        else:
            disp, evidence, reason = disposition_for(num)
        entries[str(num)] = {
            "disposition": disp,
            "evidence": evidence,
            "reason": reason,
            "family": rules[num]["family"],
            "title": rules[num]["title"],
        }
    counts = {d: 0 for d in DISPOSITIONS}
    for entry in entries.values():
        counts[entry["disposition"]] = counts.get(entry["disposition"], 0) + 1
    families = {}
    for num in sorted(rules):
        entry = entries[str(num)]
        fam = families.setdefault(
            entry["family"], {"rules": [], "dispositions": {}, "evidence": []}
        )
        fam["rules"].append(num)
        fam["dispositions"].setdefault(entry["disposition"], []).append(num)
        for part in _evidence_parts(entry["evidence"]):
            if part not in fam["evidence"]:
                fam["evidence"].append(part)
    for fam in families.values():
        fam["rules"].sort()
        fam["evidence"].sort()
        if len(fam["dispositions"]) == 1:
            fam["disposition"] = list(fam["dispositions"])[0]
        else:
            fam["disposition"] = "mixed"
    return {
        "schema": SCHEMA,
        "source": AGENTS,
        "generated_by": "scripts/sdd_rules_check.py",
        "dispositions": DISPOSITIONS,
        "counts": counts,
        "gaps": gaps,
        "families": families,
        "rules": entries,
    }


def _evidence_parts(evidence):
    """Parte una evidencia multiple separada por " + "."""
    return [p.strip() for p in (evidence or "").split(" + ") if p.strip()]


def write(root=ROOT):
    """Regenera scripts/sdd-rules-index.json."""
    path = os.path.join(root, INDEX)
    index = build_index(root, previous=load_index(root))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1, ensure_ascii=False, sort_keys=False)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n")
    print("wrote %s" % path)
    return index


def load_index(root=ROOT):
    path = os.path.join(root, INDEX)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def check(strict=False, verbose=False, root=ROOT):
    """Gate del indice. Devuelve 1 si hay falhas."""
    errs = []
    rules, gaps = parse_rules(root)
    index = load_index(root)
    if index is None:
        print("FAIL no existe %s (usa --write para generarlo)" % INDEX)
        return 1
    if index.get("schema") != SCHEMA:
        errs.append("schema invalido: %r (se espera %r)" % (index.get("schema"), SCHEMA))
    indexed = index.get("rules", {})
    parsed = set(rules)
    seen = set()
    for key in indexed:
        try:
            seen.add(int(key))
        except (TypeError, ValueError):
            errs.append("clave de regla no numerica: %r" % key)
    missing = sorted(parsed - seen)
    extra = sorted(seen - parsed)
    for num in missing:
        errs.append("regla %d presente en %s pero ausente del indice" % (num, AGENTS))
    for num in extra:
        errs.append("regla %d presente en el indice pero ausente de %s" % (num, AGENTS))
    counts = {d: 0 for d in DISPOSITIONS}
    for key in sorted(indexed, key=lambda k: int(k) if k.isdigit() else 0):
        entry = indexed[key]
        num = int(key)
        disp = entry.get("disposition")
        if disp not in DISPOSITIONS:
            errs.append("regla %d: disposicion invalida %r" % (num, disp))
            continue
        counts[disp] += 1
        evidence = (entry.get("evidence") or "").strip()
        reason = (entry.get("reason") or "").strip()
        parts = _evidence_parts(evidence)
        if disp == PRESERVED and not parts:
            errs.append("regla %d: 'preserved' exige evidencia" % num)
        if disp == UNKNOWN and parts:
            errs.append("regla %d: 'unknown' no puede declarar evidencia" % num)
        if disp != UNKNOWN and not parts:
            errs.append("regla %d: la disposicion %r exige evidencia" % (num, disp))
        if disp in (DIFFERENCE, EXTERNAL) and not reason:
            errs.append("regla %d: la disposicion %r exige razon" % (num, disp))
        for part in parts:
            if not os.path.exists(os.path.join(root, part)):
                errs.append("regla %d: la evidencia %r no existe en disco" % (num, part))
        if num in rules:
            if entry.get("title") != rules[num]["title"]:
                errs.append("regla %d: el titulo del indice no coincide con %s" % (num, AGENTS))
            if entry.get("family") != rules[num]["family"]:
                errs.append("regla %d: la familia del indice no coincide con %s" % (num, AGENTS))
    if list(index.get("gaps", [])) != gaps:
        errs.append("gaps del indice %r != gaps calculados %r" % (index.get("gaps"), gaps))
    if index.get("counts") != counts:
        errs.append("counts del indice %r != counts recalculados %r" % (index.get("counts"), counts))
    for err in errs:
        print("FAIL %s" % err)
    total = sum(counts.values())
    print("rules: %d total, gaps: %d" % (total, len(gaps)))
    for disp in DISPOSITIONS:
        print("%s: %d" % (disp, counts[disp]))
    if strict and counts[UNKNOWN] > 0:
        print("FAIL strict: %d reglas sin evidencia de enforcement" % counts[UNKNOWN])
        errs.append("strict")
    if verbose:
        by_disp = {d: [] for d in DISPOSITIONS}
        for key in sorted(indexed, key=lambda k: int(k) if k.isdigit() else 0):
            by_disp[indexed[key].get("disposition", UNKNOWN)].append(int(key))
        for disp in DISPOSITIONS:
            print("%s: %s" % (disp, ",".join(str(n) for n in by_disp[disp])))
    return 1 if errs else 0


if __name__ == "__main__":
    if "--write" in sys.argv:
        write()
    sys.exit(check("--strict" in sys.argv, "--verbose" in sys.argv))
