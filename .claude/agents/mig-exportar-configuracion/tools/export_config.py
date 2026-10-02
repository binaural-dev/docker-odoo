#!/usr/bin/env python3
"""Exporta configuracion (no transaccional) de una instancia Odoo en la nube a .xlsx.

Piloto (v1) de la skill mig-exportar-configuracion: lee dominios declarados en
domains.json, uno al lado de este script, y para cada modelo genera un .xlsx
listo para el importador nativo de Odoo (Ajustes > Tecnico > Importar) en el
ambiente destino.

Reutiliza el cliente de solo lectura de la skill core:odoo-cloud (mismo
mecanismo de autenticacion y la misma whitelist de metodos -- nunca escribe)
en vez de reimplementar autenticacion. No requiere dependencias fuera de
stdlib + openpyxl (ya presente en el entorno de este proyecto).

Uso:
  export_config.py --source <instancia> --domain general
  export_config.py --source <instancia> --domain general,contabilidad --out-dir /ruta
  export_config.py --source <instancia> --domain all --custom-path src/custom/<cliente>

Salida: <out-dir>/<dominio>/<modelo>.xlsx + <out-dir>/<dominio>/notas-version.md
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import sys

try:
    import openpyxl
except ImportError:
    sys.exit(
        "Falta openpyxl. Es la unica dependencia externa de este script.\n"
        "Instalar con: pip install --user openpyxl"
    )

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_DOMAINS_FILE = os.path.join(SCRIPT_DIR, "domains.json")

# Candidatos donde puede vivir odoo_client.py segun como se haya instalado el
# plugin core de Binaural. Se prueba en orden; ODOO_CLIENT_PATH gana siempre.
ODOO_CLIENT_CANDIDATES = [
    os.path.expanduser(
        "~/.claude/plugins/marketplaces/binaural/plugins/core/skills/odoo-cloud/scripts/odoo_client.py"
    ),
]

# Metadata, no configuracion de negocio -- ruido en todo export de cualquier modelo.
DEFAULT_EXCLUDED_FIELDS = {
    "__last_update",
    "create_date",
    "create_uid",
    "write_date",
    "write_uid",
    "display_name",
}

# Donde cruzar si un campo exportado sigue existiendo en el core de la version
# destino. No es una resolucion de modulo exacta (ver notas-version.md generado):
# solo busca si el nombre del campo aparece definido en algun `= fields.` del
# checkout -- cero matches es una senal real (confirmado con ir.cron.numbercall
# en una migracion de codigo previa); muchos matches con un campo generico
# (ej. "name") no se interpreta como senal, se ignora.
#
# Los campos de negocio (IGTF, ISLR, Megasoft, kiosco, etc.) no viven en el
# core/enterprise de Odoo sino en integra-addons/odoo-venezuela/third-party-addons
# y en el custom del propio cliente: pasar la raiz del custom con --custom-path
# (cubre sus submodulos, son carpetas normales en disco). Sin eso, la
# heuristica marca como "eliminado" casi todo lo que en realidad es custom.
#
# Raiz de docker-odoo: se deriva de la ubicacion real de este script
# (<raiz>/.claude/agents/<skill>/tools/), sin asumir ninguna ruta de usuario.
DOCKER_ODOO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, *[os.pardir] * 4))


def core_paths(custom_paths):
    """ODOO_CORE_PATHS (separado por os.pathsep) reemplaza los defaults."""
    env = os.environ.get("ODOO_CORE_PATHS")
    if env:
        base = [os.path.expanduser(p) for p in env.split(os.pathsep) if p]
    else:
        base = [
            os.path.expanduser("~/binaural/Core Odoo/odoo-19.0"),
            os.path.join(DOCKER_ODOO_ROOT, "src", "enterprise-19.0"),
        ]
    return base + [os.path.expanduser(p) for p in custom_paths]


def load_odoo_client_module():
    path = os.environ.get("ODOO_CLIENT_PATH")
    candidates = [path] if path else ODOO_CLIENT_CANDIDATES
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            spec = importlib.util.spec_from_file_location("odoo_client", candidate)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    sys.exit(
        "No se encontro odoo_client.py (skill core:odoo-cloud). "
        "Fija ODOO_CLIENT_PATH=/ruta/a/odoo_client.py si esta en otro lugar."
    )


def load_domains(path):
    with open(path) as f:
        data = json.load(f)
    return data["domains"]


def resolve_domain_names(requested, available):
    if requested == "all":
        return sorted(available)
    names = [n.strip() for n in requested.split(",") if n.strip()]
    unknown = [n for n in names if n not in available]
    if unknown:
        sys.exit(
            f"Dominio(s) desconocido(s): {', '.join(unknown)}.\n"
            f"Disponibles: {', '.join(sorted(available))}"
        )
    return names


def field_meta(client, model):
    """fields_get crudo: type/relation/store por campo."""
    return client.call_kw(
        model,
        "fields_get",
        args=[],
        kwargs={"attributes": ["type", "relation", "store", "string"]},
    )


def default_field_list(meta, skip_fields):
    excluded = DEFAULT_EXCLUDED_FIELDS | set(skip_fields or [])
    chosen = []
    for name, info in meta.items():
        if name in excluded or name == "id":
            continue
        if info.get("type") in ("binary", "one2many"):
            continue
        if info.get("store") is False:
            continue
        chosen.append(name)
    return sorted(chosen)


def external_id(model, record_id):
    return f"__export__.{model.replace('.', '_')}_{record_id}"


def fetch_domain_records(client, domain_name, domain_cfg, ext_id_map):
    """Trae todos los registros de todos los modelos del dominio.

    `ext_id_map` es {(model, id): external_id} **compartido entre todos los
    dominios de la corrida** (se le agrega acá, no se crea nuevo por
    dominio) -- si no, un modelo de `pos` que referencia `res.company`
    (dominio `general`) nunca resuelve la referencia aunque ambos se exporten
    juntos, porque cada dominio vería un mapa vacío. Devuelve `resultados`:
    {model: {"fields": [...], "field_meta": {...}, "records": [...], "notes": str}}.
    """
    resultados = {}
    for entry in domain_cfg["models"]:
        model = entry["model"]
        meta = field_meta(client, model)
        fields = entry.get("fields") or default_field_list(meta, entry.get("skip_fields"))
        domain_filter = entry.get("domain", [])
        records = client.call_kw(
            model,
            "search_read",
            kwargs={"domain": domain_filter, "fields": ["id"] + fields},
        )
        for rec in records:
            ext_id_map[(model, rec["id"])] = external_id(model, rec["id"])
        resultados[model] = {
            "fields": fields,
            "field_meta": meta,
            "records": records,
            "notes": entry.get("notes", ""),
        }
    return resultados


def resolve_value(field_name, info, value, ext_id_map, missing_refs):
    """Muchos2one/many2many -> referencia a external id si esta en alcance,
    si no, un valor legible (display_name) marcado para revision manual."""
    rel_model = info.get("relation")
    if info.get("type") == "many2one":
        if not value:
            return ""
        rel_id, display = value[0], value[1]
        key = (rel_model, rel_id)
        if key in ext_id_map:
            return ext_id_map[key]
        missing_refs.append((field_name, rel_model, rel_id, display))
        return f"# REVISAR: {display}"
    if info.get("type") == "many2many":
        if not value:
            return ""
        parts = []
        for rel_id in value:
            key = (rel_model, rel_id)
            if key in ext_id_map:
                parts.append(ext_id_map[key])
            else:
                missing_refs.append((field_name, rel_model, rel_id, None))
        return ",".join(parts)
    if isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value if value is not False else ""


def write_xlsx(path, model, fields, field_meta_map, records, ext_id_map, missing_refs):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = model[:31]

    headers = ["id"]
    for f in fields:
        info = field_meta_map.get(f, {})
        if info.get("type") in ("many2one", "many2many"):
            headers.append(f"{f}/id")
        else:
            headers.append(f)
    ws.append(headers)

    for rec in records:
        row = [external_id(model, rec["id"])]
        for f in fields:
            info = field_meta_map.get(f, {})
            row.append(resolve_value(f, info, rec.get(f), ext_id_map, missing_refs))
        ws.append(row)

    wb.save(path)


def scan_core_for_fields(field_names, paths):
    """Un solo paso sobre el checkout local por cada campo a chequear (no uno
    por campo): O(archivos), no O(campos x archivos). Devuelve {campo: bool}.

    Los campos `module_<tecnico>` (checkboxes de instalacion en
    res.config.settings) no se declaran con `= fields.` en Python -- Odoo los
    genera a partir de que exista la carpeta del modulo, se referencian solo
    en XML. Se dan siempre por "encontrados": lo que hay que chequear ahi es
    si el modulo `<tecnico>` existe en destino, no el nombre del campo.
    """
    found = {name: True for name in field_names if name.startswith("module_")}
    remaining = {
        name: re.compile(r"\b" + re.escape(name) + r"\s*=\s*fields\.")
        for name in field_names
        if name not in found
    }
    found.update({name: False for name in remaining})
    for core_path in paths:
        if not os.path.isdir(core_path) or not remaining:
            continue
        for root, dirs, files in os.walk(core_path):
            if not remaining:
                break
            dirs[:] = [d for d in dirs if d != ".git"]
            for fname in files:
                if not remaining:
                    break
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                except OSError:
                    continue
                for name in list(remaining):
                    if remaining[name].search(content):
                        found[name] = True
                        del remaining[name]
    return found


def write_version_notes(path, domain_name, resultados, field_status):
    lines = [f"# Notas de compatibilidad v19 -- dominio `{domain_name}`", ""]
    lines.append(
        "Heuristica: se busca el nombre de cada campo exportado como "
        "`<campo> = fields.` en el checkout local de Odoo 19 "
        "(ver ODOO_CORE_PATHS / --custom-path). "
        "Cero coincidencias es una senal real de campo eliminado/renombrado "
        "(confirmado antes con `ir.cron.numbercall`); no bloquea el export, "
        "solo advierte para revision manual antes de importar."
    )
    lines.append("")
    any_flag = False
    for model, data in resultados.items():
        flagged = [f for f in data["fields"] if not field_status.get(f, True)]
        if flagged:
            any_flag = True
            lines.append(f"## `{model}`")
            for f in flagged:
                lines.append(
                    f"- `{f}`: sin coincidencias en el core v19 local -- "
                    "revisar si fue eliminado/renombrado antes de importar."
                )
            lines.append("")
    if not any_flag:
        lines.append("Sin advertencias: todos los campos exportados aparecen definidos "
                      "en el core v19 local.")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_readme(out_dir, source_name, domain_names, missing_refs_by_domain):
    path = os.path.join(out_dir, "README.md")
    lines = [
        f"# Export de configuracion -- origen `{source_name}`",
        "",
        f"Generado: {datetime.datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Orden de importacion recomendado",
        "",
        "1. `general` (compania/moneda) -- **antes que cualquier dato con montos**. "
        "Si el destino cambia de moneda base (ej. USD -> Bs), configurar la moneda "
        "de la compania primero y revisar a mano los montos que asumian la moneda vieja.",
        "2. `contabilidad` (plan de cuentas, impuestos, posiciones fiscales, diarios, "
        "terminos de pago).",
        "3. `inventario` (almacenes, ubicaciones, categorias, tipos de operacion).",
        "4. `ventas_compras` (equipos de venta, listas de precio).",
        "5. `pos` -- **verificar primero** que el destino ya tenga instalados "
        "`point_of_sale` y los modulos POS custom correspondientes "
        "(`-i <destino> search_read ir.module.module --domain "
        "'[[\"name\",\"in\",[...]]]' --fields name,state`). Si figuran "
        "`uninstalled`, no importar este dominio todavia.",
        "6. `seguridad` / `automatizaciones` -- al final, revisando a mano "
        "usuarios/logins para no duplicar los que ya existan en destino.",
        "",
        "## Dominios en este export",
        "",
    ]
    for d in domain_names:
        lines.append(f"- `{d}/` -- ver `{d}/notas-version.md` por advertencias de campos.")
        missing = missing_refs_by_domain.get(d) or []
        if missing:
            lines.append(
                f"  - {len(missing)} referencia(s) relacional(es) fuera del alcance de "
                "este export (quedaron marcadas `# REVISAR: <nombre>` en el .xlsx "
                "correspondiente -- completar el external id a mano o correr el "
                "export incluyendo el dominio que contiene ese modelo relacionado)."
            )
    lines.append("")
    lines.append(
        "## Importar\n\nEste export es de solo lectura sobre el origen -- ningun paso "
        "de esta skill escribe en el destino. Importar cada .xlsx manualmente en "
        "*Ajustes > Tecnico > Importar* del ambiente destino, en el orden de arriba."
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="Nombre de la instancia origen en odoo-cloud config")
    parser.add_argument("--domain", required=True, help="Nombre de dominio, lista separada por coma, o 'all'")
    parser.add_argument("--domains-file", default=DEFAULT_DOMAINS_FILE)
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Default: ~/binaural/config-export/<source>/<fecha>/",
    )
    parser.add_argument(
        "--custom-path",
        action="append",
        default=[],
        help="Raiz del custom del cliente a escanear (repetible), ej. src/custom/<cliente>",
    )
    args = parser.parse_args()

    odoo_client = load_odoo_client_module()
    domains = load_domains(args.domains_file)
    domain_names = resolve_domain_names(args.domain, domains)

    name, config = odoo_client.select_instance(args.source)
    client = odoo_client.OdooClient(config, name=name)
    client.authenticate()

    out_dir = args.out_dir or os.path.join(
        os.path.expanduser("~/binaural/config-export"),
        args.source,
        datetime.date.today().isoformat(),
    )
    os.makedirs(out_dir, exist_ok=True)

    # Fase 1 -- traer TODOS los dominios primero, acumulando un unico mapa de
    # external ids. Si se escribiera dominio por dominio, un modelo de `pos`
    # nunca resolveria su referencia a `res.company` (dominio `general`)
    # aunque ambos esten en la misma corrida: necesita ver el mapa completo.
    ext_id_map = {}
    resultados_by_domain = {}
    for domain_name in domain_names:
        domain_cfg = domains[domain_name]
        print(f"[{domain_name}] extrayendo {len(domain_cfg['models'])} modelo(s)...", file=sys.stderr)
        resultados_by_domain[domain_name] = fetch_domain_records(client, domain_name, domain_cfg, ext_id_map)

    # Fase 2 -- ya con el mapa completo, escribir los .xlsx.
    missing_refs_by_domain = {}
    for domain_name, resultados in resultados_by_domain.items():
        domain_dir = os.path.join(out_dir, domain_name)
        os.makedirs(domain_dir, exist_ok=True)

        domain_missing_refs = []
        for model, data in resultados.items():
            xlsx_path = os.path.join(domain_dir, f"{model.replace('.', '_')}.xlsx")
            missing_refs = []
            write_xlsx(
                xlsx_path, model, data["fields"], data["field_meta"],
                data["records"], ext_id_map, missing_refs,
            )
            domain_missing_refs.extend(missing_refs)
            print(
                f"[{domain_name}] {model}: {len(data['records'])} registro(s) -> {xlsx_path}"
                + (f" ({len(missing_refs)} referencia(s) fuera de alcance)" if missing_refs else ""),
                file=sys.stderr,
            )

        missing_refs_by_domain[domain_name] = domain_missing_refs

    all_fields = {
        f
        for resultados in resultados_by_domain.values()
        for data in resultados.values()
        for f in data["fields"]
    }
    print(f"Chequeando {len(all_fields)} campo(s) unico(s) contra el core v19 local...", file=sys.stderr)
    field_status = scan_core_for_fields(all_fields, core_paths(args.custom_path))

    for domain_name, resultados in resultados_by_domain.items():
        domain_dir = os.path.join(out_dir, domain_name)
        write_version_notes(
            os.path.join(domain_dir, "notas-version.md"), domain_name, resultados, field_status
        )

    write_readme(out_dir, args.source, domain_names, missing_refs_by_domain)
    print(f"\nListo: {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
