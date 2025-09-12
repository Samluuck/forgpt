# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
import datetime


class compania(models.Model):
    _inherit = 'res.company'


    contador = fields.Char(string='Apellido/ Nombre del Contador')
    ruc_contador = fields.Char(string="RUC del Contador")
    auditor = fields.Char(string="Apellido / Nombre del Auditor")
    ruc_auditor = fields.Char(string="RUC del Auditor")








