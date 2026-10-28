from odoo import fields, models


class FleetInspectionLine(models.Model):
    _name = "fleet.inspection.line"
    _description = "Línea del checklist de inspección"
    _order = "sequence, id"

    inspection_id = fields.Many2one("fleet.inspection", required=True, ondelete="cascade")
    item_id = fields.Many2one("fleet.inspection.item", string="Punto", required=True)
    sequence = fields.Integer(related="item_id.sequence", store=True)
    critical = fields.Boolean(related="item_id.critical")
    result = fields.Selection(
        [("ok", "Bien"), ("fail", "Falla"), ("na", "No aplica")],
        string="Resultado",
    )
    comment = fields.Char(string="Comentario")
    state = fields.Selection(related="inspection_id.state")
