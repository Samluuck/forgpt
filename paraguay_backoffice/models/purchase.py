# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # @api.multi

    def action_view_invoice(self, invoices=False):
        """This function returns an action that display existing vendor bills of
        given purchase order ids. When only one found, show the vendor bill
        immediately.
        """
        if not invoices:
            # Invoice_ids may be filtered depending on the user. To ensure we get all
            # invoices related to the purchase order, we read them in sudo to fill the
            # cache.
            self.sudo()._read(['invoice_ids'])
            invoices = self.invoice_ids

        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        tipo_comprobante = self.env['ruc.tipo.documento'].search([('codigo_hechauka', '=', 1)])
        if len(tipo_comprobante) > 0:
            tipo = tipo_comprobante[0].id
        else:
            tipo = False
        # choose the view_mode accordingly
        result['context'] = {
            'type': 'in_invoice',
            'default_purchase_id': self.id,
            'default_currency_id': self.currency_id.id,
            'default_company_id': self.company_id.id,
            'company_id': self.company_id.id,
            'default_tipo_comprobante': tipo
        }
        if self.partner_id.timbrado:
            result['context']['default_timbrado'] = self.partner_id.timbrado
        if len(invoices) > 1:
            result['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = invoices.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result

    # def action_view_invoice(self,invoices=False):
    #
    #     '''
    #          This function returns an action that display existing vendor bills of given purchase order ids.
    #          When only one found, show the vendor bill immediately.
    #          '''
    #     action = self.env.ref('account.action_vendor_bill_template')
    #     result = action.read()[0]
    #     create_bill = self.env.context.get('create_bill', False)
    #     # override the context to get rid of the default filtering
    #     tipo_comprobante = self.env['ruc.tipo.documento'].search([('codigo_hechauka','=',1)])
    #     if len(tipo_comprobante) > 0:
    #         tipo = tipo_comprobante[0].id
    #     else:
    #         tipo = False
    #     result['context'] = {
    #         'type': 'in_invoice',
    #         'default_purchase_id': self.id,
    #         'default_currency_id': self.currency_id.id,
    #         'default_company_id': self.company_id.id,
    #         'company_id': self.company_id.id,
    #         'default_tipo_comprobante' : tipo
    #     }
    #     # choose the view_mode accordingly
    #     if len(self.invoice_ids) > 1 and not create_bill:
    #         result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
    #     else:
    #         res = self.env.ref('account.invoice_supplier_form', False)
    #         form_view = [(res and res.id or False, 'form')]
    #         if 'views' in result:
    #             result['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
    #         else:
    #             result['views'] = form_view
    #         # Do not set an invoice_id if we want to create a new bill.
    #         if not create_bill:
    #             result['res_id'] = self.invoice_ids.id or False
    #     result['context']['default_origin'] = self.name
    #     result['context']['default_reference'] = self.partner_ref
    #     if self.partner_id.timbrado:
    #         result['context']['default_timbrado'] = self.partner_id.timbrado
    #     return result

    # @api.multi
    def button_confirm(self):

        fechas = datetime.strptime(str(self.date_order), '%Y-%m-%d %H:%M:%S')


        # fecha_actual = fields.Date.context_today(self,fechas.date() )
        fecha_actual = fields.Date.context_today(self,fechas)
        fecha_1 = datetime.strptime(str(fecha_actual), '%Y-%m-%d')

        fecha = datetime.strftime(fecha_1, "%Y/%m/%d")
        # raise ValidationError('aaaa %s' % fecha_actual)

        # if self.currency_id.id != self.env.company.currency_id.id:
        #     coti = self.env['res.currency.rate'].search( [['name', '=', fecha], ['currency_id', '=', self.currency_id.id]])
        #     if not coti:
        #         raise ValidationError(
        #         'No se encuentra cotizacion para el dia %s . Verifique que la cotizacion se encuentre cargada ' % fecha)
        res = super(PurchaseOrder,self).button_confirm()
        
        for p in self.picking_ids:
            for pickin in p:
                pickin.partner_id=self.partner_id
        return res
