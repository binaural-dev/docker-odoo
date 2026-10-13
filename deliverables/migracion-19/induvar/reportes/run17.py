import odoo, sys
A = ("/home/odoo/src/enterprise-17,/home/odoo/src/custom/idv,/home/odoo/src/custom/idv/integra-addons,"
     "/home/odoo/src/custom/idv/third-party-addons,/home/odoo/src/custom/idv/odoo-venezuela")
odoo.tools.config.parse_config(["-c", "/tmp/idv17.conf", "--addons-path", A, "--db_host", "db-pg16",
    "--db_user", "odoo", "--db_password", "odoo", "--max-cron-threads", "0", "--log-level", "error"])
odoo.modules.module.initialize_sys_path()
odoo.addons.__path__[:] = [p for p in odoo.addons.__path__ if "/custom/thk" not in p]
print("NS", [p for p in odoo.addons.__path__ if "custom" in p])
from odoo.api import Environment
reg = odoo.modules.registry.Registry("17_idv_src")
with reg.cursor() as cr:
    env = Environment(cr, odoo.SUPERUSER_ID, {})
    import odoo.addons.l10n_ve_tax as t; print("L10N_VE_TAX", t.__file__)
    exec(open("/tmp/dump_reports.py").read(), {"env": env, "__name__": "__dump__"})
    cr.rollback()
