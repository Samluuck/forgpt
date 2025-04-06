from odoo import api, fields, models, registry, _
from dateutil.relativedelta import relativedelta
import datetime
from datetime import timedelta
from odoo.exceptions import ValidationError


class EmployeeAttendanceRegister(models.TransientModel):
    _name = 'employee.attendance.register'
    _description = 'Employee Attendance Register'

    @api.model
    def default_get(self, default_fields):
        res = super(EmployeeAttendanceRegister, self).default_get(default_fields)
        today = datetime.date.today()
        first = today.replace(day=1)
        last_month_first = (today - timedelta(days=today.day)).replace(day=1)
        last_month = first - datetime.timedelta(days=1)
        res.update({
            'start_date': last_month_first or False,
            'end_date': last_month or False
        })
        return res

    @api.onchange('dept_id')
    def onchange_employee(self):
        for dept in self:
            emp = []
            for employee in self.env['hr.employee'].search([('department_id', '=', dept.dept_id.id)]):
                emp.append(employee.id)
            dept.employee_ids = emp

    dept_id = fields.Many2one('hr.department', 'Departamento')
    employee_ids = fields.Many2many('hr.employee', 'employee_rel', 'category_id', string='Empleado', required=True)
    start_date = fields.Date('Fecha de Inicio', required=True)
    end_date = fields.Date('Fecha Final', required=True)
    absent = fields.Char('Absent', default='A')

    def get_data(self):
        date_list = []
        start_date = self.start_date
        end_date = self.end_date
        delta = relativedelta(days=1)
        while start_date <= end_date:
            date_list.append({
                "date_list": start_date.day,
            })
            start_date += delta
        return date_list

    def check_attendance(self):
        data = []
        report = self.env['hr.attendance'].search(
            [('employee_id', 'in', self.employee_ids.ids), ('check_in', '>=', self.start_date),
             ('check_in', '<=', self.end_date)])
        for rec in report:
            val = rec.check_in.date()
            if rec.check_in:
                data.append({
                    'date': val.day,
                    'state': 'P',
                    'employee': rec.employee_id.id,
                    'department': rec.employee_id.department_id.id,
                })
        res_list = [i for n, i in enumerate(data)
                    if i not in data[n + 1:]]
        return res_list

    def print_pdf(self):
        return {
            'type': 'ir.actions.report',
            'report_name': 'rrhh_basics.report_attendance_register',
            'report_type': 'qweb-pdf'
        }



