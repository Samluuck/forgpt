# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from datetime import datetime


class DepositoFacturasWizard(models.TransientModel):
    _name = 'wizard.deposito.facturas'
    _description = 'Wizard para generar el reporte de Depósito de Facturas'

    chofer_id = fields.Many2one('res.partner', string="Chofer", required=True, domain=[('chofer', '=', True)])
    fecha_inicio = fields.Datetime(string="Desde", required=True)
    fecha_fin = fields.Datetime(string="Hasta", required=True)
    entregado_a = fields.Char(string="Entregado a", required=True)

    @api.multi
    def imprimir(self):
        data = {
            'entregado_a': self.entregado_a,
            'fecha_inicio': self.fecha_inicio.strftime('%Y-%m-%d %H:%M:%S'),
            'fecha_fin': self.fecha_fin.strftime('%Y-%m-%d %H:%M:%S'),
            'chofer_id': self.chofer_id.id,
        }

        return self.env.ref('reparto_yasy.action_reporte_deposito_facturas').report_action(
            [],  # No docids, usamos data
            data=data,
            config=False
        )
