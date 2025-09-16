# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class CountryFactElect(models.Model):
    _inherit = 'res.country'

    codigo_set=fields.Char('Codigo Pais SET')