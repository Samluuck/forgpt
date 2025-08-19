from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_timesheet_reminder = fields.Boolean(
        string="Recordatorio Timesheet",
        implied_group='timesheet_reminder.group_timesheet_reminder',
        help="Activar recordatorios automáticos diarios para cargar timesheet"
    )