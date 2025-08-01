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
    _inherit = 'account.tax'

    forma_afectacion=fields.Selection( [('1', 'Gravado IVA'),
                                        ('2', 'Exonerado -Art. 83- Ley125/91'),
                                        ('3', 'Exento'),
                                        ('4',' Gravado parcial (Grav-Exento)'),
                    ])
