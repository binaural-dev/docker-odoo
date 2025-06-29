# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    tax_classification = fields.Selection(
        string='Tax Classification',
        selection=[('value1', 'A'),
                   ('value2', 'B'),
                   ('value3', 'C'),
                   ],
        default='value1')

