import io
import json
from datetime import datetime, date
from dateutil.rrule import rrule, DAILY

from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import date_utils

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class HrAttendanceReport(models.TransientModel):
    """ Wizard for Employee Attendance Report """
    _name = 'employee.attendance.report'
    _description = 'Employee Attendance Report Wizard'

    from_date = fields.Date('Fecha desde', help="Fecha de inicio del informe")
    to_date = fields.Date('Fecha Hasta', help="Fecha de finalización del informe")
    employee_ids = fields.Many2many('hr.employee', string='Empleado',
                                    help='Nombre del Empleado')

    def action_print_xlsx(self):
        if not self.from_date:
            self.from_date = date.today()
        if not self.to_date:
            self.to_date = date.today()
        if self.from_date > self.to_date:
            raise ValidationError(_('Desde la fecha debe ser anterior a la fecha hasta.'))
        attendances = self.env['hr.attendance'].search(
            [('employee_id', 'in', self.employee_ids.ids)])
        data = {
            'from_date': self.from_date,
            'to_date': self.to_date,
            'employee_ids': self.employee_ids.ids
        }
        if self.employee_ids and not attendances:
            raise ValidationError(
                _("No hay registros de asistencia del empleado."))
        if self.from_date and self.to_date:
            return {
                'type': 'ir.actions.report',
                'data': {'model': 'employee.attendance.report',
                         'options': json.dumps(
                             data, default=date_utils.json_default),
                         'output_format': 'xlsx',
                         'report_name': 'Reporte de Asistencias',
                         },
                'report_type': 'xlsx',
            }

    def get_xlsx_report(self, data, response):

        query = """select hr_e.name,date(hr_at.check_in),
            SUM(hr_at.worked_hours) from hr_attendance hr_at LEFT JOIN
            hr_employee hr_e ON hr_at.employee_id = hr_e.id"""

        if not data['employee_ids']:
            query += """ GROUP BY date(check_in), hr_e.name"""

        else:
            query += """ WHERE hr_e.id in (%s) GROUP BY date(check_in),
            hr_e.name""" % (', '.join(str(employee_id)
                                      for employee_id in data['employee_ids']))
        self.env.cr.execute(query)
        docs = self.env.cr.dictfetchall()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('docs')
        start_date = datetime.strptime(data['from_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['to_date'], '%Y-%m-%d').date()
        date_range = rrule(DAILY, dtstart=start_date, until=end_date)
        sheet.set_column(1, 1, 15)
        sheet.set_column(2, 2, 15)
        border = workbook.add_format({'border': 1,'align': 'center'})
        green = workbook.add_format({'bg_color': '#28A828', 'border': 1,'align': 'center'})
        red = workbook.add_format({'bg_color': '#ff3333', 'border': 1,'align': 'center'})
        rose = workbook.add_format({'bg_color': '#DA70D6', 'border': 1,'align': 'center'})
        head = workbook.add_format({'bold': True, 'font_size': 30, 'align': 'center'})
        date_size = workbook.add_format({'font_size': 12, 'bold': True, 'align': 'center'})
        sheet.merge_range('C3:K6', 'Reporte de Asistencias', head)
        sheet.merge_range('B8:C9', 'Fecha desde: ' + data['from_date'], date_size)
        sheet.merge_range('B10:C11', 'Fecha Hasta: ' + data['to_date'], date_size)
        sheet.write(2, 12, '', green)
        sheet.write(2, 13, 'Presente')
        sheet.write(4, 12, '', red)
        sheet.write(4, 13, 'Ausente')
        sheet.write(6, 12, '', rose)
        sheet.write(6, 13, 'Medio dia')
        sheet.merge_range('B16:B17', 'Sl.No', border)
        sheet.merge_range('C16:C17', 'Empleado', border)
        row = 15
        col = 2
        for date_data in date_range:
            col += 1
            sheet.write(row, col, date_data.strftime('%Y-%m-%d'), border)
        row = 16
        col = 2
        for date_data in date_range:
            col += 1
            sheet.write(row, col, date_data.strftime('%a'), border)
        employee_names = []
        attendance_list = []
        for doc in docs:
            if doc['name'] not in employee_names:
                date_sum_list = []
                employee_names.append(doc['name'])
                for date_data in date_range:
                    date_out = date_data.strftime('%Y-%m-%d')
                    record_list = list(
                        filter(
                            lambda x: x['name'] == doc['name'] and x[
                                'date'].strftime(
                                '%Y-%m-%d') == date_out, docs))
                    if record_list:
                        date_sum_list.append(record_list[0])
                    else:
                        date_sum_list.append({
                            'name': '',
                            'date': '',
                            'sum': 0
                        })
                attendance_list.append(
                    {'name': doc['name'], 'items': date_sum_list})
        work = self.env.ref('resource.resource_calendar_std')
        row = 17
        i = 0
        for rec in attendance_list:
            row += 1
            col = 1
            i += 1
            sheet.write(row, col, i, border)
            col += 1
            sheet.write(row, col, rec['name'], border)
            for item in rec['items']:
                col += 1
                if item['sum'] >= work.hours_per_day:
                    sheet.write(row, col, 'Presente', green)
                elif 1 <= item['sum'] <= 4 or 4 <= item['sum'] <= \
                        work.hours_per_day:
                    sheet.write(row, col, 'Presente Medio dia', rose)
                else:
                    sheet.write(row, col, 'Ausente', red)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
