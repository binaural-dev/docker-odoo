# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import models, fields, api


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    def emplyee_bday(self):
        current_date = datetime.now().date()
        next_week = current_date + timedelta(days=7)

        return self.search([
            ('birthday', '!=', False),
            ('birthday', '>=', fields.Date.to_string(current_date)),
            ('birthday', '<=', fields.Date.to_string(next_week))
        ])

    def _send_birthday_reminders(self):
        template = self.env.ref('binaural_notification.birthday_reminder_email')
        employees = self.emplyee_bday()

        for employee in employees:
            template.send_mail(employee.id, force_send=True)

        return True



