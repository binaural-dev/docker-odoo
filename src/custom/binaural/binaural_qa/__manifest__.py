# -*- coding: utf-8 -*-
{
    'name': "Binaural QA",

    'summary': "Cutom module for Binaural QA",

    'description': """
Custom module for Binaural to perform QA to product quality
    """,

    'author': "Binaural",
    'website': "https://www.binaural.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Products',
    'version': '17.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
        'models/quality_check_required.xml',
        'views/stock_view.xml',
        'wizards/quality_check_wizard_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3'
}

