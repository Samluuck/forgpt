# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

class accountTipoIva(models.Model):
    _name = "account.tipo.iva"

    name = fields.Char(string="Descripción")
    active = fields.Boolean(string="Activo", default=True)