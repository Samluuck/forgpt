from odoo import models, fields

class AntuxDataHubEmpleadosReportWizard(models.TransientModel):
    _name = 'antux.datahub.empleados.report.wizard'
    _description = 'Seleccionar tipo de reporte Empleados / Obreros'

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

        # MENSUAL → nuevo reporte con formato
        if self.report_type == 'monthly':
            return {
                'type': 'ir.actions.act_url',
                'url': f'/antux_datahub/empleados_obreros/mensual/{batch_id}',
                'target': 'self',
            }

        # ANUAL → EL DE SIEMPRE (NO TOCAR)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/antux_datahub/empleados_obreros/{batch_id}',
            'target': 'self',
        }

