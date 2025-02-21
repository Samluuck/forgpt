from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    banco_itau_codigo_empresa = fields.Char(string='Código de Empresa ITAU')
    banco_itau_nro_cuenta = fields.Char(string='Nro Cuenta ITAU')
