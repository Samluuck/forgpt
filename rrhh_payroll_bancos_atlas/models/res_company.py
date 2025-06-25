from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    banco_atlas_codigo_empresa = fields.Char(string='Código de Empresa ATLAS')
    banco_atlas_nro_cuenta = fields.Char(string='Nro Cuenta ATLAS')