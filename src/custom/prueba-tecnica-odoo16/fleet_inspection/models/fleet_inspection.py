from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

VEHICLE_TYPES = [
    ("motorcycle", "Moto"),
    ("car", "Carro"),
    ("truck", "Camión"),
    ("other", "Otro"),
]


class FleetInspection(models.Model):
    _name = "fleet.inspection"
    _description = "Inspección de vehículo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Número", required=True, copy=False, readonly=True, default="/")
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehículo",
        required=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    vehicle_type = fields.Selection(
        VEHICLE_TYPES,
        string="Tipo de vehículo",
        required=True,
        default="car",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    inspector_id = fields.Many2one(
        "res.users",
        string="Inspector",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    date = fields.Date(
        string="Fecha", required=True, default=fields.Date.context_today, tracking=True
    )
    odometer = fields.Float(string="Kilometraje")
    line_ids = fields.One2many(
        "fleet.inspection.line", "inspection_id", string="Checklist", copy=True
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("in_progress", "En curso"),
            ("approved", "Aprobada"),
            ("rejected", "Rechazada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    notes = fields.Text(string="Observaciones")
    failed_count = fields.Integer(string="Puntos fallidos", compute="_compute_counts", store=True)
    pending_count = fields.Integer(string="Puntos pendientes", compute="_compute_counts", store=True)
    is_overdue = fields.Boolean(string="Vencida", readonly=True, copy=False)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "El número de la inspección debe ser único."),
    ]

    @api.depends("line_ids.result")
    def _compute_counts(self):
        for inspection in self:
            inspection.failed_count = len(inspection.line_ids.filtered(lambda l: l.result == "fail"))
            inspection.pending_count = len(inspection.line_ids.filtered(lambda l: not l.result))

    @api.constrains("odometer")
    def _check_odometer(self):
        for inspection in self:
            if inspection.odometer < 0:
                raise ValidationError(_("El kilometraje no puede ser negativo."))

    @api.model
    def create(self, vals):
        if vals.get("name", "/") == "/":
            vals["name"] = self.env["ir.sequence"].next_by_code("fleet.inspection") or "/"
        if not vals.get("line_ids"):
            items = self.env["fleet.inspection.item"].search([])
            vals["line_ids"] = [(0, 0, {"item_id": item.id}) for item in items]
        return super(FleetInspection, self).create(vals)

    def name_get(self):
        result = []
        for inspection in self:
            label = inspection.name
            if inspection.vehicle_id:
                label = "%s - %s" % (inspection.name, inspection.vehicle_id.license_plate or inspection.vehicle_id.name)
            result.append((inspection.id, label))
        return result

    def action_start(self):
        for inspection in self:
            if not inspection.line_ids:
                raise UserError(_("La inspección %s no tiene puntos en el checklist.") % inspection.name)
        self.write({"state": "in_progress"})

    def action_approve(self):
        for inspection in self:
            if inspection.pending_count:
                raise UserError(_("Faltan puntos por revisar en la inspección %s.") % inspection.name)
            critical_failed = inspection.line_ids.filtered(lambda l: l.result == "fail" and l.item_id.critical)
            if critical_failed:
                raise UserError(
                    _("No se puede aprobar: fallaron puntos críticos (%s).")
                    % ", ".join(critical_failed.mapped("item_id.name"))
                )
        self.write({"state": "approved", "is_overdue": False})

    def action_reject(self):
        self.write({"state": "rejected", "is_overdue": False})

    def action_reset_draft(self):
        self.write({"state": "draft"})

    def unlink(self):
        if any(inspection.state != "draft" for inspection in self):
            raise UserError(_("Solo se pueden eliminar inspecciones en borrador."))
        return super(FleetInspection, self).unlink()

    @api.model
    def _cron_mark_overdue(self, days=7):
        limit_date = fields.Date.context_today(self) - timedelta(days=days)
        overdue = self.search([("state", "=", "in_progress"), ("date", "<", limit_date), ("is_overdue", "=", False)])
        overdue.write({"is_overdue": True})
        for inspection in overdue:
            inspection.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=inspection.inspector_id.id,
                summary=_("Inspección en curso desde hace más de %s días") % days,
            )
        return True
