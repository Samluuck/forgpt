# -*- coding: utf-8 -*-

from odoo import models, fields, api



class Invoice_reparto(models.Model):
    _inherit = 'account.invoice'


    reparto_id=fields.Many2one('delivery.order')

