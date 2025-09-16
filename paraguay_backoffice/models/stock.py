
# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api, _
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError,UserError
from odoo.tools import float_compare, float_round, float_is_zero, pycompat
from collections import defaultdict


import logging
_logger = logging.getLogger(__name__)

class boleta_remision(models.Model):
    _inherit = "stock.picking"

    invoice_imp_id = fields.Many2one('account.move', 'Factura de importación')
    final_partner_id = fields.Many2one('res.partner',compute='_get_final_partner')
    obs = fields.Char(string="Observaciones", help="Nombre que se utilizará en los apuntes contables")

    @api.depends('invoice_imp_id','move_line_ids_without_package','move_line_ids','move_lines')
    def _get_final_partner(self):
        for rec in self:
            rec.final_partner_id = False
            if rec.invoice_imp_id:
                rec.final_partner_id = rec.invoice_imp_id.partner_id
            else:
                if rec.partner_id:
                    rec.final_partner_id = rec.partner_id

# class StockMove(models.Model):
#     _inherit = "stock.move"
#
#     partner_id = fields.Many2one(related="picking_id.partner_id",store=True,string="Empresa")
#
#
#     def _get_price_unit(self):
#         #raise ValidationError ('AAAEEE')
#         """ Returns the unit price to store on the quant """
#         self.ensure_one()
#         if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
#             line = self.purchase_line_id
#             order = line.order_id
#             price_unit = line.price_unit
#             if line.taxes_id:
#                 price_unit = line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id,
#                                                                     quantity=1.0)['total_excluded']
#             if line.product_uom.id != line.product_id.uom_id.id:
#                 price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
#             if order.currency_id != order.company_id.currency_id:
#                 # The date must be today, and not the date of the move since the move move is still
#                 # in assigned state. However, the move date is the scheduled date until move is
#                 # done, then date of actual move processing. See:
#                 # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
#                 #price_unit = order.currency_id._convert(price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self),round=False)
#                 invoice_lin = self.purchase_line_id.mapped('invoice_lines').filtered(lambda r: r.move_id.payment_state in ('not_paid', 'paid','partial','in_payment'))
#                 invoice_currency = invoice_lin.mapped('currency_id')
#
#                 if invoice_currency:
#                     invoice_currency = invoice_currency[0]
#                     if invoice_currency != self.company_id.currency_id:
#                         # Do not use price_unit since we want the price tax excluded. And by the way, qty
#                         # is in the UOM of the product, not the UOM of the PO line.
#                         linea_factura = self.purchase_line_id.mapped('invoice_lines')
#                         if len(linea_factura) > 1:
#
#                             linea_factura = linea_factura[0]
#
#                         else:
#                             if linea_factura:
#                                 linea_factura = linea_factura
#
#                         if linea_factura.quantity == 0:
#                             raise ValidationError(
#                                 'No se puede calcular el costo si la cantidad del producto %s en la factura es 0' % linea_factura.product_id.name)
#
#                         invoice_unit = (linea_factura.price_subtotal / linea_factura.quantity)
#                         rate = self.env['res.currency.rate'].search(
#                             [('name', '=', linea_factura.move_id.invoice_date),
#                              ('currency_id', '=', linea_factura.currency_id.id)])
#                         if not rate:
#                             raise ValidationError(
#                                 'Debe cargar cotizacion para la fecha %s' % linea_factura.move_id.invoice_date)
#                         price_unit = invoice_unit * rate[0].set_venta
#             return price_unit
#         return super(StockMove, self)._get_price_unit()
#
#     # TODO Migrar a la V15
#     # def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id):
#     #     """ Overridden from stock_account to support amount_currency on valuation lines generated from inv
#     #     """
#     #     self.ensure_one()
#     #     #raise ValidationError('eee')
#     #     rslt = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id)
#     #     invoice_lin = self.purchase_line_id.mapped('invoice_lines').filtered(lambda r: r.invoice_id.state != 'cancel')
#     #     invoice_currency = invoice_lin.mapped('currency_id')
#     #     if self.purchase_line_id.currency_id and (self.purchase_line_id.currency_id != self.company_id.currency_id):
#     #         if not self.purchase_line_id.invoice_lines:
#     #             raise ValidationError('No se puede recibir el producto sin haber cargado la factura cuando la compra es en una moneda extranjera')
#     #
#     #     if self.purchase_line_id.invoice_lines:
#     #         invoice_lin = self.purchase_line_id.mapped('invoice_lines').filtered(lambda r: r.invoice_id.state in ('open','paid'))
#     #         invoice_currency = invoice_lin.mapped('currency_id')
#     #         if not invoice_currency and self.purchase_line_id.currency_id != self.company_id.currency_id:
#     #             raise ValidationError('No se puede recibir el producto sin haber cargado o validado la factura cuando la compra es en una moneda extranjera')
#     #         linea_factura = self.purchase_line_id.mapped('invoice_lines')
#     #         if len(linea_factura) > 1:
#     #
#     #             linea_factura = linea_factura[0]
#     #
#     #         else:
#     #             if linea_factura:
#     #                 linea_factura = linea_factura
#     #         if invoice_currency:
#     #             invoice_currency = invoice_currency[0]
#     #             if invoice_currency != self.company_id.currency_id:
#     #                 # Do not use price_unit since we want the price tax excluded. And by the way, qty
#     #                 # is in the UOM of the product, not the UOM of the PO line.
#     #                 linea_factura = self.purchase_line_id.mapped('invoice_lines')
#     #                 if len(linea_factura)>1:
#     #
#     #
#     #                     linea_factura = linea_factura[0]
#     #
#     #                 else:
#     #                     if linea_factura:
#     #                         linea_factura = linea_factura
#     #
#     #                 if linea_factura.quantity == 0:
#     #                     raise ValidationError(
#     #                         'No se puede calcular el costo si la cantidad del producto %s en la factura es 0' % linea_factura.product_id.name)
#     #
#     #                 invoice_price_unit = (linea_factura.price_subtotal / linea_factura.quantity )
#     #                 currency_move_valuation = invoice_currency.round(invoice_price_unit * abs(qty))
#     #                 rate = self.env['res.currency.rate'].search([('name','=',linea_factura.invoice_id.date_invoice),('currency_id','=',invoice_currency.id)])
#     #                 if not rate:
#     #                     raise ValidationError('Debe cargar cotizacion para la fecha %s' % linea_factura.invoice_id.date_invoice )
#     #                 if len(rate) > 0:
#     #                     rslt['credit_line_vals']['amount_currency'] = rslt['credit_line_vals']['credit'] and -currency_move_valuation or currency_move_valuation
#     #                     rslt['credit_line_vals']['currency_id'] = invoice_currency.id
#     #                     rslt['credit_line_vals']['credit'] = abs(rslt['credit_line_vals']['amount_currency']) * rate[0].set_venta
#     #                     rslt['debit_line_vals']['amount_currency'] = rslt['debit_line_vals']['credit'] and -currency_move_valuation or currency_move_valuation
#     #                     rslt['debit_line_vals']['currency_id'] = invoice_currency.id
#     #                     rslt['debit_line_vals']['debit'] = abs(rslt['debit_line_vals']['amount_currency']) *  rate[0].set_venta
#     #         rslt['credit_line_vals']['ref'] =  linea_factura.invoice_id.name
#     #         rslt['debit_line_vals']['ref'] =  linea_factura.invoice_id.name
#     #     if self.picking_id.invoice_imp_id:
#     #         rslt['credit_line_vals']['ref'] = self.picking_id.invoice_imp_id.number + '-' + self.picking_id.name
#     #         rslt['debit_line_vals']['ref'] = self.picking_id.invoice_imp_id.number+ '-' + self.picking_id.name
#     #
#     #     if self.sale_line_id.invoice_lines:
#     #         linea_factura = self.sale_line_id.invoice_lines[0]
#     #         rslt['credit_line_vals']['ref'] =  linea_factura.invoice_id.name + '-' + self.picking_id.name
#     #         rslt['debit_line_vals']['ref'] =  linea_factura.invoice_id.name + '-' + self.picking_id.name
#     #     if self.picking_id.obs:
#     #         rslt['credit_line_vals']['ref'] = self.picking_id.obs + '-' + self.picking_id.name
#     #         rslt['debit_line_vals']['ref'] = self.picking_id.obs + '-' + self.picking_id.name
#     #
#     #
#     #     return rslt
#
#     # @api.multi
#     def _force_assign(self):
#         """ Allow to work on stock move lines even if the reservationis not possible. We just mark
#         the move as assigned, so the view does not block the user.
#         """
#         for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available', 'assigned']):
#             move.write({'state': 'assigned'})
#
#     def _is_out(self):
#         """ Check if the move should be considered as leaving the company so that the cost method
#         will be able to apply the correct logic.
#         :return: True if the move is leaving the company else False
#         """
#         for move_line in self.move_line_ids.filtered(lambda ml: not ml.owner_id):
#             if move_line.location_id._should_be_valued() and not move_line.location_dest_id._should_be_valued():
#                 return True
#             elif move_line.location_id.valuation_out_account_id and move_line.location_id.usage in ('production', 'inventory') and self.picking_code == 'outgoing' and not move_line.location_dest_id._should_be_valued():
#                 return True
#
#         return False
#
#     # TODO Migrar a la V15
#     # def _account_entry_move(self):
#     #     """ Accounting Valuation Entries """
#     #     self.ensure_one()
#     #     if self.product_id.type != 'product':
#     #         # no stock valuation for consumable products
#     #         return False
#     #     if self.restrict_partner_id:
#     #         # if the move isn't owned by the company, we don't make any valuation
#     #         return False
#     #
#     #     location_from = self.location_id
#     #     location_to = self.location_dest_id
#     #     company_from = self.mapped('move_line_ids.location_id.company_id') if self._is_out() else False
#     #     company_to = self.mapped('move_line_ids.location_dest_id.company_id') if self._is_in() else False
#     #
#     #     # Create Journal Entry for products arriving in the company; in case of routes making the link between several
#     #     # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
#     #     if self._is_in():
#     #         journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
#     #         if location_from and location_from.usage == 'customer':  # goods returned from customer
#     #             self.with_context(force_company=company_to.id)._create_account_move_line(acc_dest, acc_valuation, journal_id)
#     #         else:
#     #             self.with_context(force_company=company_to.id)._create_account_move_line(acc_src, acc_valuation, journal_id)
#     #
#     #     # Create Journal Entry for products leaving the company
#     #     if self._is_out():
#     #         journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
#     #         if location_to and location_to.usage == 'supplier':  # goods returned to supplier
#     #             self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_src, journal_id)
#     #         elif location_from and location_from.usage in ('production','inventory') and self.picking_code == 'outgoing' and location_to.usage == 'customer':
#     #             self.with_context(force_company=company_from.id)._create_account_move_line(acc_src, acc_dest, journal_id)
#     #
#     #         else:
#     #             self.with_context(force_company=company_from.id)._create_account_move_line(acc_valuation, acc_dest, journal_id)
#     #
#     #     if self.company_id.anglo_saxon_accounting:
#     #         # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
#     #         journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
#     #         if self._is_dropshipped():
#     #             self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_src, acc_dest, journal_id)
#     #         elif self._is_dropshipped_returned():
#     #             self.with_context(force_company=self.company_id.id)._create_account_move_line(acc_dest, acc_src, journal_id)
#     #
#     #     if self.company_id.anglo_saxon_accounting:
#     #         #eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
#     #         allowed_invoice_types = self._is_in() and ('in_invoice', 'out_refund') or ('in_refund', 'out_invoice')
#     #         self._get_related_invoices().filtered(lambda x: x.type in allowed_invoice_types)._anglo_saxon_reconcile_valuation(product=self.product_id)
#
#
#
#
#     def _run_valuation(self, quantity=None):
#         self.ensure_one()
#         value_to_return = 0
#         if self._is_in():
#             valued_move_lines = self.move_line_ids.filtered(lambda ml: not ml.location_id._should_be_valued() and ml.location_dest_id._should_be_valued() and not ml.owner_id)
#             valued_quantity = 0
#             for valued_move_line in valued_move_lines:
#                 valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, self.product_id.uom_id)
#
#             # Note: we always compute the fifo `remaining_value` and `remaining_qty` fields no
#             # matter which cost method is set, to ease the switching of cost method.
#             vals = {}
#             price_unit = self._get_price_unit()
#             value = price_unit * (quantity or valued_quantity)
#             value_to_return = value if quantity is None or not self.value else self.value
#             vals = {
#                 'price_unit': price_unit,
#                 'value': value_to_return,
#                 'remaining_value': value if quantity is None else self.remaining_value + value,
#             }
#             vals['remaining_qty'] = valued_quantity if quantity is None else self.remaining_qty + quantity
#
#             if self.product_id.cost_method == 'standard':
#                 value = self.product_id.standard_price * (quantity or valued_quantity)
#                 value_to_return = value if quantity is None or not self.value else self.value
#                 vals.update({
#                     'price_unit': self.product_id.standard_price,
#                     'value': value_to_return,
#                 })
#             self.write(vals)
#         elif self._is_out():
#             valued_move_lines = self.move_line_ids.filtered(lambda ml: ml.location_id._should_be_valued() and not ml.location_dest_id._should_be_valued() and not ml.owner_id)
#             if not valued_move_lines:
#                 valued_move_lines = self.move_line_ids.filtered(lambda move_line: move_line.location_id.valuation_out_account_id and move_line.location_id.usage in ('production', 'inventory') and move_line.move_id.picking_code == 'outgoing' and not move_line.location_dest_id._should_be_valued() and not move_line.owner_id)
#             valued_quantity = 0
#             for valued_move_line in valued_move_lines:
#                 valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, self.product_id.uom_id)
#             self.env['stock.move']._run_fifo(self, quantity=quantity)
#             if self.product_id.cost_method in ['standard', 'average']:
#                 curr_rounding = self.company_id.currency_id.rounding
#                 value = -float_round(self.product_id.standard_price * (valued_quantity if quantity is None else quantity), precision_rounding=curr_rounding)
#                 value_to_return = value if quantity is None else self.value + value
#                 if self.asset_id:
#                     self.write({
#                         'value': -self.asset_id.valor_venta,
#                         'price_unit': self.asset_id.valor_venta,
#                     })
#                 else:
#                     self.write({
#                         'value': value_to_return,
#                         'price_unit': value / valued_quantity,
#                     })
#         elif self._is_dropshipped() or self._is_dropshipped_returned():
#             curr_rounding = self.company_id.currency_id.rounding
#             if self.product_id.cost_method in ['fifo']:
#                 price_unit = self._get_price_unit()
#                 # see test_dropship_fifo_perpetual_anglosaxon_ordered
#                 self.product_id.standard_price = price_unit
#             else:
#                 price_unit = self.product_id.standard_price
#             value = float_round(self.product_qty * price_unit, precision_rounding=curr_rounding)
#             value_to_return = value if self._is_dropshipped() else -value
#             # In move have a positive value, out move have a negative value, let's arbitrary say
#             # dropship are positive.
#             self.write({
#                 'value': value_to_return,
#                 'price_unit': price_unit if self._is_dropshipped() else -price_unit,
#             })
#         return value_to_return
#
#     # @api.multi
#     def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id):
#         for rec in self:
#             result = super(StockMove, rec.with_context(force_period_date=rec.date_expected))._create_account_move_line(credit_account_id,debit_account_id,journal_id)
#             return result
#
# class StockMoveLine(models.Model):
#     _inherit = "stock.move.line"
#
#     partner_id = fields.Many2one(related="picking_id.partner_id",store =True, string="Empresa")

