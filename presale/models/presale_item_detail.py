from odoo import models, fields, api

class PresaleOrderItemDetail(models.Model):
    _name = 'presale.order.item.detail'
    _description = 'Presale Order Item Detail'

    name = fields.Char(string="Nombre del Detalle")
    item_id = fields.Many2one('presale.order.item', string="Presale Item", ondelete="cascade")
    product_id = fields.Many2one('product.product', string="Producto")
    qty = fields.Float(string="Cantidad", default=1.0)
    unit_price = fields.Float(string="Precio Unitario")
    total = fields.Float(string="Total", compute="_calcular_total", store=True)

    @api.depends('qty', 'unit_price')
    def _calcular_total(self):
        for record in self:
            record.total = record.qty * record.unit_price if record.unit_price else 0.0

