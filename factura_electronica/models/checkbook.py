# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class PaymentFactElect(models.Model):
    _inherit = 'account.checkbook'

    bank_id=fields.Many2one('res.bank')