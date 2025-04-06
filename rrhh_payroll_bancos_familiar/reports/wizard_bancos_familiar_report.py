from odoo import api, fields, models
import datetime
from odoo.exceptions import ValidationError


class WizardBancoFamiliar(models.TransientModel):
    _name = 'wizard_bancos_familiar'
    _description = 'Wizard Banco Familiar'

    name = fields.Char(string='Nombre', required=True)
    date_from = fields.Date(string='Fecha Desde', required=True)
    date_to = fields.Date(string='Fecha Hasta', required=True)
    input_type_ids = fields.Many2many('hr.payslip.input.type', string='Tipos de entrada de Nómina')
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Lote de Nómina', required=True)

    def get_formatted_string_left(self, text, length, fill_character=' '):
        text = text or ''
        return text[:length].ljust(length, fill_character)

    def get_formatted_string_right(self, text, length, fill_character='0'):
        text = text or ''
        return text[:length].rjust(length, fill_character)

    def get_values_for_report_bancos_familiar(self):
        if not self.env.user.company_id.banco_familiar_nro_cuenta:
            raise ValidationError('Falta configuración del banco en la compañía.')

        # Filtrar nóminas por lote
        payslips = self.env['hr.payslip'].search([
            ('payslip_run_id', '=', self.payslip_run_id.id),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
        ]).filtered(lambda p: p.employee_id.bank_id.is_banco_familiar)

        final_text = []
        inputs_dates = []  # Inicializa la lista de fechas aquí
        c = 0  # Contador de registros

        for payslip in payslips:
            if self.input_type_ids:
                inputs = self.env['hr.payslip.input'].search([
                    ('input_type_id', 'in', self.input_type_ids.ids),
                    ('payslip_id', '=', payslip.id),
                ])
                lines_to_process = inputs
                inputs_dates.extend([i.payslip_id.date_to for i in inputs])  # Agrega fechas de los inputs
            else:
                # Asegurarse de que las fechas de las nóminas se agreguen cuando se procesan las líneas directamente
                lines_to_process = payslip.line_ids.filtered(lambda l: l.salary_rule_id.salario_neto)
                inputs_dates.append(payslip.date_to)  # Agrega la fecha de la nómina

            # Validar si el monto en cada línea es mayor a 0 antes de procesarla
            for line in lines_to_process:
                # Validar si el monto es mayor que 0 antes de continuar
                amount = line.total if self.input_type_ids else line.amount
                if amount > 0:
                    c += 1
                    line_text = ' CI'
                    line_text += self.get_formatted_string_left(payslip.employee_id.identification_id, 15)
                    line_text += self.get_formatted_string_left(payslip.employee_id.name, 80)
                    line_text += self.get_formatted_string_right(str(int(amount)), 18)  # Usar el monto de la línea
                    line_text += '00'
                    line_text += self.get_formatted_string_left('', 200)
                    final_text.append(line_text)

        first_line = 'PS'
        first_line += self.get_formatted_string_right(str(c), 3)
        first_line += self.get_formatted_string_left(self.name + ',Va', 20)
        first_line += self.get_formatted_string_right(datetime.date.strftime(datetime.date.today(), '%Y%m%d'), 8)
        first_line += 'S'
        first_line += 'PYG'
        first_line += self.get_formatted_string_left(self.env.user.company_id.banco_familiar_nro_cuenta, 11)
        first_line += self.get_formatted_string_left('', 200)

        final_text.insert(0, first_line)  # Inserta la primera línea al inicio del texto final
        return '\n'.join(final_text)  # Une todas las líneas con saltos de línea

    def print_wizard_bancos_familiar_report(self):
        action = self.env.ref('rrhh_payroll_bancos_familiar.wizard_bancos_familiar_report').report_action(self)
        if 'report_type' not in action or action['report_type'] != 'qweb-text':
            action['type'] = 'ir.actions.act_url'
            action['target'] = 'new'
            action['url'] += '&download=true'
        return action