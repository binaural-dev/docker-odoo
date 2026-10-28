from odoo import fields, models


class FleetInspectionVehicleType(models.Model):
    _name = "fleet.inspection.vehicle.type"
    _description = "Tipo de vehículo para inspecciones"
    _order = "sequence, name"

    name = fields.Char(string="Tipo de vehículo", required=True, translate=True)
    code = fields.Char(
        string="Código", required=True,
        help="Identificador técnico estable. Los tipos iniciales usan los valores del antiguo campo de selección "
             "(motorcycle, car, truck, other) para que la migración los relacione.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Ya existe un tipo de vehículo con ese código."),
    ]
