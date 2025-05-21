from odoo import models
from datetime import datetime, timedelta

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_total_days_in_month(self, date):
        """Get the total number of days in the month of the given date."""
        year = date.year
        month = date.month
        if month == 12:
            last_day = 31
        else:
            last_day = (datetime(year, month + 1, 1) - timedelta(days=1)).day
        return last_day

    def _update_leave_days_in_payslip(self):
        """Actualiza el número de días en las entradas de trabajo del recibo de nómina
        basándose en las ausencias validadas del empleado, solo si es corrido."""
        for payslip in self:
            employee = payslip.employee_id

            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', payslip.date_to),
                ('request_date_to', '>=', payslip.date_from)
            ])

            for leave in leaves:
                if leave.holiday_status_id.es_corrido:
                    work_entry_type = leave.holiday_status_id.work_entry_type_id
                    if not work_entry_type:
                        continue

                    worked_days_line = payslip.worked_days_line_ids.filtered(
                        lambda line: line.work_entry_type_id == work_entry_type
                    )

                    number_of_days = leave.number_of_days or 0

                    if worked_days_line:
                        worked_days_line.number_of_days = number_of_days
                        worked_days_line.number_of_hours = number_of_days * 8
                    else:
                        self.env['hr.payslip.worked_days'].create({
                            'payslip_id': payslip.id,
                            'work_entry_type_id': work_entry_type.id,
                            'number_of_days': number_of_days,
                            'number_of_hours': number_of_days * 8,
                        })

    def compute_sheet(self):
        res = super(HrPayslip, self).compute_sheet()
        self._update_leave_days_in_payslip()
        return res
