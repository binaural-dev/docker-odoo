{
    'name': 'Inventario - Alertas',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Alertas de stock crítico para productos',
    'author': 'Tu Nombre',
    'depends': ['stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'data/cron_stock_alert.xml',
        'views/stock_critical_dashboard_view.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}