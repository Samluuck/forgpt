# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError

import time


# class new_model(models.Model):
#     _name = 'payments.rg'
#     _order = 'date'
#
#     book_id = fields.Many2one('account.book')
#     payment_id = fields.Many2one('account.payment',string='Pagos')
#     voucher_id = fields.Many2one('account.voucher',string='Pagos')
#     date = fields.Date(string='Fecha',compute='obtener_tipo_hecha')
#     no_listar= fields.Boolean(string='No Listar')
#     amount_total = fields.Float(compute='obtener_tipo_hecha',string='Total')
#     tipo_rg90 = fields.Integer(string='Tipo Documento', compute='obtener_tipo_hecha')
#     imputa_ire = fields.Boolean(string="Imputa al IRE", compute='obtener_tipo_hecha')
#     imputa_irp_rsp = fields.Boolean(string="Imputa al IRP-RSP", default=False, compute='obtener_tipo_hecha')
#
#
#
#
#     @api.depends('voucher_id','payment_id')
#     def obtener_tipo_hecha(self):
#         for rec in self:
#             if rec.payment_id:
#                 rec.tipo_rg90 = rec.payment_id.tipo_comprobante.codigo_rg90
#                 rec.date= rec.payment_id.payment_date
#                 rec.imputa_ire = rec.payment_id.imputa_ire
#                 rec.imputa_irp_rsp = rec.payment_id.imputa_irp_rsp
#                 rec.amount_total=rec.payment_id.amount
#             elif rec.voucher_id:
#                 rec.tipo_rg90 = rec.voucher_id.tipo_comprobante.codigo_rg90
#                 rec.imputa_ire = rec.voucher_id.imputa_ire
#                 rec.imputa_irp_rsp = rec.voucher_id.imputa_irp_rsp
#                 rec.date = rec.voucher_id.date
#                 rec.amount_total = rec.voucher_id.amount




class payment_books(models.Model):
    _inherit = "account.payment"


    tipo_comprobante = fields.Many2one('ruc.tipo.documento', string='Tipo comprobante')
                                       #default=lambda self: self._get_default_tipo_comprobante())
    tipo_rg90 = fields.Integer(string='Tipo Documento', compute='obtener_tipo_hecha')
    imputa_ire = fields.Boolean(string="Imputa al IRE", default=True)
    imputa_irp_rsp = fields.Boolean(string="Imputa al IRP-RSP", default=False)

    @api.depends('tipo_comprobante')
    def obtener_tipo_hecha(self):
        for rec in self:
            if rec.tipo_comprobante:
                rec.tipo_rg90 = rec.tipo_comprobante.codigo_rg90


class voucher_books(models.Model):
    _inherit = "account.voucher"


    tipo_comprobante = fields.Many2one('ruc.tipo.documento', string='Tipo comprobante')
                                       #default=lambda self: self._get_default_tipo_comprobante())
    tipo_rg90 = fields.Integer(string='Tipo Documento', compute='obtener_tipo_hecha')
    imputa_ire = fields.Boolean(string="Imputa al IRE", default=True)
    imputa_irp_rsp = fields.Boolean(string="Imputa al IRP-RSP", default=False)

    @api.depends('tipo_comprobante')
    def obtener_tipo_hecha(self):
        for rec in self:
            if rec.tipo_comprobante:
                rec.tipo_rg90 = rec.tipo_comprobante.codigo_rg90
