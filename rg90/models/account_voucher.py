# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError

import time

class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    tipo_comprobante = fields.Many2one('ruc.tipo.documento', string='Tipo comprobante', tracking=True)
    fecha_comprobante = fields.Date()
    nro_comprobante = fields.Char()
    number_card_credit_debit = fields.Integer()
    bank_id = fields.Many2one('res.bank', tracking=True)
    partner_external = fields.Char()
    nro_cuenta_corriente_caja_ahorro = fields.Integer()
    razon_social_banco_financiera_cooperativa = fields.Char()
    razon_social_bien_servicio = fields.Char()
    tipo_documento=fields.Selection(selection=[('1','Cédula paraguaya'),
                                                        ('2','Pasaporte'),
                                                        ('3','Cédula extranjera'),
                                                        ('4','Carnet de residencia'),
                                                        ('5','Innominado'),
                                                        ('6','Tarjeta Diplomática de exoneración fiscal'),('9','Otro')])
    presenta_rg90_ingreso_egreso = fields.Boolean(related='company_id.presenta_rg90_ingreso_egreso')