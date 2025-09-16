# -*- coding: utf-8 -*-
import qrcode
import base64
from io import BytesIO
import hashlib
import operator
import time
from odoo import models, fields, api
from num2words import num2words
import random
from odoo.exceptions import ValidationError
import pytz
from datetime import datetime
import collections
import requests
from requests import Session
import lxml.etree
import xml.etree.ElementTree as ET
import logging
from signxml import XMLSigner, XMLVerifier
import signxml
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception,content_disposition
from odoo.tools import float_compare, float_round, float_is_zero,float_repr
from hashlib import md5,sha256,sha224
import pytz
#TEST

_logger = logging.getLogger(__name__)
try:
    from zeep import Client
    from zeep.transports import Transport
    from zeep.plugins import HistoryPlugin
except (ImportError, IOError) as err:
    _logger.debug(err)

try:
    from OpenSSL import crypto
    type_ = crypto.FILETYPE_PEM
except ImportError:
    _logger.warning('Error en cargar crypto')

ROUNDING=0.01

class InvoiceFactElect(models.Model):
    _inherit = 'account.move'



    qr_code = fields.Binary("QR Code", attachment=True)
    tasa = fields.Float(string="Tipo de cambio de la operación",compute='get_tipo_cambio')

    tipo_transaccion=fields.Selection(selection=[('1' , 'Venta de mercadería'),
                                        ('2' , 'Prestación de servicios'),
                                        ('3' , 'Mixto'),
                                        ('4' , 'Venta de activo fijo'),
                                        ('5' , 'Venta de divisas'),
                                        ('6' , 'Compra de divisas'),
                                        ('7' , 'Promoción o entrega de muestras'),
                                        ('8' , 'Donación'),
                                        ('9' , 'Anticipo'),
                                        ('10' , 'Compra de productos'),
                                        ('11' , 'Compra de servicios'),
                                        ('12' , 'Venta de crédito fiscal'),
                                        ('13' , 'Muestras médicas')
                                           ],default='2')
    tipo_impuesto=fields.Selection(selection=[('1' , 'IVA'),
                                    ('2' , 'ISC'),
                                    ('3' , 'Renta'),
                                    ('4' , 'Ninguno'),
                                    ('5' , 'IVA - Renta')
                                    ],default='1')
    indicador_presencia=fields.Selection(selection=[('1' , 'Operación presencia'),
                                    ('2' , 'Operación electrónica'),
                                    ('3' , 'Operación telemarketing'),
                                    ('4' , 'Venta a domicilio '),
                                    ('5' , 'Operación bancaria'),
                                    ('6' , 'Operación cíclica'),
                                    ('9' , 'Otro'),
                                    ],default='1')
    descripcion_indi_presencia=fields.Char()

    operacion_credito=fields.Selection(selection=[('1', 'Plazo'),
                                                  ('2','Cuota')],default='1')

    tipo_documento_asociado=fields.Selection(selection=[
                                    ('1' ,'Electrónico'),
                                    ('2' ,'Impreso'),
                                    ('3' ,'Constancia Electrónica')
    ])
    cdc=fields.Char(copy=False, tracking=True)
    estado_de=fields.Selection(selection=[('no-enviado','No enviado'),('enviado','Enviado'),('aprobado','Aprobado'),('rechazado','Rechazado'),('cancelado','Cancelado')],default='no-enviado', tracking=True ,copy=False)
    secuencia=fields.Char(copy=False)
    fecha_firma=fields.Datetime(copy=False)
    motivo_emision_nc=fields.Selection(selection=[('1', 'Devolución y Ajuste de precios'),
                                                  ('2', 'Devolución'),
                                                  ('3', 'Descuento'),
                                                  ('4', 'Bonificación'),
                                                  ('5', 'Crédito incobrable'),
                                                  ('6', 'Recupero de costo'),
                                                  ('7', 'Recupero de gasto'),
                                                  ('8', 'Ajuste de precio')
                                                  ])
    tipo_emision=fields.Selection(selection=[('1','Normal'),
                                             ('2','Contigencia')],default='1')
    info_kude=fields.Char(string='Informacion adicional para el kude')
    autofactura_partner_id = fields.Many2one('res.partner',string='Vendedor Autofactura')
    lotes_ids = fields.Many2many('envio.lotes', 'account_move_lote_rel','move_id','lote_id','Lotes')
    respuesta_lote = fields.Text(related='lotes_ids.respuesta',string="Respuesta del lote")
    respuesta=fields.Text(copy=False)
    texto_qr=fields.Char(copy=False)
    # campos de respuesta de parte de la set
    dEstRes=fields.Char(string="Resultado SET")
    dProtAut=fields.Char(string='Codigo de respuesta')
    dFecProc=fields.Datetime(string='Fecha de Respuesta',help="Fecha en que se recibió una respuesta por parte del SIFEN para la aprobación o rechazo")
    mje_resultado_ids=fields.One2many('mje.resultado','invoice_id',string='Mjes de Respuestas')
    # campos para autofactura
    tipo_constancia=fields.Selection(selection=[('1','Constancia de no ser contribuyente'),
                                                ('2','Constancia de microproductores')])
    nro_constancia=fields.Char()
    nro_control_constancia=fields.Char()
    fecha_procesamiento = fields.Datetime(string="Fecha de procesamiento", help="Fecha en que se recibió una respuesta por parte del SIFEN para la aprobación o rechazo",copy=False)
    aplicar_descuento = fields.Boolean(string="Aplicar descuento/Anticipo", default=False,tracking=True)
    tipo_descuento = fields.Selection(
        [('descuento_a', 'Descuento Global por %'), ('descuento_b', 'Descuento Global Monto'),
         ('anticipo_a', 'Anticipo Global %'), ('anticipo_b', 'Anticipo Global Monto')],
        string="Tipo Descuento/Anticipo",tracking=True)
    porcentaje_descuento = fields.Float(string="% Desc. global", default=0,tracking=True)
    monto_descuento = fields.Float(string="Monto Descuento/Anticipo",tracking=True)
    producto_descuento = fields.Many2one('product.product', string="Producto de descuento/anticipo",tracking=True)


    def aplicar_descuento_lineas(self):
        for rec in self:
            if any(line.product_id.id == rec.producto_descuento.id for line in rec.invoice_line_ids):
                raise ValidationError('El producto de descuento/anticipo %s no puede estar asignado en ninguna línea de factura' % (rec.producto_descuento.name))
            if not rec.producto_descuento:
                raise ValidationError('Favor seleccionar producto de descuento/anticipo')
            if not rec.state == 'draft':
                raise ValidationError('Factura Debe estar en borrador para aplicar descuentos/anticipos')
            new_lines = self.env['account.move.line']
            if rec.tipo_descuento=='descuento_a':
                if rec.porcentaje_descuento > 0:

                    # account_move_line_obj = self.env['account.invoice.line']
                    if len(rec.invoice_line_ids) == 0:
                        raise ValidationError('Para aplicar un descuento global primero debe cargar lineas de factura')
                    taxes = rec.producto_descuento.taxes_id
                    invoice_line_tax_ids = rec.fiscal_position_id.map_tax(taxes)
                    new_line_vals = {
                        'product_id': rec.producto_descuento.id,
                        'name': rec.producto_descuento.description_sale if rec.producto_descuento.description_sale else rec.producto_descuento.name,
                        'account_id': rec.producto_descuento.property_account_income_id.id if rec.producto_descuento.property_account_income_id else False,
                        'quantity': 1,
                        'product_uom_id': rec.producto_descuento.uom_id.id,
                        'porcentaje_descuento': rec.porcentaje_descuento,
                        'price_unit': -sum(
                            (line.price_total * rec.porcentaje_descuento) / 100 for line in rec.invoice_line_ids),
                        'exclude_from_invoice_tab': False,
                        'move_id': rec.id,
                        'tiene_descuento' : True,
                        'tax_ids': invoice_line_tax_ids.ids
                    }
                    new_line = new_lines.new(new_line_vals)
                    new_lines += new_line
                    rec.invoice_line_ids += new_lines
            elif rec.tipo_descuento=='descuento_b':
                # raise ValidationError('Funcionalidad en proceso')
                if rec.monto_descuento != 0:

                    # account_move_line_obj = self.env['account.invoice.line']
                    # if len(rec.invoice_line_ids) == 0:
                    #     raise ValidationError('Para aplicar un descuento global primero debe cargar lineas de factura')
                    taxes = rec.producto_descuento.taxes_id
                    invoice_line_tax_ids = rec.fiscal_position_id.map_tax(taxes)
                    new_line_vals = {
                        'product_id': rec.producto_descuento.id,
                        'name': rec.producto_descuento.description_sale if rec.producto_descuento.description_sale else rec.producto_descuento.name,
                        'account_id': rec.producto_descuento.property_account_income_id.id if rec.producto_descuento.property_account_income_id else False,
                        'quantity': 1,
                        'product_uom_id': rec.producto_descuento.uom_id.id,
                        'price_unit': - abs(rec.monto_descuento),
                        'exclude_from_invoice_tab': False,
                        'move_id': rec.id,
                        # 'monto_anticipo': rec.monto_descuento,
                        'tiene_descuento': True,
                        'tax_ids': invoice_line_tax_ids.ids
                    }
                    new_line = new_lines.new(new_line_vals)
                    new_lines += new_line
                    rec.invoice_line_ids += new_lines
            elif rec.tipo_descuento == 'anticipo_a':
                # raise ValidationError('Funcionalidad en proceso')
                anti_tot=0
                for line in rec.invoice_line_ids :
                    # anticipo_item =line.
                    anticipo_item = (line.price_total * rec.porcentaje_descuento) / 100
                    anti_tot += anticipo_item
                    # line.monto_anticipo = anticipo_item
                    super(models.Model, line).write({'monto_anticipo': anticipo_item})
                if rec.porcentaje_descuento > 0:

                    # account_move_line_obj = self.env['account.invoice.line']
                    if len(rec.invoice_line_ids) == 0:
                        raise ValidationError('Para aplicar un descuento global primero debe cargar lineas de factura')
                    taxes = rec.producto_descuento.taxes_id
                    invoice_line_tax_ids = rec.fiscal_position_id.map_tax(taxes)
                    new_line_vals = {
                        'product_id': rec.producto_descuento.id,
                        'name': rec.producto_descuento.description_sale if rec.producto_descuento.description_sale else rec.producto_descuento.name,
                        'account_id': rec.producto_descuento.property_account_income_id.id if rec.producto_descuento.property_account_income_id else False,
                        'quantity': 1,
                        'product_uom_id': rec.producto_descuento.uom_id.id,
                        'price_unit': -sum(
                            (line.price_total * rec.porcentaje_descuento) / 100 for line in rec.invoice_line_ids),
                        # 'porcentaje_descuento': rec.porcentaje_descuento,
                        'monto_anticipo': anti_tot,
                        'exclude_from_invoice_tab': False,
                        'move_id': rec.id,

                        'tiene_anticipo': True,
                        'tax_ids': invoice_line_tax_ids.ids
                    }
                    new_line = new_lines.new(new_line_vals)
                    new_lines += new_line
                    rec.invoice_line_ids += new_lines
                    # rec.write({'invoice_line_ids': [(0, 0, new_line_vals)]})
            elif rec.tipo_descuento == 'anticipo_b':
                if rec.monto_descuento != 0:
                    anticipo_item = rec.monto_descuento / len(rec.invoice_line_ids.filtered(lambda r: not r.tiene_descuento and not r.tiene_anticipo))

                    for line in rec.invoice_line_ids:
                        # anticipo_item =line.

                        line.monto_anticipo = anticipo_item
                        super(models.Model, line).write({'monto_anticipo':anticipo_item})
                    # account_move_line_obj = self.env['account.invoice.line']
                    # if len(rec.invoice_line_ids) == 0:
                    #     raise ValidationError('Para aplicar un descuento global primero debe cargar lineas de factura')
                    taxes=rec.producto_descuento.taxes_id
                    invoice_line_tax_ids = rec.fiscal_position_id.map_tax(taxes)
                    new_line_vals = {
                        'product_id': rec.producto_descuento.id,
                        'name': rec.producto_descuento.description_sale if rec.producto_descuento.description_sale else rec.producto_descuento.name,
                        'account_id': rec.producto_descuento.property_account_income_id.id if rec.producto_descuento.property_account_income_id else False,
                        'quantity': 1,
                        'product_uom_id': rec.producto_descuento.uom_id.id,
                        'price_unit': - abs(rec.monto_descuento),
                        'exclude_from_invoice_tab': False,

                        'move_id': rec.id,
                        'monto_anticipo': rec.monto_descuento,
                        'tiene_anticipo': True,
                        'tax_ids': invoice_line_tax_ids.ids
                    }
                    new_line = new_lines.new(new_line_vals)
                    new_lines += new_line
                    rec.invoice_line_ids +=new_lines
            for line in rec.invoice_line_ids:
                line._onchange_price_subtotal()
                rec._recompute_dynamic_lines()
    
    # def aplicar_descuento_lineas(self):
    #     for rec in self:
    #         if rec.porcentaje_descuento > 0:
    #             if not rec.producto_descuento:
    #                 raise ValidationError('Favor seleccionar producto de descuento')
    #             account_move_line_obj = self.env['account.move.line']
    #             if len(rec.invoice_line_ids) == 0:
    #                 raise ValidationError('Para aplicar un descuento global primero debe cargar lineas de factura')
    #             new_line_vals = {
    #                 'product_id': rec.producto_descuento.id,
    #                 'name': rec.producto_descuento.description_sale if rec.producto_descuento.description_sale else rec.producto_descuento.name,
    #                 'account_id': rec.producto_descuento.property_account_income_id.id if rec.producto_descuento.property_account_income_id else False,
    #                 'quantity': 1,
    #                 'product_uom_id': rec.producto_descuento.uom_id.id,
    #                 'price_unit': -sum(
    #                     (line.price_total * rec.porcentaje_descuento) / 100 for line in rec.invoice_line_ids),
    #                 'exclude_from_invoice_tab': False,
    #                 'move_id': rec.id,
    #                 'tiene_descuento' : True
    #             }
    #             rec.write({'invoice_line_ids': [(0, 0, new_line_vals)]})
    # 
    #             for line in rec.invoice_line_ids:
    #                 line._onchange_price_subtotal()
    #                 rec._recompute_dynamic_lines()

    def conversion_monetaria_fact(self,numero, moneda):
        entero = int(numero)
        if 'USD' in moneda:
            decimal = str(numero)
            numero_con_punto = ''
            print(f"decimal ->{decimal}")
            entero_string = '.'.join([str(int(entero))[::-1][i:i + 3] for i in range(0, len(str(int(entero))), 3)])[
                            ::-1]
            print(f"entero_string->{entero_string}")
            decimal_string = str(decimal).split('.')
            print(f"decimal_string->{decimal_string}")
            if decimal_string and len(decimal_string) > 1:
                if decimal_string and len(decimal_string[1]) >= 2:
                    numero_con_punto = entero_string + ',' + decimal_string[1][:2]
                elif len(decimal_string[1]) < 2 and decimal_string[1] != '0':
                    numero_con_punto = entero_string + ',' + decimal_string[1] + '0'
                elif len(decimal_string[1]) < 2 and decimal_string[1] == '0':
                    numero_con_punto = entero_string + ',' + decimal_string[1]
            else:
                numero_con_punto = entero_string
        else:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(entero))), 3)])[
                               ::-1]
        num_return = numero_con_punto
        return num_return

    def redondeo_por_tres_decimales_fact(self, numero, moneda):
        print(type(numero))
        ajuste = 5
        if type(numero) is float:
            nuevo_numero = str(numero).split('.')
            decimal1 = 0
            decimal2 = 0
            decimal3 = 0
            if nuevo_numero[1][:1]:
                decimal1 = int(nuevo_numero[1][:1])
            if nuevo_numero[1][1:2]:
                decimal2 = int(nuevo_numero[1][1:2])
            if nuevo_numero[1][2:3]:
                decimal3 = int(nuevo_numero[1][2:3])
            numero = int(numero)
            
            if 'PYG' in moneda:
                if decimal3 >= ajuste and (decimal2 + 1) >= ajuste and (decimal1 + 1) >= ajuste:
                    numero += 1
                    flotante = float(numero)
                    
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) >= ajuste and (decimal1 + 1) < ajuste:
                    decimal1 += 1
                    letter_decimal = str(decimal1) + '0'
                    flotante = float(str(numero) + '.' + letter_decimal)
                    
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) <= ajuste:
                    decimal2 += 1
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    
                    return flotante
                elif decimal3 < ajuste and decimal2 < ajuste and decimal1 < ajuste:
                    if decimal2 != 0 or decimal1 != 0:
                        letter_decimal = str(decimal1) + str(decimal2)
                        flotante = float(str(numero) + '.' + letter_decimal)
                        
                        return flotante
                    elif decimal2 == 0 and decimal1 == 0:
                        flotante = float(numero)
                        
                        return flotante
                elif decimal3 < ajuste and decimal2 >= ajuste and (decimal1 + 1) < ajuste:
                    decimal1 += 1
                    letter_decimal = str(decimal1) + '0'
                    flotante = float(str(numero) + '.' + letter_decimal)
                    
                    return flotante
                elif decimal3 < ajuste and decimal2 < ajuste and decimal1 >= ajuste:
                    numero += 1
                    flotante = float(numero)
                    
                    return flotante
                else:
                    flotante = float(numero)
                    
                    return flotante
            else:
                
                if decimal3 >= ajuste and (decimal2 + 1) > 9 and (decimal1 + 1) > 9:
                    numero += 1
                    flotante = float(numero)
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) >= ajuste and (decimal2 + 1) < 10:
                    decimal2 += 1
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) >= ajuste and (decimal1 + 1) < 10:
                    decimal1 += 1
                    letter_decimal = str(decimal1)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 < ajuste and decimal2 < ajuste and decimal1 < ajuste:
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 < ajuste and decimal2 >= ajuste and decimal1 < ajuste:
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 < ajuste and decimal2 >= ajuste and decimal1 >= ajuste:
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 < ajuste and decimal2 < ajuste and decimal1 >= ajuste:
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 > ajuste and (decimal2 + 1) < ajuste and decimal1 < ajuste:
                    decimal2 += 1
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) < ajuste and decimal1 >= ajuste:
                    decimal2 += 1
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) < ajuste and decimal1 < ajuste:
                    decimal2 += 1
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                else:
                    flotante = float(numero)

                    return flotante
        else:
            
            return numero

    #TODO: función para generar evento de  inutilización desde vista de lista de facturas
    #   por el momento se debe crear una acción de servidor manualmente
    def generar_evento_inutilizacion(self):
        for rec in self:
            evento_data = {
                'tipo':'inutilizacion',
                'timbrado_id': rec.talonario_factura.id,
                'dNumIn': rec.nro,
                'dNumFin':rec.nro,
                'mOtEve' : 'No corresponde'
            }
            evento = self.env['eventos.dte'].create(evento_data)
    def write(self, vals):
        for move in self:
            if move.estado_de == 'aprobado':
                if not self.env.user.has_group('factura_electronica.usuario_factu_elect_modif_group'):
                    if vals.get('partner_id') or vals.get('tipo_comprobante') or vals.get('tipo_factura') or vals.get(
                            'invoice_date') or vals.get('name') or vals.get('talonario_factura') or vals.get(
                            'timbrado') or vals.get('invoice_line_ids') or vals.get(
                            'tipo_documento_asociado') or vals.get('motivo_emicion_nc') or vals.get(
                            'factura_afectada') or vals.get('vencimiento_timbrado') or vals.get(
                            'invoice_payment_term_id') or vals.get('currency_id'):
                        raise ValidationError(
                            'No se pueden realizar modificaciones sobre una factura con estado de documento electrónico aprobado')
            super(InvoiceFactElect, move).write(vals)

    @api.depends('currency_id','invoice_date')
    def get_tipo_cambio(self):
        for rec in self:
            tasa = self.env['res.currency.rate'].search([('currency_id', '=', rec.currency_id.id), ('name', '=', rec.invoice_date),
                                                         ('company_id', '=', self.env.company.id)])
            if len(tasa) > 0:
                rec.tasa = tasa[0].set_venta
            else:
                rec.tasa = 0

    def get_tipo_cambio_reporte(self):
        for rec in self:
            tasa = self.env['res.currency.rate'].search([
                ('currency_id', '=', rec.currency_id.id),
                ('name', '=', rec.invoice_date),
                # Quita o ajusta el filtro de company_id
                '|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)
            ], limit=1)  # Añade limit=1 para eficiencia
            
            if tasa:
                return tasa.set_venta
            else:
                return 0

    @api.onchange('tipo_comprobante')
    def verificar_tipo_comprobante(self):
        self.tipo_documento_asociado = None
        if self.tipo_comprobante:
            if self.tipo_comprobante.codigo_hechauka == 5:
                self.tipo_documento_asociado="3"


    @api.onchange('autofactura_partner_id')
    def setear_autofactura(self):
        if self.autofactura_partner_id:
            self.autofactura=self.autofactura_partner_id.name
        else:
            self.autofactura=False

    def enviar_factura_electronica(self):

        if self.tipo_factura == 1 and self.state != 'paid':
            raise ValidationError('El tipo de factura es Contado por ende la factura debe estar pagada para poder remitir la Factura, favor agregarle el cobro a la factura para continuar')

        if self.env.company.servidor == 'prueba':
            # wsdl = 'http://sifen-test.set.gov.py/de/ws/sync/recibe.wsdl?wsdl'
            wsdl = 'https://sifen-test.set.gov.py/de/ws/sync/recibe.wsdl'
        else:
            wsdl = 'https://sifen.set.gov.py/de/ws/sync/recibe.wsdl'
        today = fields.Date.today()
        # certificado=self.env['l10n.es.aeat.certificate'].search([
        #     ('company_id', '=', self.env.company.id),
        #     ('state', '=', 'active')
        # ], limit=1)
        certificado=self.env['firma.digital'].search([
            ('company_id', '=', self.env.company.id),('user_ids','=',self.env.user.id),
            ('estado', '=', 'activo')
        ], limit=1)
        if not certificado:
            raise ValidationError('No se encontro ningun certificado activo en el sistema para su usuario')
        else:
            public_crt = certificado.public_key
            private_key = certificado.private_key
        # _logger.warning('INICIO DE SISION')
        if not self.secuencia:
            self.secuencia=self.env['ir.sequence'].get('factura_electronica.sequence')
        
        xml = self.generar_xml(certificado)
        xml = str(xml)[2:-1]
        soap = self.generar_soap_rEnviDe(xml)
        headers = {"Content-Type": "text/xml; charset=UTF-8"}
        certificado2 = (public_crt, private_key)
        # try:
        response = requests.post(url=wsdl, data=soap,  cert=certificado2,headers=headers,verify=False, timeout=60)
        # _logger.info('Codigo de retorno set %s' % response.status_code)
        # _logger.info('Retorno set %s' % response.text)
        self.parsear_response(response)
        # except:
        #     _logger.info('Error de conexion')
        #     raise ValidationError('Error de conexion con el servidor de la SIFEN. Favor intente mas tarde')
        # self.generate_qr_code()



    def generar_soap_rEnviDe(self,xml):
        header='<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:ns0="http://ekuatia.set.gov.py/sifen/xsd">' \
               '<soap:Body>' \
               '<ns0:rEnviDe>'
        id='<ns0:dId>'+self.secuencia+'</ns0:dId>'
        rde='<ns0:xDE>'+xml+'</ns0:xDE>'
        footer='</ns0:rEnviDe>' \
               '</soap:Body>' \
               '</soap:Envelope>'
        soap=header+id+rde+footer
        # _logger.info('------soap-------')
        # _logger.info(soap)
        # _logger.info('------fin soap------')
        return soap

    def parsear_response(self,response):
        if response.status_code ==200:
            res_tex = response.text
            if res_tex.find('html')<0:

                self.respuesta = res_tex
                res_tex = res_tex.replace('env:', "").replace('ns2:', "")
                rProtDe = res_tex[res_tex.find('rProtDe') - 1:res_tex.rfind('rProtDe') + len('rProtDe') + 1]
                root = ET.fromstring(rProtDe)
                for child in root:
                    if child.tag=='dFecProc':
                        dFecProc=child.text
                        # dFecProc=dFecProc[:dFecProc.rfind('-')]
                        # date_time_obj = datetime.strptime(dFecProc, '%Y-%m-%dT%H:%M:%S')
                        date_time_obj=parsear_fecha_respuesta(dFecProc)
                        self.dFecProc=date_time_obj
                    elif child.tag=='dEstRes':
                        self.dEstRes=child.text
                        if child.text == 'Aprobado':
                            self.estado_de='aprobado'
                            self.fecha_procesamiento = datetime.now()
                        elif child.text == 'Rechazado':
                            self.estado_de='rechazado'
                            self.fecha_procesamiento = datetime.now()
                        elif child.text == 'Aprobado con observación':
                            self.estado_de='aprobado'
                            self.fecha_procesamiento = datetime.now()
                    elif child.tag=='dProtAut':
                        self.dProtAut=child.text
                    elif child.tag=='gResProc':
                        data = {'invoice_id': self.id,'tipo':'individual'}
                        for c in child:
                            if c.tag=='dCodRes':
                                data.update({'name': c.text})
                            elif c.tag=='dMsgRes':
                                data.update({'dMsgRes': c.text})
                        self.env['mje.resultado'].create(data)
            else:
                raise ValidationError('Error de conexion con el servidor de la SIFEN. Favor intente mas tarde')

    def generar_xml(self,certificado,lote=False):
        """
        Funcion principal encargada en agrupar los datos necesarios, convercion en formato xml y enviar xml al servicio de la set
        en el cuerpo de la funcion se van detallando cada paso y a que parte del documento tecnico pertenece
        :return:
        """

        #if not self.cdc:
        #Siempre se debe generar codigo de control
        #if not self.cdc:
        self.generar_codigo_control()




        #AA. Campos que idenfitican el formato electronico XML PAGINA 62##
        NAMESPACE = {None: 'http://ekuatia.set.gov.py/sifen/xsd',
                     # 'ns2':'http://www.w3.org/2000/09/xmldsig#',
                     'xsi':'http://www.w3.org/2001/XMLSchema-instance',
                     }
        attr_qname = lxml.etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
        #rde=lxml.etree.Element('rde',{attr_qname: 'http://ekuatia.set.gov.py/sifen/xsd siRecepDE_v150.xsd'},nsmap=NAMESPACE)#ORIGINAL


        rde=lxml.etree.Element('rDE',{attr_qname: 'http://ekuatia.set.gov.py/sifen/xsd siRecepDE_v150.xsd'},nsmap=NAMESPACE)
        lxml.etree.SubElement(rde,'dVerFor').text = '150'

        # A. Campos firmados del Documento Electrónico PAGINA 62
        DE=lxml.etree.SubElement(rde,'DE', Id=self.cdc)
        lxml.etree.SubElement(DE,'dDVId').text = str(self.cdc[-1:])
        if (self.fecha_firma and self.estado_de != 'aprobado') or not self.fecha_firma:
            self.fecha_firma = datetime.now()

        # PARSEAR LA FECHA DE LA FIRMA, REBOTA LA FACTURA POR EL TEMA DE HORARIO
        fecha_firma=str(self.fecha_firma.isoformat())
        fecha_firma = fecha_firma[:fecha_firma.find('.')]
        date_time_obj = datetime.strptime(fecha_firma, '%Y-%m-%dT%H:%M:%S')
        tz1 = 'America/Asuncion'
        tz = pytz.timezone(tz1)
        fecha = pytz.utc.localize(date_time_obj).astimezone(tz)
        fecha = fecha.isoformat()
        fecha = str(fecha)
        fecha_firma=fecha[:fecha.rfind('-')]

        # FIN CALCULO DE FECHA -- batallazo armar
        c002 = self.talonario_factura.timbrado_electronico
        # _logger.info('----c002----> %s ' %str(c002) )

        lxml.etree.SubElement(DE,'dFecFirma').text=str(fecha_firma)
        lxml.etree.SubElement(DE,'dSisFact').text='1'
        # ----> FIN APARTADO A <----

        # B. Campos inherentes a la operación de Documentos Electrónicos PAGINA 63
        gOpeDE=lxml.etree.SubElement(DE,'gOpeDE')




        tipo_emision_DE = int(self.tipo_emision)
        tipo_emision_DE_desc = dict(self._fields['tipo_emision'].selection).get(self.tipo_emision)

        tipo_tipo_emision=tipo_emision_DE_desc
        lxml.etree.SubElement(gOpeDE, 'iTipEmi').text = str(tipo_emision_DE)
        lxml.etree.SubElement(gOpeDE, 'dDesTipEmi').text = tipo_emision_DE_desc
        lxml.etree.SubElement(gOpeDE, 'dCodSeg').text = str(self.cdc[34:-1])
        # DATOS OPCIONALES DEL APARTADO esta comentado por no ser obligatorio
        # lxml.etree.SubElement(gOpeDE, 'dInfoEmi').text = 'a'
        if self.info_kude:
            lxml.etree.SubElement(gOpeDE, 'dInfoFisc').text =self.info_kude
        # ----> FIN APARTADO B <----

        # C. Campos de datos del Timbrado PAGINA 64
        # SE LLAMA A LA FUNCION DONDE YA RETORNA LOS VALORES YA SETEADOS Y DONDE SE HACE TODAS LAS VALIDACIONES
        gTimb_dic=self.datos_del_timbrado()
        gTimb = lxml.etree.SubElement(DE, 'gTimb')
        lxml.etree.SubElement(gTimb, 'iTiDE').text = str(gTimb_dic['iTiDE'])
        lxml.etree.SubElement(gTimb, 'dDesTiDE').text = str(gTimb_dic['dDesTiDE'])
        lxml.etree.SubElement(gTimb, 'dNumTim').text = str(gTimb_dic['dNumTim'])
        lxml.etree.SubElement(gTimb, 'dEst').text = str(gTimb_dic['dEst'])
        lxml.etree.SubElement(gTimb, 'dPunExp').text = str(gTimb_dic['dPunExp'])
        lxml.etree.SubElement(gTimb, 'dNumDoc').text = str(gTimb_dic['dNumDoc'])
        lxml.etree.SubElement(gTimb, 'dFeIniT').text = str(gTimb_dic['dFeIniT'])
        # ----> FIN APARTADO C <----

        # D. Campos Generales del Documento Electrónico DE - PAGINA 66
        # SE LLAMA A LA FUNCION DONDE YA RETORNA LOS VALORES YA SETEADOS Y DONDE SE HACE TODAS LAS VALIDACIONES
        gDatGralOpe_dic=self.campos_generales_DE()
        gDatGralOpe = lxml.etree.SubElement(DE, 'gDatGralOpe')
        lxml.etree.SubElement(gDatGralOpe,'dFeEmiDE').text = str(gDatGralOpe_dic['dFeEmiDE'])
        # D1. Campos inherentes a la operación comercial PAGINA 66
        gOpeCom = lxml.etree.SubElement(gDatGralOpe, 'gOpeCom')
        if c002 == '1' or c002 == '4':
            lxml.etree.SubElement(gOpeCom,'iTipTra').text = str(gDatGralOpe_dic['gOpeCom']['iTipTra'])
            lxml.etree.SubElement(gOpeCom,'dDesTipTra').text = str(gDatGralOpe_dic['gOpeCom']['dDesTipTra'])
        lxml.etree.SubElement(gOpeCom,'iTImp').text = str(gDatGralOpe_dic['gOpeCom']['iTImp'])
        lxml.etree.SubElement(gOpeCom,'dDesTImp').text = str(gDatGralOpe_dic['gOpeCom']['dDesTImp'])
        lxml.etree.SubElement(gOpeCom,'cMoneOpe').text = str(gDatGralOpe_dic['gOpeCom']['cMoneOpe'])
        lxml.etree.SubElement(gOpeCom,'dDesMoneOpe').text = str(gDatGralOpe_dic['gOpeCom']['dDesMoneOpe'])
        try:
            lxml.etree.SubElement(gOpeCom,'dCondTiCam').text = str(gDatGralOpe_dic['gOpeCom']['dCondTiCam'])
            lxml.etree.SubElement(gOpeCom,'dTiCam').text = str(gDatGralOpe_dic['gOpeCom']['dTiCam'])
        except:
            pass
        # ----> FIN APARTADO D1 <----

        # D2 Campos que identifican al emisor del Documento Electrónico DE - PAGINA 68
        gEmis = lxml.etree.SubElement(gDatGralOpe, 'gEmis')
        lxml.etree.SubElement(gEmis, 'dRucEm').text = str(gDatGralOpe_dic['gEmis']['dRucEm'])
        lxml.etree.SubElement(gEmis, 'dDVEmi').text = str(gDatGralOpe_dic['gEmis']['dDVEmi'])
        lxml.etree.SubElement(gEmis, 'iTipCont').text = str(gDatGralOpe_dic['gEmis']['iTipCont'])
        try:
            if gDatGralOpe_dic['gEmis']['cTipReg']:
                lxml.etree.SubElement(gEmis, 'cTipReg').text = str(gDatGralOpe_dic['gEmis']['cTipReg'])
        except:
            _logger.info('No tiene seteado en la companhia tipo de regimen')
        lxml.etree.SubElement(gEmis, 'dNomEmi').text = str(gDatGralOpe_dic['gEmis']['dNomEmi'])
        # lxml.etree.SubElement(gEmis, 'dNomFanEmi').text = str(gDatGralOpe_dic['gEmis']['dNomFanEmi'])
        lxml.etree.SubElement(gEmis, 'dDirEmi').text = str(gDatGralOpe_dic['gEmis']['dDirEmi'])
        lxml.etree.SubElement(gEmis, 'dNumCas').text = str(gDatGralOpe_dic['gEmis']['dNumCas'])
        # lxml.etree.SubElement(gEmis, 'dCompDir1').text = str(gDatGralOpe_dic['gEmis']['dCompDir1'])
        # lxml.etree.SubElement(gEmis, 'dCompDir2').text = str(gDatGralOpe_dic['gEmis']['dCompDir2'])
        lxml.etree.SubElement(gEmis, 'cDepEmi').text = str(gDatGralOpe_dic['gEmis']['cDepEmi'])
        lxml.etree.SubElement(gEmis, 'dDesDepEmi').text = str(gDatGralOpe_dic['gEmis']['dDesDepEmi'])
        # lxml.etree.SubElement(gEmis, 'cDisEmi').text = str(gDatGralOpe_dic['gEmis']['cDisEmi'])
        # lxml.etree.SubElement(gEmis, 'dDesDisEmi').text = str(gDatGralOpe_dic['gEmis']['dDesDisEmi'])
        lxml.etree.SubElement(gEmis, 'cCiuEmi').text = str(gDatGralOpe_dic['gEmis']['cCiuEmi'])
        lxml.etree.SubElement(gEmis, 'dDesCiuEmi').text = str(gDatGralOpe_dic['gEmis']['dDesCiuEmi'])
        lxml.etree.SubElement(gEmis, 'dTelEmi').text = str(gDatGralOpe_dic['gEmis']['dTelEmi'])
        lxml.etree.SubElement(gEmis, 'dEmailE').text = str(gDatGralOpe_dic['gEmis']['dEmailE'])
        # lxml.etree.SubElement(gEmis, 'dDenSuc').text = str(gDatGralOpe_dic['gEmis']['dDenSuc'])

        #  D2.1 HIJO DE D2 Campos que describen la actividad económica del emisor PAGINA 70
        gActEco=lxml.etree.SubElement(gEmis, 'gActEco')
        lxml.etree.SubElement(gActEco, 'cActEco').text = str(gDatGralOpe_dic['gEmis']['gActEco']['cActEco'])
        lxml.etree.SubElement(gActEco, 'dDesActEco').text = str(gDatGralOpe_dic['gEmis']['gActEco']['dDesActEco'])
        # ----> FIN APARTADO D2.1 <----
        # ----> FIN APARTADO D2 <----

        # D3. Campos que identifican al receptor del Documento Electrónico DE - PAGINA 71
        gDatRec = lxml.etree.SubElement(gDatGralOpe, 'gDatRec')
        if c002 == '4':
            partner_id=self.env.company.partner_id
        else:
            partner_id=self.partner_id
        if int(self.partner_id.naturaleza_receptor) == 1:
            lxml.etree.SubElement(gDatRec, 'iNatRec').text = str(gDatGralOpe_dic['gDatRec']['iNatRec'])
            lxml.etree.SubElement(gDatRec, 'iTiOpe').text = str(gDatGralOpe_dic['gDatRec']['iTiOpe'])
            lxml.etree.SubElement(gDatRec, 'cPaisRec').text = str(gDatGralOpe_dic['gDatRec']['cPaisRec'])
            lxml.etree.SubElement(gDatRec, 'dDesPaisRe').text = str(gDatGralOpe_dic['gDatRec']['dDesPaisRe'])
            lxml.etree.SubElement(gDatRec, 'iTiContRec').text = str(gDatGralOpe_dic['gDatRec']['iTiContRec'])
            lxml.etree.SubElement(gDatRec, 'dRucRec').text = str(gDatGralOpe_dic['gDatRec']['dRucRec'])
            lxml.etree.SubElement(gDatRec, 'dDVRec').text = str(gDatGralOpe_dic['gDatRec']['dDVRec'])
        else:
            # if int(self.partner_id.naturaleza_receptor) == 2 and int(self.partner_id.naturaleza_receptor) != 4:
            if int(self.partner_id.naturaleza_receptor) == 2 :
                lxml.etree.SubElement(gDatRec, 'iNatRec').text = str(gDatGralOpe_dic['gDatRec']['iNatRec'])
                lxml.etree.SubElement(gDatRec, 'iTiOpe').text = str(gDatGralOpe_dic['gDatRec']['iTiOpe'])
                lxml.etree.SubElement(gDatRec, 'cPaisRec').text = str(gDatGralOpe_dic['gDatRec']['cPaisRec'])
                lxml.etree.SubElement(gDatRec, 'dDesPaisRe').text = str(gDatGralOpe_dic['gDatRec']['dDesPaisRe'])
                lxml.etree.SubElement(gDatRec, 'iTipIDRec').text = str(gDatGralOpe_dic['gDatRec']['iTipIDRec'])
                lxml.etree.SubElement(gDatRec, 'dDTipIDRec').text = str(gDatGralOpe_dic['gDatRec']['dDTipIDRec'])
                lxml.etree.SubElement(gDatRec, 'dNumIDRec').text = str(gDatGralOpe_dic['gDatRec']['dNumIDRec'])

        lxml.etree.SubElement(gDatRec, 'dNomRec').text = str(gDatGralOpe_dic['gDatRec']['dNomRec'])
        # lxml.etree.SubElement(gDatRec, 'dNomFanRec').text = str(gDatGralOpe_dic['gDatRec']['dNomFanRec'])
        if gDatGralOpe_dic['gDatRec']['dDirRec'] and gDatGralOpe_dic['gDatRec']['dNumCasRec']:
            lxml.etree.SubElement(gDatRec, 'dDirRec').text = str(gDatGralOpe_dic['gDatRec']['dDirRec'])
            lxml.etree.SubElement(gDatRec, 'dNumCasRec').text = str(gDatGralOpe_dic['gDatRec']['dNumCasRec'])
        # CAMPOS NO OBLIGATORIOS SE COMENTA MIENTRAS
        # lxml.etree.SubElement(gDatRec, 'cDepRec').text = str(gDatGralOpe_dic['gDatRec']['cDepRec'])
        # lxml.etree.SubElement(gDatRec, 'dDesDepRec').text = str(gDatGralOpe_dic['gDatRec']['dDesDepRec'])
        # lxml.etree.SubElement(gDatRec, 'cDisRec').text = str(gDatGralOpe_dic['gDatRec']['cDisRec'])
        # lxml.etree.SubElement(gDatRec, 'dDesDisRec').text = str(gDatGralOpe_dic['gDatRec']['dDesDisRec'])
        # lxml.etree.SubElement(gDatRec, 'cCiuRec').text = str(gDatGralOpe_dic['gDatRec']['cCiuRec'])
        # lxml.etree.SubElement(gDatRec, 'dDesCiuRec').text = str(gDatGralOpe_dic['gDatRec']['dDesCiuRec'])
        # lxml.etree.SubElement(gDatRec, 'dTelRec').text = str(gDatGralOpe_dic['gDatRec']['dTelRec'])
        # lxml.etree.SubElement(gDatRec, 'dCelRec').text = str(gDatGralOpe_dic['gDatRec']['dCelRec'])
        # lxml.etree.SubElement(gDatRec, 'dEmailRec').text = str(gDatGralOpe_dic['gDatRec']['dEmailRec'])
        # lxml.etree.SubElement(gDatRec, 'dEmailRec').text = str(gDatGralOpe_dic['dCodCliente']['dCodCliente'])
        # ----> FIN APARTADO D3 <----

        # E. Campos específicos por tipo de Documento Electrónico - PAGINA 74

        # SE LLAMA A LA FUNCION DONDE YA RETORNA LOS VALORES YA SETEADOS Y DONDE SE HACE TODAS LAS VALIDACIONES
        if self.currency_id.name != 'PYG':
            gDtipDE_dic = self.campos_especificos_DE(gDatGralOpe_dic['gOpeCom']['dTiCam'])
        else:
            gDtipDE_dic = self.campos_especificos_DE()
        gDtipDE = lxml.etree.SubElement(DE, 'gDtipDE')
        if c002 == '1':
            gCamFE= lxml.etree.SubElement(gDtipDE, 'gCamFE')
            lxml.etree.SubElement(gCamFE, 'iIndPres').text = str(gDtipDE_dic['gCamFE']['iIndPres'])
            lxml.etree.SubElement(gCamFE, 'dDesIndPres').text = str(gDtipDE_dic['gCamFE']['dDesIndPres'])

        if c002 == '4':
            gCamAE = lxml.etree.SubElement(gDtipDE, 'gCamAE')
            lxml.etree.SubElement(gCamAE, 'iNatVen').text = str(gDtipDE_dic['gCamAE']['iNatVen'])
            lxml.etree.SubElement(gCamAE, 'dDesNatVen').text = str(gDtipDE_dic['gCamAE']['dDesNatVen'])
            lxml.etree.SubElement(gCamAE, 'iTipIDVen').text = str(gDtipDE_dic['gCamAE']['iTipIDVen'])
            lxml.etree.SubElement(gCamAE, 'dDTipIDVen').text = str(gDtipDE_dic['gCamAE']['dDTipIDVen'])
            lxml.etree.SubElement(gCamAE, 'dNumIDVen').text = str(gDtipDE_dic['gCamAE']['dNumIDVen'])
            lxml.etree.SubElement(gCamAE, 'dNomVen').text = str(gDtipDE_dic['gCamAE']['dNomVen'])
            lxml.etree.SubElement(gCamAE, 'dDirVen').text = str(gDtipDE_dic['gCamAE']['dDirVen'])
            lxml.etree.SubElement(gCamAE, 'dNumCasVen').text = str(gDtipDE_dic['gCamAE']['dNumCasVen'])
            lxml.etree.SubElement(gCamAE, 'cDepVen').text = str(gDtipDE_dic['gCamAE']['cDepVen'])
            lxml.etree.SubElement(gCamAE, 'dDesDepVen').text = str(gDtipDE_dic['gCamAE']['dDesDepVen'])
            lxml.etree.SubElement(gCamAE, 'cCiuVen').text = str(gDtipDE_dic['gCamAE']['cCiuVen'])
            lxml.etree.SubElement(gCamAE, 'dDesCiuVen').text = str(gDtipDE_dic['gCamAE']['dDesCiuVen'])
            lxml.etree.SubElement(gCamAE, 'dDirProv').text = str(gDtipDE_dic['gCamAE']['dDirProv'])
            lxml.etree.SubElement(gCamAE, 'cDepProv').text = str(gDtipDE_dic['gCamAE']['cDepProv'])
            lxml.etree.SubElement(gCamAE, 'dDesDepProv').text = str(gDtipDE_dic['gCamAE']['dDesDepProv'])
            lxml.etree.SubElement(gCamAE, 'cCiuProv').text = str(gDtipDE_dic['gCamAE']['cCiuProv'])
            lxml.etree.SubElement(gCamAE, 'dDesCiuProv').text = str(gDtipDE_dic['gCamAE']['dDesCiuProv'])
        if c002== '5' or  c002 == '6':
            gCamNCDE = lxml.etree.SubElement(gDtipDE, 'gCamNCDE')
            lxml.etree.SubElement(gCamNCDE, 'iMotEmi').text = str(gDtipDE_dic['gCamNCDE']['iMotEmi'])
            lxml.etree.SubElement(gCamNCDE, 'dDesMotEmi').text = str(gDtipDE_dic['gCamNCDE']['dDesMotEmi'])
        if c002=='1' or c002=='4':
            gCamCond = lxml.etree.SubElement(gDtipDE, 'gCamCond')
            # _logger.info('factura %s' %self.nro_factura)
            lxml.etree.SubElement(gCamCond, 'iCondOpe').text = str(gDtipDE_dic['gCamCond']['iCondOpe'])
            lxml.etree.SubElement(gCamCond, 'dDCondOpe').text = str(gDtipDE_dic['gCamCond']['dDCondOpe'])
            if self.tipo_factura == '1' and self.payment_state in ['paid','partial','in_payment']:
                for g in gDtipDE_dic['gCamCond']['gPaConEIni']:
                    gPaConEIni = lxml.etree.SubElement(gCamCond, 'gPaConEIni')
                    lxml.etree.SubElement(gPaConEIni,'iTiPago').text=str(g['iTiPago'])
                    lxml.etree.SubElement(gPaConEIni,'dDesTiPag').text=str(g['dDesTiPag'])
                    lxml.etree.SubElement(gPaConEIni,'dMonTiPag').text=str(g['dMonTiPag'])
                    lxml.etree.SubElement(gPaConEIni,'cMoneTiPag').text=str(g['cMoneTiPag'])
                    lxml.etree.SubElement(gPaConEIni,'dDMoneTiPag').text=str(g['dDMoneTiPag'])
                    try:
                        lxml.etree.SubElement(gPaConEIni,'dTiCamTiPag').text=str(g['dTiCamTiPag'])
                    except:
                        pass
                    try:
                        iDenTarj=g['gPagTarCD']['iDenTarj']
                        gPagTarCD = lxml.etree.SubElement(gPaConEIni, 'gPagTarCD')
                        lxml.etree.SubElement(gPagTarCD, 'iDenTarj').text = str(iDenTarj)
                        lxml.etree.SubElement(gPagTarCD, 'dDesDenTarj').text = str(g['gPagTarCD']['dDesDenTarj'])
                        lxml.etree.SubElement(gPagTarCD, 'iForProPa').text = str(g['gPagTarCD']['iForProPa'])
                    except:
                        pass
                    try:
                        dNumCheq=g['gPagCheq']['dNumCheq']
                        gPagCheq = lxml.etree.SubElement(gPaConEIni, 'gPagCheq')
                        lxml.etree.SubElement(gPagCheq, 'dNumCheq').text = str(dNumCheq)
                        lxml.etree.SubElement(gPagCheq, 'dBcoEmi').text = str(g['gPagCheq']['dBcoEmi'])
                    except:
                        pass


            if self.tipo_factura == '2' and self.state == 'posted':
                if c002 == '1' or c002 == '4':
                    gPagCred=lxml.etree.SubElement(gCamCond, 'gPagCred')
                    lxml.etree.SubElement(gPagCred, 'iCondCred').text = str(gDtipDE_dic['gCamCond']['gPagCred']['iCondCred'])
                    lxml.etree.SubElement(gPagCred, 'dDCondCred').text = str(gDtipDE_dic['gCamCond']['gPagCred']['dDCondCred'])
                    if self.operacion_credito == '1':
                        lxml.etree.SubElement(gPagCred, 'dPlazoCre').text = str(gDtipDE_dic['gCamCond']['gPagCred']['dPlazoCre'])
                    else:
                        lxml.etree.SubElement(gPagCred, 'dCuotas').text = str(gDtipDE_dic['gCamCond']['gPagCred']['dCuotas'])


        for g in gDtipDE_dic['list_gCamItem']:
            gCamItem=lxml.etree.SubElement(gDtipDE, 'gCamItem')
            lxml.etree.SubElement(gCamItem, 'dCodInt').text = str(g['dCodInt'])
            lxml.etree.SubElement(gCamItem, 'dDesProSer').text = str(g['dDesProSer']).strip()
            lxml.etree.SubElement(gCamItem, 'cUniMed').text = str(g['cUniMed'])
            lxml.etree.SubElement(gCamItem, 'dDesUniMed').text = str(g['dDesUniMed'])
            lxml.etree.SubElement(gCamItem, 'dCantProSer').text = str(g['dCantProSer'])
            gValorItem = lxml.etree.SubElement(gCamItem, 'gValorItem')
            lxml.etree.SubElement(gValorItem, 'dPUniProSer').text = str(g['gValorItem']['dPUniProSer'])
            lxml.etree.SubElement(gValorItem, 'dTotBruOpeItem').text = str(g['gValorItem']['dTotBruOpeItem'])
            gValorRestaItem = lxml.etree.SubElement(gValorItem, 'gValorRestaItem')
            lxml.etree.SubElement(gValorRestaItem, 'dDescGloItem').text = str(g['gValorItem']['gValorRestaItem']['dDescGloItem'])
            if g['gValorItem']['gValorRestaItem'].get('dDescItem') > 0: #EN CASO QUE EL DESCUENTO PARTICULAR SEA MAYOR A CERO
                lxml.etree.SubElement(gValorRestaItem, 'dDescItem').text = str(
                    g['gValorItem']['gValorRestaItem']['dDescItem'])
                lxml.etree.SubElement(gValorRestaItem, 'dPorcDesIt').text = str(
                    g['gValorItem']['gValorRestaItem']['dPorcDesIt'])
            lxml.etree.SubElement(gValorRestaItem, 'dAntPreUniIt').text = str(g['gValorItem']['gValorRestaItem']['dAntPreUniIt'])
            lxml.etree.SubElement(gValorRestaItem, 'dAntGloPreUniIt').text = str(g['gValorItem']['gValorRestaItem']['dAntGloPreUniIt'])
            lxml.etree.SubElement(gValorRestaItem, 'dTotOpeItem').text = str(g['gValorItem']['gValorRestaItem']['dTotOpeItem'])
            if c002 != '4' and  c002 != '7':
                gCamIVA=lxml.etree.SubElement(gCamItem, 'gCamIVA')


                lxml.etree.SubElement(gCamIVA, 'iAfecIVA').text = str(g['gCamIVA']['iAfecIVA'])
                lxml.etree.SubElement(gCamIVA, 'dDesAfecIVA').text = str(g['gCamIVA']['dDesAfecIVA'])
                lxml.etree.SubElement(gCamIVA, 'dPropIVA').text = str(g['gCamIVA']['dPropIVA'])
                lxml.etree.SubElement(gCamIVA, 'dTasaIVA').text = str(g['gCamIVA']['dTasaIVA'])
                lxml.etree.SubElement(gCamIVA, 'dBasGravIVA').text = str(g['gCamIVA']['dBasGravIVA'])
                lxml.etree.SubElement(gCamIVA, 'dLiqIVAItem').text = str((g['gCamIVA']['dLiqIVAItem']))
                lxml.etree.SubElement(gCamIVA, 'dBasExe').text = str(g['gCamIVA']['dBasExe'])





                if g.get('gRasMerc'):
                    _logger.info(g['gRasMerc'])
                    gRasMerc = lxml.etree.SubElement(gCamItem, 'gRasMerc')
                    if g['gRasMerc']['dNumLote']:
                        lxml.etree.SubElement(gRasMerc, 'dNumLote').text = str(g['gRasMerc']['dNumLote'])

                    if g['gRasMerc']['dVencMerc']:
                        lxml.etree.SubElement(gRasMerc, 'dVencMerc').text = str(g['gRasMerc']['dVencMerc'])
                    if  g['gRasMerc']['dNSerie']:
                        lxml.etree.SubElement(gRasMerc, 'dNSerie').text = str(g['gRasMerc']['dNSerie']).replace('-','')
                    if g['gRasMerc']['dNumPedi']:
                        lxml.etree.SubElement(gRasMerc, 'dNumPedi').text = str(g['gRasMerc']['dNumPedi'])
                    if g['gRasMerc']['dNumSegui']:
                        lxml.etree.SubElement(gRasMerc, 'dNumSegui').text = str(g['gRasMerc']['dNumSegui'])
                    if g['gRasMerc']['dNomImp']:
                        lxml.etree.SubElement(gRasMerc, 'dNomImp').text = str((g['gRasMerc']['dNomImp']))
                    if g['gRasMerc']['dDirImp']:
                        lxml.etree.SubElement(gRasMerc, 'dDirImp').text = str((g['gRasMerc']['dDirImp']))
                    if g['gRasMerc']['dNumFir']:
                        lxml.etree.SubElement(gRasMerc, 'dNumFir').text = str((g['gRasMerc']['dNumFir']))
                    if g['gRasMerc']['dNumReg']:
                        lxml.etree.SubElement(gRasMerc, 'dNumReg').text = str((g['gRasMerc']['dNumReg']))
                    if g['gRasMerc']['dNumRegEntCom']:
                        lxml.etree.SubElement(gRasMerc, 'dNumRegEntCom').text = str((g['gRasMerc']['dNumRegEntCom']))
                    if g['gRasMerc']['dNomPro']:
                        lxml.etree.SubElement(gRasMerc, 'dNomPro').text = str(g['gRasMerc']['dNomPro'])

        # F.Campos que describen los subtotales y totales de la transacción documentada(F001 - F099) DE
        gTotSub = lxml.etree.SubElement(DE, 'gTotSub')
        if c002 !='4' :
            lxml.etree.SubElement(gTotSub,'dSubExe').text=str(gDtipDE_dic['gTotSub']['dSubExe'])
            lxml.etree.SubElement(gTotSub,'dSubExo').text=str(gDtipDE_dic['gTotSub']['dSubExo'])
            if self.tipo_impuesto == '1':
                lxml.etree.SubElement(gTotSub,'dSub5').text=str(gDtipDE_dic['gTotSub']['dSub5'])
                lxml.etree.SubElement(gTotSub,'dSub10').text=str(gDtipDE_dic['gTotSub']['dSub10'])
        lxml.etree.SubElement(gTotSub,'dTotOpe').text=str(gDtipDE_dic['gTotSub']['dTotOpe'])
        lxml.etree.SubElement(gTotSub,'dTotDesc').text=str(gDtipDE_dic['gTotSub']['dTotDesc'])
        lxml.etree.SubElement(gTotSub,'dTotDescGlotem').text=str(gDtipDE_dic['gTotSub']['dTotDescGlotem'])
        lxml.etree.SubElement(gTotSub,'dTotAntItem').text=str(gDtipDE_dic['gTotSub']['dTotAntItem'])
        lxml.etree.SubElement(gTotSub,'dTotAnt').text=str(gDtipDE_dic['gTotSub']['dTotAnt'])
        lxml.etree.SubElement(gTotSub,'dPorcDescTotal').text=str(gDtipDE_dic['gTotSub']['dPorcDescTotal'])
        lxml.etree.SubElement(gTotSub,'dDescTotal').text=str(gDtipDE_dic['gTotSub']['dDescTotal'])
        lxml.etree.SubElement(gTotSub,'dAnticipo').text=str(gDtipDE_dic['gTotSub']['dAnticipo'])
        lxml.etree.SubElement(gTotSub,'dRedon').text=str(gDtipDE_dic['gTotSub']['dRedon'])
        lxml.etree.SubElement(gTotSub,'dTotGralOpe').text=str(gDtipDE_dic['gTotSub']['dTotGralOpe'])
        if c002 != '4':
            lxml.etree.SubElement(gTotSub,'dIVA5').text=str(gDtipDE_dic['gTotSub']['dIVA5'])
            lxml.etree.SubElement(gTotSub,'dIVA10').text=str(gDtipDE_dic['gTotSub']['dIVA10'])
        if self.tipo_impuesto != '1' or self.tipo_impuesto != '5':
            lxml.etree.SubElement(gTotSub, 'dLiqTotIVA5').text = str(gDtipDE_dic['gTotSub']['dLiqTotIVA5'])
            lxml.etree.SubElement(gTotSub, 'dLiqTotIVA10').text = str(gDtipDE_dic['gTotSub']['dLiqTotIVA10'])
            val_dTotIVA=0
            if c002 != '4':
                val_dTotIVA=gDtipDE_dic['gTotSub']['dTotIVA']
                lxml.etree.SubElement(gTotSub, 'dTotIVA').text = str(val_dTotIVA)
                lxml.etree.SubElement(gTotSub, 'dBaseGrav5').text = str(gDtipDE_dic['gTotSub']['dBaseGrav5'])
                lxml.etree.SubElement(gTotSub, 'dBaseGrav10').text = str(gDtipDE_dic['gTotSub']['dBaseGrav10'])
                lxml.etree.SubElement(gTotSub, 'dTBasGraIVA').text = str(gDtipDE_dic['gTotSub']['dTBasGraIVA'])
                if self.currency_id.name != 'PYG':
                    lxml.etree.SubElement(gTotSub, 'dTotalGs').text = str(gDtipDE_dic['gTotSub']['dTotalGs'])
        if c002=='5' or c002=='6' or c002=='4' :
            dic_gCamDEAsoc=self.identifican_documento_asociado()
            gCamDEAsoc = lxml.etree.SubElement(DE, 'gCamDEAsoc')
            lxml.etree.SubElement(gCamDEAsoc, 'iTipDocAso').text = str(dic_gCamDEAsoc['iTipDocAso'])
            lxml.etree.SubElement(gCamDEAsoc, 'dDesTipDocAso').text = str(dic_gCamDEAsoc['dDesTipDocAso'])
            if self.tipo_documento_asociado == '1':
                lxml.etree.SubElement(gCamDEAsoc, 'dCdCDERef').text = str(dic_gCamDEAsoc['dCdCDERef'])
            if self.tipo_documento_asociado == '2':
                lxml.etree.SubElement(gCamDEAsoc, 'dNTimDI').text = str(dic_gCamDEAsoc['dNTimDI'])
                lxml.etree.SubElement(gCamDEAsoc, 'dEstDocAso').text = str(dic_gCamDEAsoc['dEstDocAso'])
                lxml.etree.SubElement(gCamDEAsoc, 'dPExpDocAso').text = str(dic_gCamDEAsoc['dPExpDocAso'])
                lxml.etree.SubElement(gCamDEAsoc, 'dNumDocAso').text = str(dic_gCamDEAsoc['dNumDocAso'])
                lxml.etree.SubElement(gCamDEAsoc, 'iTipoDocAso').text = str(dic_gCamDEAsoc['iTipoDocAso'])
                lxml.etree.SubElement(gCamDEAsoc, 'dDTipoDocAso').text = str(dic_gCamDEAsoc['dDTipoDocAso'])
                lxml.etree.SubElement(gCamDEAsoc, 'dFecEmiDI').text = str(dic_gCamDEAsoc['dFecEmiDI'])
            if self.tipo_documento_asociado == '3':
                lxml.etree.SubElement(gCamDEAsoc, 'iTipCons').text = str(dic_gCamDEAsoc['iTipCons'])
                lxml.etree.SubElement(gCamDEAsoc, 'dDesTipCons').text = str(dic_gCamDEAsoc['dDesTipCons'])
                if self.tipo_constancia=='2':
                    lxml.etree.SubElement(gCamDEAsoc, 'dNumCons').text = str(dic_gCamDEAsoc['dNumCons'])
                if self.tipo_constancia=='1':
                    lxml.etree.SubElement(gCamDEAsoc, 'dNumControl').text = str(dic_gCamDEAsoc['dNumControl'])


        # E1 HIJO DE E Campos que componen la Factura Electrónica FE - PAGINA 74
        # lxml.etree.SubElement(gDtipDE, 'iIndPres').text = str(gDtipDE_dic['gDtipDE']['gCamFE']['iIndPres'])
        # gCamFE= lxml.etree.SubElement(gDtipDE, 'gCamFE')
        # if self.talonario_factura.timbrado_electronico == 1 or self.talonario_factura.timbrado_electronico == 4:



        if self.env.company.servidor == 'prueba':
            url = 'https://ekuatia.set.gov.py/consultas-test/qr?'
        else:
            url = 'https://ekuatia.set.gov.py/consultas/qr?'








        # SE AGREGA LAS ETIQUETAS SIGNATURE AL XML

        xml = lxml.etree.tostring(rde, encoding="unicode", pretty_print=True)


        key2 = open(certificado.private_key).read()
        cert2 = open(certificado.public_key).read()
        signer = XMLSigner(method=signxml.methods.enveloped,c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315',
                                signature_algorithm='rsa-sha256', digest_algorithm="sha256")
        ns = {}
        ns[None] = signer.namespaces['ds']
        signer.namespaces = ns
        signed_root=signer.sign(rde, reference_uri="#"+str(self.cdc), id_attribute="Id",key=key2,cert=cert2)

        #verifica la firma correcta
        # verified_data=XMLVerifier().verify(signed_root,ca_pem_file=certificado.private_key,x509_cert=cert2).signed_xml





        root = signed_root.getchildren()[2]

        DigestValue=root.getchildren()[0].getchildren()[2].getchildren()[2].text
        dato1=root.getchildren()[2].getchildren()[0].getchildren()[0].text
        dato2=root.getchildren()[2].getchildren()[0].getchildren()[0]
        dato_string=str(dato1)
        dato2.text=dato_string.replace('\n',"")

        # hash_disgest_value=sha256(str(DigestValue).encode('utf-8')).hexdigest()
        hash_disgest_value=str(DigestValue).encode('utf-8').hex()
        # print(hash_disgest_value)
        fecha_hash=gDatGralOpe_dic['dFeEmiDE'].encode('utf-8').hex()
        # texto_qr='https://ekuatia.set.gov.py/consultas-test'
        texto_qr='nVersion=150'
        texto_qr+='&Id='+self.cdc
        texto_qr+='&dFeEmiDE='+ str(fecha_hash)
        if self.partner_id.naturaleza_receptor == '1':
            texto_qr+='&dRucRec='+ gDatGralOpe_dic['gDatRec']['dRucRec']
        else:
            texto_qr += '&dNumIDRec=' + gDatGralOpe_dic['gDatRec']['dNumIDRec']
        texto_qr+='&dTotGralOpe='+ str(redondear(self.amount_total))
        texto_qr+='&dTotIVA='+ str(val_dTotIVA)
        texto_qr+='&cItems='+ str(len(self.invoice_line_ids.filtered(lambda r:r.display_type == False and r.tiene_descuento == False and not r.tiene_anticipo)))
        texto_qr+='&DigestValue='+ str(hash_disgest_value)
        texto_qr+='&IdCSC='+ self.env.company.IdCSC
        CSC=self.env.company.csc
        data_qr=texto_qr+CSC
        hash_qr=sha256(data_qr.encode('utf-8')).hexdigest()
        texto_qr+='&cHashQR='+str(hash_qr)
        self.texto_qr=url+texto_qr
        val_dCarQR=url+texto_qr

        for element in signed_root.iter('{http://ekuatia.set.gov.py/sifen/xsd}rDE'):
            gCamFuFD = lxml.etree.Element("gCamFuFD")
            lxml.etree.SubElement(gCamFuFD, 'dCarQR').text = str(val_dCarQR)
            element.insert(10,gCamFuFD)

        data_serialized = lxml.etree.tostring(signed_root)



        return data_serialized

    def encrypt_string(self,hash_string):
        sha_signature = hashlib.sha256(hash_string.encode()).hexdigest()
        return sha_signature

    def conectar(self):
        print('conectando')

    def descargar_xml(self):
        # if self.tipo_comprobante.id == 2:
        #     self.generate_qr_code()
        return {
            'type': 'ir.actions.act_url',
            'url': '/getXML/' + str(self.id),
            'target': 'current'
        }
    # @api.depends('type')
    # def setear_tipo_documento(self):
    #     if self.type in  ('out_refund','out_invoice'):
    #         self.tipo_documento_asociado=1
    #     else:
    #         if self.partner_id.parent_id:
    #             self.tipo_documento_asociado=self.partner_id.parent_id.tipo_documento
    #         elif self.partner_id:
    #             self.tipo_documento_asociado=self.partner_id.tipo_documento
    #         else:
    #             self.tipo_documento_asociado=2

    def calcular_dv(self,valor):
        """
        Funcion algoritmo Modulo 11 que calcula el digito verificador
        :param valor que se calculara su digito verificador
        :return: el digito verificador
        """
        ruc_str = str(valor)[::-1]

        # variable total que almacena el resultado
        v_total = 0

        basemax = 11

        # el factor de chequeo actual,
        # inicializa en 2
        k = 2

        for i in range(0, len(ruc_str)):
            if k > basemax:
                k = 2
            # multiplicación de cada valor por el factor de chequeo actual(k)
            v_total += int(ruc_str[i]) * k
            # se incrementa el valor de la variable k
            k += 1

        # resto de la división entre el resultado y el valor de la
        # variable basemax
        resto = v_total % basemax

        if resto > 1:
            # si el resto es mayor que uno, entonces el valor de basemax
            # es restado por el resultado de la operación anterior
            return basemax - resto
        else:
            return 0

    def generar_codigo_control(self):
        """
        Funcion donde se conforma  el CDC(Codigo de Control) Pagina 50 y 51 del Manual Tecnico
        :return: no retorna nada pero setea el campo cdc del account.move
        """
        if self.estado_de in ('aprobado','cancelado'):
            return True
        else:
            concatenar=''
            # cdc_fe='01'
            val_iTiDE = str(self.talonario_factura.timbrado_electronico)
            val_iTiDE='0'+val_iTiDE
            cdc_fe=val_iTiDE
            cdc_ruc=''
            cdc_dv=''

            cdc_ruc=self.env.company.ruc
            cdc_dv = self.env.company.dv
            if not cdc_ruc or not cdc_dv:
                raise ValidationError('Favor agregar ruc y dv a la compañia')
            # if not cdc_ruc and self.ruc_factura:
            #     ruc_factura=self.ruc_factura
            #     cdc_ruc=ruc_factura[:ruc_factura.find('-')]
            #     cdc_dv=ruc_factura[ruc_factura.find('-')+1:]
            if self.suc and self.sec and self.nro:
                cdc_suc = self.suc
                cdc_sec = self.sec
                if len(self.nro) < 7:
                    if len(self.nro) > 0:
                        numero_str = str(self.nro)
                        cdc_nro = numero_str.zfill(7)
                    else:
                        cdc_nro = self.nro
                else:
                    cdc_nro = self.nro
            else:
                if self.nro_factura:
                    try:
                        datos_factura = self.nro_factura.split('-')
                        cdc_suc = datos_factura[0]
                        cdc_sec = datos_factura[1]
                        cdc_nro = datos_factura[2]
                    except:
                        raise ValidationError('Favor completar nro. de factura y verificar que tenga los ceros necesarios')
            if self.env.company.partner_id.company_type == 'person':
                tipo_contribuyente=1
            else:
                tipo_contribuyente = 2
            cdc_tc=str(tipo_contribuyente)
            cdc_fecha=str(self.invoice_date)
            cdc_fecha=cdc_fecha.replace('-','')
            cdc_te=str(1)
            cdc_cs=str(random.randrange(0,999999999))
            if len(cdc_cs) < 9:
                for i in range (len(cdc_cs),9):
                    cdc_cs='0'+cdc_cs
            concatenar=cdc_fe+cdc_ruc+cdc_dv+cdc_suc+cdc_sec+cdc_nro+cdc_tc+cdc_fecha+cdc_te+cdc_cs
            print(concatenar)
            try:
                valor = self.calcular_dv(concatenar)

                cdc=concatenar+str(valor)
                if self.cdc:
                    cdc_ant = self.cdc[:-10]
                    cdc_nuevo = cdc[:-10]
                    if cdc_ant != cdc_nuevo:
                        self.cdc=cdc
                else:
                    self.cdc=cdc
            except:
                self.cdc='NOTVALID'

    def datos_del_timbrado(self):
        """
        Esta funcion pertenece al apartado C. Campos de datos del Timbrado del Manual Tecnico de ekuatia
        Donde se integra todos los campos para dicho apartado
        :return: un diccionario con todos los campos seteados con su nombre y dato segun el apartado
        """
        gTimb=collections.OrderedDict()
        if self.talonario_factura:
            value=[(1, 'Factura electrónica'),(2, 'Factura electrónica de exportación'),
                   (3, 'Factura electrónica de importación'),(4, 'Autofactura electrónica'),
                   (5, 'Nota de crédito electrónica'),(6, 'Nota de débito electrónica'),
                   (7, 'Nota de remisión electrónica'),(8, 'Comprobante de retención electrónico')
                   ]
            if not self.talonario_factura.timbrado_electronico:
                raise ValidationError( 'El Talonario/Timbrado nro %s de la Factura no posee el campo Tipo de Documento Electronico. Favor agregarle' % self.talonario_factura.name)
            timbrado_electronico = int(self.talonario_factura.timbrado_electronico)
            tipo=dict(value)[timbrado_electronico]


            if (self.move_type in ('in_invoice') and self.talonario_factura.timbrado_electronico != '4') :
                raise ValidationError('Es una factura de proveedor no se puede enviar')

            val_iTiDE=str(self.talonario_factura.timbrado_electronico)
            gTimb.setdefault('iTiDE',val_iTiDE)
            gTimb.setdefault('dNumTim', str(self.talonario_factura.name))


            gTimb.setdefault('dDesTiDE',str(tipo))
            gTimb.setdefault('dEst',str(self.suc))
            gTimb.setdefault('dPunExp',str(self.sec))
            gTimb.setdefault('dNumDoc',str(self.nro))
            gTimb.setdefault('dFeIniT',str(self.talonario_factura.fecha_inicio))

            return gTimb
        else:
            raise ValidationError('El DE %s no tiene asociado un talonario favor verificar' %self.nro_factura)

    def campos_generales_DE(self):
        """
        Esta funcion pertenece al apartado D. Campos Generales del Documento Electronico DE  del Manual Tecnico de ekuatia
        En este apartado se encuentra los principales datos de la factura como sus lineas y datos del partner, etc
        :return: un diccionario con todos los campos seteados con su nombre y dato segun el apartado
        """
        gDatGralOpe=collections.OrderedDict()
        #     SE ESTABLECE EL FORMATO DE FECHA
        fecha=self.invoice_date
        fecha=datetime.strptime(fecha.strftime('%Y-%m-%d %H:%M:%S'),'%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%dT%H:%M:%S")
        gDatGralOpe.setdefault('dFeEmiDE',fecha)

        # VARIABLE TEMPORAL PARA UNA VALIDACION CORRECTA CUANDO EL CODIGO SE ENCUENTRE COMPLETO Y BIEN ESTRUCTURADO
        c002=self.talonario_factura.timbrado_electronico

        if c002!='7':
            gOpeCom=collections.OrderedDict()

            # VARIABLE TEMPORAL PARA UNA VALIDACION CORRECTA CUANDO EL CODIGO SE ENCUENTRE COMPLETO Y BIEN ESTRUCTURADO
            c002_1=self.talonario_factura.timbrado_electronico
            tipo_impuesto = int(self.tipo_impuesto)
            value_1 = [(1, 'IVA'), (2, 'ISC'), (3, 'Renta'), (4, 'Ninguno'), (5, 'IVA - Renta')]
            if not self.tipo_impuesto:
                raise ValidationError('El DE %s no posee el campo Tipo de Impuesto. Favor agregarle' %self.nro_factura)
            gOpeCom.setdefault('iTImp', tipo_impuesto)
            tipo_1 = dict(value_1)[tipo_impuesto]
            gOpeCom.setdefault('dDesTImp', tipo_1)
            moneda = self.currency_id.name
            if moneda.find('-') > 0:
                moneda = moneda[0:moneda.find('-')]
            gOpeCom.setdefault('cMoneOpe', moneda)
            gOpeCom.setdefault('dDesMoneOpe', self.currency_id.currency_unit_label)
            if moneda != 'PYG':
                # Condicion del Tipo de Cambio
                # 1 global
                # 2 por item
                gOpeCom.setdefault('dCondTiCam', '1')
                rate = self.env['res.currency.rate'].search(
                    [('currency_id', '=', self.currency_id.id), ('name', '=', str(self.date))])
                # La siguient linea es obligatoria si dCondTiCam es igual a 1, para nuestro creo que siempre va a ser 1
                gOpeCom.setdefault('dTiCam', rate.set_venta)

            if c002 == '1' or c002 == '4':
                value=[( 1 , 'Venta de mercadería'),(2 , 'Prestación de servicios'),
                       (3 , 'Mixto'),(4 , 'Venta de activo fijo'),(5 , 'Venta de divisas'),
                       (6 , 'Compra de divisas'),(7 , 'Promoción o entrega de muestras'),
                       (8 , 'Donación'),(9 , 'Anticipo'),(10 , 'Compra de productos'),
                       (11 , 'Compra de servicios'),(12 , 'Venta de crédito fiscal'),
                       (13 , 'Muestras médicas')
                       ]
                if self.tipo_transaccion:
                    gOpeCom.setdefault('iTipTra',int(self.tipo_transaccion))
                else:
                    raise ValidationError('El DE %s no posee el campo Tipo de Transaccion. Favor agregarle' %self.nro_factura)
                tipo = dict(value)[int(self.tipo_transaccion)]
                gOpeCom.setdefault('dDesTipTra',tipo)









        # Final del apartado D1 se agrega el diccionario generado al diccionario padre
        gDatGralOpe.setdefault('gOpeCom',gOpeCom)

        #APARTADO D2
        gEmis=collections.OrderedDict()
        ruc=self.company_id.ruc
        gEmis.setdefault('dRucEm',ruc)
        dv=self.partner_id.obtener_dv(ruc)
        gEmis.setdefault('dDVEmi',dv)
        if self.env.company.partner_id.company_type == 'person':
            tipo_contribuyente=1
        else:
            tipo_contribuyente = 2
        gEmis.setdefault('iTipCont',tipo_contribuyente)
        if not self.company_id.regimen:
            raise ValidationError('Favor agregar tipo de regimen en la ficha de la compañia')
        gEmis.setdefault('cTipReg',self.company_id.regimen)
        if self.env.company.servidor == 'prueba':
            nombre_prueba="DE generado en ambiente de prueba - sin valor comercial ni fiscal"
            gEmis.setdefault('dNomEmi', nombre_prueba)
        else:
            gEmis.setdefault('dNomEmi',str(self.company_id.name))
            if self.company_id.partner_id.nombre_fantasia:
                gEmis.setdefault('dNomEmi',str(self.company_id.partner_id.nombre_fantasia))


        gEmis.setdefault('dDirEmi',str(self.company_id.street))
        if self.company_id.nro_casa:
            gEmis.setdefault('dNumCas',str(self.company_id.nro_casa))
        else:
            gEmis.setdefault('dNumCas', str(0))
        if self.company_id.street2:
            gEmis.setdefault('dCompDir2',str(self.company_id.street2))

        #         Aqui va los datos del departamento por ahora se setea asuncion de forma estatica
        # TODO hay que enlazar luego con la ciudad de
        gEmis=self.setear_ciudad_emisor(gEmis)
        # if self.company_id.city=='Pirapo':
        #     gEmis.setdefault('cDepEmi', 8)
        #     gEmis.setdefault('dDesDepEmi', 'ITAPUA')
        #     gEmis.setdefault('cDisEmi', 221)
        #     gEmis.setdefault('dDesDisEmi', 'PIRAPO')
        #     gEmis.setdefault('cCiuEmi', 5698)
        #     gEmis.setdefault('dDesCiuEmi', 'PIRAPO')
        #
        # else:
        # gEmis.setdefault('cDepEmi',1)
        # gEmis.setdefault('dDesDepEmi','CAPITAL')
        # gEmis.setdefault('cDisEmi','ASUNCION (DISTRITO)')
        # gEmis.setdefault('dDesDisEmi','1')
        # gEmis.setdefault('cCiuEmi',1)
        # gEmis.setdefault('dDesCiuEmi','ASUNCION (DISTRITO)')
        #         FIN
        if not self.company_id.phone:
            raise ValidationError('Favor agregue numero de telefono a la compañia')
        gEmis.setdefault('dTelEmi',str(self.company_id.phone))
        if not self.company_id.email:
            raise ValidationError('Favor agregue cuenta de email a la compañia')
        gEmis.setdefault('dEmailE',str(self.company_id.email))

        # gEmis.setdefault('dDenSuc', ) no es obligatorio pero averiguar que es


        #         APARTADO D2.1
        gActEco=collections.OrderedDict()
        if self.talonario_factura.codigo_actividad and self.talonario_factura.actividad_economica:
            gActEco.setdefault('cActEco',str(self.talonario_factura.codigo_actividad))
            gActEco.setdefault('dDesActEco',str(self.talonario_factura.actividad_economica))
        else:
            if not self.company_id.actividad_economica:
                raise ValidationError('En la ficha de la Compañia no se encuentra cargado el campo Codigo de Actividad')
            gActEco.setdefault('cActEco',str(self.company_id.codigo_actividad))
            if not self.company_id.codigo_actividad:
                raise ValidationError('En la ficha de la Compañia no se encuentra cargado el campo Actividad Economica')
            gActEco.setdefault('dDesActEco',str(self.company_id.actividad_economica))

        # Final del apartado D2.1 se agrega el diccionario generado al diccionario padre
        gEmis.setdefault('gActEco',gActEco)

        # Final del apartado D2 se agrega el diccionario generado al diccionario padre
        gDatGralOpe.setdefault('gEmis',gEmis)


        #         APARTADO D3
        gDatRec=collections.OrderedDict()
        if c002 == '4':
            partner_id=self.env.company.partner_id
        else:
            partner_id=self.partner_id
        if not self.partner_id.naturaleza_receptor:
            raise ValidationError('Favor agregar Naturaleza Receptor en la ficha de la empresa en la pestaña Documentos Electronicos a %s' %partner_id.name)
        gDatRec.setdefault('iNatRec',str(int(self.partner_id.naturaleza_receptor)))

        if not partner_id.tipo_operacion:
            raise ValidationError('En la ficha de %s no se encuentra cargado el campo Tipo de Operacion. Ver el apartado de Documentos Electronicos' %partner_id.name)
        gDatRec.setdefault('iTiOpe',str(partner_id.tipo_operacion))
        if partner_id.country_id:
            if partner_id.country_id.codigo_set:
                gDatRec.setdefault('cPaisRec',str(partner_id.country_id.codigo_set))
            else:
                raise ValidationError('No se encontro el codigo del Pais %s, favor agregar. Para eso vaya al modulo de '
                                      'Contactos y dentro de uno de sus menus debe estar Paises, si no le muestra contacte con el Administrador' %self.partner_id.country_id.name)
        else:
            raise ValidationError('El cliente no tiene asignado a que País corresponde, Favor agregarle en la ficha del Cliente %s' % self.partner_id.name)
        # gDatRec.setdefault('cPaisRec',str(self.partner_id.country_id.currency_id.name))#SE CAMBIA DEBIDO AL FORMATO ESTABLECIDO POR LA ISO 4217
        # gDatRec.setdefault('cPaisRec',str('PRY'))
        gDatRec.setdefault('dDesPaisRe',str(partner_id.country_id.name))
        # if not self.naturaleza_receptor_DE:
        #     raise ValidationError('La empresa %s no tiene el campo Naturaleza del receptor favor agregarle' %self.)

        naturaleza_receptor_DE = int(self.partner_id.naturaleza_receptor)
        if naturaleza_receptor_DE==1:

            if partner_id.company_type == 'person':
                gDatRec.setdefault('iTiContRec',1)
            else:
                gDatRec.setdefault('iTiContRec',2)
            if not partner_id.rucdv:
                if partner_id.parent_id:
                    if not partner_id.parent_id.rucdv:
                        raise ValidationError('El contacto %s no se econtro con el ruc '%partner_id.parent_id.name)
                    ruc_fact = partner_id.parent_id.rucdv
                else:
                    if not partner_id.rucdv:
                        raise ValidationError('El contacto %s no se econtro con el ruc ' % partner_id.name)

            else:
                ruc_fact=partner_id.rucdv

            ruc_fact = ruc_fact[0:ruc_fact.find('-')]

            gDatRec.setdefault('dRucRec',ruc_fact)
            dv_fact = self.partner_id.obtener_dv(ruc_fact)
            gDatRec.setdefault('dDVRec', dv_fact)

        # D208 Y D209 210 VER DESPUES COMO HACER
        else:
            if naturaleza_receptor_DE==2 :
                value_tipo_doc=[(1,'Cédula paraguaya'),(2,'Pasaporte'),(3,'Cédula extranjera'),(4,'Carnet de residencia'),(5,'Innominado'),(6,'Tarjeta Diplomática de exoneración fiscal'),(9,'Otro')]
                tipo_tipo_doc = dict(value_tipo_doc)[int(partner_id.tipo_documento_receptor)]
                gDatRec.setdefault('iTipIDRec', int(partner_id.tipo_documento_receptor))
                gDatRec.setdefault('dDTipIDRec', tipo_tipo_doc)
                gDatRec.setdefault('dNumIDRec', partner_id.nro_documento or partner_id.digitointer  or partner_id.ci  or partner_id.rucdv )


        # if  self.partner_id.property_account_position_id and self.partner_id.tipo_operacion != 4:
        #     if not self.partner_id.ruc and self.partner_id.ci:
        #         gDatRec.setdefault('iTipIDRec',1)
        nombre=partner_id.name

        if partner_id.parent_id:
            nombre=partner_id.parent_id.name
        truestr = nombre.strip()
        # truestr = nombre
        truestr=truestr.replace("'"," ")
        # truestr=truestr.replace("ñ","n")
        # truestr=truestr.replace("Ñ","N")
        # namesio=truestr
        nombre=truestr
        # namesio=truestr.encode(encoding='ASCII', errors='strict')
        if self.partner_id.naturaleza_receptor == '1':
            gDatRec.setdefault('dNomRec',nombre)
        elif self.partner_id.naturaleza_receptor == '2':
            if self.partner_id.tipo_documento_receptor == '9':
               gDatRec.setdefault('dNomRec', 'Sin Nombre')
            else:
                gDatRec.setdefault('dNomRec', nombre)
        if self.partner_id.tipo_operacion=='4':
            if partner_id.street:
                gDatRec.setdefault('dDirRec', partner_id.street or ' Exterior')
            else:
                raise ValidationError('Favor completar la direccion de %s' % partner_id.name)
            if partner_id.nro_casa:
                gDatRec.setdefault('dNumCasRec', partner_id.nro_casa or ' 000')
            else:
                raise ValidationError('Favor completar el campo Numero de Casa de %s' % partner_id.name)
        else:
            gDatRec.setdefault('dDirRec', partner_id.street or None)
            gDatRec.setdefault('dNumCasRec', partner_id.nro_casa or None)

        #         FALTA D203 D218
        #CAMPOS UTILIZADAS PARA NOTA DE REMISION
#         if self.partner_id.nro_casa:
#             gDatRec.setdefault('dNumCasRec',str(self.partner_id.nro_casa))
#         else:
#             gDatRec.setdefault('dNumCasRec',0)
#         if self.partner_id.tipo_operacion != 4:
#             AQUI DEBE IR LOS DATOS DEL DEPARTAMENTO DEL CLIENTE
#             gDatRec.setdefault('cDepRec',1)
#             gDatRec.setdefault('dDesDepRec','CAPITAL')
#             gDatRec.setdefault('cDisRec',1)
#             gDatRec.setdefault('dDesDisRec','ASUNCION (DISTRITO)')
#             gDatRec.setdefault('cCiuRec',1)
#             gDatRec.setdefault('dDesCiuRec','ASUNCION (DISTRITO)')
#         CAMPOS NO OBLIGATORIOS SE COMENTA MIENTRAS
#         if self.partner_id.country_id.code == 'PYG' or self.partner_id.country_id.code == 'PRY':
#             gDatRec.setdefault('dTelRec',self.partner_id.phone)
#             gDatRec.setdefault('dCelRec',self.partner_id.phone)
#             gDatRec.setdefault('dEmailRec',self.partner_id.phone)
#             gDatRec.setdefault('dCodClientegOpeCom',self.partner_id.phone)

        # Final del apartado D3 se agrega el diccionario generado al diccionario padre
        gDatGralOpe.setdefault('gDatRec',gDatRec)

        return gDatGralOpe

    def campos_especificos_DE(self,rate=0):
        """
            Esta funcion pertenece a los apartados
             E. Campos específicos por tipo de Documento Electrónico,
             F. Campos que describen los subtotales y totales de la transacción documentada
              Donde se integra todos los campos para los apartados
            :return: un diccionario con todos los campos seteados con su nombre y dato segun el apartado
        """
        c002=self.talonario_factura.timbrado_electronico
        gDtipDE = collections.OrderedDict()
        if  c002== '1':
            gCamFE=collections.OrderedDict()
            if not self.indicador_presencia:
                raise ValidationError('Favor agregar indicador de presencia, que se encuentra en la pestaña de Documento Electronico de la Facturas %s ' %self.nro_factura)
            gCamFE.setdefault('iIndPres',self.indicador_presencia)
            value=[(1 , 'Operación presencial'),
                   (2 , 'Operación electrónica'),
                   (3 , 'Operación telemarketing'),
                   (4 , 'Venta a domicilio '),
                   (5 , 'Operación bancaria'),
                   (6 , 'Operación cíclica'),
                   (9 , 'Otro')]
            if self.indicador_presencia != '9':
                tipo = dict(value)[int(self.indicador_presencia)]
                gCamFE.setdefault('dDesIndPres', tipo)
            else:
                gCamFE.setdefault('dDesIndPres',self.descripcion_indi_presencia)

            #         dFecEmNR CAMPO OPCIONAL VER SI AGREGAR DESPUES
            # Final del apartado E1 se agrega el diccionario generado al diccionario padre
            gDtipDE.setdefault('gCamFE',gCamFE)
            # print(gDtipDE)

        #E1.1.Campos de informaciones  de Compras Públicas(E020 - E029)
        #En caso que la factura sea para el gobierno pide datos de la licitacion ganada se omite para mas adelante
        # if self.partner_id.parent_id:
        #     if self.partner_id.parent_id.tipo_operacion == 3:

        # gCompPub=collections.OrderedDict()

        # E4.Campos  que componen la Autofactura Electrónica AFE(E300 - E399)
        if c002 == '4':
            if not self.autofactura_partner_id:
                raise ValidationError('El DE %s no posee datos del Vendedor Autofactura. Favor agregarle' %self.nro_factura)
            gCamAE=collections.OrderedDict()

            if not self.autofactura_partner_id.naturaleza_vendedor:
                raise ValidationError('La empresa %s no tiene en su ficha el campo naturaleza de vendedor. Favor fijarse en la pestaña Documentos Electronicos' %self.autofactura_partner_id.name)
            value_vendedor = [(1, 'No contribuyente'), (2, 'Extranjero')]
            tipo_vendedor = dict(value_vendedor)[int(self.autofactura_partner_id.naturaleza_vendedor)]
            gCamAE.setdefault('iNatVen', str(self.autofactura_partner_id.naturaleza_vendedor))
            gCamAE.setdefault('dDesNatVen', tipo_vendedor)
            if not self.autofactura_partner_id.tipo_documento_vendedor:
                raise ValidationError('La empresa %s no tiene en su ficha el campo tipo de documento de vendedor. Favor fijarse en la pestaña Documentos Electronicos' % self.autofactura_partner_id.name)
            value_tipo_doc_vend=[(1,'Cédula paraguaya'),(2,'Pasaporte'),(3,'Cédula extranjera'),(4,'Carnet de residencia')]
            tipo_tipo_doc_vend=dict(value_tipo_doc_vend)[int(self.autofactura_partner_id.tipo_documento_vendedor)]
            gCamAE.setdefault('iTipIDVen', str(self.autofactura_partner_id.tipo_documento_vendedor))
            gCamAE.setdefault('dDTipIDVen', tipo_tipo_doc_vend)

            if not self.autofactura_partner_id.nro_documento:
                raise ValidationError('La empresa %s no tiene en su ficha el campo numero de documento. Favor fijarse en la pestaña Documentos Electronicos' % self.autofactura_partner_id.name)
            gCamAE.setdefault('dNumIDVen', self.autofactura_partner_id.nro_documento)
            gCamAE.setdefault('dNomVen', self.autofactura_partner_id.name)
            if self.autofactura_partner_id.naturaleza_vendedor==2:
                calle=self.company_id.street
            else:
                if not self.autofactura_partner_id.street:
                    raise ValidationError('Favor agregue direccion a la empresa %s '%self.autofactura_partner_id.name)
                else:
                    calle=self.autofactura_partner_id.street
            gCamAE.setdefault('dDirVen', calle)
            gCamAE.setdefault('dNumCasVen', '0')

            gCamAE.setdefault('cDepVen', 1)
            gCamAE.setdefault('dDesDepVen', 'CAPITAL')
            gCamAE.setdefault('cCiuVen', 1)
            gCamAE.setdefault('dDesCiuVen', 'ASUNCION (DISTRITO)')

            gCamAE.setdefault('dDirProv', self.company_id.street)
            gCamAE.setdefault('cDepProv', 1)
            gCamAE.setdefault('dDesDepProv', 'CAPITAL')
            gCamAE.setdefault('cCiuProv', 1)
            gCamAE.setdefault('dDesCiuProv', 'ASUNCION (DISTRITO)')

            gDtipDE.setdefault('gCamAE',gCamAE)



        # E5.Campos que componen la Nota de Crédito / Débito Electrónica NCE - NDE(E400 - E499)

        if c002== '5' or  c002 == '6':
            gCamNCDE = collections.OrderedDict()
            gCamNCDE.setdefault('iMotEmi',self.motivo_emision_nc)
            valor =[(1, 'Devolución y Ajuste de precios'),
                                                  (2, 'Devolución'),
                                                  (3, 'Descuento'),
                                                  (4, 'Bonificación'),
                                                  (5, 'Crédito incobrable'),
                                                  (6, 'Recupero de costo'),
                                                  (7, 'Recupero de gasto'),
                                                  (8, 'Ajuste de precio')
                                                  ]
            tipo_1 = dict(valor)[int(self.motivo_emision_nc)]
            gCamNCDE.setdefault('dDesMotEmi', tipo_1)
            gDtipDE.setdefault('gCamNCDE', gCamNCDE)


        # E7.Campos que describen la condición de la operación(E600 - E699)

        if c002 == '1' or  c002 == '4':
            gCamCond=collections.OrderedDict()
            if not self.tipo_factura and c002 == '1' :
                raise ValidationError('Favor agregue si la factura es credito o contado')
            if not self.tipo_factura and c002 == '4' :
                self.tipo_factura='1'

            gCamCond.setdefault('iCondOpe',int(self.tipo_factura))
            valor_tipo_factura=[(1 , 'Contado'),
                    (2 , 'Crédito')]

            tipo_tipo_factura= dict(valor_tipo_factura)[int(self.tipo_factura)]
            gCamCond.setdefault('dDCondOpe',tipo_tipo_factura)

            # E7 .1.Campos que describen la forma de pago de la operación al contado o del monto de la entrega inicial(E605 -E619)
            #Descripcion:
            #            Para este apartado se almacena en una lista list_gPaConEIni donde estaran las distintas formas de pagos/cobros
            #            de factura
            list_gPaConEIni = []
            if self.tipo_factura == '1':
                if self.payment_state not in ['paid','partial','in_payment']:
                    raise ValidationError('EL DE numero %s es del tipo Contado, necesariamente debe estar completamente pagada. No debe tener saldo adeudado' % (self.nro_factura or ''))
                valor =[(1 , 'Efectivo'),
                        (2 , 'Cheque'),
                        (3 , 'Tarjeta de crédito'),
                        (4 , 'Tarjeta de débito'),
                        (5 , 'Transferencia'),
                        (6 , 'Giro'),
                        (7 , 'Billetera electrónica'),
                        (8 , 'Tarjeta empresarial'),
                        (9 , 'Vale'),
                        (10 , 'Retención'),
                        (11 , 'Pago por anticipo'),
                        (12 , 'Valor fiscal'),
                        (13 , 'Valor comercial'),
                        (14 , 'Compensación'),
                        (15 , 'Permuta'),
                        (16 , 'Pago bancario'),
                        (17 , 'Pago Móvil'),
                        (18 , 'Donación'),
                        (19 , 'Promoción'),
                        (20 , 'Consumo Interno'),
                        (21 , 'Pago Electrónico'),
                        (99 , 'Otro')]

                # lineas_pagos=self.payment_line_ids
                if self.move_type in ('out_invoice','out_refund'):

                    lineas_de_deuda=self.line_ids.filtered(lambda r: r.account_internal_type=='receivable')
                    if lineas_de_deuda:
                        for lineas_deuda in lineas_de_deuda:
                            lineas_pagos=lineas_deuda.matched_credit_ids.mapped('credit_move_id')

                elif self.move_type in ('in_invoice','in_refund'):
                    lineas_de_deuda = self.line_ids.filtered(lambda r: r.account_internal_type == 'payable')
                    if lineas_de_deuda:
                        for lineas_deuda in lineas_de_deuda:
                            lineas_pagos=lineas_deuda.matched_debit_ids.mapped('debit_move_id')

                for p in lineas_pagos:
                    gPaConEIni = collections.OrderedDict()
                    # se verifica que en el diario se encuentra el tipo de pago seteado
                    if not p.journal_id.tipo_pago:
                        raise ValidationError('El Diario %s no tiene Tipo de Pago, favor agregarle en el formulario del Diario' % p.journal_id.name)
                    gPaConEIni.setdefault('iTiPago',p.journal_id.tipo_pago)
                    tipo_2=dict(valor)[int(p.journal_id.tipo_pago)]

                    if p.journal_id.tipo_pago != '99':
                        gPaConEIni.setdefault('dDesTiPag', tipo_2)
                    else:
                        if p.payment_id.descripcion_tipo_pago:

                            gPaConEIni.setdefault('dDesTiPag', p.payment_id.descripcion_tipo_pago)
                        else:
                            gPaConEIni.setdefault('dDesTiPag', p.journal_id.descripcion_tipo_pago or 'No especificado')
                    gPaConEIni.setdefault('dMonTiPag', abs(p.balance))
                    # Como la moneda dolares en la localizacion es USD-COMPRA O USD-VENTA se excluye lo que esta despues del guion
                    # importante que la moneda con el nombre mencionado anteriormente
                    cotizacion=None
                    if p.currency_id and p.currency_id != self.env.company.currency_id:
                        if p.payment_id:
                            if p.payment_id.moneda_pago and p.payment_id.moneda_pago != p.payment_id.currency_id:
                                moneda_name=p.payment_id.moneda_pago.name
                                moneda=p.payment_id.moneda_pago
                                if p.payment_id.cotizacion and p.payment_id.cotizacion != 0:
                                    cotizacion=p.payment_id.cotizacion
                                elif p.payment_id.cotizacion==0:
                                    coti=self.env['res.currency.rate'].search([('name','=',p.date),('currency_id','=',p.currency_id.id)])
                                    cotizacion = coti.set_venta
                            else:
                                moneda_name=p.payment_id.currency_id.name
                                moneda=p.payment_id.currency_id
                                if p.payment_id.cotizacion and p.payment_id.cotizacion != 0:
                                    cotizacion=p.payment_id.cotizacion
                                elif p.payment_id.cotizacion==0:
                                    coti=self.env['res.currency.rate'].search([('name','=',p.date),('currency_id','=',p.currency_id.id)])
                                    cotizacion = coti.set_venta
                    else:
                        moneda_name = self.env.company.currency_id.name
                        moneda = self.env.company.currency_id
                    if moneda_name.find('-')>0:
                        gPaConEIni.setdefault('cMoneTiPag', moneda_name[:moneda_name.find('-')])
                    else:
                        gPaConEIni.setdefault('cMoneTiPag', moneda_name)
                    if not moneda.currency_unit_label:
                        raise ValidationError('La moneda de la forma de pago %s  no tiene Unidad de Divisa, favor agregarle en el formulario de la moneda para countinuar' %moneda.name)
                    if p.currency_id:
                        gPaConEIni.setdefault('dDMoneTiPag', p.currency_id.currency_unit_label)
                    else:
                        gPaConEIni.setdefault('dDMoneTiPag', self.env.company.currency_id.currency_unit_label)
                    if moneda != self.env.company.currency_id:

                        if not cotizacion or cotizacion ==0:
                            tasa=self.env['res.currency.rate'].search([('currency_id','=',moneda.id),('name','=',p.date),('company_id','=',self.env.company.id)])
                            cotizacion=tasa.set_venta
                        gPaConEIni.setdefault('dTiCamTiPag', cotizacion)
                    # E7.1.1. Campos que describen el pago o entrega inicial de la operación con tarjeta de crédito / débito
                    #si la forma de pago es tarjeta de credito o tarjeta de debito
                    if p.journal_id.tipo_pago == '3' or p.journal_id.tipo_pago == '4':
                        if not p.payment_id:
                            raise ValidationError('El diario %s  esta configurado como Tarjeta para eso debe definir que tipo de tarjeta es pero no tiene asociado un Pago, esta relacionado a un asiento. Para poder '
                                                  'avanzar podria favor cambie el tipo de pago del diario por otro o genere un pago y defina el tipo de tarjeta utilizado' %p.journal_id.name)
                        tipo_tarjeta=[  (1 , 'Visa'),
                                        (2 , 'Mastercard'),
                                        (3 , 'American Express'),
                                        (4 , 'Maestro'),
                                        (5 , 'Panal'),
                                        (6 , 'Cabal'),
                                        (99 , 'Otro')
                                      ]
                        tipo_3= dict(tipo_tarjeta)[int(p.payment_id.tipo_tarjeta)]
                        gPagTarCD=collections.OrderedDict()
                        gPagTarCD.setdefault('iDenTarj',p.payment_id.tipo_tarjeta)
                        if p.payment_id.tipo_tarjeta == '99':
                            gPagTarCD.setdefault('dDesDenTarj', p.payment_id.descripcion_tipo_tarjeta)
                        else:
                            gPagTarCD.setdefault('dDesDenTarj',tipo_3)
                        # La forma de procesamiento de pago por tarjeta se deja por el momento como 1: POS
                        gPagTarCD.setdefault('iForProPa','1')
                        #FIN APARTADO E7.1.1
                        gPaConEIni.setdefault('gPagTarCD',gPagTarCD)
                    # E7.1.2.Campos que describen el pago o entrega inicial de la operación con cheque(E630 - E639)
                    if p.journal_id.tipo_pago == '2':
                        if not p.payment_id:
                            raise ValidationError('El diario %s  esta configurado como Cheque para eso debe estar vinculado a un pago y no a un Asiento, favor verifique' % p.journal_id.name)
                        if p.payment_id.issued_check_ids or p.payment_id.received_third_check_ids:
                            cheques=p.payment_id.received_third_check_ids or p.payment_id.issued_check_ids
                            gPagCheq=collections.OrderedDict()
                            for cheque in cheques:
                                numero_cheque=cheque.name
                                if len(str(cheque.name))<8:
                                    for i in range(len(str(cheque.name)),8):
                                        numero_cheque='0'+numero_cheque

                                gPagCheq.setdefault('dNumCheq', numero_cheque)
                                if not cheque.bank_id:
                                    raise ValidationError('El cheque %s  no tiene el Banco favor agreguele para continuar' %cheque.name)
                                else:
                                    gPagCheq.setdefault('dBcoEmi', cheque.bank_id.name[:19])
                            gPaConEIni.setdefault('gPagCheq', gPagCheq)
                        else:
                            raise ValidationError('El diario de pago %s esta configurado como cheque pero no se encontro ningun cheque relacionado al pago. Favor verifique' %p.journal_id.name)
                            # FIN APARTADO E7.1.2

                    if gPaConEIni:
                        list_gPaConEIni.append(gPaConEIni)
            # FIN APARTADO E7.1
            if list_gPaConEIni:
                gCamCond.setdefault('gPaConEIni',list_gPaConEIni)
                gDtipDE.setdefault('gCamCond',gCamCond)



            # E7.2.Campos que describen la operación a crédito(E640 - E649)
            if self.tipo_factura == '2' and self.state == 'posted' :
                gPagCred=collections.OrderedDict()
                if not self.operacion_credito:
                    raise ValidationError('Favor agregue operacion de Credito que se encuentra en la pestaña de Documento Electronico de la Factura')
                gPagCred.setdefault('iCondCred',int(self.operacion_credito))
                valor_2=[(1, 'Plazo'),(2,'Cuota')]
                tipo_3 = dict(valor_2)[int(self.operacion_credito)]
                gPagCred.setdefault('dDCondCred',tipo_3)
                if self.operacion_credito =='1':
                    if self.invoice_payment_term_id:
                        if self.invoice_payment_term_id.line_ids:
                            dias=sum([i.days for i in self.invoice_payment_term_id.line_ids])
                            plazo=str(dias)+' dias'
                            gPagCred.setdefault('dPlazoCre',plazo)
                    else:
                        raise ValidationError('No tiene el plazo establecido para el DE nro %s favor fijarte en la seccion Otra infromacion para agregarle' %self.nro_factura)
                else:
                    gPagCred.setdefault('dCuotas',self.cantidad_cuotas)
                    #E7.2.1.Campos que describen las cuotas (E650-E659)
                    # gCuotas=collections.OrderedDict()
                    # gPagCred.setdefault('gCuotas',gCuotas)
#                 FALTA ESPECIFICAR EL APARTADO DE LAS CUOTAS
                #FIN APARTADO E7.2 Y E7
                gCamCond.setdefault('gPagCred',gPagCred)
                gDtipDE.setdefault('gCamCond', gCamCond)

        # E8. Campos que describen los ítems de la operación(E700 - E899)
        gCamItem=collections.OrderedDict()
        list_gCamItem=[]

        #util para el apartado F
        iva10 = self.env.ref('l10n_py.grupo_10')
        iva5 = self.env.ref('l10n_py.grupo_5')
        exentas = self.env.ref('l10n_py.grupo_exenta')

        sum_iva10=0
        sum_iva5=0
        sum_exento=0
        sum_exonerado=0
        sum_dIVA5 = 0
        sum_dIVA10 = 0
        sum_dBaseGrav5 = 0
        sum_dBaseGrav10 = 0
        sum_dTBasGraIVA = 0
        dTotDescGlotem = 0
        dTotAnt = 0
        dTotDesc = 0
        for lineas in self.invoice_line_ids.filtered(lambda r:r.display_type == False and r.tiene_descuento == False and  not r.tiene_anticipo):
            gCamItem=collections.OrderedDict()

            if not lineas.product_id.default_code:
                raise ValidationError('El producto %s no posee codigo interno, favor agregar para continuar ya que esto es un campo requerido. Del DE nro %s' %(lineas.product_id.name,lineas.invoice_id.nro_factura))
            dCodInt=lineas.product_id.default_code
            gCamItem.setdefault('dCodInt',dCodInt)
            lin_name=lineas.name[:120]
            characters = "\\n"
            dDesProSer=lin_name.replace(characters, " ")
            characters = "\n"
            dDesProSer=dDesProSer.replace(characters, " ")
            if not lineas.product_uom_id.codigo:
                raise ValidationError('La UDM %s no tiene codigo favor agregarle en base a la tabla 5 del documento tecnico' %lineas.product_uom_id.name)
            cUniMed=lineas.product_uom_id.codigo
            dDesUniMed=str(lineas.product_uom_id.sifen_name)
            gCamItem.setdefault('dDesProSer',dDesProSer)
            gCamItem.setdefault('cUniMed',cUniMed)
            gCamItem.setdefault('dDesUniMed',dDesUniMed)
            if lineas.quantity >0:
                dCantProSer=lineas.quantity
                # if int(lineas.quantity)-lineas.quantity > 0:
                #     dCantProSer=lineas.quantity
                # elif int(lineas.quantity)-lineas.quantity == 0:
                #     dCantProSer = int(lineas.quantity)
            else:
                raise ValidationError('La cantidad de un producto no es mayor a 0 favor verificar')
            gCamItem.setdefault('dCantProSer', dCantProSer)

            # E8.1.Campos que describen el precio, tipo de cambio y valor total de la operación por ítem(E720 - E729)
            gValorItem=collections.OrderedDict()
            if lineas.price_unit and lineas.price_unit > 0:
                if self.currency_id != self.env.company.currency_id:
                    gValorItem.setdefault('dPUniProSer', lineas.price_unit)
                else:
                    gValorItem.setdefault('dPUniProSer', lineas.price_unit)
            else:
                gValorItem.setdefault('dPUniProSer', 0)
            if self.get_linea_rastreo(lineas):
                gRasMerc = collections.OrderedDict()
                gRasMerc=self.set_grupo_rastreo(lineas,gRasMerc)
                gCamItem.setdefault('gRasMerc', gRasMerc)
            if lineas.price_total and lineas.price_total > 0:
                if int(lineas.price_total) - lineas.price_total != 0:
                    """
                    Función para verificar decimales a través de string. Con método float no realizaba en algunos casos el corte,
                    además no se requiere redondear debido a que afectará el valor total de la suma en la operación.
                    """
                    decimales = str(lineas.price_total)
                    if '.' in decimales:
                        valores_antes_coma = decimales.split('.')[0]
                        valores_despues_coma = decimales.split('.')[1]
                        valores_despues_coma = valores_despues_coma[:8]
                        valor_final = float(valores_antes_coma+'.'+valores_despues_coma)
                        gValorItem.setdefault('dTotBruOpeItem', valor_final)
                    else:
                        gValorItem.setdefault('dTotBruOpeItem', lineas.price_total)
                elif int(lineas.price_total) - lineas.price_total == 0:
                    gValorItem.setdefault('dTotBruOpeItem', int(lineas.price_total))
            else:
                gValorItem.setdefault('dTotBruOpeItem', 0)

            # gValorItem.setdefault('dTotBruOpeItem',lineas.price_total)

             #E8.1.1 Campos que describen los descuentos, anticipos y valor total por ítem(EA001 - EA050)
            gValorRestaItem=collections.OrderedDict()
            monto_descuento = 0
            if lineas.porcentaje_descuento !=0:
                monto_descuento=(lineas.price_unit*lineas.porcentaje_descuento)/100
                dTotDesc += monto_descuento
            gValorRestaItem.setdefault('dDescItem', monto_descuento)
            if monto_descuento != 0:
                gValorRestaItem.setdefault('dPorcDesIt', lineas.porcentaje_descuento)
            #Encontrar luego como aplicar los descuentos globales
            dDescGloItem=0
            dAntiGloItem = 0
            if self.tipo_descuento in ('descuento_a', 'descuento_b'):
                if self.porcentaje_descuento  > 0 and self.tipo_descuento=='descuento_a' :
                    dDescGloItem = (lineas.price_unit * self.porcentaje_descuento) / 100


                    dTotDescGlotem += (dDescGloItem * lineas.quantity)
                elif self.monto_descuento  > 0 and self.tipo_descuento=='descuento_b' :
                    descuento_item = self.monto_descuento / len(self.invoice_line_ids.filtered(lambda r: not r.tiene_descuento and not r.tiene_anticipo))

                    dDescGloItem = descuento_item / lineas.quantity
                    dTotDescGlotem += (dDescGloItem * lineas.quantity)
                if self.currency_id != self.env.company.currency_id:
                    dDescGloItem = round(dDescGloItem, 4)
                else:
                    dDescGloItem = round(dDescGloItem, 8)


            if lineas.monto_anticipo != 0:
                dAntiGloItem = lineas.monto_anticipo / lineas.quantity
                
                if self.currency_id != self.env.company.currency_id:
                    dAntiGloItem = round(dAntiGloItem, 4)
                else:
                    dAntiGloItem = round(dAntiGloItem, 8)
                dTotAnt += lineas.monto_anticipo
            gValorRestaItem.setdefault('dDescGloItem', dDescGloItem)
            dAntPreUniIt=0
            gValorRestaItem.setdefault('dAntPreUniIt', dAntPreUniIt)
            dAntGloPreUniIt=dAntiGloItem
            gValorRestaItem.setdefault('dAntGloPreUniIt', dAntGloPreUniIt)
            if self.talonario_factura.timbrado_electronico == '4':
                val_dTotOpeItem = lineas.price_unit * lineas.quantity
                if int(val_dTotOpeItem) - val_dTotOpeItem > 0:
                    dTotOpeItem = lineas.price_unit * lineas.quantity
                elif int(val_dTotOpeItem) - val_dTotOpeItem == 0:
                    dTotOpeItem =  int(lineas.price_unit * lineas.quantity)
                # dTotOpeItem = lineas.price_unit * lineas.quantity
            else:
                val_dTotOpeItem = (lineas.price_unit-monto_descuento-dDescGloItem-dAntPreUniIt-dAntGloPreUniIt)*lineas.quantity
                # raise ValidationError('val_dTotOpeItem:' + str(val_dTotOpeItem))
                if int(val_dTotOpeItem) - val_dTotOpeItem != 0:
                    if self.currency_id != self.env.company.currency_id:
                        dTotOpeItem = (lineas.price_unit - monto_descuento - dDescGloItem - dAntPreUniIt - dAntGloPreUniIt) * lineas.quantity

                    else:
                        
                        dTotOpeItem = (lineas.price_unit - monto_descuento - dDescGloItem - dAntPreUniIt - dAntGloPreUniIt) * lineas.quantity
                        if dDescGloItem ==0:
                            dTotOpeItem = round(float_round(dTotOpeItem, precision_rounding=1, rounding_method='HALF-UP'))
                        else:
                            dTotOpeItem =round(dTotOpeItem, 3)
                        # dTotOpeItem = int(dTotOpeItem)
                elif int(val_dTotOpeItem) - val_dTotOpeItem == 0:
                    dTotOpeItem = int((lineas.price_unit - monto_descuento - dDescGloItem - dAntPreUniIt - dAntGloPreUniIt) * lineas.quantity)

                # dTotOpeItem=(lineas.price_unit-monto_descuento-dDescGloItem-dAntPreUniIt-dAntGloPreUniIt)*lineas.quantity
            if dDescGloItem ==0:
                dTotOpeItem=redondear(dTotOpeItem)
            else:
                dTotOpeItem = round(dTotOpeItem,8)
            gValorRestaItem.setdefault('dTotOpeItem', dTotOpeItem)

            # if tasa_cambio !=0:
            #     gValorRestaItem.setdefault('dTotOpeGs', dTotOpeItem*tasa_cambio)

            gValorItem.setdefault('gValorRestaItem',gValorRestaItem)
            gCamItem.setdefault('gValorItem', gValorItem)
            list_gCamItem.append(gCamItem)
            # list_gCamItem.append(gCamItem)
            # E8.2.Campos que describen el IVA de la operación por ítem(E730 - E739)
            gCamIVA=collections.OrderedDict()
            if len(lineas.tax_ids) >1:
                raise ValidationError('Una de las lineas de la factura tiene mas de un impuesto favor verificar')
            elif not lineas.tax_ids:
                raise ValidationError('Una de la lineas de la factura no tiene impuesto favor verificar')

            try:
                forma_afectacion_DE = int(lineas.tax_ids[0].forma_afectacion)
            except:
                raise ValidationError('El impuesto %s no tiene cargado el campo forma de afectacion favor verificar' %str(lineas.tax_ids[0].name))

            #util para el apartado F
            if lineas.tax_ids[0].tax_group_id.id == iva10.id:

                sum_iva10+=lineas.price_total - monto_descuento - (dDescGloItem * lineas.quantity) - (dAntiGloItem * lineas.quantity)

            elif lineas.tax_ids[0].tax_group_id.id == iva5.id:
                sum_iva5+=lineas.price_total - monto_descuento -  (dDescGloItem * lineas.quantity) - (dAntiGloItem * lineas.quantity)
            else:
                if forma_afectacion_DE == 2:
                    sum_exonerado += lineas.price_total - monto_descuento - ( (dDescGloItem * lineas.quantity) - (dAntiGloItem * lineas.quantity))
                else:
                    sum_exento+=lineas.price_total - monto_descuento -  (dDescGloItem * lineas.quantity)  - (dAntiGloItem * lineas.quantity)



            valor_3=[(1, 'Gravado IVA'),
                    (2, 'Exonerado (Art. 100 - Ley 6380/2019)'),
                    (3, 'Exento'),
                    (4,' Gravado parcial (Grav-Exento)')
                    ]
            try:
                tipo_4 = dict(valor_3)[forma_afectacion_DE]
            except:
                raise ValidationError('El impuesto %s no tiene cargado el campo forma de afectacion favor verificar' %str(lineas.tax_ids[0].name))
            gCamIVA.setdefault('iAfecIVA', forma_afectacion_DE)
            gCamIVA.setdefault('dDesAfecIVA', tipo_4)
            # if cantidad_imp and len(cantidad_imp)>1 :
            #     dPropIVA=(1/len(cantidad_imp))*100
            # else:
            # Este es un campo que para B.C seria siempre 100 ver otros clientes su comportamiento
            dPropIVA = 100
            dBasExe = 0
            if forma_afectacion_DE==1:
             dPropIVA = 100
            elif forma_afectacion_DE==3:
                dPropIVA=0
            elif forma_afectacion_DE==2:
                dPropIVA=0
            elif forma_afectacion_DE==4:

               # 100 * EA008 * (100 – E733)] / [10000 + (E734 * E733)]
                val_dTasaIVA = int(lineas.invoice_line_tax_ids[0].amount)
                dPropIVA = val_dTasaIVA
               #TODO RECALCULAR CUANDO SE USE EL TIPO DE IVA GRAVADO PARCIAL
                dBasExe = (100 * dTotOpeItem (100 - dPropIVA)) / (10000+ (val_dTasaIVA * dPropIVA))


            gCamIVA.setdefault('dPropIVA',dPropIVA)
            gCamIVA.setdefault('dBasExe', dBasExe)


            if forma_afectacion_DE == 2 or forma_afectacion_DE == 3:
                gCamIVA.setdefault('dTasaIVA',0)
                gCamIVA.setdefault('dBasGravIVA',0)
                gCamIVA.setdefault('dLiqIVAItem',0)
                gCamIVA.setdefault('dBasExe', 0)
            else:
                # val_dTasaIVA = lineas.tax_ids[0].amount
                # if int(val_dTasaIVA) - val_dTasaIVA > 0:
                #     gCamIVA.setdefault('dTasaIVA', int(lineas.tax_ids[0].amount))
                # elif int(val_dTasaIVA) - val_dTasaIVA == 0:
                #     gCamIVA.setdefault('dTasaIVA', int(lineas.tax_ids[0].amount))
                val_dTasaIVA =int(lineas.tax_ids[0].amount)
                gCamIVA.setdefault('dTasaIVA', val_dTasaIVA)
                # _logger.info('linea impuesto %s' %val_dTasaIVA)
                # En el manual tecnico hace referencia a una formula para el calculo del campo dBasGravIVA
                val_dBasGravIVA=0



                if lineas.tax_ids[0].tax_group_id.id == iva10.id:
                    val_dBasGravIVA = (dTotOpeItem*(dPropIVA/100))/1.1
                    sum_dBaseGrav10 +=val_dBasGravIVA

                elif lineas.tax_ids[0].tax_group_id.id == iva5.id:
                    val_dBasGravIVA = (dTotOpeItem * (dPropIVA / 100)) / 1.05
                    sum_dBaseGrav5 += val_dBasGravIVA

                sum_dTBasGraIVA +=val_dBasGravIVA

                # En el manual tecnico hace referencia a una formula para el calculo del campo dLiqIVAItem
                val_dLiqIVAItem = (val_dBasGravIVA * (val_dTasaIVA / 100))
                if lineas.tax_ids[0].tax_group_id.id == iva10.id:
                    sum_dIVA10 += val_dLiqIVAItem
                elif lineas.tax_ids[0].tax_group_id.id == iva5.id:
                    sum_dIVA5 += round(val_dLiqIVAItem,2)

                # if val_dBasGravIVA !=0:
                #     val_dBasGravIVA = redondear(val_dBasGravIVA)
                #     val_dLiqIVAItem = redondear(val_dLiqIVAItem)

                # val_dBasGravIVA = lineas.price_subtotal

                # _logger.info(val_dBasGravIVA)
                # if int(val_dBasGravIVA) - val_dBasGravIVA > 0:
                #     gCamIVA.setdefault('dBasGravIVA', lineas.price_subtotal)
                # elif int(val_dBasGravIVA) - val_dBasGravIVA == 0:
                #     gCamIVA.setdefault('dBasGravIVA', int(val_dBasGravIVA))
                # _logger.info('dBasGravIVA %s' %str(redondear(val_dBasGravIVA)))
                redondeado_1=redondear(val_dBasGravIVA)
                redondeado_2=redondear(val_dLiqIVAItem)
                gCamIVA.setdefault('dBasGravIVA',redondeado_1)
                gCamIVA.setdefault('dLiqIVAItem',redondeado_2)

            gCamItem.setdefault('gCamIVA',gCamIVA)

        gDtipDE.setdefault('list_gCamItem',list_gCamItem)
        #FIN APARTADO E8.2

        # F. Campos que describen los subtotales y totales de la transacción documentada (F001-F099)
        gTotSub=collections.OrderedDict()
        gTotSub.setdefault('dSubExe',redondear(sum_exento))
        gTotSub.setdefault('dSubExo',redondear(sum_exonerado))
        sum_TtoSub=0
        if self.tipo_impuesto == '1':
            sum_iva5=redondear(sum_iva5)
            sum_iva10=redondear(sum_iva10)
            gTotSub.setdefault('dSub5',sum_iva5)
            gTotSub.setdefault('dSub10',sum_iva10)
            sum_TtoSub=sum_iva5+sum_iva10+sum_exento+sum_exonerado
        gTotSub.setdefault('dTotOpe',redondear(sum_TtoSub))
        # CAMPOS SETEADOS A CERO VERIFICAR DESPUES COMO PUEDE IR CAMBIANDO SU VALOR
        gTotSub.setdefault('dTotDesc',dTotDesc)
        if self.currency_id != self.env.company.currency_id:
            gTotSub.setdefault('dTotDescGlotem', round(dTotDescGlotem,4))
        else:
            gTotSub.setdefault('dTotDescGlotem', round(dTotDescGlotem))


        gTotSub.setdefault('dTotAntItem',0)
        gTotSub.setdefault('dTotAnt',round(dTotAnt,6))
        if self.tipo_descuento in ('descuento_a','descuento_b'):
            gTotSub.setdefault('dPorcDescTotal',self.porcentaje_descuento)
        else:
            gTotSub.setdefault('dPorcDescTotal', 0)
        if self.currency_id != self.env.company.currency_id:
            gTotSub.setdefault('dDescTotal',round(dTotDesc + dTotDescGlotem,4))
        else:
            gTotSub.setdefault('dDescTotal', round(dTotDesc + dTotDescGlotem))
        gTotSub.setdefault('dAnticipo',round(dTotAnt,6))
        gTotSub.setdefault('dRedon',0)
        monto_total=redondear(self.amount_total)
        gTotSub.setdefault('dTotGralOpe',str(monto_total))
        #ojo

        sum_dIVA10= redondear(sum_dIVA10)
        sum_dIVA5= redondear(sum_dIVA5)

        gTotSub.setdefault('dIVA5',str(sum_dIVA5))
        gTotSub.setdefault('dIVA10',str(sum_dIVA10))

        if self.tipo_impuesto != '1' or self.tipo_impuesto != '5':
            # if sum_iva5 >0:
            val_dLiqTotIVA5 = sum_iva5
            if val_dLiqTotIVA5 != sum_iva5:
                val_dLiqTotIVA5=round_down(sum_iva5,50)/1.05
                val_dLiqTotIVA5=val_dLiqTotIVA5/1.05
                val_dLiqTotIVA5 = redondear(val_dLiqTotIVA5)
                gTotSub.setdefault('dLiqTotIVA5',str(val_dLiqTotIVA5))
            else:
                gTotSub.setdefault('dLiqTotIVA5', str(0))
            # if sum_iva10 >0:
            # val_dLiqTotIVA10 = round_down(sum_iva10, 50)
            val_dLiqTotIVA10 = sum_iva10
            # _logger.info('sum_iva10 %s' %str(sum_iva10))
            # _logger.info('val_dLiqTotIVA10 %s' %str(val_dLiqTotIVA10))
            if val_dLiqTotIVA10 != sum_iva10:
                val_dLiqTotIVA10 = val_dLiqTotIVA10 / 1.1
                val_dLiqTotIVA10 = redondear(val_dLiqTotIVA10)
                gTotSub.setdefault('dLiqTotIVA10', str(val_dLiqTotIVA10))
            else:
                gTotSub.setdefault('dLiqTotIVA10', str(0))
                val_dLiqTotIVA10=0



            # val_dTotIVA=sum_dIVA5+sum_dIVA10-val_dLiqTotIVA5-val_dLiqTotIVA10
            val_dTotIVA=sum_dIVA5+sum_dIVA10
            # _logger.info('sum_dIVA5 %s' %str(sum_dIVA5))
            # _logger.info('sum_dIVA10 %s' %str(sum_dIVA10))
            # _logger.info('val_dLiqTotIVA5 %s' %str(val_dLiqTotIVA5))
            # _logger.info('val_dLiqTotIVA10 %s' %str(val_dLiqTotIVA10))

            val_dTotIVA = redondear(val_dTotIVA)
            gTotSub.setdefault('dTotIVA', str(val_dTotIVA))
        sum_dBaseGrav5 = redondear(sum_dBaseGrav5)
        gTotSub.setdefault('dBaseGrav5', str(sum_dBaseGrav5))
        sum_dBaseGrav10 = redondear(sum_dBaseGrav10)
        gTotSub.setdefault('dBaseGrav10', str(sum_dBaseGrav10))
        sum_dTBasGraIVA = redondear(sum_dTBasGraIVA)
        # En caso de moneda distinta a PYG se debe declarar el total en Gs.
        # CAMPO F023
        gTotSub.setdefault('dTBasGraIVA', str(sum_dTBasGraIVA))
        if self.currency_id.name != 'PYG':
            gTotSub.setdefault('dTotalGs', str(round((monto_total * rate))))
        gDtipDE.setdefault('gTotSub',gTotSub)

        return gDtipDE

    def identifican_documento_asociado(self):
        """
            Esta funcion pertenece al apartado
             H. Campos que identifican al documento asociado
        :return: dicionario con los campos necesarios seteados
        """


        gCamDEAsoc=collections.OrderedDict()
        gCamDEAsoc.setdefault('iTipDocAso',self.tipo_documento_asociado)
        valor=[(1 ,'Electrónico'),
               (2 ,'Impreso'),
                (3 ,'Constancia Electrónica')
                ]
        tipo = dict(valor)[int(self.tipo_documento_asociado)]
        gCamDEAsoc.setdefault('dDesTipDocAso', tipo)
        if self.tipo_documento_asociado == '1':
            gCamDEAsoc.setdefault('dCdCDERef', self.factura_afectada.cdc)
        if self.tipo_documento_asociado == '2':
            if not self.factura_afectada:
                raise ValidationError('Favor agregue factura afectada para DE numero %s' %self.nro_factura)
            if not self.factura_afectada.timbrado:
                raise ValidationError('La factura afectad %s no se encontro timbrado alguno, favor verifique' %self.nro_factura)
            gCamDEAsoc.setdefault('dNTimDI', self.factura_afectada.timbrado)
            gCamDEAsoc.setdefault('dEstDocAso', self.factura_afectada.suc)
            gCamDEAsoc.setdefault('dPExpDocAso', self.factura_afectada.sec)
            gCamDEAsoc.setdefault('dNumDocAso', self.factura_afectada.nro)
            gCamDEAsoc.setdefault('iTipoDocAso', '1')
            gCamDEAsoc.setdefault('dDTipoDocAso', 'Factura')
            gCamDEAsoc.setdefault('dFecEmiDI', str(self.factura_afectada.invoice_date))
        if self.tipo_documento_asociado == '3':
            if not self.tipo_constancia:
                raise ValidationError('Favor cargue el tipo de constancia al DE %s' %self.nro_factura)
            if not self.nro_constancia and self.tipo_constancia=='2':
                raise ValidationError('Favor cargue el nro de constancia al DE %s' %self.nro_factura)
            if not self.nro_control_constancia and self.tipo_constancia=='1':
                raise ValidationError('Favor cargue el nro de control de la constancia al DE %s' %self.nro_factura)

            value_constancia=[(1 ,'Constancia de no ser contribuyente'),
                              (2 ,'Constancia de microproductores')
                                ]
            tipo_constancia = dict(value_constancia)[int(self.tipo_constancia)]
            nro_control_constancia=''
            if self.nro_control_constancia:
                nro_control_constancia=self.nro_control_constancia
                gCamDEAsoc.setdefault('dNumControl', nro_control_constancia)
            nro_constancia=''
            if self.nro_constancia:
                nro_constancia=self.nro_constancia
                gCamDEAsoc.setdefault('dNumCons', nro_constancia)
            
            gCamDEAsoc.setdefault('iTipCons', self.tipo_constancia)
            gCamDEAsoc.setdefault('dDesTipCons', tipo_constancia)
            
            

        return gCamDEAsoc

    # termino_pago=fields.Integer(compute="_get_termino_pago")
    #
    # @api.depends
    # def _get_termino_pago(self):
    #     fecha_factura=int(self.invoice_date)
    #     fecha_vencimiento=int(self.date_due)
    #     return fecha_factura - fecha_vencimiento
    def setear_ciudad_emisor(self,gEmis):
        gEmis.setdefault('cDepEmi', 1)
        gEmis.setdefault('dDesDepEmi', 'CAPITAL')
        gEmis.setdefault('cDisEmi', 'ASUNCION (DISTRITO)')
        gEmis.setdefault('dDesDisEmi', '1')
        gEmis.setdefault('cCiuEmi', 1)
        gEmis.setdefault('dDesCiuEmi', 'ASUNCION (DISTRITO)')
        return gEmis

    def get_linea_rastreo(self,lineas):
        if lineas.nro_lote_fe or lineas.fecha_vencimiento_fe or lineas.nro_serie_fe or lineas.nro_pedido_fe or lineas.nro_seguimiento_fe or lineas.nombre_importador_fe or  lineas.direccion_importador_fe or lineas.nro_registro_imp_fe or lineas.nro_registro_senave_producto or lineas.nro_registro_senave_entidad_comercial:
            return True
        else:
            return False

    def set_grupo_rastreo(self,lineas,gRasMerc):
        num_lote=lineas.nro_lote_fe
        fecha_vencimiento_fe=lineas.fecha_vencimiento_fe
        nro_serie_fe=lineas.nro_serie_fe
        nro_pedido_fe=lineas.nro_pedido_fe
        nro_seguimiento_fe=lineas.nro_seguimiento_fe
        nombre_importador_fe=lineas.nombre_importador_fe
        direccion_importador_fe=lineas.direccion_importador_fe
        nro_registro_imp_fe=lineas.nro_registro_imp_fe
        nro_registro_senave_producto=lineas.nro_registro_senave_producto
        nro_registro_senave_entidad_comercial=lineas.nro_registro_senave_entidad_comercial
        nombre_producto=lineas.product_id.name[:29]
        gRasMerc.setdefault('dNumLote', num_lote)
        gRasMerc.setdefault('dNomPro', nombre_producto)
        gRasMerc.setdefault('dVencMerc', fecha_vencimiento_fe)
        gRasMerc.setdefault('dNSerie', nro_serie_fe)
        gRasMerc.setdefault('dNumPedi', nro_pedido_fe)
        gRasMerc.setdefault('dNumSegui', nro_seguimiento_fe)
        gRasMerc.setdefault('dNomImp', nombre_importador_fe)
        gRasMerc.setdefault('dDirImp', direccion_importador_fe)
        gRasMerc.setdefault('dNumFir', nro_registro_imp_fe)
        gRasMerc.setdefault('dNumReg', nro_registro_senave_producto)
        gRasMerc.setdefault('dNumRegEntCom', nro_registro_senave_entidad_comercial)
        return gRasMerc


    def _get_fecha(self):
        hora=fields.Datetime.now()
        return (hora)

    def get_invoice_data(self):
        invoice = self
        datos = list()
        dato_final= 'None'
        for orden in invoice:
            datos.append(orden.nro_factura)
            datos.append(orden.talonario_factura.name)
            datos.append(orden.talonario_factura.fecha_inicio)
            datos.append(orden.talonario_factura.fecha_final)
            dato_final=orden.talonario_factura.name

        return datos


    def sacacoma(self, n):
        return int(n)

    
    def tipofactura(self,n):
        if(n == '2'):
            return 'Credito'
        elif(n == '1'):
            return 'Contado'

    def verificar_nombre_moneda(self,moneda):
        if moneda.find('-') > 0:
            moneda = moneda[0:moneda.find('-')]
        return moneda

    def formatear_fecha(self,fecha):
        fecha = datetime.strptime(fecha.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S').strftime(
            "%d-%m-%YT%H:%M:%S")
        return fecha

    
    def calcular_letras(self, numero):
        # letras = self.monto_en_letras = num2words(numero, lang='es').upper()
        letras = num2words(numero, lang='es').upper()
        letras = '--'+'GUARANIES ' + letras + '--'
        return letras

    
    def calcular_letras_dolar(self, numero):
        # numero_redondeado = round(numero,2)
        nuevo_numero = str(numero).split('.')
        literal = str(nuevo_numero[1])
        nuevo_literal = literal[:2]
        entero= num2words(int(nuevo_numero[0]), lang='es').upper()
        # if len(nuevo_numero[1] == 1):
        if len(nuevo_numero[1]) == 1:
            if nuevo_numero[1] == '0':
                decimal = num2words(int(nuevo_numero[1]), lang='es').upper()
            else:
                decimal = num2words(int(nuevo_numero[1]+'0'), lang='es').upper()
        else:
            decimal=num2words(int(nuevo_literal), lang='es').upper()
        letras= entero + ' DOLARES ' + ' CON ' + decimal + ' CENTAVOS '
        return letras

    def generate_qr_code(self):
        qr= qrcode.QRCode(
            version =1,
            error_correction =qrcode.constants.ERROR_CORRECT_L,
            box_size = 10,
            border = 4,
        )
        # if self.texto_qr:
        #     qr.add_data(self.texto_qr)
        # else:
        #     qr.add_data('qr code')
        qr.add_data(self.texto_qr)
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp,format="PNG")
        qr_image = base64.b64encode(temp.getvalue())

        self.write({
            'qr_code': qr_image
        })
        # self.qr_code = qr_image

    
    # def agregar_punto_de_miles(self, numero):
    #     numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
    #     return numero_con_punto

    def agregar_punto_de_miles(self, numero,moneda='PYG'):
        entero = int(numero)
        if 'USD' in moneda:
            # el format redondea el valor y para el caso de valor en dolares no debe hacer eso por lo que se pasa comentar eso
            #decimal = '{0:.2f}'.format(numero-entero)
            decimal = str(numero-entero)
            entero_string = '.'.join([str(int(entero))[::-1][i:i +3] for i in range(0, len(str(int(entero))), 3)])[::-1]
            #if decimal == '0.00':
            #numero_con_punto = entero_string + ',00'
            #else:
            decimal_string = str(decimal).split('.')
            if decimal_string and len(decimal_string[1]) > 2:
                numero_con_punto = entero_string + ',' + decimal_string[1][:2]
            else:
                numero_con_punto = entero_string+','+ decimal_string[1]
        else:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i+3] for i in range(0, len(str(int(entero))), 3)])[::-1]
        num_return = numero_con_punto
        return num_return

    # 
    # def action_invoice_cancel(self):
    #     if self.cdc:
    #         self.cdc=None
    #     return super(InvoiceFactElect, self).action_cancel()
    def set_discount_lines(self):
        for rec in self:
            if rec.producto_descuento and rec.aplicar_descuento:
                for lines in rec.invoice_line_ids.filtered(lambda r: not r.tiene_anticipo and not r.tiene_descuento and r.product_id ==rec.producto_descuento):
                    if rec.tipo_descuento in ('descuento_a','descuento_b'):
                        super(models.Model, lines).write({'tiene_descuento': True})
                    elif rec.tipo_descuento in ('anticipo_a','anticipo_b'):
                        super(models.Model, lines).write({'tiene_anticipo': True})
    def action_post(self):

        res=super(InvoiceFactElect, self).action_post()
        if self.move_type in ('out_invoice','out_refund'):
            if self.estado_de not in ('aprobado','cancelado'):
                self.set_discount_lines()
                self.generar_codigo_control()
                self.generate_qr_code()
        return res
    def calcula_moneda(self, moneda):
        if 'USD' in moneda:
            return '$'
        elif 'PYG' in moneda:
            return 'Gs.'
        
    def redondeo_por_tres_cifras(self, numero, ajuste, moneda):
        print(type(numero))
        if type(numero) is float:
            nuevo_numero = str(numero).split('.')
            decimal1 = 0
            decimal2 = 0
            decimal3 = 0
            if nuevo_numero[1][:1]:
                decimal1 = int(nuevo_numero[1][:1])
            if nuevo_numero[1][1:2]:
                decimal2 = int(nuevo_numero[1][1:2])
            if nuevo_numero[1][2:3]:
                decimal3 = int(nuevo_numero[1][2:3])
            numero = int(numero)
            if 'PYG' in moneda:
                if decimal3 >= ajuste and (decimal2 + 1) >= ajuste and (decimal1 + 1) >= ajuste:
                    numero += 1
                    flotante = float(numero)
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) >= ajuste and (decimal1 + 1) < ajuste:
                    decimal1 += 1
                    letter_decimal = str(decimal1) + '0'
                    flotante = float(str(numero) + '.' + letter_decimal)
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) <= ajuste:
                    decimal2 += 1
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    return flotante
                elif decimal3 < ajuste and decimal2 < ajuste and decimal1 < ajuste:
                    if decimal2 != 0 or decimal1 != 0:
                        letter_decimal = str(decimal1) + str(decimal2)
                        flotante = float(str(numero) + '.' + letter_decimal)
                        return flotante
                    elif decimal2 == 0 and decimal1 == 0:
                        flotante = float(numero)
                        return flotante
                elif decimal3 < ajuste and decimal2 >= ajuste and (decimal1 + 1) < ajuste:
                    decimal1 += 1
                    letter_decimal = str(decimal1) + '0'
                    flotante = float(str(numero) + '.' + letter_decimal)
                    return flotante
                elif decimal3 < ajuste and decimal2 < ajuste and decimal1 >= ajuste:
                    numero += 1
                    flotante = float(numero)
                    return flotante
            else:
                print(numero)
                if decimal3 >= ajuste and (decimal2 + 1) >= ajuste and (decimal1 + 1) == 10:
                    numero += 1
                    flotante = float(numero)
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) >= ajuste and (decimal1 + 1) < 10:
                    decimal1 += 1
                    letter_decimal = str(decimal1)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 < ajuste and decimal2 < ajuste and decimal1 < ajuste:
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 < ajuste and decimal2 >= ajuste and decimal1 < ajuste:
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 < ajuste and decimal2 >= ajuste and decimal1 >= ajuste:
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 < ajuste and decimal2 < ajuste and decimal1 >= ajuste:
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 > ajuste and (decimal2 + 1) < ajuste and decimal1 < ajuste:
                    decimal2 += 1
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) < ajuste and decimal1 >= ajuste:
                    decimal2 += 1
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
                elif decimal3 >= ajuste and (decimal2 + 1) < ajuste and decimal1 < ajuste:
                    decimal2 += 1
                    letter_decimal = str(decimal1) + str(decimal2)
                    flotante = float(str(numero) + '.' + letter_decimal)
                    print(f"flotante ->{flotante}")
                    return flotante
        else:
            return numero
    def agregar_punto(self,numero, moneda):
        entero = int(numero)
        if 'USD' in moneda:
            decimal = str(numero)
            numero_con_punto = ''
            print(f"decimal ->{decimal}")
            entero_string = '.'.join([str(int(entero))[::-1][i:i + 3] for i in range(0, len(str(int(entero))), 3)])[
                            ::-1]
            print(f"entero_string->{entero_string}")
            decimal_string = str(decimal).split('.')
            print(f"decimal_string->{decimal_string}")
            if decimal_string and len(decimal_string) > 1:
                if decimal_string and len(decimal_string[1]) >= 2:
                    numero_con_punto = entero_string + ',' + decimal_string[1][:2]
                elif len(decimal_string[1]) < 2 and decimal_string[1] != '0':
                    numero_con_punto = entero_string + ',' + decimal_string[1] + '0'
                elif len(decimal_string[1]) < 2 and decimal_string[1] == '0':
                    numero_con_punto = entero_string + ',' + decimal_string[1]
            else:
                numero_con_punto = entero_string
        else:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(entero))), 3)])[
                               ::-1]
        num_return = numero_con_punto
        return num_return

class DownloadXLS(http.Controller):
    @http.route('/getXML/<int:id>', auth='public',type='http')
    def generarXLSX(self, id=None, **kw):
        record = request.env['account.move'].browse(id)
        certificado=request.env['firma.digital'].search([
            ('company_id', '=', record.env.user.company_id.id),
            ('estado', '=', 'activo')
        ], limit=1)
        xml = record.generar_xml(certificado)
        # record.generate_qr_code()
        xml = str(xml)[2:-1]
        xml2 = xml
        characters = "\n"
        xml2 = xml2.replace(characters, "")
        filename='factura_electronica-'+record.nro_factura+'.xml'
        return request.make_response(xml2,
                                     [('Content-Type',
                                       'application/xml'),
                                      ('Content-Disposition', content_disposition(filename))])



def round_down(num, divisor):
    return num - (num%divisor)

def redondear(numero):
    """
    Funcion de calculo de redondeo
    """
    num=float_round(numero, precision_rounding=ROUNDING,rounding_method='HALF-UP')
    positivo=num
    if num < 0:
        positivo=num*-1
    entero=int(positivo)
    diferencia=positivo-entero
    # _logger.info('diferencia %s'  %str(diferencia))
    if diferencia > 0:
        numero=float_round(positivo, precision_rounding=ROUNDING,rounding_method='HALF-UP')
        numero="%.2f" % numero
        numero=float(numero)
        # _logger.info('redondear %s' % str(numero))
    else:
        numero=int(positivo)
    if num <0:

        numero=numero*-1

    return numero

def parsear_fecha_respuesta(fecha):
    dFecProc = fecha[:fecha.rfind('-')]
    tz_string = fecha[fecha.rfind('-'):]
    tz_string = tz_string.replace(':', '')
    dFecProc = dFecProc + tz_string
    # _logger.info(dFecProc)
    date_time_obj = datetime.strptime(dFecProc, '%Y-%m-%dT%H:%M:%S%z')
    date_time = date_time_obj.astimezone(pytz.utc).replace(tzinfo=None)
    return date_time

