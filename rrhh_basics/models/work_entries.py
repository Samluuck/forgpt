from odoo import models, fields, api
from datetime import date, timedelta

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def get_current_month_range(self):
        """Calcula el primer y último día del mes actual."""
        today = date.today()
        first_day = today.replace(day=1)
        last_day = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        return first_day, last_day

    def update_work_entries(self, start_date=None, end_date=None):
        """Actualiza las entradas de trabajo eliminando las existentes y generando nuevas."""

        # Si no se pasan fechas, calcula el mes actual automáticamente
        if not start_date or not end_date:
            start_date, end_date = self.get_current_month_range()

        for emp in self:
            # Elimina las entradas de trabajo existentes en el rango de fechas
            work_entries = self.env['hr.work.entry'].search([
                ('employee_id', '=', emp.id),
                ('date_start', '>=', start_date),
                ('date_stop', '<=', end_date)
            ])
            work_entries.unlink()

            # Genera nuevas entradas de trabajo para el empleado
            new_work_entries = emp.generate_work_entries(start_date, end_date, True)

            # Verifica si el retorno no es `False`
            if new_work_entries and isinstance(new_work_entries, (list, models.BaseModel)):
                # Si la función devuelve una lista, convertirla a recordset
                if isinstance(new_work_entries, list):
                    new_work_entries = self.env['hr.work.entry'].browse([entry.id for entry in new_work_entries])

                # Si hay nuevas entradas, imprime los ids
                if new_work_entries:
                    print(f"Nuevas entradas de trabajo creadas para {emp.name}: {new_work_entries.ids}")
            else:
                print(f"No se generaron nuevas entradas de trabajo para {emp.name}.")
