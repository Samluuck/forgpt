# -*- coding: utf-8 -*-

from odoo import models, fields, api



class StockPicking_reparot(models.Model):
    _inherit = 'stock.picking'


    reparto_id=fields.Many2one('delivery.order')
    tipo_entrega = fields.Selection([('local','Local'),('delivery','Delivery')], default='local',string="Tipo de Entrega")
    city = fields.Many2one(related='partner_id.state_id',string='Ciudad',store=True)
    barrio = fields.Char(related='partner_id.city',string="Barrio",store=True)