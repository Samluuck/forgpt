# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountAccount(models.Model):
    _inherit = 'account.account'

    f500_category_id = fields.Many2one(
        'f500.category',
        string='Categoría F500',
        ondelete='restrict',
        help='Categoría del Formulario 500 IRE a la que pertenece esta cuenta'
    )
    
    f500_cell = fields.Char(
        string='Casilla F500',
        related='f500_category_id.f500_cell',
        store=True,
        readonly=True,
        help='Número de casilla del Formulario 500 (desde la categoría)'
    )
    
    f500_category_type = fields.Selection(
        string='Tipo Categoría',
        related='f500_category_id.category_type',
        store=True,
        readonly=True
    )
    
    f500_operation = fields.Selection(
        string='Operación',
        related='f500_category_id.operation',
        store=True,
        readonly=True
    )