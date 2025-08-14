# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.tools.misc import formatLang, format_date
from odoo.tools.translate import _
from odoo.tools import append_content_to_html, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class account_invoice_report(models.Model):
    _inherit = 'account.invoice.report'

    nro_factura = fields.Char(string='Nro. Factura' , readonly=True)
    price_unit = fields.Float(string='Precio Unitario', readonly=True)
    amount_totals = fields.Float(string='Total Factura', readonly=True)
    invoice_curr=fields.Many2one('res.currency',string="Moneda de la Factura", readonly=True)
    amount_untaxeds = fields.Float(string='Total libre de impuestos moneda factura', readonly=True)
    partner_category_id = fields.Many2one('res.partner.category', string='Partner Category', readonly=True)
    costo = fields.Float(string="Costo")
    costo_total = fields.Float(string="Costo Total")
    utilidad_total_gs = fields.Float(string="Utilidad Total")
    utilidad_unitaria_gs = fields.Float(string="Utilidad Unitaria")
    price_total_inv = fields.Float(string="Total en GS")
    porcentaje_ganancia = fields.Float(string="Porcentaje ganancia")
    tipo_factura = fields.Selection([
        ('contado', 'Contado'),
        ('credito', 'Crédito')
    ], string="Tipo de factura", tracking=True)
    amount_total_company_currency = fields.Float(string='Total con impuestos en Moneda Local', readonly=True)
    exchange_rate = fields.Float(string='Tasa de Cambio', readonly=True,group_operator="avg")

    def _select(self):
        select_str = super(account_invoice_report, self)._select()
        additional_fields = """
        , CASE WHEN move.move_type = 'out_refund' or move.move_type = 'in_refund' THEN -(line.price_total) ELSE line.price_total END as amount_totals
        , line.price_subtotal as amount_untaxeds
        , move.nro_factura as nro_factura
        , line.currency_id as invoice_curr
        , line.price_unit as price_unit
        , line.costo as costo
        , 0 as porcentaje_ganancia
        , line.costo_total as costo_total 
        , line.utilidad_total_gs as utilidad_total_gs
        , line.utilidad_unitaria_gs as utilidad_unitaria_gs
    
        , CASE WHEN move.tipo_factura = '1' THEN 'Contado' ELSE 'Crédito' END as tipo_factura
        ,line.price_total* currency_table.rate                         AS price_total_inv
        , partner_category_rel.category_id as partner_category_id
        , COALESCE(res_currency_rate.set_venta, 1) AS exchange_rate
        , CASE 
            WHEN COALESCE(res_currency_rate.set_venta, 1) = 1 THEN 
                (CASE WHEN move.move_type = 'out_refund' or move.move_type = 'in_refund' THEN -(line.price_total) ELSE line.price_total END) 
            ELSE 
                (CASE WHEN move.move_type = 'out_refund' or move.move_type = 'in_refund' THEN -(line.price_total) ELSE line.price_total END) * COALESCE(res_currency_rate.set_venta, 1) 
          END as amount_total_company_currency
        """
        return select_str + additional_fields

    def _sub_select(self):
        return super(account_invoice_report,
                     self)._sub_select() + ", ai.nro_factura as nro_factura, ail.currency_id as invoice_curr, ail.costo_total as costo_total, ail.utilidad_total_gs as utilidad_total_gs,ail.utilidad_unitaria_gs as utilidad_unitaria_gs, ail.price_total as amount_totals, ail.price_subtotal as amount_untaxeds, ail.price_unit as price_unit,  CASE WHEN ai.tipo_factura = 'contado' THEN 'Contado' ELSE 'Crédito' END as tipo_factura, ail.costo as costo, 0 as porcentaje_ganancia, partner_category_rel.category_id as partner_category_id"

    def _group_by(self):
        return super(account_invoice_report,
                     self)._group_by() + ", ai.tipo_factura, ai.nro_factura, ail.currency_id, ail.price_unit, ail.price_total, ail.price_subtotal,   partner_category_rel.category_id"

    def _from(self):
        # Obtener la consulta original
        from_str = super()._from()

        # Agregar el JOIN para la relación de categorías de socios
        from_str += """
        LEFT JOIN (
            SELECT DISTINCT ON (partner_id) partner_id, category_id
            FROM res_partner_res_partner_category_rel
            ORDER BY partner_id, category_id
        ) AS partner_category_rel ON partner_category_rel.partner_id = partner.id
        """

        # Agregar el JOIN para las tasas de cambio
        from_str += """
        LEFT JOIN res_currency_rate ON res_currency_rate.currency_id = line.currency_id AND res_currency_rate.company_id = line.company_id AND res_currency_rate.name = move.invoice_date
        """

        return from_str






















