from odoo import api, fields, models


class HREmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    banco_atlas_nro_cuenta = fields.Char(string='Nro Cuenta ATLAS')