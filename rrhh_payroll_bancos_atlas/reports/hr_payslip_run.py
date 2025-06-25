from odoo import models, fields, api, exceptions
import datetime
from odoo.exceptions import UserError

class HRPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def get_values_for_report_bancos_atlas(self):
        def change_characters(text):
            allowed_characters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ .,1234567890'
            for character_pair in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n')]:
                text = text.replace(character_pair[0], character_pair[1])
                text = text.replace(character_pair[0].upper(), character_pair[1].upper())
            for character in text:
                if character not in allowed_characters:
                    text = text.replace(character, ' ')
            return text

        def get_formatted_string_left(text, lenght, fill_character=' '):
            text = change_characters(text or '')
            return text[:lenght].ljust(lenght, fill_character)

        def get_formatted_string_right(text, lenght, fill_character='0'):
            text = change_characters(text or '')
            return text[:lenght].rjust(lenght, fill_character)

        final_text = ''

        payslips_all = self.slip_ids.filtered(
            lambda x: x.state in ['done', 'paid'] and x.employee_id.bank_id == self.env.ref('reportes_ministerio_trabajo_py.banco_atlas'))
        if not payslips_all:
            return final_text

        payslip_dates = payslips_all.mapped('date_to')
        payslip_dates.append(datetime.date.today())

        for contract in payslips_all.mapped('contract_id'):
            payslips_contract = payslips_all.filtered(lambda payslip: payslip.contract_id == contract)
            payslips_contract_amount = int(sum(payslips_contract.line_ids.filtered(lambda x: x.code in ['NET']).mapped('total')))
            if payslips_contract_amount:
                description = ', '.join([payslip.name.replace('/', ' ') for payslip in payslips_contract])
                final_text += 'D'  # ITIREG
                final_text += '01'  # ITITRA
                final_text += get_formatted_string_right(self.company_id.banco_atlas_codigo_empresa, 3)  # ICDSRV
                final_text += get_formatted_string_right(self.company_id.banco_atlas_nro_cuenta, 10)  # ICTDEB
                final_text += '017'  # IBCOCR
                final_text += get_formatted_string_right(contract.employee_id.bank_account, 10)  # ICTCRE
                final_text += 'C'  # ITCRDB
                final_text += get_formatted_string_left(contract.employee_id.nombre + ' ' + contract.employee_id.apellido, 50)  # IORDEN
                final_text += '0'  # IMONED
                final_text += get_formatted_string_right((str(payslips_contract_amount) + '00'), 15)  # IMTOTR
                final_text += get_formatted_string_right('', 15)  # IMTOT2
                final_text += get_formatted_string_left((contract.employee_id.identification_id), 12)  # INRODO
                final_text += '0'  # ITIFAC
                final_text += get_formatted_string_left('', 20)  # INRFAC
                final_text += '000'  # INRCUO
                final_text += get_formatted_string_right(datetime.date.strftime(max(payslip_dates), '%Y%m%d'), 8)  # IFCHCR
                final_text += get_formatted_string_right('', 8)  # IFCHC2
                final_text += get_formatted_string_left('', 50)  # ICEPTO
                final_text += get_formatted_string_left(description, 15)  # INRREF
                final_text += get_formatted_string_right(datetime.date.strftime(max(payslip_dates), '%Y%m%d'), 8)  # IFECCA
                final_text += get_formatted_string_right('080000', 6)  # IHORCA
                final_text += get_formatted_string_left('', 10)  # IUSUCA
                final_text += '\n'
        
        final_text += 'C'  # ITIREG
        final_text += '00'  # ITITRA
        final_text += get_formatted_string_right('', 3)  # ICDSRV
        final_text += get_formatted_string_right(self.company_id.banco_atlas_nro_cuenta, 10)  # ICTDEB
        final_text += '000'  # IBCOCR
        final_text += get_formatted_string_right('', 10)  # ICTCRE
        final_text += ' '  # ITCRDB
        final_text += get_formatted_string_left('', 50)  # IORDEN
        final_text += '0'  # IMONED
        final_text += get_formatted_string_right((str(int(sum(payslips_all.line_ids.filtered(lambda x: x.code in ['NET']).mapped('total')))) + '00'), 15)  # IMTOTR
        final_text += get_formatted_string_right('', 15)  # IMTOT2
        final_text += get_formatted_string_left('', 12)  # INRODO
        final_text += '0'  # ITIFAC
        final_text += get_formatted_string_left('', 20)  # INRFAC
        final_text += '000'  # INRCUO
        final_text += get_formatted_string_left('', 8, '0')  # IFCHCR
        final_text += get_formatted_string_left('', 8, '0')  # IFCHC2
        final_text += get_formatted_string_left('', 50)  # ICEPTO
        final_text += get_formatted_string_left('', 15)  # INRREF
        final_text += get_formatted_string_right(datetime.date.strftime(max(payslip_dates), '%Y%m%d'), 8)  # IFECCA
        final_text += get_formatted_string_right('000000', 6)  # IHORCA
        final_text += get_formatted_string_left('', 10)  # IUSUCA

        return final_text