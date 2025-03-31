# -*- coding: utf-8 -*-
##############################################################################
#
#    ODOO, Open Source Management Solution
#    Copyright (C) 2016 Steigend IT Solutions
#    For more details, check COPYRIGHT and LICENSE files
#
##############################################################################
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp


class AccountAccount(models.Model):
    _inherit = "account.account"

    diferencia_de_pago = fields.Boolean(
        string='Diferencia depago',
        required=False)