from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_per_use = fields.Float(string='Cantidad/Vec. Uso')