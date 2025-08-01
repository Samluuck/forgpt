# -*- coding: utf-8 -*-

from odoo import models, fields, api
from num2words import num2words
import logging
import random
from odoo.exceptions import ValidationError
import pytz
from datetime import datetime
import collections
_logger = logging.getLogger(__name__)

class ProductUomFactElect(models.Model):
    _inherit = 'uom.uom'

    codigo=fields.Integer()
    sifen_name=fields.Char(string='Nombre en la SIFEN')
