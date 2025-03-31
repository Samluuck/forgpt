# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import date, datetime, time, timedelta
from dateutil.parser import parse
from dateutil import relativedelta
from odoo.exceptions import ValidationError
import time
import pytz
import logging
_logger = logging.getLogger(__name__)


class BookBank(models.TransientModel):

    _name = 'bank_reconciliation.report_book_bank'

    journal_id = fields.Many2one('account.journal', 'Diario', domain=[('type', '=', 'bank')])
    account_id = fields.Many2one('account.account', 'Cuenta')
    date_from = fields.Date('Fecha desde', default=time.strftime('%Y-%m-01'))
    date_to = fields.Date('Fecha hasta',
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[
                                  :10])
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get('bank.statement'))
    filter_wizard = fields.Selection(
        string='Filtros',
        selection=[('all', 'Todos'),
                   ('reconciled', 'Conciliados'),
                   ('unreconciled', 'No Conciliados')],
        required=False, default='all')
    sent = fields.Boolean(string='Sent', default=False)

    # @api.multi
    def report_book_bank(self):
        # if self.mes:
        self.ensure_one()
        self.sent = True
        return self.env.ref('bank_reconciliation.report_book_bank').report_action(self)

    @api.onchange('journal_id')
    def get_data(self):
        if self.journal_id:
            self.account_id = self.journal_id.default_account_id.id or self.journal_id.default_credit_account_id.id
            if 'USD' in self.account_id.name or 'Usd' in self.account_id.name or '$' in self.account_id.name:
                moneda = self.env['res.currency'].browse(173)
                self.currency_id = moneda
            else:
                moneda = self.env.user.company_id.currency_id
                self.currency_id = moneda

    # def account_mvl_object2(self):
    #     domain = [('account_id', '=', self.account_id.id)]
    #
    #     domain += [('move_id.state', '=', 'posted')]  # Modificado aquí
    #     lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
    #     if self.date_from:
    #         domain += [('date', '>=', self.date_from)]
    #     if self.date_to:
    #         domain += [('date', '<=', self.date_to)]
    #     if self.filter_wizard == 'reconciled':
    #         domain += [('statement_date', '!=', False)]
    #     if self.filter_wizard == 'unreconciled':
    #         domain += [('statement_date', '=', False)]
    #     domain += [('move_id.journal_id.exchange_rate_journal', '=', False)]
    #     domain += [('move_id.apertura', '=', False)]
    #     domain += [('move_id.cierre', '=', False)]
    #     domain += [('move_id.resultado', '=', False)]
    #     domain += [('parent_state', 'in', 'posted')]
    #     lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
    #     print('Aqui empieza')
    #     ids_agregados = []
    #     print('Aqui empieza')
    #     ids_agregados = []
    #     for l in lines:
    #         print('el movimiento en cuestion es ', l.name)
    #         # c = 0
    #         if l.id not in ids_agregados:
    #             print('entra en el primer if')
    #             if l.payment_id:
    #                 print('entra en el segundo if')
    #                 if l.payment_id.move_line_ids:
    #                     print('entra en el tercer if')
    #                     for m in l.payment_id.move_line_ids:
    #                         print(m.name)
    #                         if m.id != l.id and m.account_id.id == self.account_id.id:
    #                             print('entra en el cuarto if')
    #                             ids_agregados.append(m.id)
    #                 if l.payment_id.monto_moneda_pago > 0.0:
    #                     if l.debit > 0.0:
    #                         l.credito = l.payment_id.monto_moneda_pago
    #                     if l.credit > 0.0:
    #                         l.debito = l.payment_id.monto_moneda_pago
    #                 else:
    #                     if l.debit > 0.0:
    #                         l.credito = l.payment_id.amount
    #                     if l.credit > 0.0:
    #                         l.debito = l.payment_id.amount
    #                 if l.payment_id.recibo_id:
    #                     move = self.env['account.move.line'].search(
    #                         [('name', '=', 'Pago de Recibo Nro. ' + l.payment_id.recibo_id.name),
    #                          ('account_id', '=', self.account_id.id)])
    #                     if move:
    #                         print('se encontro el asiento recibo')
    #                         ids_agregados.append(move.id)
    #                 if l.payment_id.orden_pago_id:
    #                     move1 = self.env['account.move.line'].search(
    #                         [('name', '=', 'Orden de Pago. ' + l.payment_id.orden_pago_id.name),
    #                          ('account_id', '=', self.account_id.id)])
    #                     if move1:
    #                         print('se encontro el asiento orden de pago ')
    #                         ids_agregados.append(move1.id)
    #                 if l.payment_id.received_third_check_ids:
    #                     for third in l.payment_id.received_third_check_ids:
    #                         l.check_number += third.name
    #                 if l.payment_id.issued_check_ids:
    #                     for third in l.payment_id.issued_check_ids:
    #                         l.check_number = third.name
    #             else:
    #                 voucher = self.env['account.voucher'].search([('move_id', '=', l.move_id.id),
    #                                                               ('check_id', '!=', False)])
    #                 if voucher:
    #                     for v in voucher:
    #                         l.check_number = v.check_id.name
    #
    #     print(ids_agregados)
    #     print(len(ids_agregados))
    #     domain += [('id', 'not in', ids_agregados)]
    #     print('Aqui termina')
    #     lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
    #     print(lines)
    #     return lines

    def account_mvl_object2(self):
        domain = [('account_id', '=', self.account_id.id)]

        if self.date_from:
            domain += [('date', '>=', self.date_from)]
        if self.date_to:
            domain += [('date', '<=', self.date_to)]
        if self.filter_wizard == 'reconciled':
            domain += [('statement_line_id', '!=', False)]
        if self.filter_wizard == 'unreconciled':
            domain += [('statement_line_id', '=', False)]
        domain += [('move_id.journal_id.type', '!=', 'exchange_rate_journal')]
        domain += [('move_id.apertura', '=', False)]
        domain += [('move_id.cierre', '=', False)]
        domain += [('move_id.resultado', '=', False)]
        domain += [('move_id.state', '=', 'posted')]  # Modificado aquí

        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)

        ids_agregados = []
        for line in lines:
            if line.id not in ids_agregados:
                if line.payment_id:
                    for payment_line in line.payment_id.move_line_ids:
                        if payment_line.id != line.id and payment_line.account_id.id == self.account_id.id:
                            ids_agregados.append(payment_line.id)
                    if line.payment_id.has_invoices:
                        line.adjusted_credit = line.payment_id.amount_currency if line.credit > 0 else 0
                        line.adjusted_debit = line.payment_id.amount_currency if line.debit > 0 else 0
                    else:
                        line.adjusted_credit = line.payment_id.amount if line.credit > 0 else 0
                        line.adjusted_debit = line.payment_id.amount if line.debit > 0 else 0

        # Excluir los IDs agregados del dominio final
        domain += [('id', 'not in', ids_agregados)]
        final_lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)

        return final_lines

    def calcular_saldo_anterior2(self):
        # if not self.saldo_anterior_informe:
            if self.currency_id == self.env.user.company_id.currency_id:
                s = self.saldo_al_dia2()
            else:
                s = self.saldo_en_dolares2()
            return s

    def saldo_al_dia2(self):
        domain = [('account_id', '=', self.account_id.id)]
        if self.date_from:
            domain += [('date', '<=', self.date_from)]
        domain += [('move_id.journal_id.exchange_rate_journal', '=', False)]
        domain += [('move_id.apertura', '=', False)]
        domain += [('move_id.cierre', '=', False)]
        domain += [('move_id.resultado', '=', False)]
        domain += [('parent_state', '=', 'posted')]
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        ids_agregados = []
        for l in lines:
            if l.id not in ids_agregados:
                if l.payment_id:
                    if l.payment_id.move_line_ids:
                        for m in l.payment_id.move_line_ids:
                            if m.id != l.id and m.account_id.id == self.account_id.id:
                                ids_agregados.append(m.id)
                    if l.payment_id.monto_moneda_pago > 0.0:
                        if l.debit > 0.0:
                            l.credito = l.payment_id.monto_moneda_pago
                        if l.credit > 0.0:
                            l.debito = l.payment_id.monto_moneda_pago
                    else:
                        if l.debit > 0.0:
                            l.credito = l.payment_id.amount
                        if l.credit > 0.0:
                            l.debito = l.payment_id.amount
                    if l.payment_id.recibo_id:
                        move = self.env['account.move.line'].search(
                            [('name', '=', 'Pago de Recibo Nro. ' + l.payment_id.recibo_id.name),
                             ('account_id', '=', self.account_id.id)])
                        if move:
                            print('se encontro el asiento recibo')
                            ids_agregados.append(move.id)
                    if l.payment_id.orden_pago_id:
                        move1 = self.env['account.move.line'].search(
                            [('name', '=', 'Orden de Pago. ' + l.payment_id.orden_pago_id.name),
                             ('account_id', '=', self.account_id.id)])
                        if move1:
                            print('se encontro el asiento orden de pago ')
                            ids_agregados.append(move1.id)

        domain += [('id', 'not in', ids_agregados)]
        print('Aqui termina')
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        total = 0
        for l in lines:
                total += l.credito - l.debito
        return total

    def saldo_en_dolares2(self):
        domain = [('account_id', '=', self.account_id.id)]
        if self.date_from:
            domain += [('date', '<=', self.date_from)]
        domain += [('move_id.journal_id.exchange_rate_journal', '=', False)]
        domain += [('move_id.apertura', '=', False)]
        domain += [('move_id.cierre', '=', False)]
        domain += [('move_id.resultado', '=', False)]
        domain += [('state', 'in', 'posted')]
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        print('Aqui empieza')
        ids_agregados = []
        print('Aqui empieza')
        ids_agregados = []
        for l in lines:
            if l.id not in ids_agregados:
                print('entra en el primer if')
                if l.payment_id:
                    print('entra en el segundo if')
                    if l.payment_id.move_line_ids:
                        print('entra en el tercer if')
                        for m in l.payment_id.move_line_ids:
                            print(m.name)
                            if m.id != l.id and m.account_id.id == self.account_id.id:
                                print('entra en el cuarto if')
                                ids_agregados.append(m.id)
                    if l.payment_id.monto_moneda_pago > 0.0:
                        if l.debit > 0.0:
                            l.credito = l.payment_id.monto_moneda_pago
                        if l.credit > 0.0:
                            l.debito = l.payment_id.monto_moneda_pago
                    else:
                        if l.debit > 0.0:
                            l.credito = l.payment_id.amount
                        if l.credit > 0.0:
                            l.debito = l.payment_id.amount
                    if l.payment_id.recibo_id:
                        move = self.env['account.move.line'].search(
                            [('name', '=', 'Pago de Recibo Nro. ' + l.payment_id.recibo_id.name),
                             ('account_id', '=', self.account_id.id)])
                        if move:
                            print('se encontro el asiento recibo')
                            ids_agregados.append(move.id)
                    if l.payment_id.orden_pago_id:
                        move1 = self.env['account.move.line'].search(
                            [('name', '=', 'Orden de Pago. ' + l.payment_id.orden_pago_id.name),
                             ('account_id', '=', self.account_id.id)])
                        if move1:
                            print('se encontro el asiento orden de pago ')
                            ids_agregados.append(move1.id)
        print(ids_agregados)
        print(len(ids_agregados))
        domain += [('id', 'not in', ids_agregados)]
        print('Aqui termina')
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        total = 0
        for l in lines:
                total += l.credito - l.debito
        return total

    def agregar_punto_de_miles(self, numero, moneda):
        entero = int(numero)
        if 'USD' in moneda:

            decimal = '{0:.2f}'.format(numero - entero)
            entero_string = '.'.join([str(int(entero))[::-1][i:i + 3] for i in range(0, len(str(int(entero))), 3)])[
                            ::-1]
            if decimal == '0.00':
                numero_con_punto = entero_string + ',00'
            else:
                decimal_string = str(decimal).split('.')
                numero_con_punto = entero_string + ',' + decimal_string[1]
        elif 'PYG' in moneda:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[
                               ::-1]
            return numero_con_punto
        else:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(entero))), 3)])[
                               ::-1]
        num_return = numero_con_punto
        return num_return