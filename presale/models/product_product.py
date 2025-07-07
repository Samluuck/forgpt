from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ✅ CORREGIDO: Campo con configuración completa
    qty_per_use = fields.Float(
        string='Cantidad/Vec. Uso',
        digits='Product Unit of Measure',
        default=1.0,  # ✅ Valor por defecto
        help="Cantidad promedio de veces que se usa este producto en preventas"
    )
    
    # ✅ OPCIONAL: Campos adicionales para preventas
    is_presale_product = fields.Boolean(
        string='Producto de Preventa',
        default=False,
        help="Marcar si este producto se usa frecuentemente en preventas"
    )
    
    mul_divi = fields.Selection([
        ('multiplicar', 'Multiplicar'),
        ('dividir', 'Dividir'),
    ], string="Multiplicar/Dividir en Preventa")
    
    presale_category = fields.Selection([
        ('equipo', 'Equipos'),
        ('insumo', 'Insumos y Elementos'),
        ('maquina', 'Máquinas'),
        ('epi_epc', 'EPI / EPC'),
        ('turno', 'Turnos'),
        ('otro', 'Otros'),
    ], string="Categoría de Preventa", help="Categoría predeterminada para preventas")

    # ✅ MEJORA: SQL Constraints
    _sql_constraints = [
        ('positive_qty_per_use', 'CHECK(qty_per_use > 0)', 
         'La cantidad por uso debe ser mayor que cero.'),
    ]

    # ✅ MEJORA: OnChange para automarcar como producto de preventa
    @api.onchange('qty_per_use', 'presale_category')
    def _onchange_presale_fields(self):
        """Marcar automáticamente como producto de preventa si se configuran campos"""
        if (self.qty_per_use > 1.0 or self.presale_category) and not self.is_presale_product:
            self.is_presale_product = True

    # ✅ MEJORA: Validaciones
    @api.constrains('qty_per_use', 'is_presale_product')
    def _check_presale_values(self):
        """Validar valores de preventa"""
        for template in self:
            if template.is_presale_product and template.qty_per_use <= 0:
                raise ValidationError(f"El producto {template.name} marcado para preventas debe tener cantidad por uso mayor a cero.")

    # ✅ MEJORA: Método para obtener configuración de preventa
    def get_presale_config(self):
        """Obtener configuración completa para preventas"""
        self.ensure_one()
        return {
            'template_id': self.id,
            'name': self.name,
            'qty_per_use': self.qty_per_use,
            'standard_price': self.standard_price,
            'category': self.presale_category,
            'is_presale_product': self.is_presale_product,
        }