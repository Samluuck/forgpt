# -*- coding: utf-8 -*-

from odoo import models, fields, api



class SaleOrder(models.Model):
    _inherit = 'sale.order'


    tipo_entrega = fields.Selection([('local','Local'),('delivery','Delivery')], default='local',string="Tipo de Entrega")

    @api.multi
    def _action_confirm(self):
        super(SaleOrder, self)._action_confirm()
        for order in self:
            if order.picking_ids:
                for picking in order.picking_ids:
                    picking.tipo_entrega = order.tipo_entrega
