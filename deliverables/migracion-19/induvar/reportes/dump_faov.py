# Ejecuta los reportes legales de nómina con los mismos parámetros y vuelca lo que
# entregan (el `data` de report_action o el contenido del archivo) a JSON.
# Corre igual en Odoo 17 y en Odoo 19: solo pasa los campos que el asistente tiene.
import base64, datetime, json, os
from markupsafe import Markup

OUT = os.environ.get("OUT", "/tmp/reportes.json")
COMPANIES = [1, 2, 3, 4]
PERIODS = {
    "q1_2026": ("q1", "2026-01-01", "2026-03-31"),
    "q2_2026": ("q2", "2026-04-01", "2026-06-30"),
}
MONTHS = {"2026-05": ("2026-05-01", "2026-05-31"), "2026-06": ("2026-06-01", "2026-06-30")}
ARC_YEAR = ("2025-01-01", "2025-12-31")


def norm(v):
    if isinstance(v, dict):
        return {str(k): norm(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [norm(x) for x in v]
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8", "replace")
        except Exception:
            return base64.b64encode(v).decode()
    if isinstance(v, Markup):
        return str(v)
    if hasattr(v, "_name") and hasattr(v, "ids"):
        return {"model": v._name, "ids": sorted(v.ids)}
    return v


def make(model, company_id, vals):
    M = env[model].with_company(company_id).with_context(allowed_company_ids=[company_id])
    vals = {k: v for k, v in vals.items() if k in M._fields}
    return M.create(vals)


def capture(fn):
    try:
        with env.cr.savepoint():
            res = fn()
            env.flush_all()
            out = norm(res.get("data") if isinstance(res, dict) and "data" in res else res)
            raise _Rollback(out)
    except _Rollback as r:
        return {"ok": True, "result": r.out}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e).splitlines()[0][:300]}"}


class _Rollback(Exception):
    def __init__(self, out):
        self.out = out


results = {}
for c in COMPANIES:
    comp = env["res.company"].browse(c)
    R = results.setdefault(comp.name, {})
    env.cr.execute("SELECT DISTINCT st.type_id FROM hr_payslip p JOIN hr_payroll_structure st ON st.id=p.struct_id WHERE p.company_id=%s AND st.type_id IS NOT NULL", [c])
    types = [r[0] for r in env.cr.fetchall()]
    for label, (d1, d2) in dict(MONTHS, **{"2026-03": ("2026-03-01", "2026-03-31"), "2025-12": ("2025-12-01", "2025-12-31")}).items():
        R[f"faov_{label}"] = capture(lambda: make("faov.report.wizard", c, {
            "company_id": c, "date_from": d1, "date_to": d2, "struct_type_ids": [(6, 0, types)],
        }).action_generate_report())
env.cr.rollback()
with open(OUT, "w") as fh:
    json.dump(results, fh, ensure_ascii=False, indent=1, sort_keys=True, default=str)
print("DUMP_OK", OUT)
