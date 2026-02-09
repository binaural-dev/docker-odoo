from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class AccountFinancialKpi(models.Model):
    _name = 'account.financial.kpi'
    _description = 'Financial KPI'
    _order = 'sequence, id'

    name = fields.Char(string='KPI Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    formula = fields.Text(
        string='Formula',
        required=True,
        help='Python expression to calculate the KPI value. Available variables: total_income, total_expense, total_assets, total_liabilities, total_receivable, total_payable, total_equity.',
    )
    threshold_warning = fields.Float(
        string='Warning Threshold',
        default=0.0,
        help='Values below this threshold will be shown in yellow.',
    )
    threshold_critical = fields.Float(
        string='Critical Threshold',
        default=0.0,
        help='Values below this threshold will be shown in red.',
    )
    invert_thresholds = fields.Boolean(
        string='Invert Thresholds',
        default=False,
        help='If checked, values above thresholds will trigger warnings instead of below.',
    )
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    description = fields.Text(string='Description', translate=True)
    kpi_value = fields.Float(
        string='Current Value',
        compute='_compute_kpi_value',
        store=True,
    )
    kpi_status = fields.Selection(
        selection=[
            ('green', 'Good'),
            ('yellow', 'Warning'),
            ('red', 'Critical'),
        ],
        string='Status',
        compute='_compute_kpi_value',
        store=True,
    )
    unit_type = fields.Selection(
        selection=[
            ('currency', 'Currency'),
            ('percentage', 'Percentage'),
            ('ratio', 'Ratio'),
        ],
        string='Unit Type',
        default='ratio',
    )

    @api.depends('formula', 'threshold_warning', 'threshold_critical', 'invert_thresholds')
    def _compute_kpi_value(self):
        for kpi in self:
            value = kpi._calculate_kpi_value()
            kpi.kpi_value = value
            kpi.kpi_status = kpi._get_status(value)

    def _calculate_kpi_value(self):
        self.ensure_one()
        if not self.formula:
            return 0.0

        company = self.company_id or self.env.company
        context = self._get_formula_context(company)

        try:
            result = safe_eval(self.formula, context)
            return float(result) if result else 0.0
        except Exception:
            return 0.0

    def _get_formula_context(self, company):
        AccountMoveLine = self.env['account.move.line']
        domain_posted = [
            ('move_id.state', '=', 'posted'),
            ('company_id', '=', company.id),
        ]

        total_income = abs(sum(AccountMoveLine.search(
            domain_posted + [('account_id.account_type', '=', 'income')]
        ).mapped('balance')))

        total_expense = abs(sum(AccountMoveLine.search(
            domain_posted + [('account_id.account_type', '=', 'expense')]
        ).mapped('balance')))

        total_assets = sum(AccountMoveLine.search(
            domain_posted + [('account_id.account_type', 'in', ['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed'])]
        ).mapped('balance'))

        total_liabilities = abs(sum(AccountMoveLine.search(
            domain_posted + [('account_id.account_type', 'in', ['liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current'])]
        ).mapped('balance')))

        total_receivable = sum(AccountMoveLine.search(
            domain_posted + [('account_id.account_type', '=', 'asset_receivable')]
        ).mapped('balance'))

        total_payable = abs(sum(AccountMoveLine.search(
            domain_posted + [('account_id.account_type', '=', 'liability_payable')]
        ).mapped('balance')))

        total_equity = abs(sum(AccountMoveLine.search(
            domain_posted + [('account_id.account_type', '=', 'equity')]
        ).mapped('balance')))

        total_current_assets = sum(AccountMoveLine.search(
            domain_posted + [('account_id.account_type', 'in', ['asset_receivable', 'asset_cash', 'asset_current'])]
        ).mapped('balance'))

        total_current_liabilities = abs(sum(AccountMoveLine.search(
            domain_posted + [('account_id.account_type', 'in', ['liability_payable', 'liability_credit_card', 'liability_current'])]
        ).mapped('balance')))

        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_receivable': total_receivable,
            'total_payable': total_payable,
            'total_equity': total_equity,
            'total_current_assets': total_current_assets,
            'total_current_liabilities': total_current_liabilities,
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
        }

    def _get_status(self, value):
        self.ensure_one()
        if self.invert_thresholds:
            if value >= self.threshold_critical:
                return 'red'
            elif value >= self.threshold_warning:
                return 'yellow'
            else:
                return 'green'
        else:
            if value <= self.threshold_critical:
                return 'red'
            elif value <= self.threshold_warning:
                return 'yellow'
            else:
                return 'green'

    def action_refresh(self):
        self._compute_kpi_value()
        return True
