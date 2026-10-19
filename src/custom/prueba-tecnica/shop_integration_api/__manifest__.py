{
    'name': 'Shop Integration API',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'API REST para integración con tienda en línea',
    'depends': ['sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/shop_api_log.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}