from odoo import models, fields, api
from datetime import timedelta

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.depends('request_date_from', 'request_date_to', 'holiday_status_id')
    def _compute_number_of_days(self):
        """
        Calcula automáticamente los días corridos cuando el tipo de ausencia
        tiene el campo `es_corrido` activado.
        """
        for leave in self:
            if leave.holiday_status_id and leave.holiday_status_id.es_corrido:
                if leave.request_date_from and leave.request_date_to:
                    # Normaliza las fechas y calcula días corridos
                    leave.number_of_days = (leave.request_date_to - leave.request_date_from).days + 1
                else:
                    leave.number_of_days = 0
            else:
                # Lógica estándar de Odoo si no es "corrido"
                for holiday in self:
                    if holiday.date_from and holiday.date_to:
                        holiday.number_of_days = holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)['days']
                    else:
                        holiday.number_of_days = 0

    @api.onchange('request_date_from', 'request_date_to', 'holiday_status_id')
    def _onchange_dates(self):
        """
        Lógica para actualizar los días corridos cuando se cambian las fechas
        en la interfaz de usuario.
        """
        if self.holiday_status_id:
            self._compute_number_of_days()

    def action_approve(self):
        """
        Sobrescribe la acción de aprobación para asegurar el cálculo correcto
        de los días corridos.
        """
        res = super(HrLeave, self).action_approve()
        if self.holiday_status_id:
            self._compute_number_of_days()
        return res