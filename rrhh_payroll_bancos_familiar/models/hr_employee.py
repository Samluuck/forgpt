from odoo import api, fields, models


class HREmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    banco_familiar_nro_cuenta = fields.Char(string='Nro Cuenta FAMILIAR')
    bank_id = fields.Many2one('res.bank', string='Banco principal')
    bank_account = fields.Char(string='Cuenta Bancaria')