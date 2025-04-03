# -*- coding: utf-8 -*-
import logging
from pickletools import stringnl

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    statement_date = fields.Date('Bank.St Date', copy=False)
    monto_moneda_pago = fields.Float(string="Monto moneda pago")
    moneda_pago = fields.Many2one('res.currency',"Moneda Pago")
    moneda_extracto = fields.Many2one('res.currency',string="Moneda Extracto",compute="get_moneda_extracto")
    descripcion = fields.Char(string="Descripción", help="Descripción o tipo de transacción")
    debito = fields.Float(
        string='Débito',
        compute='get_debito',
        required=False)
    credito = fields.Float(
        string='Crédito',
        required=False,
        compute='get_credito')
    saldo = fields.Float(
        string='Saldo',
        required=False)
    check_number = fields.Char(
        string='Cheque Nro.',
        default='')
    debito_abs = fields.Float(
        string='Débito',
        compute='_compute_abs_debito',
        store=False)
    credito_abs = fields.Float(
        string='Crédito',
        compute='_compute_abs_credito',
        store=False)

    @api.depends('debito')
    def _compute_abs_debito(self):
        for rec in self:
            rec.debito_abs = abs(rec.debito)

    @api.depends('credito')
    def _compute_abs_credito(self):
        for rec in self:
            rec.credito_abs = abs(rec.credito)

    @api.depends('currency_id','moneda_pago')
    def get_moneda_extracto(self):
        for rec in self:
            if rec.currency_id:
                currency_id=rec.currency_id
                if rec.moneda_pago:
                    currency_id=rec.moneda_pago
            else:
                currency_id=None
            rec.moneda_extracto=currency_id

    'Código original para obtener el débito'

    @api.depends('amount_currency', 'currency_id')
    def get_debito(self):
        for rec in self:
            rec.debito = 0
            dif = 0
            # Validación segura de 'recibo_id'
            recibo = getattr(rec.payment_id, 'recibo_id', None)
            if recibo and recibo.move_diferencia_id:
                move = recibo.move_diferencia_id.line_ids
                for m in move:
                    if m.account_id.id == rec.account_id.id:
                        dif = m.debit + m.credit
            else:
                # Validación segura de 'orden_pago_id'
                orden_pago = getattr(rec.payment_id, 'orden_pago_id', None)
                if orden_pago and orden_pago.move_diferencia_id:
                    move = orden_pago.move_diferencia_id.line_ids
                    for m in move:
                        if m.account_id.id == rec.account_id.id:
                            dif = m.credit - m.debit

            if rec.amount_currency != 0.0:
                if rec.amount_currency > 0:
                    if rec.currency_id:
                        if rec.currency_id != rec.env.user.company_id.currency_id:
                            rec.debito = rec.amount_currency  # Tomar siempre el monto en la moneda original
                        else:
                            rec.debito = round(rec.amount_currency + dif)
                    else:
                        rec.debito = round(rec.amount_currency + dif)

    @api.depends('amount_currency', 'currency_id')
    def get_credito(self):
        for rec in self:
            dif = 0
            rec.credito = 0
            payment = rec.payment_id
            # Validamos la existencia de 'recibo_id' de forma segura
            recibo = getattr(payment, 'recibo_id', None)
            if recibo and recibo.move_diferencia_id:
                move = recibo.move_diferencia_id.line_ids
                for m in move:
                    if m.account_id.id == rec.account_id.id:
                        dif = m.debit + m.credit
            elif getattr(payment, 'orden_pago_id', None):
                orden = payment.orden_pago_id
                if orden.move_diferencia_id:
                    move = orden.move_diferencia_id.line_ids
                    for m in move:
                        if m.account_id.id == rec.account_id.id:
                            dif = m.debit + m.credit

            if rec.amount_currency != 0.0:
                if rec.amount_currency < 0:
                    if rec.currency_id:
                        if rec.currency_id != rec.env.user.company_id.currency_id:
                            rec.credito = abs(rec.amount_currency)  # Usar siempre el monto en la moneda original
                        else:
                            rec.credito = round(rec.amount_currency + dif)
                    else:
                        rec.credito = round(rec.amount_currency + dif)
            else:
                if rec.debit != 0.0:
                    rec.credito = round(rec.amount_currency + dif)
