
# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api,_
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError, UserError

class resCurrency(models.Model):
    _inherit= 'res.currency'

    name = fields.Char(string='Currency', size=15, required=True, help="Currency Code (ISO 4217)")
    ambito = fields.Selection([('venta','Venta'),('compra','Compra')],string="Ámbito", default=False, required=True)
    rate = fields.Float(compute='_compute_current_rate', string='Current Rate', digits=(12, 12),
                        help='The rate of the currency to the currency of rate 1.')
    moneda_compania = fields.Boolean(compute='_get_currency_company')


    def _get_currency_company(self):
        for moneda in self:
            if moneda.id == self.env.company.currency_id.id:
                moneda.moneda_compania = True
            else:
                moneda.moneda_compania = False




class cotizaciones(models.Model):
    _inherit = "res.currency.rate"

    cotizacion  = fields.Float(String='Cotizacion comercial')
#     set_compra = fields.Float(String='Cotizacion SET Compra')
    rate = fields.Float(digits=(12, 12), help='The rate of the currency to the currency of rate 1')
    set_venta = fields.Float(String='Cotizacion')
    name = fields.Date(string='Date', required=True, index=True,
                           default=lambda self: fields.Date.today())
    @api.onchange('set_venta')
    def _cambiar_rate(self):
        if self.set_venta:
            self.rate= 1 / self.set_venta

class Voucher(models.Model):

    _inherit= 'account.voucher'

    #account_id = fields.Many2one('account.account', 'Account',
     #                            required=True, readonly=True, states={'draft': [('readonly', False)]},
     #                            domain="[('deprecated', '=', False),('internal_type','in',('liquidity','payable','receivable'))]")
    account_id = fields.Many2one('account.account', 'Account',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 domain="[('deprecated', '=', False)]")
    def agregar_punto_de_miles(self,numero):
        entero=int(numero)
        decimal='{0:.3f}'.format(numero-entero)
        entero_string='.'.join([str(int(entero))[::-1][i:i+3] for i in range(0,len(str(int(entero))),3)])[::-1]
        if decimal == '0.000':
            numero_con_punto=entero_string
        else:
            decimal_string=str(decimal).split('.')
            numero_con_punto=entero_string+','+decimal_string[1]
        return numero_con_punto

class Voucher_line(models.Model):

    _inherit = 'account.voucher.line'


    def product_id_change(self, product_id, partner_id=False, price_unit=False, company_id=None, currency_id=None,type=None):
        # TDE note: mix of old and new onchange badly written in 9, multi but does not use record set
        context = self._context


        company_id = company_id if company_id is not None else context.get('company_id', False)
        company = self.env['res.company'].browse(company_id)
        currency = self.env['res.currency'].browse(currency_id)
        if not partner_id:
            raise UserError(_("You must first select a partner."))
        part = self.env['res.partner'].browse(partner_id)
        if part.lang:
            self = self.with_context(lang=part.lang)

        product = self.env['product.product'].browse(product_id)
        fpos = part.property_account_position_id
        account = self._get_account(product, fpos, type)
        values = {
            'name': product.partner_ref,
            'account_id': account.id,
        }

        if type == 'purchase':
            values['price_unit'] = price_unit or product.standard_price
            taxes = product.supplier_taxes_id or account.tax_ids
            if product.description_purchase:
                values['name'] += '\n' + product.description_purchase
        else:
            values['price_unit'] = price_unit or product.lst_price
            taxes = product.taxes_id or account.tax_ids
            if product.description_sale:
                values['name'] += '\n' + product.description_sale

        values['tax_ids'] = taxes.ids

        if company and currency:
            if company.currency_id != currency:
                if type == 'purchase':
                    values['price_unit'] = price_unit or product.standard_price
                # values['price_unit'] = values['price_unit'] * currency.rate

        return {'value': values, 'domain': {}}

#     # @api.multi
#     def proforma_voucher(self):
#         if self.currency_id.id != self.env.company.currency_id.id:
#             fecha = self.date
#             coti = self.env['res.currency.rate'].search( [['name', '=', self.date], ['currency_id', '=', self.currency_id.id]])
#             # coti = fact.currency_id.compute(1, self.env.company.currency_id)
#             if not coti:
#                 raise ValidationError(
#                     'No se encuentra cotizacion para el dia %s . Verifique que la cotizacion se encuentre cargada ' % fecha)
#         self.action_move_line_create()

class cuent(models.Model):
    _inherit = "account.account"

    name = fields.Char(translate=True)
    # active= fields.Boolean(string="Activo",default=True)
class diarios(models.Model):
    _inherit = "account.journal"
    orden_pago = fields.Boolean(string='Metodo de pago en OP? ', default=False)
    caja_chica = fields.Boolean(string='Fondo Rotativo? ', default=False)
    codigo = fields.Integer(string='Codigo Interno')
    recibo_diario = fields.Boolean(string='Diario para Recibo', default=False, store=True)
#     type = fields.Selection(selection_add=[('retencion', 'Retencion'), ('tarjeta_credito', 'Tarjeta de Credito'),
#                                            ('tarjeta_debito', 'Tarjeta de Debito')], tracking=True)
    update_posted = fields.Boolean(default=True)
    exchange_rate_journal = fields.Boolean(
        string='Diferencia de cambio ',
        required=False)

