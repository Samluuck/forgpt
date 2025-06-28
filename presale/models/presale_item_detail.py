from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PresaleOrderItemDetail(models.Model):
    _name = 'presale.order.item.detail'
    _description = 'Presale Order Item Detail'

    # Campos comunes en la mayoria de categorias
    name = fields.Char(string="Nombre del Detalle")
    item_id = fields.Many2one('presale.order.item', string="Item", ondelete="cascade", readonly=True)
    product_id = fields.Many2one('product.product', string="Producto")
    qty = fields.Float(string="Cantidad", default=0.0)
    unit_price = fields.Float(string="Precio")
    total = fields.Float(string="Precio por uso", compute="_calcular_total", store=True)
    
    # Campos específicos para categoria Turnos
    operarios = fields.Integer(string="N° Operarios", help="Número de operarios para el turno")
    diurnas_semanales = fields.Integer(string="Diurnas Semanales", help="Número de diurnas semanales")
    horas = fields.Float(string="Horas por Turno", help="Horas totales del turno")
    total_turno = fields.Float(string="Total Turno", compute="_compute_total_turno", store=True)
    
    #----------------------------------------------------------#  
    show_turno_fields = fields.Boolean(
        string="Mostrar campos de turno",
        compute='_compute_show_turno_fields',
        store=True
    )

    @api.depends('item_id.is_turno')
    def _compute_show_turno_fields(self):
        for record in self:
            # Mostrar campos solo si es un turno
            record.show_turno_fields = record.item_id.is_turno if record.item_id else False
    #----------------------------------------------------------#        
            
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Actualiza unit_price y qty cuando se selecciona un producto"""
        for record in self:
            if record.product_id:
                # Autocompleta unit_price si hay standard_price
                if record.product_id.standard_price > 0:
                    record.unit_price = record.product_id.standard_price
                # Autocompleta qty con qty_per_use del producto
                if record.product_id.qty_per_use > 0:
                    record.qty = record.product_id.qty_per_use

    @api.model
    def create(self, vals):
        """Autocompleta qty y unit_price al crear el registro"""
        if 'product_id' in vals:
            product = self.env['product.product'].browse(vals['product_id'])
            if product:
                # Qty
                if 'qty' not in vals and product.qty_per_use > 0:
                    vals['qty'] = product.qty_per_use
                if 'unit_price' not in vals and product.standard_price > 0:
                    vals['unit_price'] = product.standard_price
        return super().create(vals)
    
    @api.depends('qty', 'unit_price')
    def _calcular_total(self):
        for record in self:
            if record.item_id.is_turno:
                record.total = 0  # Para turnos usamos total_turno en su lugar
            else:
                record.total = record.unit_price / record.qty if record.unit_price and record.qty != 0 else 0.0

    @api.depends('qty', 'unit_price', 'item_id.is_turno')
    def _compute_total(self):
        for record in self:
            if record.item_id.is_turno:
                # Para turnos, el cálculo normal no aplica (usamos total_turno)
                record.total = 0
            else:
                # Para otras categorías: precio unitario / cantidad de usos
                record.total = record.unit_price / record.qty if record.qty != 0 else 0

    @api.depends('operarios', 'diurnas_semanales', 'horas', 'unit_price')
    def _compute_total_turno(self):
        for record in self:
            if record.item_id.is_turno:
                record.total_turno = (record.operarios or 0) * (record.diurnas_semanales or 0) * (record.horas or 0) * (record.unit_price or 0)
            else:
                record.total_turno = 0

    @api.constrains('qty', 'unit_price', 'operarios', 'horas')
    def _check_values(self):
        for record in self:
            if record.item_id.is_turno:
                if record.operarios <= 0:
                    raise ValidationError("El número de operarios debe ser mayor que cero")
                if record.horas <= 0:
                    raise ValidationError("Las horas por turno deben ser mayores que cero")
            else:
                if record.qty <= 0:
                    raise ValidationError("La cantidad de usos debe ser mayor que cero")
                if record.unit_price < 0:
                    raise ValidationError("El precio no puede ser negativo")