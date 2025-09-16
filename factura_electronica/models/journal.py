# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class JournalFactElect(models.Model):
    _inherit = 'account.journal'
    tipo_pago=fields.Selection(selection=[('1' ,'Efectivo'),
                                    ('2' , 'Cheque'),
                                    ('3' , 'Tarjeta de crédito'),
                                    ('4' , 'Tarjeta de débito'),
                                    ('5' , 'Transferencia'),
                                    ('6' , 'Giro'),
                                    ('7' , 'Billetera electrónica'),
                                    ('8' , 'Tarjeta empresarial'),
                                    ('9' , 'Vale'),
                                    ('10' , 'Retención'),
                                    ('11' , 'Pago por anticipo'),
                                    ('12' , 'Valor fiscal'),
                                    ('13' , 'Valor comercial'),
                                    ('14' , 'Compensación'),
                                    ('15' , 'Permuta'),
                                    ('16' , 'Pago bancario'),
                                    ('17' , 'Pago Móvil'),
                                    ('18' , 'Donación'),
                                    ('19' , 'Promoción'),
                                    ('20' , 'Consumo Interno'),
                                    ('21' , 'Pago Electrónico'),
                                    ('99' , 'Otro')],default='1',string='Tipo de Pago DE')
    descripcion_tipo_pago=fields.Char()

    @api.onchange('payment_subtype')
    def verificar_tipo_cheque(self):
        if self.payment_subtype:
            self.tipo_pago='2'

