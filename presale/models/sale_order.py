from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    presale_id = fields.Many2one('presale.order')
