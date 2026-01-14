from odoo import models, fields
from datetime import date

class AntuxDatahubSueldosJornalesReportWizard(models.TransientModel):
    _name = 'antux.datahub.sueldos.jornales.report.wizard'
    _description = 'Wizard Sueldos y Jornales'

    report_type = fields.Selection(
        [
            ('mensual', 'Mensual'),
            ('anual', 'Anual'),
        ],
        default='mensual',
        required=True
    )

    year = fields.Integer(
        string='Año',
        default=lambda self: date.today().year
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )

    def action_print_report(self):
        self.ensure_one()

        batch_id = self.env.context.get('active_id')

        if self.report_type == 'mensual':
            return {
                'type': 'ir.actions.act_url',
                'url': f'/antux_datahub/sueldos_jornales/mensual/{batch_id}',
                'target': 'self',
            }

        # Para anual, pasamos company_id y year en la URL
        return {
            'type': 'ir.actions.act_url',
            'url': f'/antux_datahub/sueldos_jornales/anual/{self.company_id.id}/{self.year}',
            'target': 'self',
        }
