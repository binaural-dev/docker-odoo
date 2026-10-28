from odoo import SUPERUSER_ID, api

from odoo.addons.fleet_inspection.migration_utils import assign_vehicle_types


def migrate(cr, version):
    """Con el catálogo ya cargado: asignar a cada inspección el tipo que tenía."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    assign_vehicle_types(env)
