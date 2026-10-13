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
    for label, (q, d1, d2) in PERIODS.items():
        base = {"company_id": c, "quarter_selection": q, "date_from": d1, "date_to": d2}
        R[f"inces_{label}"] = capture(lambda: make("quarterly.inces.wizard", c, dict(
            base, employer_contribution_report=True, worker_retention_report=True, report_type="quarterly",
        )).action_generate_report())
        R[f"mpppst_{label}"] = capture(lambda: make("quarterly.salary.statement.mpppst.wizard", c, {
            "company_id": c, "selected_quarter": q, "start_date": d1, "end_date": d2, "report_format": "pdf",
        }).action_generate_report())
        for rep in ("worker_data", "condition_worker_data"):
            R[f"mpppst_txt_{rep}_{label}"] = capture(lambda: make("txt.quarterly.salary.statement.mpppst.wizard", c, {
                "company_id": c, "selected_report": rep, "selected_report_type": "txt", "date_from": d1, "date_to": d2,
            }).generate_mpppst_txt())
    for label, (d1, d2) in MONTHS.items():
        R[f"faov_{label}"] = capture(lambda: make("faov.report.wizard", c, {
            "company_id": c, "date_from": d1, "date_to": d2,
        }).action_generate_report())
        R[f"horas_extra_{label}"] = capture(lambda: make("extraordinary.hours.report.wizard", c, {
            "company_id": c, "all_employees": True, "date_from": d1, "date_to": d2, "report_currency_mode": "base",
            "employee_ids": [(6, 0, env["hr.employee"].with_context(active_test=False).search([("company_id", "=", c)]).ids)],
        }).action_generate_report())
    # ARC: año 2025, empleados con recibos en ese año
    env.cr.execute(
        "SELECT DISTINCT employee_id FROM hr_payslip WHERE company_id=%s AND date_from>=%s AND date_to<=%s ORDER BY 1",
        [c, ARC_YEAR[0], ARC_YEAR[1]],
    )
    emp_ids = [r[0] for r in env.cr.fetchall()]
    R["arc_2025"] = capture(lambda: make("arc.receipt.wizard", c, {
        "company_id": c, "start_date": ARC_YEAR[0], "end_date": ARC_YEAR[1], "employee_ids": [(6, 0, emp_ids)],
    }).action_generate_report())
    R["arc_2025_empleados"] = len(emp_ids)

env.cr.rollback()
with open(OUT, "w") as fh:
    json.dump(results, fh, ensure_ascii=False, indent=1, sort_keys=True, default=str)
print("DUMP_OK", OUT, sum(1 for comp in results.values() for k, v in comp.items() if isinstance(v, dict) and v.get("ok")),
      "ok /", sum(1 for comp in results.values() for k, v in comp.items() if isinstance(v, dict)), "reportes")
