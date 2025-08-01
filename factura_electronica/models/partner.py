# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class PartnerFactElect(models.Model):
    _inherit = 'res.partner'
    tipo_operacion=fields.Selection(selection=[('1' ,'B2B'),
                                    ('2' ,'B2C'),
                                    ('3' ,'B2G'),
                                    ('4' ,'B2F')
                                ],default='2')
    nro_casa=fields.Integer(default=0)
    tipo_documento=fields.Selection(selection=[
                                    ('1' ,'Electrónico'),
                                    ('2' ,'Impreso'),
                                    ('3' ,'Constancia Electrónica')
    ])
    naturaleza_receptor=fields.Selection(selection=[('1','contribuyente'),
                                                    ('2','no contribuyente')],default='1')
    naturaleza_vendedor=fields.Selection(selection=[('1','No contribuyente'),
                                                    ('2','Extranjero')])

    tipo_documento_receptor=fields.Selection(selection=[('1','Cédula paraguaya'),
                                                        ('2','Pasaporte'),
                                                        ('3','Cédula extranjera'),
                                                        ('4','Carnet de residencia'),
                                                        ('5','Innominado'),
                                                        ('6','Tarjeta Diplomática de exoneración fiscal'),('9','Otro')])
    tipo_documento_vendedor=fields.Selection(selection=[('1','Cédula paraguaya'),
                                                        ('2','Pasaporte'),
                                                        ('3','Cédula extranjera'),
                                                        ('4','Carnet de residencia')])
    nro_documento=fields.Char()


    @api.onchange('ci')
    def set_document_data(self):
        for rec in self:
            if rec.ci:
                rec.nro_documento = rec.ci

    @api.onchange('digitointer')
    def set_digitointer_data(self):
        for rec in self:
            if rec.digitointer:
                rec.nro_documento = rec.digitointer
            else:
                rec.nro_documento= None

    @api.onchange('country_id')
    def set_foreign_data(self):
        for rec in self:
            if rec.country_id:
                if rec.country_id != self.env.company.country_id:
                    rec.tipo_operacion = '4'
                    rec.naturaleza_receptor = '2'
                    rec.tipo_documento_receptor = '3'
                    rec.nro_documento=rec.digitointer
                else:
                    rec.tipo_operacion = '2'
                    rec.naturaleza_receptor = '1'
                    rec.tipo_documento_receptor = None
                    rec.nro_documento = rec.rucdv or rec.ci or ''