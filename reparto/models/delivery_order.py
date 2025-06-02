# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import datetime


class delivery_order_parent(models.Model):
    
    _name='delivery.order.parent'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    
    name = fields.Char(string='Numero de reparto',track_visibility='onchange' )
    delivered_documents= fields.One2many('delivery.order','parent_id', string="Documentos Entregados")
    chofer_id=fields.Many2one('res.partner',string="Chofer")
    vehiculo_id = fields.Many2one('fleet.vehicle', string="Vehiculo")
    fecha_salida=fields.Datetime(string="Fecha de Salida")
    company_id = fields.Many2one('res.company', string='Compañia', required=True,default=lambda self: self._get_default_company())

    @api.multi
    def set_cancelado(self):
        for rec in self:
            for d in rec.delivered_documents:
                if d.state == 'en_camino':
                    d.state = 'cancelado'

    
    @api.model
    def _get_default_company(self):
        return self.env.user.company_id.id
    
class DeliveryOrder(models.Model):
    _name = 'delivery.order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Numero de reparto',track_visibility='onchange')
    partner_id = fields.Many2one('res.partner','Cliente',track_visibility='onchange')
    parent_id = fields.Many2one('delivery.order.parent', track_visibility='onchange')
    invoice_id = fields.Many2one('account.invoice',inverse_name='reparto_id',string='Numero de Factura')
    picking_id = fields.Many2one('stock.picking',inverse_name='reparto_id',string='Numero de Remision')
    chofer_id=fields.Many2one('res.partner',string="Chofer")
    vehiculo_id = fields.Many2one('fleet.vehicle', string="Vehiculo")
    state = fields.Selection([('borrador','Borrador'),('en_camino', 'En camino'), ('entregado', 'entregado'),('cancelado','Cancelado')],default='borrador', track_visibility='onchange')
    fecha_salida=fields.Datetime(string="Fecha de Salida")
    fecha_entrega=fields.Datetime(string="Fecha de Entrega")
    tiene_factura=fields.Integer(compute='_cantidad_factura')
    tiene_picking=fields.Integer(compute='_cantidad_picking')
    tipo_documento = fields.Selection([('picking','Remisión'),('invoice','Factura')],string="Tipo de Documento")
    company_id = fields.Many2one('res.company', string='Compañia', required=True,default=lambda self: self._get_default_company())
    state_invoice = fields.Selection(related='invoice_id.state',string="Estado Factura")
    invoice_amount = fields.Monetary(related='invoice_id.amount_total',currency_field='currency_id',string="Total Factura")
    invoice_residual = fields.Monetary(related='invoice_id.residual',currency_field='currency_id',string="Saldo")
    currency_id = fields.Many2one(related='invoice_id.currency_id',string="Moneda")

    #line_ids : fields.One2many('delivery.order.line','Detalle del Reparto')

    # @api.multi
    # def action_view_picking(self):
    #
    #     action = self.env.ref('stock.action_picking_tree_all').read()[0]
    #
    #     pickings = self.mapped('picking_ids')
    #     if len(pickings) > 1:
    #         action['domain'] = [('id', 'in', pickings.ids)]
    #     elif pickings:
    #         action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
    #         action['res_id'] = pickings.id
    #     return action
    #
    # @api.multi
    # def action_view_invoice(self):
    #     invoices = self.mapped('invoice_ids')
    #     action = self.env.ref('account.action_invoice_tree1').read()[0]
    #     if len(invoices) > 1:
    #         action['domain'] = [('id', 'in', invoices.ids)]
    #     elif len(invoices) == 1:
    #         action['views'] = [(self.env.ref('account.invoice_form').id, 'form')]
    #         action['res_id'] = invoices.ids[0]
    #     else:
    #         action = {'type': 'ir.actions.act_window_close'}
    #     return action

    @api.multi
    def set_cancelado(self):
        for rec in self:
            if rec.state == 'en_camino':
                rec.state = 'cancelado'


    @api.multi
    def set_borrador(self):
        for rec in self:
            rec.state = 'borrador'

    @api.multi
    def set_entregado(self):
        for rec in self:
            rec.state = 'entregado'
            rec.fecha_entrega = fields.datetime.now()

    @api.multi
    def set_camino(self):
        for rec in self:
            rec.name = self.env['ir.sequence'].next_by_code('reparto.sequence')
            rec.state = 'en_camino'

    @api.model
    def _get_default_company(self):
        return self.env.user.company_id.id


    def _cantidad_factura(self):
        for rec in self:
            if rec.invoice_id:
                rec.tiene_factura = True
            else:
                return 0

    def _cantidad_picking(self):
        for rec in self:
            if rec.picking_id:
                rec.tiene_picking = True
            else:
                return 0
