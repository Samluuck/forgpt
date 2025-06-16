# -*- coding: utf-8 -*-
from odoo import models, api


class ReportDepositoFacturas(models.AbstractModel):
    _name = 'report.reparto_yasy.deposito_facturas_report_template'
    _description = 'Reporte Depósito de Facturas'

    @api.model
    def _get_report_values(self, docids, data=None):
        repartos = self.env['delivery.order'].search([
            ('chofer_id', '=', data['chofer_id']),
            ('fecha_salida', '>=', data['fecha_inicio']),
            ('fecha_salida', '<=', data['fecha_fin']),
            ('tipo_documento', '=', 'invoice'),
        ])

        chofer = self.env['res.partner'].browse(data['chofer_id'])

        return {
            'doc_ids': [],
            'doc_model': 'delivery.order',
            'docs': [{
                'repartos': repartos,
                'chofer_id': chofer,
                'entregado_a': data.get('entregado_a'),
                'puntodemiles': self.puntodemiles,  # 👈 habilitamos en QWeb
            }],
        }

    def puntodemiles(self, a):
        try:
            b = str("{:,.0f}".format(a))
            return b.replace(",", ".")
        except:
            return a