# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError

import time

class company_res(models.Model):
    _inherit = 'res.company'
    imputa_iva = fields.Boolean(string="Imputa al IVA", default=True)
    imputa_ire = fields.Boolean(string="Imputa al IRE", default=True)
    imputa_irp_rsp = fields.Boolean(string="Imputa al IRP-RSP", default=False)
    presenta_rg90_ingreso_egreso = fields.Boolean(string="Presenta RG90 Ingreso/Egreso", default=False)

class invoices_cl(models.Model):
    _inherit= 'account.move'

    # tipo_rg90 = fields.Integer(string='Tipo Documento',compute='obtener_tipo_rg90')
    tipo_rg90 = fields.Integer(string='Tipo Documento')
    imputa_iva=fields.Boolean(string="Imputa al IVA",default=lambda self: self._get_default_imputa_iva())
    imputa_ire=fields.Boolean(string="Imputa al IRE",default=lambda self: self._get_default_imputa_ire())
    imputa_irp_rsp=fields.Boolean(string="Imputa al IRP-RSP",default=lambda self: self._get_default_imputa_irp_rsp())
    virtual= fields.Boolean(string='Virtual/No aparecer en RG90',default=False)
    no_imputa= fields.Boolean(string='No imputa',default=False)

    @api.model
    def _get_default_imputa_iva(self):

        if self.env.user.company_id.imputa_iva:

            return True

    @api.model
    def _get_default_imputa_ire(self):

        if self.env.user.company_id.imputa_ire:
            return True
    @api.model
    def _get_default_imputa_irp_rsp(self):

        if self.env.user.company_id.imputa_irp_rsp:
            return True

    @api.constrains('imputa_ire','imputa_irp_rsp','no_imputa')
    def check_imputa(self):
        for rec in self:
            if rec.imputa_irp_rsp and rec.imputa_ire:
                raise ValidationError ('Una factura no puede imputar al IRE y IRP al mismo tiempo')
            # if rec.no_imputa and (not rec.imputa_iva and not rec.imputa_ire and not rec.imputa_irp_rsp):
            #     raise ValidationError('Si el campo no imputa se encuentra marcado debe marcar una Obligacion')


    # @api.model
    # def _get_default_tipo_comprobante(self):
    #     tipo=self.env.ref('sportgroup-rg90.tipo_comprobante_1')
    #     return tipo

    @api.onchange('tipo_comprobante')
    def obtener_tipo_rg90(self):
        for rec in self:
            if rec.tipo_comprobante:
                rec.tipo_rg90=rec.tipo_comprobante.codigo_rg90
