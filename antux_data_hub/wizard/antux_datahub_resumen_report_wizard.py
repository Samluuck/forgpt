from odoo import models, fields

class AntuxDataHubResumenReportWizard(models.TransientModel):
    _name = 'antux.datahub.resumen.report.wizard'
    _description = 'Seleccionar tipo de reporte Resumen General'

    report_format = fields.Selection(
        [
            ('control', 'Formato de Control (MTESS)'),
            ('tabular', 'Formato Tabular Simple'),
        ],
        string='Formato de Reporte',
        required=True,
        default='control'
    )

    def action_print_report(self):
        self.ensure_one()
        batch_id = self.env.context.get('active_id')
        
        if not batch_id:
            # Fallback si no hay active_id (ej: testing manual)
            # Intentamos buscar el ultimo batch o lanzamos error
            # Por ahora solo logueamos warning
            pass

        return {
            'type': 'ir.actions.act_url',
            'url': f'/antux_datahub/resumen_general/{batch_id}/{self.report_format}',
            'target': 'self',
        }
