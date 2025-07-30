# -*- coding: utf-8 -*-

import time
from odoo import api, models , fields
from odoo.exceptions import ValidationError

class ruc_tipo_documento(models.Model):
    _name = 'ruc.tipo.identificacion'
    _order = 'codigo_rg90 asc'

    comentario = fields.Text('Comentarios adicionales')
    name = fields.Char(string="Tipo de Identificacion",required=True)
    codigo_rg90= fields.Integer (string="Codigo en el RG90")
    active = fields.Boolean(default=True)

class Partner(models.Model):
    _inherit = 'res.partner'

    tipo_identificacion=fields.Many2one('ruc.tipo.identificacion',string="Tipo de Identificacion", default=lambda self: self._get_default_tipo_identificacion())

    @api.model
    def _get_default_tipo_identificacion(self):
        tipo_identificacion = None
        try:
            tipo_identificacion = self.env.ref('rg90.tipo_identificacion_1')
            return tipo_identificacion
        except:
            pass

    @api.onchange('supplier','country_id')
    def update_tipo_identificacion(self):
        for rec in self:
            if rec.country_id:
                if rec.country_id.phone_code and rec.country_id.phone_code != 595 and rec.supplier == True:
                    print(f"country->{rec.country_id.name} // supplier: {rec.supplier}")
                    if rec.tipo_identificacion and rec.tipo_identificacion.codigo_rg90 and rec.tipo_identificacion.codigo_rg90 != 17:
                        raise ValidationError("Al crear la ficha para proveedores del exterior debe tener colocado tipo de identificación: Identificación tributaria")

    # @api.oncchange('situation')
    # def update_value_tipo_identificacion(self):
    #     for rec in self:
    #         if rec.situacion == 'NO_RESIDENTE':
    #             rec.tipo_identificacion = ''


    

