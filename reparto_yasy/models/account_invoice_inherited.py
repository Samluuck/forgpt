from odoo import models, fields, api

class InvoiceRepartoCustom(models.Model):
    _inherit = 'account.invoice'

    parent_id = fields.Many2one('delivery.order.parent', string='Orden de Entrega')