from odoo import api, fields, models


class ResBank(models.AbstractModel):
    _inherit = 'res.bank'

    is_banco_atlas = fields.Boolean(
        string="¿Es Banco ATLAS? (No/Si)",
        help='Marcar este campo como Banco ATLAS para el reporte de txt del Banco ATLAS'
    )