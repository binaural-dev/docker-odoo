from odoo.addons.fleet_inspection.migration_utils import save_legacy_vehicle_type


def migrate(cr, version):
    """Antes de cargar el modelo nuevo: respaldar el tipo de vehículo (selección) en una columna propia."""
    save_legacy_vehicle_type(cr)
