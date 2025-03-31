# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, http
import time
import pandas as pd
import math
import io
from odoo.http import request
from datetime import datetime
from datetime import time as datetime_time
from dateutil import relativedelta
import base64
from datetime import date
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class BankStatement(models.Model):
    _name = 'bank.statement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    stage = fields.Selection([
        ('nueva', 'Nueva'),
        ('en_proceso', 'En proceso'),
        ('finalizada', 'Finalizada')
    ], default='nueva', string='Etapa', tracking=True)
    imprimir_responsable = fields.Boolean(string="Firma Responsable", default=False)
    reporte_al_cierre = fields.Binary("Reporte al cierre", readonly=True)

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            self.account_id = self.journal_id.default_account_id.id
        else:
            self.account_id = False

    # @api.depends('statement_lines.statement_date')
    # def _compute_stage(self):
    #     for record in self:
    #         if any(line.statement_date for line in record.statement_lines):
    #             record.stage = 'en_proceso'
    #         elif all(line.statement_date for line in record.statement_lines):
    #             record.stage = 'finalizada'
    #         else:
    #             record.stage = 'nueva'


    @api.onchange('obtener_valores')
    def _get_lines(self):
        if self.obtener_valores:
            if not self.journal_id:
                raise ValidationError('Favor seleccionar Banco')
            if self.date_from > self.date_to:
                raise ValidationError('La fecha desde no puede ser mayor a la fecha hasta')
            self.account_id = self.journal_id.default_account_id.id
            exchange_journal_id = self.env.company.currency_exchange_journal_id.id

            if self.account_id:
                if 'USD' in self.account_id.name or 'Usd' in self.account_id.name or '$' in self.account_id.name:
                    moneda = self.env['res.currency'].search([('name', 'like', 'USD')], limit=1)
                    self.currency_id = moneda
                else:
                    moneda = self.env.user.company_id.currency_id
                    self.currency_id = moneda

            # Ajuste del dominio para filtrar usando statement_date o date
            domain = [('account_id', '=', self.account_id.id)]
            if self.date_from and self.date_to:
                domain += ['|',
                           '&', ('statement_date', '>=', self.date_from), ('statement_date', '<=', self.date_to),
                           '&', ('statement_date', '=', False), ('date', '<=', self.date_to)]
            domain += [('journal_id', '!=', exchange_journal_id)]
            domain += [('parent_state', '=', 'posted')]

            lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
            self.with_context(allow=True).statement_lines = [(6, 0, lines.ids)]

            _logger.info("Iniciando carga de líneas; se encontraron %s registros.", len(lines))
            ids_agregados = []
            for l in lines:
                # Si la línea no tiene statement_date y su fecha es anterior al inicio del periodo,
                # se considera que proviene de conciliaciones anteriores.
                if not l.statement_date and l.date and l.date < self.date_from:
                    _logger.info("Línea pendiente de meses anteriores: %s, fecha: %s (periodo: %s a %s)",
                                 l.name, l.date, self.date_from, self.date_to)

                total = 0
                _logger.info("Procesando línea: %s", l.name)
                if l.id not in ids_agregados:
                    if l.payment_id:
                        if l.payment_id.move_id.line_ids:
                            for m in l.payment_id.move_id.line_ids:
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
                        if 'SUPP.' in l.name or 'CUST.' in l.name:
                            move_same = self.env['account.move.line'].search([
                                ('name', '=', l.name),
                                ('account_id', '=', self.account_id.id)
                            ])
                            if len(move_same) > 1:
                                total = sum(move_same.mapped('amount_currency'))
                                if total < 0:
                                    total_gs = -1 * sum(move_same.mapped('monto_moneda_pago'))
                                    if total_gs != 0:
                                        total = total_gs
                                elif total > 0:
                                    total_gs = sum(move_same.mapped('monto_moneda_pago'))
                                    if total_gs != 0:
                                        total = total_gs
                                if total > 0:
                                    l.write({'credito': total})
                                elif total < 0:
                                    total_gs = sum(move_same.mapped('monto_moneda_pago'))
                                    if total_gs != 0:
                                        total = 0
                                    l.write({'debito': abs(total)})
                                ids_agregados.extend(r.id for r in move_same if r.id != l.id)
                        if l.payment_id.recibo_id:
                            move = self.env['account.move.line'].search([
                                ('name', '=', 'Pago de Recibo Nro. ' + (l.payment_id.recibo_id.name or '')),
                                ('account_id', '=', self.account_id.id)
                            ])
                            if move:
                                ids_agregados.append(move.id)
                        if l.payment_id.orden_pago_id:
                            move1 = self.env['account.move.line'].search([
                                ('name', '=', 'Orden de Pago. ' + l.payment_id.orden_pago_id.name),
                                ('account_id', '=', self.account_id.id)
                            ])
                            if move1:
                                ids_agregados.append(move1.id)
                        if l.payment_id.received_third_check_ids:
                            for third in l.payment_id.received_third_check_ids:
                                if l.check_number:
                                    l.check_number += (third.name if third.name else ' ') + '-'
                                else:
                                    l.check_number = (third.name if third.name else ' ') + '-'
                        if l.payment_id.issued_check_ids:
                            for third in l.payment_id.issued_check_ids:
                                l.check_number = third.name if third.name else ' '
                    else:
                        try:
                            voucher = self.env['account.voucher'].search([
                                ('move_id', '=', l.move_id.id),
                                ('check_id', '!=', False)
                            ])
                        except:
                            voucher = None
                        if voucher:
                            for v in voucher:
                                l.check_number = v.check_id.name
                        else:
                            if l.name and ('SUPP.' in l.name or 'CUST.' in l.name):
                                move_same = self.env['account.move.line'].search([
                                    ('name', '=', l.name),
                                    ('account_id', '=', self.account_id.id)
                                ])
                                if len(move_same) > 1:
                                    if l.currency_id != self.env.company.currency_id and l.currency_id == self.currency_id:
                                        total = sum(move_same.mapped('amount_currency'))
                                    else:
                                        total = sum(move_same.mapped('balance'))
                                        if total < 0:
                                            total_gs = -1 * sum(move_same.mapped('monto_moneda_pago'))
                                            if total_gs != 0:
                                                total = total_gs
                                            elif not l.moneda_pago and l.currency_id != self.env.company.currency_id:
                                                total = sum(move_same.mapped('amount_currency'))
                                        elif total > 0:
                                            total_gs = sum(move_same.mapped('monto_moneda_pago'))
                                            if total_gs != 0:
                                                total = total_gs
                                            elif not l.moneda_pago and l.currency_id != self.env.company.currency_id:
                                                total = sum(move_same.mapped('amount_currency'))
                                    if total > 0:
                                        l.write({'credito': total})
                                    elif total < 0:
                                        l.write({'debito': abs(total)})
                                    ids_agregados.extend(r.id for r in move_same if r.id != l.id)
                            else:
                                if l.currency_id != self.env.company.currency_id:
                                    if l.amount_currency < 0:
                                        l.debito = abs(l.amount_currency)
                                        l.credito = 0
                                    else:
                                        l.credito = l.amount_currency
                                        l.debito = 0
                                else:
                                    if l.balance < 0:
                                        l.debito = abs(l.balance)
                                        l.credito = 0
                                    else:
                                        l.credito = l.balance
                                        l.debito = 0

                domain += [('id', 'not in', ids_agregados)]
                lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
                self.with_context(allow=True).statement_lines = [(6, 0, lines.ids)]
                self.saldo_al_dia()
                self.obtener_valores = None

                if self.stage == 'nueva':
                    self.stage = 'en_proceso'

    def cerrar_conciliacion(self):
        """Cierra la conciliación, actualiza las líneas sin fecha de extracto al siguiente mes,
        genera el reporte PDF y lo guarda en 'reporte_al_cierre'."""
        for record in self:
            _logger.info("Iniciando cierre de conciliación para record con id: %s (tipo: %s)", record.id,
                         type(record.id))
            if record.stage == 'finalizada':
                _logger.warning("La conciliación ya se encuentra finalizada para record id: %s", record.id)
                raise ValidationError("La conciliación ya está finalizada y no se pueden hacer más cambios.")

            for line in record.statement_lines.filtered(lambda l: not l.statement_date):
                if line.date:
                    new_date = line.date + relativedelta.relativedelta(months=+1)
                else:
                    new_date = fields.Date.context_today(self) + relativedelta.relativedelta(months=+1)
                _logger.debug("Actualizando línea id %s: asignando statement_date = %s", line.id, new_date)
                line.write({'statement_date': new_date})
            record.stage = 'finalizada'
            _logger.info("Conciliación marcada como finalizada para record id: %s", record.id)


    @api.model
    def create(self, vals):
        statement_lines = vals.get('statement_lines')
        if statement_lines and statement_lines[0] and len(statement_lines[0]) > 2:
            statement_line_ids = statement_lines[0][2]
            if statement_line_ids:
                _logger.info(f"Procesando líneas de estado con IDs: {statement_line_ids}")
                statement_lines_records = self.env['account.move.line'].browse(statement_line_ids)
                if any(line.statement_date for line in statement_lines_records):
                    vals['stage'] = 'en_proceso'
                else:
                    vals['stage'] = 'nueva'
        else:
            vals['stage'] = 'nueva'

        return super(BankStatement, self).create(vals)

    # @api.one
    @api.depends('statement_lines.statement_date')
    def _compute_amount(self):
        for record in self:
            gl_balance = 0
            bank_balance = 0
            current_update = 0
            gl_balance_not_date = 0

            domain = [('account_id', '=', record.account_id.id)]
            if record.date_to:
                domain += [
                    '|',
                    '&', ('statement_date', '<=', record.date_to),
                    ('statement_date', '>=', record.date_from),
                    '&', ('date', '=', False),
                    ('date', '<=', record.date_to),
                    ('date', '>=', record.date_from)
                ]

            domain += [('move_id.journal_id.exchange_rate_journal', '=', False)]

            lines = self.env['account.move.line'].search(domain)

            gl_balance += sum([line.credito - line.debito for line in lines])

            gl_balance_not_date += sum(
                [line.credito - line.debito for line in lines.filtered(lambda r: not r.statement_date)]
            )
            # _logger.info(f"Balance GL de movimientos sin statement_date: {gl_balance_not_date}")

            # Evitar duplicados al buscar líneas para bank_balance
            domain += [('id', 'not in', record.statement_lines.ids)]
            lines = self.env['account.move.line'].search(domain)
            # _logger.info(f"Líneas de movimiento encontradas para el balance bancario: {len(lines)}")

            bank_balance += sum([line.balance for line in lines])
            # _logger.info(f"Balance bancario calculado: {bank_balance}")

            sum([line.debito_abs - line.credito_abs for line in record.statement_lines if line.statement_date])

            # _logger.info(f"Balance actualizado actual: {current_update}")

            record.gl_balance = gl_balance
            record.bank_balance = current_update
            record.balance_difference = gl_balance_not_date
            record.saldo_inicial_cierre = record.bank_balance
            # _logger.info(f"Balance final: GL {record.gl_balance}, Bancario {record.bank_balance}")

    journal_id = fields.Many2one('account.journal', 'Bank', domain=[('type', '=', 'bank')])
    account_id = fields.Many2one('account.account', 'Bank Account')
    date_from = fields.Date('Date From', default=time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date To',
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[
                                  :10])
    statement_lines = fields.Many2many('account.move.line', order='date asc, write_date desc')
    # gl_balance = fields.Monetary('Movimiento en libro banco de la compañía', readonly=True, compute='_compute_amount')
    gl_balance = fields.Float(string="Movimiento en libro banco de la compañía", readonly=True,
                              compute='_compute_amount')
    # bank_balance = fields.Monetary('Diferencia', readonly=True, compute='_compute_amount')
    bank_balance = fields.Float(string='Diferencia', readonly=True, compute='_compute_amount')
    # balance_difference = fields.Monetary('Montos no reflejados en el extracto bancario', readonly=True, compute='_compute_amount')
    balance_difference = fields.Float(string='Montos no reflejados en el extracto bancario', readonly=True,
                                      compute='_compute_amount')
    current_update = fields.Monetary(string='Balance of entries updated now')
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get('bank.statement'))
    saldo_anterior = fields.Float(string='Saldo inicial', compute='calcular_saldo_anterior', stored=True)
    saldo_inicial = fields.Float(
        string='Saldo a Ingresar',
        required=False,
        help='En este campo se debe ingresar el monto del extracto bancario'
    )
    saldo_inicial_cierre = fields.Float(
        string='Saldo Conciliación de Libro Banco',
        required=False,
        readonly=True,
        compute='_compute_saldo_inicial_cierre')
    obtener_valores = fields.Boolean(string="Obtener Valores")
    imported_line_ids = fields.One2many(
        'bank.statement.import.line',
        'bank_statement_id',
        string="Líneas no reflejadas"
    )

    # saldo_inicial_cierre2 = fields.Float(
    #     string='Saldo cierre Extracto bancario',
    #     required=False,
    #     readonly=True)
    diferencia = fields.Float(
        string='Diferencia',
        required=False,
        compute='_compute_difference')
    saldo_anterior_informe = fields.Float(
        string='Saldo Inicial',
        required=False)
    saldo_final_informe = fields.Float(store=True, readonly=True, compute="saldo_final_final")
    saldo_not_date = fields.Float(store=True, readonly=True, compute='_compute_saldo_not_date')


    @api.depends('statement_lines.statement_date', 'saldo_inicial')
    def _compute_difference(self):
        # _logger.info("Calculando la diferencia entre el saldo inicial y el saldo de cierre")
        self.diferencia = self.saldo_inicial - self.saldo_inicial_cierre
        # _logger.info(f"Diferencia calculada: {self.diferencia}")

    def saldo_por_linea(self, saldo_anterior):
        self.statement_lines = self.statement_lines.sorted(key=lambda r: (r.date, -r.write_date.timestamp()))
        _logger.info("Orden de statement_lines: %s", [(l.name, l.date) for l in self.statement_lines])
        sa = saldo_anterior
        # _logger.info("Saldo inicial: %s", sa)
        for line in self.statement_lines:
            # _logger.info("Procesando línea: %s, fecha: %s, débito: %s, crédito: %s", line.name, line.date, line.debito,
            #              line.credito)
            # Si la línea corresponde a meses anteriores, forzamos su saldo a 0
            if line.date and line.date < self.date_from:
                # _logger.info(
                #     "Línea de meses anteriores (aunque tenga statement_date) forzada a saldo 0: %s, fecha: %s (periodo: %s a %s)",
                #     line.name, line.date, self.date_from, self.date_to)
                line.saldo = 0
            else:
                if line.credito != 0:
                    sa -= abs(line.credito)
                    # _logger.info("Se resta crédito: %s, nuevo saldo: %s", abs(line.credito), sa)
                else:
                    sa += line.debito
                    # _logger.info("Se suma débito: %s, nuevo saldo: %s", line.debito, sa)
                line.saldo = sa
            # _logger.info("Saldo asignado a la línea %s: %s", line.name, line.saldo)

    @api.depends('statement_lines.saldo', 'statement_lines.credito_abs', 'statement_lines.debito_abs',
                 'statement_lines.statement_date')
    def saldo_final_final(self):
        for record in self:
            if record.statement_lines:
                record.saldo_final_informe = record.statement_lines[-1].saldo
            else:
                record.saldo_final_informe = 0

    # Saldo total de las líneas sin fecha
    @api.depends('statement_lines')
    def _compute_saldo_not_date(self):
        saldo_not_date = 0
        lines = self.statement_lines.filtered(lambda r: not r.statement_date)
        # _logger.warning(f"Líneas sin fecha %s: {len(lines)}")
        for line in lines:
            saldo_not_date += line.debito - line.credito
        self.saldo_not_date = saldo_not_date
#         _logger.warning(f'Jota %s', self.saldo_not_date)

    @api.depends('statement_lines', 'date_from', 'date_to', 'saldo_anterior_informe')
    def _compute_saldo_inicial_cierre(self):
        for record in self:
            # Inicia con el saldo inicial (saldo_anterior_informe)
            saldo_inicial_cierre = record.saldo_anterior_informe or 0
            _logger.info("Record %s: saldo_anterior_informe = %s", record.id, record.saldo_anterior_informe)
            # Filtra las líneas que tienen statement_date y que están dentro del rango
            filtered_lines = record.statement_lines.filtered(
                lambda r: r.statement_date and (
                            r.statement_date >= record.date_from and r.statement_date <= record.date_to)
            )
            _logger.info("Record %s: se han filtrado %s líneas con statement_date en el rango %s - %s",
                         record.id, len(filtered_lines), record.date_from, record.date_to)
            # Suma la diferencia (débito – crédito) de las líneas filtradas
            for line in filtered_lines:
                diferencia = line.debito_abs - line.credito_abs
                saldo_inicial_cierre += diferencia
                _logger.info("Procesando línea %s: débito = %s, crédito = %s, diferencia = %s, saldo acumulado = %s",
                             line.name, line.debito, line.credito, diferencia, saldo_inicial_cierre)
            record.saldo_inicial_cierre = saldo_inicial_cierre
            _logger.info("Record %s: saldo_inicial_cierre final asignado = %s", record.id, record.saldo_inicial_cierre)

    def bank_statement_report(self):
        # _logger.info("Generando reporte de estado bancario")
        self.ensure_one()

        try:
            report_ref = self.env.ref('bank_reconciliation.report_bank_statement')
            # _logger.info(f"Referencia del reporte: {report_ref}")
            if not report_ref:
                _logger.error("No se encontró la referencia al reporte 'bank_reconciliation.report_bank_statement'")
            return report_ref.report_action(self)
        except ValueError as e:
            _logger.error(f"Error al buscar la referencia del reporte: {str(e)}")
            raise
        except Exception as e:
            _logger.error(f"Error inesperado al generar el reporte: {str(e)}")
            raise

    def bank_book_report(self):
        # _logger.info("Generando reporte de libro de banco")
        self.ensure_one()
        self.sent = True
        return self.env.ref('bank_reconciliation.report_book_bank').report_action(self)

    def account_mvl_object(self):
        # _logger.info("Obteniendo líneas contables para el estado bancario")
        exchange_journal_id = self.env.company.currency_exchange_journal_id.id
        domain = [('account_id', '=', self.account_id.id)]
        if self.date_from:
            domain += [('statement_date', '>=', self.date_from)]
        if self.date_to:
            domain += [('date', '<=', self.date_to)]
        domain += [('journal_id', '!=', exchange_journal_id)]
        domain += [('parent_state', '=', 'posted')]

        # _logger.info(f"Dominio para búsqueda de movimientos: {domain}")
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)

        # _logger.info(f"Movimientos encontrados: {len(lines)}")
        ids_agregados = []
        for l in lines:
            # _logger.info(f"Procesando movimiento: {l.name}")
            if l.id not in ids_agregados:
                if l.payment_id:
                    if l.payment_id.move_id.line_ids:
                        for m in l.payment_id.move_id.line_ids:
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
                            [('name', '=', 'Pago de Recibo Nro. ' + (l.payment_id.recibo_id.name or '')),
                             ('account_id', '=', self.account_id.id)]
                        )
                        if move:
                            # _logger.info(f"Movimiento asociado al recibo encontrado: {move.id}")
                            ids_agregados.append(move.id)
                    if l.payment_id.orden_pago_id:
                        move1 = self.env['account.move.line'].search(
                            [('name', '=', 'Orden de Pago. ' + l.payment_id.orden_pago_id.name),
                             ('account_id', '=', self.account_id.id)])
                        if move1:
                            # _logger.info(f"Movimiento asociado a la orden de pago encontrado: {move1.id}")
                            ids_agregados.append(move1.id)

        # _logger.info(f"IDs agregados: {ids_agregados}")
        domain += [('id', 'not in', ids_agregados)]
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        # _logger.info(f"Total de líneas finales: {len(lines)}")

        return lines

    def get_all_pending_lines(self):
        self.ensure_one()
        exchange_journal_id = self.env.company.currency_exchange_journal_id.id
        domain = [
            ('account_id', '=', self.account_id.id),
            ('parent_state', '=', 'posted'),
            ('statement_date', '=', False),
            ('journal_id', '!=', exchange_journal_id),
            ('date', '<=', self.date_to)
        ]
        return self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)

    def account_mvl_object2(self):
        # _logger.info("Obteniendo líneas contables (segunda variante)")
        domain = [('account_id', '=', self.account_id.id)]
        exchange_journal_id = self.env.company.currency_exchange_journal_id.id
        if self.date_to:
            domain += ['|',
                       ('statement_date', '!=', False),
                       ('date', '<=', self.date_to)]
        domain += [('journal_id', '!=', exchange_journal_id)]
        domain += [('parent_state', '=', 'posted')]

        # _logger.info(f"Dominio para búsqueda de movimientos (segunda variante): {domain}")
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)

        # _logger.info(f"Movimientos encontrados: {len(lines)}")
        ids_agregados = []
        for l in lines:
            # _logger.info(f"Procesando movimiento: {l.name}")
            if l.id not in ids_agregados:
                if l.payment_id:
                    if l.payment_id.move_id.line_ids:
                        for m in l.payment_id.move_id.line_ids:
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
                            [('name', '=', 'Pago de Recibo Nro. ' + (l.payment_id.recibo_id.name or '')),
                             ('account_id', '=', self.account_id.id)]
                        )
                        if move:
                            # _logger.info(f"Movimiento asociado al recibo encontrado: {move.id}")
                            ids_agregados.append(move.id)
                    if l.payment_id.orden_pago_id:
                        move1 = self.env['account.move.line'].search(
                            [('name', '=', 'Orden de Pago. ' + l.payment_id.orden_pago_id.name),
                             ('account_id', '=', self.account_id.id)])
                        if move1:
                            # _logger.info(f"Movimiento asociado a la orden de pago encontrado: {move1.id}")
                            ids_agregados.append(move1.id)

        # _logger.info(f"IDs agregados: {ids_agregados}")
        domain += [('id', 'not in', ids_agregados)]
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        # _logger.info(f"Total de líneas finales: {len(lines)}")

        return lines

    def currency_symbol(self):
        guarani = '₲'
        usd = '$'
        if 'USD' in self.account_id.name:
            return usd
        else:
            return guarani
        # if self.account_id.currency_id.name in 'PYG':
        #     return guarani
        # else:
        #     return usd

    def agregar_punto_de_miles(self, numero, moneda):
        if numero is None or (isinstance(numero, float) and math.isnan(numero)) or pd.isna(numero):
            return "0,00"

        if not isinstance(moneda, str):
            moneda = str(moneda) if moneda else ""

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
        else:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(entero))), 3)])[
                               ::-1]

        return numero_con_punto

    @api.depends('currency_id', 'account_id')
    def calcular_saldo_anterior(self):
        for record in self:
            previous_statement = record.env['bank.statement'].search(
                [
                    ('date_to', '<', record.date_from),
                    ('journal_id', '=', record.journal_id.id),
                    ('stage', 'in', ['finalizada', 'en_proceso','nueva'])
                ],
                order='date_to desc',
                limit=1
            )
            if previous_statement:
                base = previous_statement.saldo_final_informe
            else:
                base = 0

            record.saldo_anterior = base
            record.saldo_anterior_informe = base
            record.saldo_por_linea(base)

    def calcular_saldo_anterior2(self):
        # _logger.info("Calculando saldo anterior (segunda versión).")
        if self.currency_id == self.env.user.company_id.currency_id:
            # _logger.info("Calculando saldo al día.")
            s = self.saldo_al_dia2()
        else:
            # _logger.info("Calculando saldo en dólares.")
            s = self.saldo_en_dolares2()
        return 0

    def saldo_al_dia(self):
        # _logger.info("Calculando saldo al día.")
        domain = [('account_id', '=', self.account_id.id)]
        exchange_journal_id = self.env.company.currency_exchange_journal_id.id
        if self.date_from:
            fecha_from = self.date_from
            if fecha_from.month == 1 and fecha_from.day == 1:
                # _logger.info("Primer día del año, saldo es 0.")
                return 0
            else:
                first_day_year = datetime(fecha_from.year, 1, 1)
                # Priorizar statement_date si existe
                domain += [
                    '|',
                    ('statement_date', '<', self.date_from),
                    '&', ('statement_date', '=', False), ('date', '<', self.date_from),
                    ('date', '>=', first_day_year)
                ]
        domain += [('journal_id', '!=', exchange_journal_id)]
        domain += [('parent_state', '=', 'posted')]

        # _logger.info(f"Dominio para la búsqueda de líneas: {domain}")
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date or r.statement_date)
        # _logger.info(f"Líneas encontradas: {len(lines)}")

        ids_agregados = []
        total = 0
        for l in lines:
            if l.id not in ids_agregados:
                if l.payment_id:
                    if l.payment_id.move_id.line_ids:
                        for m in l.payment_id.move_id.line_ids:
                            if m.id != l.id and m.account_id.id == self.account_id.id:
                                ids_agregados.append(m.id)
                    if l.payment_id.monto_moneda_pago > 0.0:
                        if l.debit > 0.0:
                            l.credito = l.payment_id.monto_moneda_pago
                        if l.credit > 0.0:
                            l.debito = l.payment_id.monto_moneda_pago
                # Evitar duplicados
                if l.id not in ids_agregados:
                    total += l.credito - l.debito
                    # _logger.info(f"Línea procesada (ID {l.id}): {l.name}, saldo parcial: {total}")

        # _logger.info(f"Saldo total calculado al día: {total}")
        return total

    def saldo_en_dolares(self):
        # _logger.info("Calculando saldo en dólares.")
        domain = [('account_id', '=', self.account_id.id)]
        exchange_journal_id = self.env.company.currency_exchange_journal_id.id
        if self.date_from:
            domain += [('date', '<', self.date_from), ('date', '>=', datetime(self.date_from.year, 1, 1))]
        domain += [('journal_id', '!=', exchange_journal_id)]
        domain += [('parent_state', '=', 'posted')]

        # _logger.info(f"Dominio para la búsqueda de líneas en dólares: {domain}")
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        # _logger.info(f"Líneas encontradas: {len(lines)}")

        ids_agregados = []
        for l in lines:
            if l.id not in ids_agregados:
                if l.payment_id:
                    if l.payment_id.move_id.line_ids:
                        for m in l.payment_id.move_id.line_ids:
                            if m.id != l.id and m.account_id.id == self.account_id.id:
                                ids_agregados.append(m.id)
                    if l.payment_id.monto_moneda_pago > 0.0:
                        if l.debit > 0.0:
                            l.credito = l.payment_id.monto_moneda_pago
                        if l.credit > 0.0:
                            l.debito = l.payment_id.monto_moneda_pago
                    if l.payment_id.recibo_id:
                        move = self.env['account.move.line'].search(
                            [('name', '=', 'Pago de Recibo Nro. ' + (l.payment_id.recibo_id.name or '')),
                             ('account_id', '=', self.account_id.id)]
                        )
                        if move:
                            # _logger.info(f"Asiento recibo encontrado: {move.id}")
                            ids_agregados.append(move.id)
                    if l.payment_id.orden_pago_id:
                        move1 = self.env['account.move.line'].search(
                            [('name', '=', 'Orden de Pago. ' + l.payment_id.orden_pago_id.name),
                             ('account_id', '=', self.account_id.id)])
                        if move1:
                            # _logger.info(f"Asiento orden de pago encontrado: {move1.id}")
                            ids_agregados.append(move1.id)

        # _logger.info(f"IDs agregados: {ids_agregados}")
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        total = 0
        for l in lines:
            total += l.credito - l.debito
        # _logger.info(f"Saldo en dólares calculado: {total}")
        return total

    def saldo_al_dia2(self):
        # _logger.info("Iniciando cálculo de saldo al día (versión 2).")
        domain = [('account_id', '=', self.account_id.id)]
        exchange_journal_id = self.env.company.currency_exchange_journal_id.id
        if self.date_from:
            domain += [('date', '<', self.date_from), ('date', '>=', datetime(self.date_from.year, 1, 1))]
        domain += [('journal_id', '!=', exchange_journal_id)]
        domain += [('parent_state', '=', 'posted')]

        # _logger.info(f"Dominio para la búsqueda de líneas: {domain}")
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        # _logger.info(f"Líneas encontradas: {len(lines)}")

        ids_agregados = []
        for l in lines:
            if l.id not in ids_agregados:
                if l.payment_id:
                    if l.payment_id.move_id.line_ids:
                        for m in l.payment_id.move_id.line_ids:
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
                            [('name', '=', 'Pago de Recibo Nro. ' + (l.payment_id.recibo_id.name or '')),
                             ('account_id', '=', self.account_id.id)]
                        )
                        if move:
                            # _logger.info(f"Asiento recibo encontrado: {move.id}")
                            ids_agregados.append(move.id)
                    if l.payment_id.orden_pago_id:
                        move1 = self.env['account.move.line'].search(
                            [('name', '=', 'Orden de Pago. ' + l.payment_id.orden_pago_id.name),
                             ('account_id', '=', self.account_id.id)])
                        if move1:
                            # _logger.info(f"Asiento orden de pago encontrado: {move1.id}")
                            ids_agregados.append(move1.id)

        # _logger.info(f"IDs agregados: {ids_agregados}")
        domain += [('id', 'not in', ids_agregados)]
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        total = 0
        for l in lines:
            total += l.credito - l.debito
        # _logger.info(f"Saldo total calculado: {total}")
        return total

    def saldo_en_dolares2(self):
        # _logger.info("Iniciando cálculo de saldo en dólares (versión 2).")
        domain = [('account_id', '=', self.account_id.id)]
        exchange_journal_id = self.env.company.currency_exchange_journal_id.id
        if self.date_from:
            domain += [('date', '<', self.date_from), ('date', '>=', datetime(self.date_from.year, 1, 1))]
        domain += [('journal_id', '!=', exchange_journal_id)]
        domain += [('parent_state', '=', 'posted')]

        # _logger.info(f"Dominio para la búsqueda de líneas en dólares: {domain}")
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        # _logger.info(f"Líneas encontradas: {len(lines)}")

        ids_agregados = []
        for l in lines:
            if l.id not in ids_agregados:
                if l.payment_id:
                    if l.payment_id.move_id.line_ids:
                        for m in l.payment_id.move_id.line_ids:
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
                            [('name', '=', 'Pago de Recibo Nro. ' + (l.payment_id.recibo_id.name or '')),
                             ('account_id', '=', self.account_id.id)]
                        )
                        if move:
                            # _logger.info(f"Asiento recibo encontrado: {move.id}")
                            ids_agregados.append(move.id)
                    if l.payment_id.orden_pago_id:
                        move1 = self.env['account.move.line'].search(
                            [('name', '=', 'Orden de Pago. ' + l.payment_id.orden_pago_id.name),
                             ('account_id', '=', self.account_id.id)])
                        if move1:
                            # _logger.info(f"Asiento orden de pago encontrado: {move1.id}")
                            ids_agregados.append(move1.id)

        # _logger.info(f"IDs agregados: {ids_agregados}")
        domain += [('id', 'not in', ids_agregados)]
        lines = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        total = 0
        for l in lines:
            total += l.credito - l.debito
        # _logger.info(f"Saldo total en dólares calculado: {total}")
        return total

    def action_generate_excel(self):
        """Genera y descarga automáticamente el Excel con las líneas en el rango de fecha."""
        self.ensure_one()
        url = "/bank_reconciliation/download_excel?record_id=%s" % self.id
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }
class ExcelDownloadController(http.Controller):
    @http.route('/bank_reconciliation/download_excel', type='http', auth='user', csrf=False)
    def download_excel(self, record_id=None, **kwargs):
        if not record_id:
            return request.not_found()

        bank_statement = request.env['bank.statement'].sudo().browse(int(record_id))
        if not bank_statement.exists():
            return request.not_found()

        bank_name = bank_statement.journal_id.name or ""
        bank_account = (bank_statement.journal_id.bank_account_id.acc_number
                        if bank_statement.journal_id.bank_account_id else "")
        currency_name = (bank_statement.journal_id.currency_id.name
                         if bank_statement.journal_id.currency_id else "PYG")

        date_from = bank_statement.date_from
        date_to = bank_statement.date_to

        lines = bank_statement.statement_lines.filtered(lambda l: (
                (l.statement_date and date_from <= l.statement_date <= date_to) or
                (not l.statement_date and l.date and date_from <= l.date <= date_to)
        ))

        data = []
        for line in lines:
            fecha_linea = line.statement_date or ""
            tipo_transaccion = line.descripcion or ""

            data.append({
                "Banco o Entidad del Sistema Financiero": bank_name,
                "Número de cuenta en la institución financiera": bank_account,
                "Fecha": fecha_linea,
                "Pais de la Cuenta del SO": bank_statement.company_id.country_id.name or "",
                "Tipo  de  Moneda": currency_name,
                "Número de Operación según Extracto Bancario": line.ref,
                "Tipo de Transacción": tipo_transaccion,
                "Debito  (A)": line.debito,
                "Credito (B)": line.credito,
                "Saldo a la Fecha": line.saldo
            })

        if not data:
            data = [{"Mensaje": "No hay líneas en el rango de fecha seleccionado."}]

        df = pd.DataFrame(data)


        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Reporte - Conciliacion Bancaria")

            workbook = writer.book
            worksheet = writer.sheets["Reporte - Conciliacion Bancaria"]

            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'middle',
                'align': 'center',
                'fg_color': '#1F4E78',
                'font_color': '#FFFFFF'
            })

            wrap_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
            })

            col_widths = [40, 40, 15, 20, 20, 45, 25, 15, 15, 18]
            for col_num, col_name in enumerate(df.columns):
                worksheet.write(0, col_num, col_name, header_format)
                worksheet.set_column(col_num, col_num, col_widths[col_num], wrap_format)

            worksheet.freeze_panes(1, 0)

        output.seek(0)
        excel_file = output.read()

        headers = [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', 'attachment; filename="Reporte - Conciliacion Bancaria.xlsx"')
        ]
        return request.make_response(excel_file, headers)


class BankStatementImportLine(models.Model):
    _name = 'bank.statement.import.line'
    _description = 'Líneas importadas del extracto no existen en la conciliación'

    ref = fields.Char("Referencia", required=True)
    statement_date = fields.Date("Fecha de Extracto")
    date = fields.Date("Fecha")
    debit = fields.Float("Débito")
    credit = fields.Float("Crédito")
    balance = fields.Float("Saldo")
    amount_currency = fields.Float("Importe en Divisa")
    bank_statement_id = fields.Many2one('bank.statement', string="Extracto Bancario", ondelete='cascade')
    descripcion = fields.Char("Descripción", help="Descripción o tipo de transacción")

