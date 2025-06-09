from odoo import fields, models, api

class lista_de_descuentos(models.Model):
    _name = "lista.descuentos"

    # Creamos un modelo para el tipo de descuento
    name = fields.Char(string="Tipo de descuento")
    codigo = fields.Char(string="Código del descuento",help="Ingresar el codigo con le que se enlaza a la regla salarial")