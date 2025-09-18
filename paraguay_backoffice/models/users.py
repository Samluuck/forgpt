
# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError



class rusers(models.Model):
    _inherit = 'res.users'

    documento_factura = fields.Many2many('ruc.documentos.timbrados', 'usuarios_timbrados_rel','timbrado_id','user_id', string='Timbrado Facturas', domain=[('activo', '=', True)])
    default_documento_factura = fields.Many2one('ruc.documentos.timbrados',string="Talonario por defecto")
    emite_remisiones = fields.Boolean(string="Emite Remisiones?")
    documento_remision= fields.Many2one('ruc.documentos.timbrados', string='Timbrado Remision', domain=[('activo', '=', True), ('tipo_documento', '=', 2)])
    emite_retenciones = fields.Boolean(string="Emite Retenciones?")
    documento_retencion = fields.Many2one('ruc.documentos.timbrados', string='Timbrado Retencion',domain=[('activo', '=', True), ('tipo_documento', '=', 3)])

    @api.constrains('default_documento_factura','documento_factura')
    def _verificar_timbrados(self):
        for rec in self:
            if rec.default_documento_factura:
                if not rec.default_documento_factura.id in rec.documento_factura.ids:
                    raise ValidationError('El talonario seleccionado debe figurar en los talonarios habilitados del usuario')