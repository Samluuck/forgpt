from odoo import models, fields, api

class PresaleOrderItemDetail(models.Model):
    _name = 'presale.order.item.detail'
    _description = 'Presale Order Item Detail'

    name = fields.Char(string="Nombre del Detalle")
    item_id = fields.Many2one('presale.order.item', string="Item", ondelete="cascade", readonly=True)
    product_id = fields.Many2one('product.product', string="Producto")
    qty = fields.Float(string="Cantidad", default=1.0)
    unit_price = fields.Float(string="Precio")
    total = fields.Float(string="Precio por uso", compute="_calcular_total", store=True)

    @api.depends('qty', 'unit_price')
    def _calcular_total(self):
        for record in self:
            record.total = record.unit_price / record.qty if record.unit_price and record.qty !=0 else 0.0

