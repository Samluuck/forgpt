# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class CompanyFactElect(models.Model):
    _inherit = 'res.company'

    regimen=fields.Selection(selection=[('1' , 'Régimen de Turismo'),
                              ('2' , 'Importador'),
                                ('3' , 'Exportador'),
                                ('4' , 'Maquila'),
                                ('5' , 'Ley N° 60/90'),
                                ('6' , 'Régimen del Pequeño Productor'),
                                ('7' , 'Régimen del Mediano Productor'),
                                ('8' , 'Régimen Contable')
                                ])
    nro_casa=fields.Char()
    actividad_economica=fields.Char()
    codigo_actividad=fields.Char()
    servidor=fields.Selection(selection=[('produccion','Produccion'),('prueba','Prueba')])
    IdCSC=fields.Char()
    csc=fields.Char(string='CSC')

    # @api.onchange('servidor')
    # def controlar_servidor(self):
    #     if self.servidor:
    #         if self.servidor == 'produccion':
    #             raise ValidationError('La utilizacion del servidor de produccion  no esta aun habilitado')
