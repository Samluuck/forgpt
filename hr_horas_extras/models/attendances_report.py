from odoo import models



class PayslipRunXls(models.AbstractModel):
    _name = 'report.rrhh.report_attendances'

    def generate_xlsx_report(self, workbook, data, lines):
        for obj in lines:
            report_name = 'Planilla de Pago: '+obj.name
            # One sheet by partner
            sheet = workbook.add_worksheet(report_name[:31])
            bold = workbook.add_format({'bold': True, 'bg_color': '#B5B2B2', 'align': 'center'})
            cell_format = workbook.add_format()
            cell_format.set_align('center')
            final_col = len(obj.slip_ids[0].line_ids)

            sheet.merge_range(0, 0, 0, final_col + 4, report_name, bold)
            sheet.set_column(0, 0, 20, cell_format, {'collapsed': 1})
            sheet.write(1, 0, 'C.I.', bold)
            sheet.set_column(1, 1, 35, cell_format, {'collapsed': 1})
            sheet.write(1, 1, 'Apellido y Nombre', bold)
            sheet.set_column(2, 2, 30, cell_format, {'collapsed': 1})
            sheet.write(1, 2, 'Departamento', bold)
            sheet.set_column(3, 3, 15, cell_format, {'collapsed': 1})
            sheet.write(1, 3, 'Días Trabajados', bold)
            sheet.set_column(4, 4, 15, cell_format, {'collapsed': 1})
            row = 1
            column =4

            for titles in obj.slip_ids[0].line_ids:
                sheet.set_column(column, final_col, 20, cell_format, {'collapsed': 1})
                sheet.write(row, column, titles.name, bold)
                column += 1
            row = 2
            for payslip in obj.slip_ids:
                column = 0
                sheet.write(row, column, payslip.employee_id.identification_id, cell_format)
                column += 1
                sheet.write(row, column, payslip.employee_id.name, cell_format)
                column += 1
                sheet.write(row, column, payslip.employee_id.department_id.name, cell_format)
                column += 1

                if payslip:
                    dias_ausente = 0
                    dias_ausente_por_enfermedad = 0
                    dias_fuera_contrato =0
                    vacaciones = 0
                    maternidad = 0
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

                    sheet.write(row, column,30-(dias_ausente+dias_ausente_por_enfermedad+dias_fuera_contrato+maternidad), cell_format)
                    column += 1


                for amount in payslip.line_ids:
                    sheet.write(row, column, amount.total, cell_format)
                    column += 1
                row += 1

