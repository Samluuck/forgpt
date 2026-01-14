from odoo import models, fields


class AntuxDataHubIPSReportWizard(models.TransientModel):
    _name = 'antux.datahub.ips.report.wizard'
    _description = 'Seleccionar tipo de reporte IPS'

    report_type = fields.Selection(
        [
            ('monthly', 'Mensual'),
            ('annual', 'Anual'),
        ],
        string='Tipo de Reporte',
        required=True,
        default='annual'
    )

    def action_print_report(self):
        self.ensure_one()
        batch_id = self.env.context.get('active_id')

        if self.report_type == 'monthly':
            url = f'/antux_datahub/ips/mensual/{batch_id}'
        else:
            url = f'/antux_datahub/ips/anual/{batch_id}'

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }
