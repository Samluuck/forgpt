from odoo import models, fields

class ProductTemplateCustom(models.Model):
    _inherit = 'product.template'

    # Los campos personalizados aquí
    presentacion_por_fardo = fields.Boolean(string='Presentación por fardo', required=True, store=True)
    cantidad_unidades_por_fardo = fields.Integer(string='Cantidad de unidades p/ fardo', required=True, store=True)
    producto_secuencia = fields.Integer(string='Secuencia en Factura', required=True, store=True)