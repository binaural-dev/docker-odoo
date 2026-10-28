from odoo import fields, models


class FleetInspectionItem(models.Model):
    _name = "fleet.inspection.item"
    _description = "Punto del checklist de inspección"
    _order = "sequence, id"

    name = fields.Char(string="Punto a revisar", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    critical = fields.Boolean(
        string="Crítico",
        help="Si un punto crítico falla, la inspección no se puede aprobar.",
    )
