from odoo import models, fields, tools


class LeaveBalanceReport(models.Model):
    _name = 'report.balance.leave'
    _description = 'Leave Balance Report'
    _auto = False

    emp_id = fields.Many2one('hr.employee', string="Empleado", readonly=True)
    gender = fields.Char(string='Género', readonly=True)
    department_id = fields.Many2one('hr.department', string='Departamento', readonly=True)
    country_id = fields.Many2one('res.country', string='Nacionalidad', readonly=True)
    job_id = fields.Many2one('hr.job', string='Trabajo', readonly=True)
    leave_type_id = fields.Many2one('hr.leave.type', string='Tipo de licencia', readonly=True)
    allocated_days = fields.Integer('Saldo asignado')
    taken_days = fields.Integer('Asignaciones tomadas ')
    balance_days = fields.Integer('Balance Restante')
    company_id = fields.Many2one('res.company', string="Compañía")

    def init(self):
        """Loads report data"""
        tools.drop_view_if_exists(self._cr, 'report_balance_leave')
        self._cr.execute("""
            CREATE or REPLACE view report_balance_leave as (
            SELECT 
                row_number() OVER (ORDER BY e.id) AS id, 
                e.id AS emp_id,
                e.gender AS gender,
                e.country_id AS country_id,
                e.department_id AS department_id,
                e.job_id AS job_id,
                al.holiday_status_id AS leave_type_id, 
                al.allocated_days,  -- Mantenemos los días asignados correctamente
                COALESCE(SUM(l.number_of_days), 0) AS taken_days, 
                al.allocated_days - COALESCE(SUM(l.number_of_days), 0) AS balance_days, 
                e.company_id AS company_id
            FROM
                hr_employee e
            JOIN 
                (SELECT employee_id, holiday_status_id, SUM(number_of_days) AS allocated_days 
                FROM hr_leave_allocation 
                GROUP BY employee_id, holiday_status_id) al
                ON al.employee_id = e.id  
            LEFT JOIN 
                hr_leave l ON l.employee_id = e.id AND l.holiday_status_id = al.holiday_status_id  
            WHERE
                e.active = true
            GROUP BY
                e.id, al.holiday_status_id, al.allocated_days, e.gender, e.country_id, 
                e.department_id, e.job_id, e.company_id)
            """)
