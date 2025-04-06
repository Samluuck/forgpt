import io
import datetime
import pytz
import xlsxwriter
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64

class HrAttendanceReport(models.TransientModel):
    _name = 'employee.attendance.report'
    _description = 'Employee Attendance Report Wizard'

    from_date = fields.Date('Fecha desde', required=True)
    to_date = fields.Date('Fecha hasta', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Empleado')
    location_id = fields.Many2one('zk.machine.location', string="Ubicación del Reloj")
    file = fields.Binary('Download Report', readonly=True)
    file_name = fields.Char('File Name')

    def action_print_xlsx(self):
        # Validaciones de fechas y empleados
        if self.from_date > self.to_date:
            raise ValidationError(_('La fecha "Desde" debe ser anterior o igual a la fecha "Hasta".'))

        # Generación del reporte
        file_path = self._generate_xlsx_report_per_employee()
        with open(file_path, "rb") as file:
            self.file = base64.b64encode(file.read())
        self.file_name = 'Reporte_de_Asistencias.xlsx'

        # Retornar acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=file&download=true&filename={self.file_name}',
            'target': 'self',
        }

    def _generate_xlsx_report_per_employee(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Definir formatos de celda para el reporte
        normal_red_format = workbook.add_format({'font_color': 'red', 'align': 'center'})
        normal_format = workbook.add_format({
            'font_size': 12,
            'font_name': 'Times New Roman',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': '0.00',
        })
        bold_format = workbook.add_format({
            'font_size': 12,
            'font_name': 'Calibri',
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'bold': True,
            'num_format': '0.00',
            'bg_color': '#C0C0C0'
        })
        title_format = workbook.add_format({
            'font_name': 'Calibri',
            'bold': True,
            'font_size': 20,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#C0C0C0'
        })
        header_format = workbook.add_format({
            'font_name': 'Calibri',
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#C0C0C0',
            'border': 1
        })
        normal_format_decimal = workbook.add_format({
            'align': 'center',
            'num_format': '0.00',
            'font_size': 10,
            'valign': 'vcenter',
        })

        if not self.employee_ids:
            all_employee_ids = self.env['hr.employee'].search([])
        else:
            all_employee_ids = self.employee_ids

        # Obtener la zona horaria del usuario
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        #utc_tz = pytz.utc

        for employee in all_employee_ids:
            # Corregir el dominio para aplicar correctamente el rango de fechas
            domain = [
                ('employee_id', '=', employee.id),
                '|',
                '&', ('check_in', '>=', self.from_date), ('check_in', '<=', self.to_date),
                '&', ('check_out', '>=', self.from_date), ('check_out', '<=', self.to_date)
            ]

            # Si se selecciona una ubicación, agregarla al dominio
            if self.location_id:
                domain.append(('machine_id.location_id', '=', self.location_id.id))

            # Obtener asistencias del empleado filtradas por ubicación y fecha
            attendances = self.env['hr.attendance'].search(domain, order='check_in asc')

            # Crear una hoja para el empleado solo si tiene asistencias
            if attendances:
                sheet_name = employee.name[:31]  # Limitar el nombre a 31 caracteres
                sheet = workbook.add_worksheet(sheet_name)
                sheet.merge_range('A1:L1', 'Reporte de Asistencia', title_format)
                sheet.set_row(0, 40)
                headers = [
                    'Fecha', 'Máquina', 'Ubicación', 'Entrada', 'Salida', 'Horas Nocturnas', 'Horas Extras Diurnas',
                    'Horas Extras Nocturnas', 'Llegadas Tardías (Min)', 'Horas Extras Domingos y Feriados',
                    'Horas Trabajadas', 'Llegada Anticipada (Min)'
                ]

                for col, header in enumerate(headers):
                    sheet.write(1, col, header, header_format)
                    sheet.set_column(col, col, len(header) * 1.3)

                row = 2
                # Generar lista de fechas en el rango
                current_date = self.from_date
                while current_date <= self.to_date:
                    # Verificar si el día es domingo
                    is_sunday = current_date.weekday() == 6

                    # Filtrar todas las asistencias de la fecha actual
                    day_attendances = attendances.filtered(
                        lambda a: (
                                (a.check_in and a.check_in.date() == current_date) or
                                (a.check_out and a.check_out.date() == current_date)
                        )
                    )

                    if day_attendances:
                        # Procesar cada asistencia individualmente
                        for attendance in day_attendances:
                            local_check_in = pytz.utc.localize(attendance.check_in).astimezone(
                                user_tz) if attendance.check_in else None
                            local_check_out = pytz.utc.localize(attendance.check_out).astimezone(
                                user_tz) if attendance.check_out else None

                            # Formatear los tiempos
                            formatted_check_in_time = local_check_in.strftime('%H:%M:%S') if local_check_in else 'A'
                            formatted_check_out_time = local_check_out.strftime('%H:%M:%S') if local_check_out else 'A'

                            # Escribir la asistencia en la hoja
                            sheet.write(row, 0, current_date.strftime('%d/%m/%Y'), normal_format)
                            sheet.write(row, 1, attendance.machine_id.name if attendance.machine_id else '',
                                        normal_format)
                            sheet.write(row, 2, attendance.machine_id.location_id.name if attendance.machine_id else '',
                                        normal_format)
                            sheet.write(row, 3, formatted_check_in_time,
                                        normal_format if local_check_in else normal_red_format)
                            sheet.write(row, 4, formatted_check_out_time,
                                        normal_format if local_check_out else normal_red_format)
                            sheet.write(row, 5, attendance.horas_nocturnas or 0, normal_format_decimal)
                            sheet.write(row, 6, attendance.horas_diurnas or 0, normal_format_decimal)
                            sheet.write(row, 7, attendance.horas_nocturnas or 0, normal_format_decimal)
                            sheet.write(row, 8, attendance.late_check_in or 0, normal_format_decimal)
                            sheet.write(row, 9, attendance.horas_domifer or 0, normal_format_decimal)
                            sheet.write(row, 10, attendance.worked_hours or 0, normal_format_decimal)
                            sheet.write(row, 11, attendance.early_check_in or 0, normal_format_decimal)
                            row += 1
                    else:
                        # Si no hay asistencias, agregar la fecha con "A" en entrada y salida, excepto domingos
                        if not is_sunday:
                            sheet.write(row, 0, current_date.strftime('%d/%m/%Y'), normal_format)
                            sheet.write(row, 1, '', normal_format)
                            sheet.write(row, 2, '', normal_format)
                            sheet.write(row, 3, 'A', normal_red_format)  # "A" en rojo
                            sheet.write(row, 4, 'A', normal_red_format)  # "A" en rojo
                            sheet.write(row, 5, 0, normal_format_decimal)
                            sheet.write(row, 6, 0, normal_format_decimal)
                            sheet.write(row, 7, 0, normal_format_decimal)
                            sheet.write(row, 8, 0, normal_format_decimal)
                            sheet.write(row, 9, 0, normal_format_decimal)
                            sheet.write(row, 10, 0, normal_format_decimal)
                            sheet.write(row, 11, 0, normal_format_decimal)
                            row += 1

                    # Incrementar al día siguiente
                    current_date += datetime.timedelta(days=1)

        workbook.close()
        output.seek(0)

        # Guardar el archivo en el sistema de archivos
        file_path = "/tmp/Attendance_Report_Per_Employee.xlsx"
        with open(file_path, "wb") as file:
            file.write(output.getvalue())

        return file_path