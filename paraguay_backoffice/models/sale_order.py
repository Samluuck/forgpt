# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from itertools import groupby
import json

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_is_zero, html_keep_url, is_html_empty

class SaleOrder2(models.Model):
    _inherit= 'sale.order'

    aplicar_descuento = fields.Boolean(string="Aplicar descuento global", default=False)
    porcentaje_descuento = fields.Float(string="% Desc. global", default=0)
    producto_descuento = fields.Many2one('product.product', string="Producto de descuento")
    productos = fields.Char(string="Producto", compute="_get_productos")
    categorias_productos = fields.Char(string="Categoría de producto", compute="_get_productos")

    @api.depends('order_line.product_id')
    def _get_productos(self):
        for rec in self:
            string = ","
            rec.productos = string.join(rec.order_line.mapped('product_id.name'))
            rec.categorias_productos = string.join(rec.order_line.mapped('product_id.categ_id.name'))

    def aplicar_descuento_lineas(self):
        for rec in self:
            if rec.porcentaje_descuento > 0:
                if not rec.producto_descuento:
                    raise ValidationError('Favor seleccionar producto de descuento')
                sale_order_line_obj = self.env['sale.order.line']
                if len(rec.order_line) == 0:
                    raise ValidationError('Para aplicar un descuento global primero debe cargar lineas de factura')
                new_line_vals = {
                    'product_id': rec.producto_descuento.id,
                    'name': rec.producto_descuento.description_sale if rec.producto_descuento.description_sale else rec.producto_descuento.name,
                    'product_uom_qty': 1,
                    'product_uom': rec.producto_descuento.uom_id.id,
                    'price_unit': -sum(
                        (line.price_total * rec.porcentaje_descuento) / 100 for line in rec.order_line),
                    'order_id': rec.id,
                }
                rec.write({'order_line': [(0, 0, new_line_vals)]})

    def _prepare_invoice(self):
        self.ensure_one()

        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(
                _('Please define an accounting sales journal for the company %s (%s).', self.company_id.name,
                  self.company_id.id))

        invoice_vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(
                self.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'invoice_date':fields.Date.today()
        }
        if self.payment_term_id:
            if sum(line.days for line in self.payment_term_id.line_ids) > 0:
                tipo_factura = "2"
            else:
                tipo_factura = "1"
            invoice_vals['tipo_factura']= tipo_factura
        tipo_comprobante = self.env['ruc.tipo.documento'].search([('codigo_hechauka','=',1)])
        if len(tipo_comprobante) > 0:
            invoice_vals['tipo_comprobante']=tipo_comprobante[0].id
        if self.env.user.default_documento_factura:
            invoice_vals['talonario_factura']=self.env.user.default_documento_factura.id
            if self.env.user.default_documento_factura.journal_id:
                invoice_vals['journal_id'] = self.env.user.default_documento_factura.journal_id.id
            invoice_vals['timbrado'] = self.env.user.default_documento_factura.name
            suc = self.env.user.default_documento_factura.suc
            sec = self.env.user.default_documento_factura.sec
            nro = self.env.user.default_documento_factura.nro_actual
            invoice_vals['suc'] = suc
            invoice_vals['sec'] = sec
            nro_s = str(nro)
            cant_nro = len(nro_s)
            if cant_nro == 1:
                nro_final = '000000' + nro_s
            elif cant_nro == 2:
                nro_final = '00000' + nro_s
            elif cant_nro == 3:
                nro_final = '0000' + nro_s
            elif cant_nro == 4:
                nro_final = '000' + nro_s
            elif cant_nro == 5:
                nro_final = '00' + nro_s
            elif cant_nro == 6:
                nro_final = '0' + nro_s
            else:
                nro_final = nro_s
            invoice_vals['nro'] = nro_final
            invoice_vals['nro_factura'] = str(suc) + '-' + str(sec) + '-' + str(nro_final)
            invoice_vals['vencimiento_timbrado'] = self.env.user.default_documento_factura.fecha_final
        if self.aplicar_descuento and self.producto_descuento and self.porcentaje_descuento:
            invoice_vals['aplicar_descuento']=True
            invoice_vals['producto_descuento'] = self.producto_descuento.id
            invoice_vals['porcentaje_descuento'] = self.porcentaje_descuento

        return invoice_vals

    # @api.multi
    def _action_confirm(self):
        """
        En base al pedido de venta se setea la unidad de medida la demanda inicial, cantidad reservada, y cantidad hecha
        campos espejos de los campos originales del odoo
        :return:
        """
        res = super(SaleOrder2, self)._action_confirm()
        for p in self.picking_ids:
            for pickin in p:
                if not pickin.partner_id:
                    pickin.partner_id=self.partner_shipping_id
        return res
