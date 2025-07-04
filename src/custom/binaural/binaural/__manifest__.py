# -*- coding: utf-8 -*-
{
    'name': "Binaural",

    'summary': "A custom module for Binaural",

    'description': """
A custom module for Binaural
    """,

    'author': "Anderson Alejandro García Ascanio",
    'website': "https://www.binaural.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Services',
    'version': '17.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/account_move.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'test': ['tests/tax_classification_unit_test.py']
}

