# -*- coding: utf-8 -*-
# from odoo import models, api


# class ReportDepositoFacturas(models.AbstractModel):
#     _name = 'report.reparto_yasy.deposito_facturas_report_template'
#     _description = 'Reporte Depósito de Facturas'

#     @api.model
#     def _get_report_values(self, docids, data=None):
#         repartos = self.env['delivery.order'].search([
#             ('chofer_id', '=', data['chofer_id']),
#             ('fecha_salida', '>=', data['fecha_inicio']),
#             ('fecha_salida', '<=', data['fecha_fin']),
#             ('tipo_documento', '=', 'invoice'),
#         ])

#         chofer = self.env['res.partner'].browse(data['chofer_id'])

#         return {
#             'doc_ids': [],
#             'doc_model': 'delivery.order',
#             'docs': [{
#                 'repartos': repartos,
#                 'chofer_id': chofer,
#                 'entregado_a': data.get('entregado_a'),
#                 'puntodemiles': self.puntodemiles,  # 👈 habilitamos en QWeb
#             }],
#         }

#     def puntodemiles(self, a):
#         try:
#             b = str("{:,.0f}".format(a))
#             return b.replace(",", ".")
#         except:
#             return a
from odoo import models, api
from datetime import datetime, time

class ReportDepositoFacturas(models.AbstractModel):
    _name = 'report.reparto_yasy.deposito_facturas_report_template'
    _description = 'Reporte Depósito de Facturas'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Si se llama desde el botón de imprimir de delivery.order
        if docids:
            current_order = self.env['delivery.order'].browse(docids[0])
            if current_order:
                # Calcular rango de fechas (todo el día)
                fecha_salida = current_order.fecha_salida
                fecha_inicio = datetime.combine(fecha_salida, time.min)
                fecha_fin = datetime.combine(fecha_salida, time.max)
                
                repartos = self.env['delivery.order'].search([
                    ('chofer_id', '=', current_order.chofer_id.id),
                    ('fecha_salida', '>=', fecha_inicio),
                    ('fecha_salida', '<=', fecha_fin),
                    ('tipo_documento', '=', 'invoice'),
                ])
                
                return {
                    'doc_ids': docids,
                    'doc_model': 'delivery.order',
                    'docs': [{
                        'repartos': repartos,
                        'chofer_id': current_order.chofer_id,
                        'entregado_a': current_order.entregado_a,  # O cualquier otro campo que quieras usar
                        'puntodemiles': self.puntodemiles,
                    }],
                }
        
        return {
            'doc_ids': [],
            'doc_model': 'delivery.order',
            'docs': [{
                'repartos': [],
                'chofer_id': False,
                'entregado_a': '',
                'puntodemiles': self.puntodemiles,
            }],
        }

    def puntodemiles(self, a):
        try:
            b = str("{:,.0f}".format(a))
            return b.replace(",", ".")
        except:
            return a