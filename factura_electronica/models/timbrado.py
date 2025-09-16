# -*- coding: utf-8 -*-

from odoo import models, fields, api
from num2words import num2words
import logging
import random
_logger = logging.getLogger(__name__)

class TimbradoFactElect(models.Model):
    _inherit = 'ruc.documentos.timbrados'

    timbrado_electronico=fields.Selection(selection=[('1', 'Factura electrónica'),
                                           ('2', 'Factura electrónica de exportación'),
                                           ('3', 'Factura electrónica de importación'),
                                           ('4', 'Autofactura electrónica'),
                                           ('5', 'Nota de crédito electrónica'),
                                           ('6', 'Nota de débito electrónica'),
                                           ('7', 'Nota de remisión electrónica'),
                                           ('8', 'Comprobante de retención electrónico')
                                           ],string="Tipo Documento Electronico")
    actividad_economica = fields.Char(string="Actividad económica",help="Actividad económica según la SET, en caso de solo utilizar una actividad económica se puede dejar vacío y cargar el dato en la compañía")
    codigo_actividad = fields.Char(string="Código de actividad económica",help="Código de actividad económica según la SET, en caso de solo utilizar una actividad económica se puede dejar vacío y cargar el dato en la compañía")

