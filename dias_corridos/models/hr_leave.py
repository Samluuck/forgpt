from odoo import models, api

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.depends('request_date_from', 'request_date_to', 'holiday_status_id')
    def _compute_number_of_days(self):
        for leave in self:
            if leave.holiday_status_id and leave.holiday_status_id.es_corrido:
                if leave.request_date_from and leave.request_date_to:
                    leave.number_of_days = (leave.request_date_to - leave.request_date_from).days + 1
                else:
                    leave.number_of_days = 0
            else:
                # Usa la lógica estándar de Odoo para casos que no sean corridos
                leave._compute_number_of_days_display()
                leave.number_of_days = leave.number_of_days_display

    @api.onchange('request_date_from', 'request_date_to', 'holiday_status_id')
    def _onchange_dates(self):
        if self.holiday_status_id:
            self._compute_number_of_days()

    def action_approve(self):
        res = super(HrLeave, self).action_approve()
        if self.holiday_status_id:
            self._compute_number_of_days()
        return res
