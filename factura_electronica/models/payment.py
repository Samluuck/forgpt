# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)
class accountPaymentRegister(models.TransientModel):

    _inherit = 'account.payment.register'

    nro_transaccion = fields.Char(string="Nro. de transacción",size=9)
    tipo_tarjeta =fields.Selection( [('1', 'Visa'),
                    ('2', 'Mastercard'),
                    ('3', 'American Express'),
                    ('4', 'Maestro'),
                    ('5', 'Panal'),
                    ('6', 'Cabal'),
                    ('99', 'Otro')
                    ])
    es_tarjeta=fields.Boolean(compute="_ver_si_es_tarjeta")
    descripcion_tipo_tarjeta = fields.Char()
    forma_pago=[(1, 'POS'),
                (2,'Pago Electrónico'),
                (9, 'Otro')]
    tipo_pago=fields.Selection(related='journal_id.tipo_pago')
    descripcion_tipo_pago = fields.Char(string="Desciprcion de tipo de Pago cuando es diario Otro")

    @api.depends('journal_id')
    def _ver_si_es_tarjeta(self):
        for rec in self:
            if rec.journal_id.tipo_pago == '3' or rec.journal_id.tipo_pago == '4':
                rec.es_tarjeta = True
            else:
                rec.es_tarjeta= False

    def _get_default_tipo_pago(self):
        if self.journal_id.tipo_pago:
            return self.journal_id.tipo_pago
        return '1'

    def _create_payment_vals_from_wizard(self):
        payment_vals = {
            'date': self.payment_date,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'ref': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'destination_account_id': self.line_ids[0].account_id.id,
            'tipo_pago': self.tipo_pago,
            'tipo_tarjeta': self.tipo_tarjeta,
            'descripcion_tipo_tarjeta': self.descripcion_tipo_tarjeta
        }

        if not self.currency_id.is_zero(self.payment_difference) and self.payment_difference_handling == 'reconcile':
            payment_vals['write_off_line_vals'] = {
                'name': self.writeoff_label,
                'amount': self.payment_difference,
                'account_id': self.writeoff_account_id.id,
            }
        if self.cheque_tercero:
            cheque = self.generar_cheque()
            payment_vals['received_third_check_ids'] = [(6,0,cheque.id)]
        return payment_vals

    def generar_cheque(self):
        cheque_tercero = self.env['account.check.third']
        datos = {
            'number': self.numero_cheque_recibo,
            'amount': self.amount,
            # 'issue_date': datetime.strftime(date.today(),"%d/%m/%Y"),
            'bank_id': self.banco_cheque_recibo.id,
            'cuit': self.nro_cuenta_recibo,
            'payment_date': self.fecha_cheque_diferido,
            'issue_date': self.fecha_cheque_recibo,
            'tipo_cheque': self.tipo_de_cheque_recibo,
            'source_partner_id': self.partner_id.id,
            'owner_name': self.titular_recibo,
        }
        cheque = cheque_tercero.create(datos)
        return cheque

    def _create_payment_vals_from_batch(self, batch_result):
        batch_values = self._get_wizard_values_from_batch(batch_result)

        if batch_values['payment_type'] == 'inbound':
            partner_bank_id = self.journal_id.bank_account_id.id
        else:
            partner_bank_id = batch_result['payment_values']['partner_bank_id']
        if self.cheque_tercero:
            cheque = self.generar_cheque()
            return {
                'date': self.payment_date,
                'amount': batch_values['source_amount_currency'],
                'payment_type': batch_values['payment_type'],
                'partner_type': batch_values['partner_type'],
                'ref': self._get_batch_communication(batch_result),
                'journal_id': self.journal_id.id,
                'currency_id': batch_values['source_currency_id'],
                'partner_id': batch_values['partner_id'],
                'partner_bank_id': partner_bank_id,
                'payment_method_line_id': self.payment_method_line_id.id,
                'destination_account_id': batch_result['lines'][0].account_id.id,
                'tipo_pago': self.tipo_pago,
                'tipo_tarjeta': self.tipo_tarjeta,
                'descripcion_tipo_tarjeta': self.descripcion_tipo_tarjeta,
                'received_third_check_ids' : [(6,0,cheque.id)]
            }

        else:
            return {
                'date': self.payment_date,
                'amount': batch_values['source_amount_currency'],
                'payment_type': batch_values['payment_type'],
                'partner_type': batch_values['partner_type'],
                'ref': self._get_batch_communication(batch_result),
                'journal_id': self.journal_id.id,
                'currency_id': batch_values['source_currency_id'],
                'partner_id': batch_values['partner_id'],
                'partner_bank_id': partner_bank_id,
                'payment_method_line_id': self.payment_method_line_id.id,
                'destination_account_id': batch_result['lines'][0].account_id.id,
                'tipo_pago': self.tipo_pago,
                'tipo_tarjeta' : self.tipo_tarjeta,
                'descripcion_tipo_tarjeta':self.descripcion_tipo_tarjeta
            }



class PaymentFactElect(models.Model):
    _inherit = 'account.payment'

    tipo_tarjeta =fields.Selection( [('1', 'Visa'),
                    ('2', 'Mastercard'),
                    ('3', 'American Express'),
                    ('4', 'Maestro'),
                    ('5', 'Panal'),
                    ('6', 'Cabal'),
                    ('99', 'Otro')
                    ])
    es_tarjeta=fields.Boolean(compute="_ver_si_es_tarjeta")
    descripcion_tipo_tarjeta = fields.Char()
    forma_pago=[(1, 'POS'),
                (2,'Pago Electrónico'),
                (9, 'Otro')]
    tipo_pago=fields.Selection(related='journal_id.tipo_pago')
    descripcion_tipo_pago = fields.Char(string="Desciprcion de tipo de Pago cuando es diario Otro")

    @api.depends('journal_id')
    def _ver_si_es_tarjeta(self):
        for rec in self:
            if rec.journal_id.tipo_pago == '3' or rec.journal_id.tipo_pago == '4':
                rec.es_tarjeta=True

    def _get_default_tipo_pago(self):
        if self.journal_id.tipo_pago:
            return self.journal_id.tipo_pago
        return '1'