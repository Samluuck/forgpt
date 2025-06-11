from odoo import models, fields, api

class PresaleOrderItem(models.Model):
    _name = 'presale.order.item'
    _description = 'Presale Order Item'

    name = fields.Char(string="Nombre del Ítem", required=True)
    presale_order_id = fields.Many2one('presale.order', string="Presale Order", ondelete="cascade")
    product_id = fields.Many2one('product.product', string="Producto", required=True)
    qty = fields.Float(string="Cantidad", default=1.0)
    unit_price = fields.Float(string="Precio Unitario")
    subtotal = fields.Float(string="Subtotal", compute="_calcular_subtotal", store=True)
    item_detail_ids = fields.One2many('presale.order.item.detail', 'item_id', string="Detalles del Ítem")

    # Campos booleanos por categoría
    is_equipo = fields.Boolean(string="Equipos")
    is_insumo = fields.Boolean(string="Insumos y Elementos")
    is_maquina = fields.Boolean(string="Máquinas")
    is_epi_epc = fields.Boolean(string="EPI / EPC (Equipo de Protección Individual)")
    is_turno = fields.Boolean(string="Turnos")
    is_otro = fields.Boolean(string="Otros (Comida, Bolt, Logística, Análisis Médicos, etc)")

    @api.depends('qty', 'unit_price')
    def _calcular_subtotal(self):
        for record in self:
            record.subtotal = record.qty * record.unit_price if record.unit_price else 0.0
