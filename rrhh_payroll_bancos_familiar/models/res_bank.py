from odoo import api, fields, models


class ResBank(models.AbstractModel):
    _inherit = 'res.bank'



    is_banco_familiar = fields.Boolean(string="¿Es Banco Familiar? (No/Si)",help='Marcar este campo como Banco familiar para el reporte de txt del Banco Familiar')
