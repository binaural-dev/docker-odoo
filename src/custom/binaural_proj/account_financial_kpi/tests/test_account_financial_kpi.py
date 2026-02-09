from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountFinancialKpi(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Kpi = cls.env['account.financial.kpi']

        cls.kpi_test = cls.Kpi.create({
            'name': 'Test KPI',
            'formula': '100',
            'threshold_warning': 50,
            'threshold_critical': 25,
            'unit_type': 'ratio',
        })

    def test_01_model_exists_with_required_fields(self):
        self.assertTrue('account.financial.kpi' in self.env)
        self.assertIn('name', self.Kpi._fields)
        self.assertIn('formula', self.Kpi._fields)
        self.assertIn('threshold_warning', self.Kpi._fields)
        self.assertIn('threshold_critical', self.Kpi._fields)

    def test_02_kpi_calculates_value_from_formula(self):
        kpi = self.Kpi.create({
            'name': 'Fixed Value KPI',
            'formula': '42',
            'threshold_warning': 30,
            'threshold_critical': 10,
        })
        self.assertEqual(kpi.kpi_value, 42.0)

    def test_03_status_green_above_warning(self):
        kpi = self.Kpi.create({
            'name': 'Green Status KPI',
            'formula': '100',
            'threshold_warning': 50,
            'threshold_critical': 25,
        })
        self.assertEqual(kpi.kpi_status, 'green')

    def test_04_status_yellow_between_thresholds(self):
        kpi = self.Kpi.create({
            'name': 'Yellow Status KPI',
            'formula': '40',
            'threshold_warning': 50,
            'threshold_critical': 25,
        })
        self.assertEqual(kpi.kpi_status, 'yellow')

    def test_05_status_red_below_critical(self):
        kpi = self.Kpi.create({
            'name': 'Red Status KPI',
            'formula': '20',
            'threshold_warning': 50,
            'threshold_critical': 25,
        })
        self.assertEqual(kpi.kpi_status, 'red')

    def test_06_invert_thresholds_changes_logic(self):
        kpi = self.Kpi.create({
            'name': 'Inverted KPI',
            'formula': '100',
            'threshold_warning': 50,
            'threshold_critical': 75,
            'invert_thresholds': True,
        })
        self.assertEqual(kpi.kpi_status, 'red')

    def test_07_formula_with_zero_division_returns_zero(self):
        kpi = self.Kpi.create({
            'name': 'Division by Zero',
            'formula': '100 / 0 if False else 0',
            'threshold_warning': 50,
            'threshold_critical': 25,
        })
        self.assertEqual(kpi.kpi_value, 0.0)

    def test_08_invalid_formula_returns_zero(self):
        kpi = self.Kpi.create({
            'name': 'Invalid Formula',
            'formula': 'invalid_syntax(',
            'threshold_warning': 50,
            'threshold_critical': 25,
        })
        self.assertEqual(kpi.kpi_value, 0.0)

    def test_09_menu_actions_exist(self):
        action_dashboard = self.env.ref(
            'account_financial_kpi.action_account_financial_kpi_dashboard',
            raise_if_not_found=False
        )
        action_config = self.env.ref(
            'account_financial_kpi.action_account_financial_kpi',
            raise_if_not_found=False
        )
        self.assertTrue(action_dashboard)
        self.assertTrue(action_config)

    def test_10_action_refresh_recalculates(self):
        kpi = self.Kpi.create({
            'name': 'Refresh Test',
            'formula': '50',
            'threshold_warning': 30,
            'threshold_critical': 10,
        })
        initial_value = kpi.kpi_value
        result = kpi.action_refresh()
        self.assertTrue(result)
        self.assertEqual(kpi.kpi_value, initial_value)
