# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import datetime
from collections import defaultdict

class DeliveryOrderParentCustom(models.Model):
    
    _inherit='delivery.order.parent'

    # campo calculado para almacenar el valor de acumulado_unidad como string para poder usar en el reporte
    acumulado_unidad_str = fields.Char(string='Cantidad Unidad (String)', compute='_compute_acumulado_unidad_str', store=True)


    @api.multi
    def get_invoice_details(self):
        self.ensure_one()  # Asegura que solo se esté procesando un registro a la vez
        invoice_details = self.delivered_documents.mapped('invoice_details')
        
        # Creamos un conjunto para almacenar los nombres únicos de cliente
        unique_partner_names = set()
        
        acumulado_por_producto = defaultdict(lambda: {'acumulado_fardo': 0, 'acumulado_unidad': [], 'secuencia': float('inf')})
        
        invoice_nros_por_cliente = defaultdict(list)
        
        for detail in invoice_details:
            unique_partner_names.add(detail.partner_name)
            acumulado_por_producto[detail.product_name]['acumulado_fardo'] += detail.acumulado_fardo
            # Verificar si el valor de acumulado_unidad es mayor que 0 antes de agregarlo
            if detail.acumulado_unidad > 0.0:
                acumulado_por_producto[detail.product_name]['acumulado_unidad'].append(str(detail.acumulado_unidad))
            acumulado_por_producto[detail.product_name]['secuencia'] = min(acumulado_por_producto[detail.product_name]['secuencia'], detail.secuencia_producto)
            
            # Verificar si el número de factura ya ha sido agregado para este cliente
            if detail.invoice_nro not in invoice_nros_por_cliente[detail.partner_name]:
                invoice_nros_por_cliente[detail.partner_name].append(detail.invoice_nro)  # Agregar el número de factura al cliente
        
        partner_names_array = list(unique_partner_names)

        # Generamos los detalles de factura con los valores acumulados como objetos
        invoice_details_accumulated = []
        for product_name, acumulados in sorted(acumulado_por_producto.items(), key=lambda x: x[1]['secuencia']):
            acumulado_unidad_str = ' // '.join(acumulados['acumulado_unidad'])
            detail_obj = self.env['delivery.order.invoice.detail'].new({
                'product_name': product_name,
                'acumulado_fardo': acumulados['acumulado_fardo'],
                'acumulado_unidad_str': acumulado_unidad_str,
            })
            invoice_details_accumulated.append(detail_obj)
        
        return partner_names_array, invoice_details_accumulated, invoice_nros_por_cliente
    



class DeliveryOrderCustom(models.Model):
    _inherit = 'delivery.order'
    
    # checks para seleccionar tipo de pago para el reporte de deposito de facturas
    medio_pago_efectivo = fields.Boolean(string="Efectivo")
    medio_pago_cheque = fields.Boolean(string="Cheque")
    medio_pago_transferencia = fields.Boolean(string="Transferencia")
    
    # campo para cargar a quien se entregara el producto
    entregado_a = fields.Char(string="Entregado a", required=True)

    # Campo relacionado para obtener los detalles de la factura
    invoice_details = fields.One2many(
        comodel_name='delivery.order.invoice.detail',
        inverse_name='delivery_order_id',
        string='Detalle de Factura',
        compute='_compute_invoice_details', 
        store=True
    )
        
    @api.depends('invoice_id')
    def _compute_invoice_details(self):
        for record in self:
            if record.invoice_id:
                invoice_details = []
                for invoice in record.invoice_id:
                    for line in invoice.invoice_line_ids:
                        product_name = line.product_id.name
                        quantity = line.quantity
                        presentation_per_bundle = line.product_id.presentacion_por_fardo  # Obtener el valor del campo "presentacion_por_fardo" del producto
                        unity_per_bundle = line.product_id.cantidad_unidades_por_fardo
                        secuencia_producto = line.product_id.producto_secuencia #orden para el reporte 
                        invoice_nro = record.invoice_id.nro_factura
                        partner_name = invoice.partner_id.name + " - " + (invoice.partner_shipping_id.name if invoice.partner_shipping_id else "")
                        invoice_details.append({
                            'product_name': product_name,
                            'quantity': quantity,
                            'presentation_per_bundle': presentation_per_bundle,  # Agregar el valor de "presentacion_por_fardo"
                            'unity_per_bundle': unity_per_bundle,
                            'partner_name': partner_name,
                            'secuencia_producto': secuencia_producto,
                            'invoice_nro': invoice_nro,
                           
                        })
                record.invoice_details = invoice_details
                # Imprimir los valores de invoice_details correctamente
          
                for detail in record.invoice_details:
                    product_name = detail.product_name
                    quantity = detail.quantity
                    secuencia_producto = detail.secuencia_producto
                    presentation_per_bundle = detail.presentation_per_bundle
                    partner_name = detail.partner_name  # Obtener el nombre del cliente desde los detalles de la factura
                    unity_per_bundle = detail.unity_per_bundle

            else:
                record.invoice_details = [(5, 0, 0)]



class DeliveryOrderInvoiceDetail(models.Model):
    _name = 'delivery.order.invoice.detail'

    delivery_order_id = fields.Many2one(
        'delivery.order',
        string='Orden de Entrega',
        ondelete='cascade'
    )
    product_name = fields.Char(string='Producto')
    partner_name = fields.Char(string='Cliente')
    quantity = fields.Float(string='Cantidad')
    secuencia_producto = fields.Integer(string='Secuencia')
    invoice_nro = fields.Char(string='Número de Factura')
    presentation_per_bundle = fields.Boolean(string='Presentación por Fardo')
    unity_per_bundle = fields.Float(string='Cant. Unidad p/ Fardo')
    acumulado_fardo = fields.Float(string='Cant. Fardo', compute='compute_bundle_fields', store=True)
    acumulado_unidad = fields.Float(string='Cant. Unidad', compute='compute_bundle_fields', store=True)
    acumulado_unidad_str = fields.Char(string='Cant. Unidad (String)') #Este almacena el acumulado para el informe

    #computado para los calculos de acumulado unidad y acumulado fardo
    @api.depends('quantity', 'unity_per_bundle', 'presentation_per_bundle')
    def compute_bundle_fields(self):
        for record in self:
            if record.presentation_per_bundle and record.unity_per_bundle != 0:
                if record.quantity < record.unity_per_bundle:
                    record.acumulado_unidad = record.quantity
                    record.acumulado_fardo = 0
                else:
                    record.acumulado_fardo = record.quantity // record.unity_per_bundle
                    record.acumulado_unidad = record.quantity % record.unity_per_bundle
            elif record.unity_per_bundle != 0:
                record.acumulado_fardo = record.quantity // record.unity_per_bundle
                record.acumulado_unidad = record.quantity % record.unity_per_bundle
            else:
                record.acumulado_fardo = 0
                record.acumulado_unidad = record.quantity

