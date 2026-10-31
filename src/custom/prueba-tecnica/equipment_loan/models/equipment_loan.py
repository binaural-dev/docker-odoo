from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EquipmentLoan(models.Model):
    """Modelo para formalizar y controlar el préstamo de laptops a colaboradores."""

    _name = "equipment.loan"
    _description = "Préstamo de Equipo"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Secuencia",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("Nuevo"),
        tracking=True,
        help="Número correlativo autogenerado del préstamo (ej. PREST/2026/0001).",
    )
    laptop_id = fields.Many2one(
        "equipment.laptop",
        string="Equipo / Laptop",
        required=True,
        tracking=True,
        help="Equipo tecnológico asignado al préstamo.",
    )
    receiver_id = fields.Many2one(
        "res.partner",
        string="Persona que Recibe",
        required=True,
        tracking=True,
        help="Colaborador o persona que recibe el equipo.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsable del Préstamo",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help="Usuario que gestiona la entrega y custodia administrativa.",
    )
    delivery_date = fields.Date(
        string="Fecha de Entrega",
        default=fields.Date.context_today,
        tracking=True,
        help="Fecha en la cual el equipo es efectivamente entregado al solicitante.",
    )
    expected_return_date = fields.Date(
        string="Fecha Previa de Devolución",
        required=True,
        tracking=True,
        help="Fecha pactada o estimada para el retorno del equipo.",
    )
    actual_return_date = fields.Date(
        string="Fecha Real de Devolución",
        readonly=True,
        copy=False,
        tracking=True,
        help="Fecha en que el equipo fue devuelto. Se registra automáticamente al presionar 'Devolver'.",
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("loaned", "Prestado"),
            ("returned", "Devuelto"),
        ],
        string="Estado",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    is_overdue = fields.Boolean(
        string="Vencido",
        compute="_compute_is_overdue",
        search="_search_is_overdue",
        help="Indica si el préstamo sigue activo y la fecha estimada de devolución ya fue superada.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    notes = fields.Text(
        string="Observaciones / Motivo",
        help="Justificación del préstamo, estado de recepción o incidentes.",
    )

    # -------------------------------------------------------------------------
    # GESTIÓN DE BASE DE DATOS Y CONCURRENCIA
    # -------------------------------------------------------------------------
    def init(self):
        """Garantiza a nivel de base de datos PostgreSQL que un equipo solo tenga un préstamo activo."""
        super().init()
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS equipment_loan_unique_active_laptop
            ON equipment_loan (laptop_id)
            WHERE state = 'loaned';
        """)

    # -------------------------------------------------------------------------
    # CAMPOS COMPUTADOS Y BÚSQUEDA
    # -------------------------------------------------------------------------
    @api.depends("state", "expected_return_date")
    def _compute_is_overdue(self):
        """Evalúa si un préstamo se encuentra en estado 'Prestado' habiendo superado la fecha pactada."""
        today = fields.Date.context_today(self)
        for record in self:
            record.is_overdue = bool(
                record.state == "loaned"
                and record.expected_return_date
                and record.expected_return_date < today
            )

    def _search_is_overdue(self, operator, value):
        """Permite filtrar en la barra de búsqueda los préstamos vencidos en Odoo 17."""
        today = fields.Date.context_today(self)
        if (operator == "=" and value) or (operator == "!=" and not value):
            return [("state", "=", "loaned"), ("expected_return_date", "<", today)]
        return ["|", ("state", "!=", "loaned"), ("expected_return_date", ">=", today)]

    # -------------------------------------------------------------------------
    # RESTRICCIONES DE INTEGRIDAD
    # -------------------------------------------------------------------------
    @api.constrains("laptop_id", "state")
    def _check_single_active_loan(self):
        """Valida que un equipo no pueda estar prestado a dos personas al mismo tiempo,
        ni a la misma persona simultáneamente."""
        for record in self:
            if record.state == "loaned" and record.laptop_id:
                active_loans = self.search([
                    ("laptop_id", "=", record.laptop_id.id),
                    ("state", "=", "loaned"),
                    ("id", "!=", record.id),
                ])
                if active_loans:
                    raise ValidationError(
                        _("El equipo '%s' ya se encuentra prestado actualmente a %s. "
                          "No puede prestarse a otra persona ni registrarse otro préstamo al mismo tiempo.")
                        % (record.laptop_id.name, active_loans[0].receiver_id.name)
                    )

    @api.constrains("delivery_date", "expected_return_date")
    def _check_dates_consistency(self):
        """Valida coherencia temporal entre la fecha de entrega y la fecha previa de devolución."""
        for record in self:
            if record.delivery_date and record.expected_return_date:
                if record.expected_return_date < record.delivery_date:
                    raise ValidationError(
                        _("La fecha previa de devolución no puede ser anterior a la fecha de entrega.")
                    )

    def write(self, vals):
        """Protege la integridad de los datos esenciales una vez que el equipo fue entregado."""
        protected_fields = {"laptop_id", "receiver_id", "delivery_date", "expected_return_date"}
        for record in self:
            if record.state != "draft" and any(field in vals for field in protected_fields):
                raise UserError(
                    _("No puede modificar la información esencial de un préstamo que ya ha sido entregado o devuelto.")
                )
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el correlativo oficial del préstamo al guardar el registro."""
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = self.env["ir.sequence"].next_by_code("equipment.loan") or _("Nuevo")
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # ACCIONES DE NEGOCIO Y BOTONES
    # -------------------------------------------------------------------------
    def action_deliver(self):
        """Realiza la entrega del equipo aplicando bloqueo de concurrencia a nivel de fila."""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Solo se pueden entregar préstamos en estado Borrador."))

            if not record.laptop_id:
                raise UserError(_("Debe seleccionar un equipo antes de realizar la entrega."))

            # Bloqueo explícito de fila en PostgreSQL para evitar Race Conditions
            self.env.cr.execute(
                "SELECT id, state FROM equipment_laptop WHERE id = %s FOR UPDATE",
                [record.laptop_id.id],
            )
            laptop_row = self.env.cr.fetchone()
            if not laptop_row or laptop_row[1] != "available":
                raise UserError(
                    _("El equipo '%s' no está disponible para ser entregado (Estado actual: %s).")
                    % (record.laptop_id.name, laptop_row[1] if laptop_row else "desconocido")
                )

            # Verificación adicional en el modelo de préstamos
            active_loans = self.search([
                ("laptop_id", "=", record.laptop_id.id),
                ("state", "=", "loaned"),
                ("id", "!=", record.id),
            ])
            if active_loans:
                raise UserError(
                    _("El equipo '%s' ya posee un préstamo activo en curso.") % record.laptop_id.name
                )

            if not record.delivery_date:
                record.delivery_date = fields.Date.context_today(record)

            record.state = "loaned"
            record.laptop_id.state = "loaned"
            record.message_post(
                body=_("Equipo entregado a %s. Fecha previa de devolución: %s.")
                % (record.receiver_id.name, record.expected_return_date)
            )
        return True

    def action_return(self):
        """Registra la devolución del equipo y almacena automáticamente la fecha real."""
        for record in self:
            if record.state != "loaned":
                raise UserError(_("Solo se pueden devolver préstamos que se encuentren en estado Prestado."))

            # Registro automático de la fecha real de devolución
            record.actual_return_date = fields.Date.context_today(record)
            record.state = "returned"
            record.laptop_id.state = "available"

            message = _("Equipo devuelto y recibido con éxito el %s.") % record.actual_return_date
            if record.actual_return_date > record.expected_return_date:
                message += _(" Nota: La devolución se efectuó posterior a la fecha previa pactada.")
            record.message_post(body=message)
        return True

    def action_view_laptop_history(self):
        """Abre el historial de préstamos del equipo seleccionado desde el propio formulario de préstamo."""
        self.ensure_one()
        if not self.laptop_id:
            raise UserError(_("Seleccione un equipo para consultar su historial."))
        return {
            "name": _("Historial de Préstamos: %s") % self.laptop_id.name,
            "type": "ir.actions.act_window",
            "res_model": "equipment.loan",
            "view_mode": "tree,form",
            "domain": [("laptop_id", "=", self.laptop_id.id)],
            "context": {"search_default_group_state": 1},
        }

