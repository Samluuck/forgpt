from odoo import models, fields, api

class HrEmployeeOvertime(models.Model):
    _inherit = 'hr.employee'

    aprobador_hhee = fields.Many2many(
        'hr.employee',
        'hr_employee_aprobador_rel',
        'employee_id',
        'aprobador_id',
        string='Aprobadores de Horas Extras',
        help='Empleados encargados de aprobar las solicitudes de horas extras de este empleado',
        domain="[('user_id', '!=', False)]",  # Solo empleados con usuario
        tracking=True
    )

    @api.onchange('aprobador_hhee')
    def _onchange_aprobador_hhee(self):
        """Validación para evitar auto-aprobación"""
        if self.aprobador_hhee and self.id in self.aprobador_hhee.ids:
            return {
                'warning': {
                    'title': 'Advertencia',
                    'message': 'Un empleado no puede ser su propio aprobador de horas extras.'
                }
            }