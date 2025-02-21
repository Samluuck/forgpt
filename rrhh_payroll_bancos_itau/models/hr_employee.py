from odoo import api, fields, models


class HREmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    banco_itau_nro_cuenta = fields.Char(string='Nro Cuenta ITAU')
