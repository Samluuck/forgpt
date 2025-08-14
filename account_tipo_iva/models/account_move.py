# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

class accountMove(models.Model):
    _inherit = "account.move"

    tipo_iva_id = fields.Many2one('account.tipo.iva', string='Tipo de IVA')
