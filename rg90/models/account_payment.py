# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError
class AccountPayment(models.Model):
    _inherit = 'account.payment'
    tipo_comprobante = fields.Many2one('ruc.tipo.documento', string='Tipo comprobante', tracking=True)
    fecha_comprobante = fields.Date()
    nro_comprobante = fields.Char()
    cod_tipo_identificacion = fields.Char()
    razon_social_proveedor = fields.Char()
    monto_comprobante = fields.Integer()
    numero_comprobante_asociado = fields.Integer()