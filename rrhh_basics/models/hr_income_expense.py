from odoo import models, fields, api

class hr_payslip_inh(models.Model):
    _name = "hr.income.expense"
    _description = "Ingresos y Descuentos de Empleados"
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Hereda de mail.thread y mail.activity.mixin

    name = fields.Char(string="Descripción", tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', tracking=True)
    code = fields.Many2one(
        'hr.payslip.input.type',
        string="Código",
        required=True,
        help="Selecciona el código del tipo de entrada.",
        tracking=True
    )
    amount = fields.Integer(string="Monto/cantidad", tracking=True)
    date_from = fields.Date(string="Fecha desde", tracking=True)
    date_to = fields.Date(string="Fecha hasta", tracking=True)

    @api.onchange('code')
    def _onchange_code(self):
        """
        Completa automáticamente el campo 'name' con el 'name' del código seleccionado.
        """
        if self.code:
            self.name = self.code.name
        else:
            self.name = False


class HrPayslipInputType(models.Model):
        _inherit = 'hr.payslip.input.type'

        def name_get(self):
            result = []
            for record in self:
                # Mostrar solo el código o combinarlo con el nombre
                display_name = record.code or record.name
                result.append((record.id, display_name))
            return result
