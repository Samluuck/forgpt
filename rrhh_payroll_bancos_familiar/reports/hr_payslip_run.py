from odoo import models, fields, api, exceptions
import datetime

class HRPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def get_values_for_report_bancos_familiar(self):
        print("Ingrsa en get_values_for_report_bancos_familiar")
        final_text = ''
        bank = self.env.ref('reportes_ministerio_trabajo_py.banco_familiar', raise_if_not_found=False)
        if not bank:
            return "Error: El banco especificado no está disponible."

        payslips_all = self.slip_ids.filtered(
            lambda x: x.state in ['done', 'paid'] and x.employee_id.bank_id == bank
        )
        if not payslips_all:
            return "No hay nóminas completadas o pagadas para este banco."

        final_text += self.format_payslip_data(payslips_all)
        return final_text

    def format_payslip_data(self, payslips_all):
        print("Ingrsa en format_data")
        final_text = ''
        count = 0
        for contract in payslips_all.mapped('contract_id'):
            payslips_contract = payslips_all.filtered(lambda payslip: payslip.contract_id == contract)
            total_line = sum(payslips_contract.mapped('line_ids').filtered(lambda x: x.code == 'NET').mapped('total'))
            if total_line:
                count += 1
                final_text += self.format_payslip_line(contract, total_line)

        first_line = self.create_summary_line(count, payslips_all)
        return first_line + final_text

    def format_payslip_line(self, contract, total_line):
        print("Ingrsa en format_payslip_line")
        formatted_line = '\nCI'
        formatted_line += self.get_formatted_string_left(contract.employee_id.identification_id, 15)
        formatted_line += self.get_formatted_string_left(', '.join([contract.employee_id.apellido, contract.employee_id.nombre]), 80)
        formatted_line += self.get_formatted_string_right(str(total_line), 18)
        formatted_line += '00'
        formatted_line += self.get_formatted_string_left('', 200)
        return formatted_line

    def create_summary_line(self, count, payslips_all):
        print("Ingrsa en create_summary_line")
        first_line = 'PS'
        first_line += self.get_formatted_string_right(str(count), 3)
        first_line += self.get_formatted_string_left(','.join(payslip.name for payslip in payslips_all), 20)
        payslip_dates = payslips_all.mapped('date_to') + [datetime.date.today()]
        first_line += self.get_formatted_string_right(datetime.date.strftime(max(payslip_dates), '%Y%m%d'), 8)
        first_line += 'S'
        first_line += 'PYG'
        first_line += self.get_formatted_string_left(self.company_id.banco_familiar_nro_cuenta, 11)
        first_line += self.get_formatted_string_left('', 200)
        return first_line

    def get_formatted_string_left(self, text, length, fill_character=' '):
        print("Ingrsa en get_formatted_string_left")
        return (text or '').ljust(length, fill_character)

    def get_formatted_string_right(self, text, length, fill_character='0'):
        print("Ingrsa en get_formatted_string_right")
        return (text or '').rjust(length, fill_character)
