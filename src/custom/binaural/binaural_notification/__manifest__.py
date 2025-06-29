# -*- coding: utf-8 -*-
{
    'name': "binaural_notification",

    'summary': "Binaural Notification",

    'description': """
A module for binaural notification, such as birthdays, anniversaries, etc.
    """,

    'author': "Binaural",
    'website': "https://www.binaural.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
        'data/mail.xml',
        'data/birthday_cron.xml',
        'views/hr_employees.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

