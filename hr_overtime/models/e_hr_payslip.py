from odoo import api, fields, models, Command
from odoo.exceptions import ValidationError

class PayslipOverTime(models.Model):
    _inherit = 'hr.payslip'

    overtime_ids = fields.Many2many('hr.overtime', string="Overtime Requests")

    def get_payslip_inputs_hook_overtime(self):
        results = []
        for rec in self:
            if not rec.employee_id or not rec.date_from or not rec.date_to:
                continue

            diurnal_type = self.env.ref('hr_overtime.input_overtime_diurnal_payroll', raise_if_not_found=False)
            nocturnal_type = self.env.ref('hr_overtime.input_overtime_nocturnal_payroll', raise_if_not_found=False)
            if not diurnal_type or not nocturnal_type:
                continue

            overtimes = self.env['hr.overtime'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('contract_id', '=', rec.contract_id.id),
                ('state', '=', 'approved'),
                ('payslip_paid', '=', False),
                ('date_from', '>=', rec.date_from),
                ('date_to', '<=', rec.date_to),
                ('type', '=', 'cash'),
            ])

            total_diurnal = sum(o.cash_hrs_diurnal_amount for o in overtimes)
            total_nocturnal = sum(o.cash_hrs_nocturnal_amount for o in overtimes)

            if total_diurnal:
                results.append({
                    'name': "50%",
                    'code': diurnal_type.code,
                    'amount': total_diurnal,
                    'sequence': 10,
                    'input_type_id': diurnal_type.id,
                    'contract_id': rec.contract_id.id,
                    'payslip_id': rec.id,
                })

            if total_nocturnal:
                results.append({
                    'name': "100%",
                    'code': nocturnal_type.code,
                    'amount': total_nocturnal,
                    'sequence': 11,
                    'input_type_id': nocturnal_type.id,
                    'contract_id': rec.contract_id.id,
                    'payslip_id': rec.id,
                })
        return results

    def compute_sheet(self):
        for rec in self:
            rec.get_payslip_inputs()
            super(PayslipOverTime, rec).compute_sheet()

    def action_payslip_done(self):
        """
        Marca las solicitudes de horas extras como pagadas solo si la nómina está en estado 'done'.
        Versión optimizada para procesamiento masivo.
        """
        # Procesamiento estándar de nóminas
        result = super(PayslipOverTime, self).action_payslip_done()
        
        # Procesar horas extras para cada nómina
        for payslip in self:
            # Verificar estado (considera 'verify' como 'done')
            if payslip.state in ('verify', 'done'):
                # Buscar y marcar horas extras pendientes
                overtimes = self.env['hr.overtime'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('contract_id', '=', payslip.contract_id.id),
                    ('state', '=', 'approved'),
                    ('payslip_paid', '=', False),
                    ('date_from', '>=', payslip.date_from),
                    ('date_to', '<=', payslip.date_to)
                ])
                
                if overtimes:
                    overtimes.write({'payslip_paid': True})
                    # Log opcional para auditoría
                    payslip.message_post(body=f"Marcadas {len(overtimes)} horas extras como pagadas")
        
        return result
