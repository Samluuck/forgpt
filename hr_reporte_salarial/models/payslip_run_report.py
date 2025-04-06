from odoo import models
from odoo.exceptions import ValidationError
import base64
import tempfile
import os
import xlsxwriter


class PayslipRunXls(models.AbstractModel):
    _name = 'report.rrhh.report_payslip_run'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        for obj in lines:
            report_name = 'Planilla de Pago: ' + obj.name
            # One sheet by partner
            sheet = workbook.add_worksheet(report_name[:31])
            bold = workbook.add_format({'bold': True, 'bg_color': '#B5B2B2', 'align': 'center'})
            cell_format = workbook.add_format()
            cell_format.set_align('center')
            final_col = len(obj.slip_ids[0].line_ids)

            sheet.merge_range(0, 0, 0, final_col + 6, report_name, bold)
            sheet.set_column(0, 0, 20, cell_format, {'collapsed': 1})
            sheet.write(1, 0, 'C.I.', bold)
            sheet.set_column(1, 1, 35, cell_format, {'collapsed': 1})
            sheet.write(1, 1, 'Apellido y Nombre', bold)
            sheet.set_column(2, 2, 30, cell_format, {'collapsed': 1})
            sheet.write(1, 2, 'Cuenta de Banco', bold)
            sheet.set_column(3, 3, 20, cell_format, {'collapsed': 1})
            sheet.write(1, 3, 'Número de Cuenta', bold)
            sheet.set_column(4, 4, 30, cell_format, {'collapsed': 1})
            sheet.write(1, 4, 'Departamento', bold)
            sheet.set_column(5, 5, 15, cell_format, {'collapsed': 1})
            sheet.write(1, 5, 'Días Trabajados', bold)
            sheet.set_column(6, 6, 15, cell_format, {'collapsed': 1})
            row = 1
            column = 6

            for titles in obj.slip_ids[0].line_ids:
                sheet.set_column(column, final_col, 20, cell_format, {'collapsed': 1})
                sheet.write(row, column, titles.name, bold)
                column += 1
            row = 2

            # Variables para almacenar los totales de cada columna
            total_dias_trabajados = 0
            total_dias_ausente = 0
            total_dias_ausente_por_enfermedad = 0
            total_dias_fuera_contrato = 0
            total_vacaciones = 0
            total_maternidad = 0
            total_amounts = [0] * len(obj.slip_ids[0].line_ids)

            for payslip in obj.slip_ids:
                column = 0
                sheet.write(row, column, payslip.employee_id.identification_id, cell_format)
                column += 1
                sheet.write(row, column, payslip.employee_id.name, cell_format)
                column += 1
                if payslip.employee_id.bank_account_id:
                    sheet.write(row, column, payslip.employee_id.bank_account_id.bank_id.name, cell_format)
                else:
                    sheet.write(row, column, "No posee cuenta", cell_format)
                column += 1
                if payslip.employee_id.bank_account_id:
                    sheet.write(row, column, payslip.employee_id.bank_account_id.acc_number, cell_format)
                else:
                    sheet.write(row, column, "No posee cuenta", cell_format)
                column += 1
                sheet.write(row, column, payslip.employee_id.department_id.name, cell_format)
                column += 1

                if payslip:
                    dias_ausente = 0
                    dias_ausente_por_enfermedad = 0
                    dias_fuera_contrato = 0
                    vacaciones = 0
                    maternidad = 0
                    worked_days = 0
                    for l in payslip.worked_days_line_ids:
                        if l.code == 'LEAVE90':
                            dias_ausente += l.number_of_days
                        if l.code == 'LEAVE110':
                            dias_ausente_por_enfermedad += l.number_of_days
                        if l.code == 'OUT':
                            dias_fuera_contrato += l.number_of_days
                        if l.code == 'VAC':
                            vacaciones += l.number_of_days
                        if l.code == 'MAT':
                            maternidad += l.number_of_days
                        if l.code == 'WORK100':
                            worked_days += l.number_of_days

                    if payslip.contract_id.structure_type_id.name == 'Mensualero':
                        if worked_days == 31:
                            dias_trabajados = worked_days - 1
                        elif worked_days < 31:
                            dias_trabajados = worked_days + dias_ausente + dias_ausente_por_enfermedad + dias_fuera_contrato + maternidad + vacaciones
                            if dias_trabajados == 31:
                                dias_trabajados = worked_days - 1
                            else:
                                dias_trabajados = worked_days
                        else:
                            dias_trabajados = worked_days
                    else:
                        dias_trabajados = worked_days

                    sheet.write(row, column, dias_trabajados, cell_format)  # Asegúrate de escribir el valor aquí
                    column += 1
                    total_dias_trabajados += dias_trabajados
                    total_dias_ausente += dias_ausente
                    total_dias_ausente_por_enfermedad += dias_ausente_por_enfermedad
                    total_dias_fuera_contrato += dias_fuera_contrato
                    total_vacaciones += vacaciones
                    total_maternidad += maternidad

                for i, amount in enumerate(payslip.line_ids):
                    sheet.write(row, column, amount.total, cell_format)
                    column += 1
                    total_amounts[i] += amount.total
                row += 1

            # Agregar la fila de totales al final
            sheet.write(row, 4, 'Totales', bold)
            sheet.write(row, 5, total_dias_trabajados, bold)
            column = 6
            for total_amount in total_amounts:
                sheet.write(row, column, total_amount, bold)
                column += 1