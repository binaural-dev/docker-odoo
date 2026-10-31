from odoo import _, api, fields, models


class EquipmentLaptop(models.Model):
    """Modelo para el registro y gestión del catálogo de laptops y equipos tecnológicos."""

    _name = "equipment.laptop"
    _description = "Equipo / Laptop"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name asc"

    name = fields.Char(
        string="Nombre / Identificador",
        required=True,
        tracking=True,
        help="Identificador interno o etiqueta del equipo (ej. Lenovo ThinkPad T14 - TI-01).",
    )
    serial_number = fields.Char(
        string="Número de Serie",
        required=True,
        copy=False,
        tracking=True,
        help="Número de serie único de fábrica.",
    )
    brand = fields.Char(
        string="Marca",
        tracking=True,
        help="Marca del equipo (ej. Dell, Lenovo, Apple, HP).",
    )
    model = fields.Char(
        string="Modelo",
        tracking=True,
        help="Modelo comercial del equipo.",
    )
    state = fields.Selection(
        [
            ("available", "Disponible"),
            ("loaned", "Prestado"),
            ("maintenance", "Mantenimiento"),
        ],
        string="Estado del Equipo",
        default="available",
        required=True,
        tracking=True,
        help="Estado físico y operativo del equipo.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    notes = fields.Text(
        string="Observaciones / Ficha Técnica",
        help="Detalles de hardware o condición del equipo.",
    )
    loan_ids = fields.One2many(
        "equipment.loan",
        "laptop_id",
        string="Historial de Préstamos",
    )
    loan_count = fields.Integer(
        string="Total de Préstamos",
        compute="_compute_loan_statistics",
        search="_search_loan_count",
        help="Cantidad total de préstamos históricos de este equipo.",
    )
    overdue_loan_count = fields.Integer(
        string="Préstamos Vencidos",
        compute="_compute_loan_statistics",
        search="_search_overdue_loan_count",
        help="Préstamos activos que han excedido su fecha estimada de devolución.",
    )

    _sql_constraints = [
        ("serial_number_uniq", "unique(serial_number)", "El número de serie de la laptop debe ser único."),
    ]

    @api.depends("loan_ids", "loan_ids.is_overdue")
    def _compute_loan_statistics(self):
        """Calcula el total de préstamos y la cantidad de préstamos vencidos."""
        for laptop in self:
            laptop.loan_count = len(laptop.loan_ids)
            laptop.overdue_loan_count = len(laptop.loan_ids.filtered(lambda l: l.is_overdue))

    def _search_loan_count(self, operator, value):
        """Permite buscar laptops según su cantidad de préstamos."""
        self.env.cr.execute("""
            SELECT laptop_id
            FROM equipment_loan
            GROUP BY laptop_id
            HAVING count(id) """ + str(operator) + """ %s
        """, [value])
        laptop_ids = [row[0] for row in self.env.cr.fetchall()]
        return [("id", "in", laptop_ids)]

    def _search_overdue_loan_count(self, operator, value):
        """Permite filtrar laptops con préstamos vencidos."""
        today = fields.Date.context_today(self)
        loans = self.env["equipment.loan"].search([
            ("state", "=", "loaned"),
            ("expected_return_date", "<", today),
        ])
        laptop_ids = loans.mapped("laptop_id").ids
        if (operator in (">", ">=") and value >= 0) or (operator == "!=" and value == 0):
            return [("id", "in", laptop_ids)]
        return [("id", "not in", laptop_ids)]

    def action_view_loans(self):
        """Abre la vista con el historial de préstamos vinculados a este equipo."""
        self.ensure_one()
        return {
            "name": _("Historial de Préstamos: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "equipment.loan",
            "view_mode": "tree,form",
            "domain": [("laptop_id", "=", self.id)],
            "context": {"default_laptop_id": self.id},
        }
