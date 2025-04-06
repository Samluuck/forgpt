from odoo import api, fields, models
import datetime


class WizardBancoSudameris(models.TransientModel):
    _name = 'wizard_bancos_sudameris'
    _description = 'Wizard Banco Sudameris'

    name = fields.Char(string='Nombre', required=True)
    date_from = fields.Date(string='Fecha Desde', required=True)
    date_to = fields.Date(string='Fecha Hasta', required=True)
    input_type_ids = fields.Many2many('hr.payslip.input.type', string='Tipos de entrada de Nómina')

    def print_wizard_bancos_sudameris_report(self):
        return self.env.ref('rrhh_payroll_bancos_sudameris.wizard_bancos_sudameris_report').report_action(self)

    def get_values_for_report_bancos_sudameris(self):
        def get_formatted_string_left(text, length, fill_character=' '):
            return (text or '').ljust(length, fill_character)
    
        def get_formatted_string_right(text, length, fill_character='0'):
            return (text or '').rjust(length, fill_character)
    
        payslips = self.env['hr.payslip'].search([
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
        ])
    
        final_text = ''
        inputs_dates = []
        c = 0
        total_amount = 0
    
        for payslip in payslips:
            if self.input_type_ids:
                inputs = self.env['hr.payslip.input'].search([
                    ('input_type_id', 'in', self.input_type_ids.ids),
                    ('payslip_id', '=', payslip.id),
                ])
                lines_to_process = inputs
                inputs_dates.extend([i.payslip_id.date_to for i in inputs])
            else:
                lines_to_process = payslip.line_ids.filtered(lambda l: l.salary_rule_id.salario_neto)
                inputs_dates.append(payslip.date_to)
    
            for line in lines_to_process:
                amount = line.amount if not self.input_type_ids else line.total
                total_amount += amount
                employee = payslip.employee_id
                name_parts = employee.name.split()
                first_name = name_parts[0] if len(name_parts) > 0 else ''
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
    
                c += 1
                final_text += '\nD;'
                final_text += get_formatted_string_left('PAGO DE SALARIO VIA BANCO', 30) + ';'
                final_text += get_formatted_string_left(last_name, 30) + ';'
                final_text += get_formatted_string_left(first_name, 30) + ';'
                final_text += get_formatted_string_right('586', 3) + ';'
                final_text += get_formatted_string_right('1', 2) + ';'
                final_text += get_formatted_string_left(employee.identification_id, 15) + ';'
                final_text += get_formatted_string_right('6900', 4) + ';'
                final_text += get_formatted_string_right(f"{int(amount * 100):.2f}", 18) + ';'
                final_text += get_formatted_string_left(payslip.date_to.strftime('%d/%m/%y'), 8) + ';'
                final_text += get_formatted_string_right('21', 3) + ';'
                final_text += get_formatted_string_right(employee.bank_account, 9) + ';'
                final_text += get_formatted_string_right('10', 3) + ';'
                final_text += get_formatted_string_right('6900', 4) + ';'
                final_text += get_formatted_string_right('', 9) + ';'
                final_text += get_formatted_string_right('', 3) + ';'
                final_text += get_formatted_string_right('', 3) + ';'
                final_text += get_formatted_string_left(self.env.user.company_id.banco_sudameris_cod_contrato, 18) + ';'
                final_text += get_formatted_string_right('1', 3) + ';'
                final_text += get_formatted_string_right(f"{total_amount:.2f}", 18) + ';'
                final_text += get_formatted_string_left('31/12/99', 8) + ';'
                final_text += get_formatted_string_left(datetime.date.today().strftime('%d/%m/%y'), 8)
    
        return final_text
