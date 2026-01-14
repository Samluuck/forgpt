from odoo import models, fields

class AntuxVacacionesReportWizard(models.TransientModel):
    _name = 'antux.datahub.vacaciones.report.wizard'
    _description = 'Wizard Vacaciones'

    report_type = fields.Selection(
        [('mensual', 'Mensual'), ('anual', 'Anual')],
        default='mensual',
        required=True
    )

    def action_print_report(self):
        self.ensure_one()
        batch_id = self.env.context.get('active_id')

        if self.report_type == 'mensual':
            return {
                'type': 'ir.actions.act_url',
                'url': f'/antux_datahub/vacaciones/mensual/{batch_id}',
                'target': 'self',
            }

        return {
            'type': 'ir.actions.act_url',
            'url': f'/antux_datahub/vacaciones/anual/{batch_id}',
            'target': 'self',
        }
