from odoo import models, fields, api
from odoo.exceptions import UserError

class AntuxDataHubSalaryReceiptWizard(models.TransientModel):
    _name = 'antux.datahub.salary.receipt.wizard'
    _description = 'Asistente de Recibo de Salario'

    employee_ids = fields.Many2many(
        'antux.datahub.line',
        string='Empleados',
        help="Deje vacío para imprimir todos los empleados del lote."
    )

    batch_id = fields.Many2one(
        'antux.datahub.batch',
        string='Lote',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )

    print_option = fields.Selection([
        ('single', 'Archivo único (PDF)'),
        ('zip', 'Archivo comprimido (ZIP)')
    ], string='Opción de impresión', default='single', required=True)

    def action_print_report(self):
        self.ensure_one()
        batch = self.batch_id
        
        # Determine which lines to process
        lines = self.employee_ids or batch.line_ids
        
        # Check for duplicates by CI
        ci_counts = {}
        duplicates = []
        for line in lines:
            ci = line.ci_number
            if ci in ci_counts:
                if ci not in duplicates:
                    duplicates.append(ci)
            else:
                ci_counts[ci] = 1
        
        if duplicates:
            raise UserError(
                "Se detectaron registros duplicados para la(s) siguiente(s) cédula(s) en este período: %s. "
                "Por favor, verifique la planilla general antes de generar los recibos." % ", ".join(duplicates)
            )
        
        if self.print_option == 'zip':
            return {
                'type': 'ir.actions.act_url',
                'url': '/antux_datahub/salary_receipts_zip/%s' % self.id,
                'target': 'new',
            }
        
        return self.env.ref('antux_data_hub.action_report_salary_receipt').report_action(self)
