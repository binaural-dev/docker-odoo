#!/usr/bin/env python3
"""sdd_inventory_check.py — exact-closure inventory gate (F3, P0-4), local and offline.

src/.opencode/inventory.json declares, per family, every file/dir that must exist and who owns it.
Checks (exit 1 on any failure): schema; declared set == real set (new or missing entry fails); one owner per
entry and owner must be a declared owner; unowned entries are counted (target 0, reported, `--strict` fails on them).
Also prints a drift report: counts declared in AGENTS.md / src/Agents.md vs the real ones (informational).

  python3 scripts/sdd_inventory_check.py            # check
  python3 scripts/sdd_inventory_check.py --write    # regenerate entries from disk (keeps existing owners)
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(ROOT, "scripts/sdd-inventory.json")
SCHEMA = "sdd-inventory/v1"
FAMILIES = {  # name: (dir relative to ROOT, kind, ignored names)
    "skills": ("src/.opencode/skills", "dir", set()),
    "agents": ("src/.opencode/agents", "file", set()),
    "commands": ("src/.opencode/commands", "file", set()),
    "claude_agents": (".claude/agents", "file", set()),
    "scripts": ("scripts", "any", {"__pycache__", ".opencode", "sdd-inventory.json"}),
}
OWNER_RULES = {  # per family, first regex match wins; fallback "unowned". Heuristic: review owners by hand.
    "skills": [(r"^(sdd|sudolang|claude|opencode|skill|skills|workspace|openrag|agents)", "harness-sdd"),
               (r"^(binaural|cadipa|l10n)", "binaural-product"),
               (r"(flujo|requerimiento|solicitud|validar|release|historial|consultar|construir|estado-cola|auditar|documentar|configurar)", "binaural-process"),
               (r"^(odoo|owl)", "odoo-knowledge"),
               (r"^(docker|terminal|devops|postgresql|gh-pr|guia_precommit|api-controller|coverage)", "dev-environment")],
    "agents": [(r".*", "harness-sdd")],
    "claude_agents": [(r".*", "harness-sdd")],
    "commands": [(r"^(cache|plan|specs|tasks|implement|index|re-index)", "harness-sdd"),
                 (r".*", "dev-environment")],
    "scripts": [(r"^(sdd|opencode|run_tests|precommit|coverage|update_addon|README|tests$)", "harness-sdd"),
                (r"^(odoo|migrate|detect_move|mcp_servers)", "odoo-tooling")],
}
OWNERS = ["harness-sdd", "binaural-product", "binaural-process", "odoo-knowledge", "dev-environment", "odoo-tooling"]


def real(family):
    d, kind, ign = FAMILIES[family]
    out = []
    for n in sorted(os.listdir(os.path.join(ROOT, d))):
        p = os.path.join(ROOT, d, n)
        if n in ign or n.startswith("."):
            continue
        if kind == "dir" and not os.path.isdir(p) or kind == "file" and not os.path.isfile(p):
            continue
        out.append(n)
    return out


def guess_owner(fam, name):
    for rx, owner in OWNER_RULES.get(fam, []):
        if re.search(rx, name):
            return owner
    return "unowned"


def write():
    old = json.load(open(INV)) if os.path.exists(INV) else {}
    inv = {"schema": SCHEMA, "owners": OWNERS, "families": {}}
    for fam in FAMILIES:
        prev = old.get("families", {}).get(fam, {})
        inv["families"][fam] = {n: prev.get(n) if prev.get(n) not in (None, "unowned") else guess_owner(fam, n) for n in real(fam)}
    json.dump(inv, open(INV, "w"), indent=1, ensure_ascii=False, sort_keys=False)
    open(INV, "a").write("\n")
    print(f"wrote {INV}")


def drift():
    pats = [("AGENTS.md", r"skills/\s*←[^(]*\((\d+) dirs\)", "skills", 0), ("AGENTS.md", r"commands/\s*←[^(]*\((\d+) commands\)", "commands", 0),
            ("src/Agents.md", r"skills/\s*#[^(]*\((\d+) skills\)", "skills", 0), ("src/Agents.md", r"agents/\s*#[^(]*\((\d+) SDD agents\)", "agents", 0)]
    lines = []
    for f, rx, fam, _ in pats:
        m = re.search(rx, open(os.path.join(ROOT, f)).read())
        if m and int(m.group(1)) != len(real(fam)):
            lines.append(f"  {f}: {fam} documented {m.group(1)} vs real {len(real(fam))}")
    return lines


def check(strict):
    inv = json.load(open(INV))
    errs, unowned = [], 0
    if inv.get("schema") != SCHEMA:
        errs.append(f"schema != {SCHEMA}")
    for fam in FAMILIES:
        declared = inv.get("families", {}).get(fam)
        if declared is None:
            errs.append(f"family {fam} missing")
            continue
        r = set(real(fam))
        for n in sorted(r - set(declared)):
            errs.append(f"{fam}: '{n}' exists but has no owner entry")
        for n in sorted(set(declared) - r):
            errs.append(f"{fam}: '{n}' declared but missing on disk")
        for n, o in declared.items():
            if o == "unowned":
                unowned += 1
            elif o not in inv.get("owners", []):
                errs.append(f"{fam}: '{n}' has undeclared owner '{o}'")
    if strict and unowned:
        errs.append(f"{unowned} unowned entries (--strict)")
    total = sum(len(v) for v in inv["families"].values())
    print(f"inventory: {total} entries, unowned: {unowned}")
    for l in drift():
        print("drift" + l)
    for e in errs:
        print("FAIL " + e)
    return 1 if errs else 0


if __name__ == "__main__":
    if "--write" in sys.argv:
        write()
    sys.exit(check("--strict" in sys.argv))
