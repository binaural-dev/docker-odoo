{
    'name': 'Stock Critical Alerts',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Genera alertas cuando el stock de producto cae por debajo de un umbral predefinido', 
    'description': """
        Este módulo añade un umbral mínimo de stock configurable a las plantillas de producto.
        Genera automáticamente un mensaje de alerta en el chat del producto cuando el stock disponible cae por debajo del umbral configurado.
        También proporciona una vista del panel de productos en estado crítico de stock.
    """,
    'author': 'Ronald Villa',
    'depends': ['stock', 'mail'],
    'data': [
        'views/product_template_views.xml',
        'views/stock_critical_dashboard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
