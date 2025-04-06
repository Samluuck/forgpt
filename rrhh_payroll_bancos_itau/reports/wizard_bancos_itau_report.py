from odoo import api, fields, models, exceptions
import datetime
import logging

_logger = logging.getLogger(__name__)

class WizardBancoItau(models.TransientModel):
    _name = 'wizard_bancos_itau'
    _description = 'Wizard Banco Itau'

    name = fields.Char(string='Nombre', required=True)
    date_from = fields.Date(string='Fecha Desde', required=True)
    date_to = fields.Date(string='Fecha Hasta', required=True)
    input_type_ids = fields.Many2many('hr.payslip.input.type', string='Tipos de Input de Nómina')
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Lote de Nómina', required=True)

    def change_characters(self, text):
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'Ñ': 'N'
        }
        return ''.join(replacements.get(c, c) for c in text if
                       c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ .,1234567890' or c in replacements)

    def get_formatted_string_left(self, text, length, fill_character=' '):
        text = self.change_characters(text or '')
        return text[:length].ljust(length, fill_character)

    def get_formatted_string_right(self, text, length, fill_character='0'):
        text = self.change_characters(text or '')
        return text[:length].rjust(length, fill_character)

    def get_values_for_report_bancos_itau(self):
        if not self.env.user.company_id.banco_itau_codigo_empresa or not self.env.user.company_id.banco_itau_nro_cuenta:
            raise exceptions.ValidationError('Falta configuración del banco en la compañía.')

        payslips = self.env['hr.payslip'].search([
            ('payslip_run_id', '=', self.payslip_run_id.id),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
        ]).filtered(lambda x: x.employee_id.bank_id.is_banco_itau)

        final_text = ''
        total_control = 0

        for payslip in payslips:
            total_amount = sum(line.amount for line in payslip.line_ids if line.category_id.code == 'NET')

            if int(total_amount) > 0:  # Convertir a entero para validar
                formatted_amount = self.get_formatted_string_right(str(int(total_amount * 100)), 15)
                # Espacios en blanco para la posición original del campo `self.name`
                empty_space = self.get_formatted_string_left('', 50)

                fecha_carga = self.get_formatted_string_right(self.date_to.strftime('%Y%m%d'), 8)

                # Mueve `self.name` al rango 214-228
                moved_name = self.get_formatted_string_left(self.name, 15)

                record = 'D01' + \
                         self.get_formatted_string_right(self.env.user.company_id.banco_itau_codigo_empresa, 3) + \
                         self.get_formatted_string_right(self.env.user.company_id.banco_itau_nro_cuenta, 10) + \
                         '017' + \
                         self.get_formatted_string_right(payslip.employee_id.bank_account, 10) + \
                         'C' + \
                         self.get_formatted_string_left(payslip.employee_id.name.upper(), 50) + \
                         '0' + \
                         formatted_amount + \
                         self.get_formatted_string_right('', 15) + \
                         self.get_formatted_string_left(payslip.employee_id.identification_id, 12) + \
                         '0' + \
                         self.get_formatted_string_left('', 20) + \
                         self.get_formatted_string_right('', 3) + \
                         self.get_formatted_string_right(datetime.date.strftime(datetime.date.today(), '%Y%m%d'), 8) + \
                         self.get_formatted_string_right('', 8) + \
                         empty_space + \
                         self.get_formatted_string_left(moved_name.upper(), 15) + \
                         self.get_formatted_string_right(datetime.date.strftime(datetime.date.today(), '%Y%m%d'), 8) + \
                         self.get_formatted_string_right(datetime.datetime.now().strftime('%H%M%S'), 6) + \
                         self.get_formatted_string_left('', 10)  # Nombre del usuario que cargó

                record = record.ljust(252, ' ')
                final_text += record + '\n'
                total_control += int(total_amount * 100)

        # Añadir el registro de control al final del archivo con el total correcto
        control_record = 'C' + \
                         self.get_formatted_string_right('', 5) + \
                         self.get_formatted_string_right(self.env.user.company_id.banco_itau_nro_cuenta, 10) + \
                         self.get_formatted_string_right('', 13) + \
                         self.get_formatted_string_left('', 51) + \
                         '0' + \
                         self.get_formatted_string_right(str(total_control), 15) + \
                         self.get_formatted_string_right('', 15) + \
                         self.get_formatted_string_left('', 12) + \
                         '0' + \
                         self.get_formatted_string_left('', 20) + \
                         self.get_formatted_string_right('', 19) + \
                         self.get_formatted_string_left('', 65) + \
                         self.get_formatted_string_right(datetime.date.strftime(datetime.date.today(), '%Y%m%d'), 8) + \
                         self.get_formatted_string_right('', 6) + \
                         self.get_formatted_string_left('', 10)

        control_record = control_record.ljust(252, ' ')
        final_text += control_record + '\n'

        return final_text

    def print_wizard_bancos_itau_report(self):
        action = self.env.ref('rrhh_payroll_bancos_itau.wizard_bancos_itau_report').report_action(self)
        return action
