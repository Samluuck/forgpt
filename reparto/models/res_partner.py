# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError


class PartnerReparto(models.Model):
    _inherit = 'res.partner'
    
    chofer = fields.Boolean(string="Chofer")