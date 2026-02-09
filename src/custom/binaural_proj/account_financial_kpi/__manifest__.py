{
    'name': 'Account Financial KPI',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Financial health indicators dashboard for the company',
    'description': 'Creates a dashboard with simple financial health indicators including traffic light visualization based on thresholds.',
    'author': 'Binaural',
    'website': 'https://www.binaural.es',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_financial_kpi_data.xml',
        'views/account_financial_kpi_views.xml',
        'views/account_financial_kpi_dashboard.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_financial_kpi/static/src/css/kpi_dashboard.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
