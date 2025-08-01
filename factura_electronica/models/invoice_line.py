from odoo import models, fields, api
from num2words import num2words
import random
from odoo.exceptions import ValidationError

class Invoice_line_FactElect(models.Model):
    _inherit = 'account.move.line'

    #Campos para productos agricolas/agrocquimico
    # Expuestos en  E8.4. Grupo de rastreo de la mercadería (E750-E760) del MT150

    nro_lote_fe= fields.Char(string='Nro Lote FE',size=80)
    fecha_vencimiento_fe = fields.Date(string="Fecha de Vencimiento prod. FE")
    nro_serie_fe= fields.Char(string='Nro Lote FE',size=10)
    nro_pedido_fe= fields.Char(string='Nro Pedido FE',size=20)
    nro_seguimiento_fe= fields.Char(string='Nro Seguimiento FE',size=20)
    nombre_importador_fe= fields.Char(string='Nombre importador FE',size=60)
    direccion_importador_fe= fields.Char(string='Direccion importador FE',size=255)
    nro_registro_imp_fe= fields.Char(string='Nro Registro Importador FE',size=20)
    nro_registro_senave_producto= fields.Char(string='Nro Registro del Producto del SENAVE',size=20)
    nro_registro_senave_entidad_comercial= fields.Char(string='Nro Registro de la entidad comercial otorgado por el SENAVE',size=20)
    porcentaje_descuento = fields.Float(string="%  particular")
    monto_anticipo = fields.Float(string="Monto particular")
    tiene_descuento = fields.Boolean(string="Es descuento", default=False)
    tiene_anticipo = fields.Boolean(string="Es Anticipo", default=False)


