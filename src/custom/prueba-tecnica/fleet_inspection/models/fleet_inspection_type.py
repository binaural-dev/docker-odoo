from odoo import fields, models


class FleetInspectionVehicleType(models.Model):
    _name = "fleet.inspection.vehicle.type"
    _description = "Tipo de vehículo de inspección"
    _order = "sequence, name"

    name = fields.Char(string="Tipo de vehículo", required=True, translate=True)
    code = fields.Char(string="Código", required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "unique(code)",
        "El código del tipo de vehículo debe ser único.",
    )