# -*- coding: utf-8 -*-
from odoo import models, api
from datetime import datetime

class ReportDepositoFacturas(models.AbstractModel):
    _name = 'report.reparto_yasy.deposito_facturas_report_template'
    _description = 'Reporte Depósito de Facturas'

    @api.model
    def _get_report_values(self, docids, data=None):
        chofer = self.env['res.partner'].browse(data['chofer_id'])
        repartos = self.env['delivery.order'].browse(data['ids'])
        return {
            'doc_ids': [],
            'doc_model': 'wizard.deposito.facturas',
            'docs': [{
                'chofer_id': chofer,
                'fecha_inicio': data['fecha_inicio'],
                'fecha_fin': data['fecha_fin'],
                'entregado_a': data['entregado_a'],
                'repartos': repartos,
            }],
        }
