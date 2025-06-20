# -*- coding: utf-8 -*-
from odoo import models, fields, api

# ---------------------------------------------------------
# cálculo de totales del reporte
# ---------------------------------------------------------
class DespachoReporteLiquidacion(models.Model):
    _inherit = 'despacho.despacho'

    lineas_aduna = fields.One2many('despacho.linea.aduna', 'despacho_id', string="Líneas Aduanas")
    lineas_servicios = fields.One2many('despacho.linea.servicio', 'despacho_id', string="Líneas Servicios")
    lineas_descuento = fields.One2many('despacho.linea.descuento', 'despacho_id', string="Líneas Descuentos")

    total_aduna = fields.Monetary(string="Total Aduanas", compute='_compute_totales_liquidacion', store=True)
    total_servicios = fields.Monetary(string="Total Servicios", compute='_compute_totales_liquidacion', store=True)
    total_descuentos = fields.Monetary(string="Total Descuentos", compute='_compute_totales_liquidacion', store=True)
    total_general = fields.Monetary(string="Total General", compute='_compute_totales_liquidacion', store=True)
    monto_en_letras = fields.Char(string="Monto en Letras", compute='_compute_totales_liquidacion', store=True)

    currency_id = fields.Many2one('res.currency', string="Moneda", required=True, default=lambda self: self.env.company.currency_id)

    @api.depends('lineas_aduna.monto_gs', 'lineas_servicios.monto_gs', 'lineas_descuento.monto_gs')
    def _compute_totales_liquidacion(self):
        for rec in self:
            rec.total_aduna = sum(line.monto_gs for line in rec.lineas_aduna)
            rec.total_servicios = sum(line.monto_gs for line in rec.lineas_servicios)
            rec.total_descuentos = sum(line.monto_gs for line in rec.lineas_descuento)
            rec.total_general = rec.total_aduna + rec.total_servicios - rec.total_descuentos

            if rec.total_general and rec.currency_id:
                rec.monto_en_letras = rec.currency_id.amount_to_text(round(rec.total_general, 2))
            else:
                rec.monto_en_letras = ''


# ---------------------------------------------------------
# Modelos de líneas del reporte
# ---------------------------------------------------------

class LineaAduna(models.Model):
    _name = 'despacho.linea.aduna'
    _description = 'Detalle Aduanas'

    despacho_id = fields.Many2one('despacho.despacho', ondelete='cascade', required=True)
    descripcion = fields.Char(required=True)
    comprobante = fields.Char()
    monto_gs = fields.Monetary()
    monto_usd = fields.Monetary()
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

class LineaServicio(models.Model):
    _name = 'despacho.linea.servicio'
    _description = 'Detalle Servicios'

    despacho_id = fields.Many2one('despacho.despacho', ondelete='cascade', required=True)
    descripcion = fields.Char(required=True)
    comprobante = fields.Char()
    tipo_documento = fields.Selection([
        ('factura', 'Factura'),
        ('jornales', 'Jornales'),
        ('s/serv', 's/Serv.'),
    ], default='factura')
    monto_gs = fields.Monetary()
    monto_usd = fields.Monetary()
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

class LineaDescuento(models.Model):
    _name = 'despacho.linea.descuento'
    _description = 'Descuentos y Retenciones'

    despacho_id = fields.Many2one('despacho.despacho', ondelete='cascade', required=True)
    descripcion = fields.Char()
    tipo_descuento = fields.Selection([
        ('pago', 'Pago cliente'),
        ('adelanto', 'Adelanto'),
        ('retencion', 'Retención'),
        ('saldo', 'Saldo a favor'),
    ], required=True)
    monto_gs = fields.Monetary()
    monto_usd = fields.Monetary()
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
