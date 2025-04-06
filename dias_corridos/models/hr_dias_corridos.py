from odoo import models, fields, api
from datetime import datetime, timedelta


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_total_days_in_month(self, date):
        """Get the total number of days in the month of the given date."""
        year = date.year
        month = date.month
        # Calculate the last day of the month
        last_day = (datetime(year, month + 1, 1) - timedelta(days=1)).day
        return last_day

    def _update_leave_days_in_payslip(self):
        """Actualiza el número de días en las entradas de trabajo del recibo de nómina
        basándose en las ausencias validadas del empleado, solo si es corrido."""
        for payslip in self:
            # Obtener el empleado asociado al recibo de nómina
            employee = payslip.employee_id

            # Obtener todas las ausencias validadas del empleado en el rango de fechas del recibo de nómina
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),  # Solo ausencias validadas
                ('request_date_from', '<=', payslip.date_to),
                ('request_date_to', '>=', payslip.date_from)
            ])

            # Para cada ausencia validada, verificar si es corrido y actualizar o crear la línea correspondiente en worked_days
            for leave in leaves:
                # Verificar si el tipo de ausencia tiene el campo es_corrido marcado
                if leave.holiday_status_id.es_corrido:
                    work_entry_type = leave.holiday_status_id.work_entry_type_id
                    if not work_entry_type:
                        continue  # Si no tiene un tipo de entrada de trabajo, saltamos

                    # Buscar si ya existe una línea de días trabajados para esta entrada de trabajo
                    worked_days_line = payslip.worked_days_line_ids.filtered(
                        lambda line: line.work_entry_type_id == work_entry_type
                    )

                    if worked_days_line:
                        # Actualizar la línea existente con el número de días de la ausencia
                        worked_days_line.number_of_days = leave.number_of_days_display
                        worked_days_line.number_of_hours = leave.number_of_days_display * 8  # Ajusta si es necesario
                    else:
                        # Crear una nueva línea con el número de días de la ausencia
                        self.env['hr.payslip.worked_days'].create({
                            'payslip_id': payslip.id,
                            'work_entry_type_id': work_entry_type.id,
                            'number_of_days': leave.number_of_days_display,
                            'number_of_hours': leave.number_of_days_display * 8,  # Ajusta si es necesario
                        })

    def compute_sheet(self):
        """Sobreescribe el método compute_sheet para incluir el cálculo de los días de ausencias."""
        super(HrPayslip, self).compute_sheet()
        # Llama a la función personalizada para actualizar las ausencias en worked_days
        self._update_leave_days_in_payslip()