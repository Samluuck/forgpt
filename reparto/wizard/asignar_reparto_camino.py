# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api,_
from datetime import datetime, timedelta
from lxml import etree
from odoo.exceptions import ValidationError





class asignar_reparto_wizard(models.TransientModel):

    _name = "wizard.asignar.reparto"


    _description = "Asignar choferes a facturas"
    chofer = fields.Many2one('res.partner',string="Chofer")
    fecha = fields.Datetime(string='Fecha de Salida')
    vehiculo_id = fields.Many2one("fleet.vehicle", string = "Vehiculo")

    @api.multi
    def procesar (self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        reparto_padre = self.env['delivery.order.parent']
        name= self.env['ir.sequence'].next_by_code('reparto.padre.sequence')
        datos_padre = {'name':name,
                      'chofer_id':self.chofer.id,
                       'fecha_salida':self.fecha,
                       'company_id':self.env.user.company_id.id,
                       'vehiculo_id': self.vehiculo_id.id,
                      }
        rep = reparto_padre.create(datos_padre) 
        if context['active_model'] == 'account.invoice':
            
            for f in self.env['account.invoice'].browse(active_ids):
                reparto = self.env['delivery.order']
                datos={
                    'chofer_id':self.chofer.id,
                    'partner_id': f.partner_id.id,
                    'vehiculo_id':self.vehiculo_id.id,
                    'fecha_salida':self.fecha,
                    'parent_id':rep.id,
                    'company_id':self.env.user.company_id.id,
                    'invoice_id': f.id,
                    'tipo_documento': 'invoice',
                }
                res=reparto.create(datos)
                res.set_camino()
            return {
                'name': _('reparto invoice'),
                'type': 'ir.actions.act_window',
                'res_model': 'delivery.order',
                'view_type': 'form',
                'view_mode': 'tree',
                'view_id': self.env.ref('reparto.reparto_tree_view_invoice').id,
                'res_id': False,
                'context': False,
                'target': 'current'
            }


        elif context['active_model'] == 'stock.picking':
            pickings = self.env['stock.picking'].browse(active_ids)
            if len(pickings.filtered(lambda r: r.tipo_entrega == 'local')) > 0:
                raise ValidationError('Solo se pueden realizar entrega de pedidos que son de tipo delivery.')
            reparto_padre = self.env['delivery.order.parent']
            name= self.env['ir.sequence'].next_by_code('reparto.padre.sequence')
            datos_padre = {'name':name,
                          'chofer_id':self.chofer.id,
                           'fecha_salida':self.fecha,
                           'company_id':self.env.user.company_id.id,
                           'vehiculo_id': self.vehiculo_id.id,
                          }
            rep = reparto_padre.create(datos_padre) 
            for r in self.env['stock.picking'].browse(active_ids):
                reparto = self.env['delivery.order']
                datos={
                    'chofer_id':self.chofer.id,
                    'partner_id': r.partner_id.id,
                    'vehiculo_id':self.vehiculo_id.id,
                    'fecha_salida':self.fecha,
                    'parent_id':rep.id,
                    'company_id':self.env.user.company_id.id,
                    'picking_id': r.id,
                    'tipo_documento' : 'picking',
                }
                res = reparto.create(datos)
                res.set_camino()
            return {
                'name': _('reparto picking'),
                'type': 'ir.actions.act_window',
                'res_model': 'delivery.order',
                'view_type': 'form',
                'view_mode': 'tree',
                'view_id': self.env.ref('reparto.reparto_tree_view_picking').id,
                'res_id': False,
                'context': False,
                'target': 'current'
            }
