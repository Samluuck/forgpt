from odoo import api, fields, models


class ResBank(models.AbstractModel):
    _inherit = 'res.bank'



    is_banco_itau = fields.Boolean(string="¿Es Banco Itaú? (No/Si)",help='Marcar este campo como Banco Itaú para el reporte de txt del Banco Itaú')
