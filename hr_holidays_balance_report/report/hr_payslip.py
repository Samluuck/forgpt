from odoo import models, fields, api
from datetime import datetime



class HrPayslipInherit(models.Model):
    _inherit = 'hr.payslip'

    balance_days = fields.Integer('Balance de días', compute='_compute_balance_days', store=True)
    dia_mes = fields.Integer(compute='obtener_dia_mes', string='Día del Mes', store=True)

    @api.depends('employee_id')
    def _compute_balance_days(self):
        for payslip in self:
            leave_balance_records = self.env['report.balance.leave'].search([
                ('emp_id', '=', payslip.employee_id.id),
                ('leave_type_id.es_vacacion', '=', True),  # Cambia 'VAC' por el código correspondiente a "Vacaciones"
            ])
            payslip.balance_days = leave_balance_records.balance_days if leave_balance_records else 0

    @api.depends('date_to')
    def obtener_dia_mes(self):
        print("######################### Entra aqui###########################33333")
        for payslip in self:
            if payslip.date_to:
                payslip.dia_mes = payslip.date_to.day
