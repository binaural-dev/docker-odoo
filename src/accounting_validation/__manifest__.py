{
    'name': 'Accounting Payment Double Validation',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Requiere doble validación para pagos mayores a un monto configurable',
    'description': """
        Módulo que añade doble validación para pagos superiores a un monto límite
        configurable por compañía.
    """,
    'author': 'Leon Chacon',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/account_payment_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}