from odoo import api, fields, models


class ResBank(models.AbstractModel):
    _inherit = 'res.bank'



    is_banco_sudameris = fields.Boolean(string="¿Es Banco Sudameris? (No/Si)",help='Marcar este campo como Banco Sudameris para el reporte de txt del Banco Sudameris')
