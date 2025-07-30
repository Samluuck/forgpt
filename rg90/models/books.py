# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api,_
import time, collections
from odoo.exceptions import ValidationError
import xlsxwriter
import logging
from datetime import date,datetime
from calendar import monthrange
import base64
# from cStringIO import StringIO
from odoo import http, _
from odoo.http import request
import calendar
import os
from  sys import platform
from odoo.addons.web.controllers.main import serialize_exception,content_disposition
_logger = logging.getLogger(__name__)
CANT_REGISTROS_HECHAUKA = 15000
from zipfile import ZipFile
import werkzeug

class ruc_tipo_documento(models.Model):
    _inherit = 'ruc.tipo.documento'
    _order = 'codigo_hechauka asc'


    tipo = fields.Selection(selection_add=[('5','Ingreso'),('6','Egreso'),('7','Ingreso/Egreso')], tracking=True)
    #type = fields.Selection(selection_add=[('retencion', 'Retencion'), ('tarjeta_credito', 'Tarjeta de Credito'), ('tarjeta_debito', 'Tarjeta de Debito')], tracking=True)

    codigo_rg90= fields.Integer (string="Codigo en el RG90")

    active = fields.Boolean(default=True)
    # talonaraio= fields.Many2one('ruc.documentos.timbrados',string="Talonario")

class invoices_books(models.TransientModel):
    _name = "account.book.rg90"

    #tipo=fields.Selection([('rg90_ventas','RG90 Ventas'),('rg90_compras','RG90 Compras'),('rg90_ingre','RG90 Ingreso'),('rg90_egre','RG90 Egreso'),('rg90','RG90 Completo')],string="Tipo")
    #tipo=fields.Selection([('rg90_ventas','RG90 Ventas'),('rg90_compras','RG90 Compras'),('rg90_ingre','RG90 Ingreso'),('rg90_egre','RG90 Egreso')],string="Tipo")
    # rg90= fields.Boolean(compute="es_rg90",string="RG90")
    rg90_file = fields.Binary(string='Archivo RG90')
    tipo=fields.Selection([('rg90_ventas','RG90 Ventas'),('rg90_compras','RG90 Compras'),('rg90_ingre','RG90 Ingreso'),('rg90_egre','RG90 Egreso')],string="Tipo")
    filename= fields.Char(string='Nombre Archivo')
    #payment_ids = fields.One2many('payments.rg', 'book_id',string='Ingresos/Egresos')
    mes = fields.Selection(
        [('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'), ('04', 'Abril'), ('05', 'Mayo'), ('06', 'Junio'),
         ('07', 'Julio'), ('08', 'Agosto'), ('09', 'Setiembre'), ('10', 'Octubre'), ('11', 'Noviembre'),
         ('12', 'Diciembre')], string="Mes")
    periodo = fields.Integer(string="Periodo/Año")
    solo_txt = fields.Boolean(string="Solo descargar TXT")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self.get_default_company())

    @api.model
    def get_default_company(self):
        return self.env.company.id

    #@api.multi
    def generar_informe(self):
        periodo = str(self.periodo) + str(self.mes)

        if not self.env.company.ruc:
            raise ValidationError(
                'No se encuentra RUC asignado para la compañia. Debe asignarla en los parametros de la compañia')
        elif not self.env.company.dv:
            raise ValidationError(
                'No se encuentra DV asignado para la compañia. Debe asignarla en los parametros de la compañia')
        elif not self.env.company.razon_social:
            raise ValidationError(
                'No se encuentra Razon Social asignada para la compañia. Debe asignarla en los parametros de la compañia')
        # elif not self.env.user.company_id.ruc_representante:
        #     raise ValidationError(
        #         'No se encuentra Ruc del Representante Legal asignado para la compañia. Debe asignarla en los parametros de la compañia')
        # elif not self.env.user.company_id.dv_representante:
        #     raise ValidationError(
        #         'No se encuentra DV del Representante Legal asignado para la compañia. Debe asignarla en los parametros de la compañia.')
        # elif not self.env.user.company_id.representante_legal:
        #     raise ValidationError(
        #         'No se encuentra Representante Legal asignado para la compañia. Debe asignarla en los parametros de la compañia.')

        # if self.tipo == 'rg90_ventas':
        #     # archivo = self.generar_ventas()
        #     return {
        #         'type': 'ir.actions.act_url',
        #         'url': '/getrg90/txt/' + str(self.id),
        #         'target': 'current'
        #     }
            # self.archivo = archivo
        #elif self.tipo == 'rg90_compras':
            # archivo = self.generar_compras()
        return {
            'type': 'ir.actions.act_url',
            'url': '/getrg90/txt/' + str(self.id),
            'target': 'current'
        }

class DownloadPDF(http.Controller):

    @http.route('/getrg90/txt/<int:id>', auth='public')
    def generarTXT(self, id=None, **kw):
        record = request.env['account.book.rg90'].browse(id)

        iva10 = record.env.ref('l10n_py.grupo_10')
        iva5 = record.env.ref('l10n_py.grupo_5')
        exentas = record.env.ref('l10n_py.grupo_exenta')

        # company_id_id = record.get_default_company()
        company_id = record.company_id

        dias = calendar.monthrange(record.periodo, int(record.mes))
        # fecha_inicio=str(record.periodo)+'-'+str(record.mes)+'-'+str(dias[0])
        fecha_inicio = str(record.periodo) + '-' + str(record.mes) + '-01'
        # fecha_fin=str(record.periodo)+'-'+str(record.mes)+'-'+str(dias[1])
        fecha_fin = str(record.periodo) + '-' + str(record.mes) + '-' + str(dias[1])
        _logger.info('dias')
        _logger.info(dias)

        # Variables,  Listas y Diccionario a ser utilizados
        lista_totales = []
        impuestos = []
        monto_iva10 = 0.0
        monto_gravada10 = 0.0
        monto_iva5 = 0.0
        monto_gravada5 = 0.0
        monto_exentas = 0.0
        total_iva10 = total_iva5 = total_grav10 = total_grav5 = total_exentas = 0.0
        diccionario_facturas = collections.OrderedDict()
        tipo = 0

        # FILTROS
        domain = []
        # domain += [('company_id', '=', company_id.id), ('date_invoice', '>=', fecha_inicio), ('date_invoice', '<=', fecha_fin)]
        if record.tipo in ('rg90_ventas','rg90_compras'):
            domain += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
                       ('date', '<=', fecha_fin),('virtual','=',False),
                       ('state', '=', 'posted')]

        if record.tipo == 'rg90_ventas':
            # SI ES VENTA FACTURA CLIENTE CON NOTA DE CREDITO PROVEEDOR
            domain += [('move_type', 'in', ('out_invoice', 'in_refund'))]
            tipo_reporte = '1'
        elif record.tipo == 'rg90_compras':
            # SI ES COMPRA FACTURA PROVEEDOR CON NOTA DE CREDITO CLIENTE
            domain += [('move_type', 'in', ('in_invoice', 'out_refund'))]
            tipo_reporte = '2'


        # AQUI SE APLICA LA MISMA LOGICA DEL LIBRO IVA
        if record.tipo in ('rg90_ventas', 'rg90_compras'):
            facturas = record.env['account.move'].search(domain, order='invoice_date')
            for f in facturas.filtered(lambda r: r.tipo_comprobante.mostrar_libro_iva):
                m = f
                impuesto_compuesto = False
                for linea in m.line_ids:

                    if linea.tax_line_id:
                        if linea.tax_line_id.tax_group_id.id == iva10.id:
                            monto_iva10 += abs(round(linea.balance, 0))
                            # if f.type in ('out_invoice', 'in_invoice'):
                            # if f.tipo_comprobante.codigo_hechauka == 4:
                            #     monto_gravada10 += linea.balance * 10
                            #     total_grav10 += linea.balance * 10
                            total_iva10 += abs(round(linea.balance, 0))
                            monto_nuevo_iva10 = abs(round(linea.balance, 0))

                            # else:
                            #     nc_total_iva10 += abs(round(linea.balance, 0))
                        if linea.tax_line_id.tax_group_id.id == iva5.id:
                            monto_iva5 += abs(round(linea.balance, 0))
                            # if f.type in ('out_invoice', 'in_invoice'):
                            total_iva5 += abs(round(linea.balance, 0))
                            # else:
                            #     nc_total_iva5 += abs(round(linea.balance, 0))

                    else:
                        if len(linea.tax_ids) == 1:
                            linea_tax = linea.tax_ids
                            # Si la factura posee iva 10%
                            if linea_tax.tax_group_id.id == iva10.id:
                                monto_gravada10 += round(linea.balance, 0)
                                # if f.type in ('out_invoice', 'in_invoice'):
                                total_grav10 += round(linea.balance, 0)
                                # else:

                                # nc_total_grav10 += round(linea.balance, 0)
                                # print(nc_total_grav10)
                            # Si la factura posee iva 5%
                            if linea_tax.tax_group_id.id == iva5.id:
                                monto_gravada5 += round(linea.balance, 0)
                                # if f.type in ('out_invoice', 'in_invoice'):
                                total_grav5 += round(linea.balance, 0)
                                # else:
                                #     nc_total_grav5 += round(linea.balance, 0)
                            # Si la factura posee exentas%
                            if linea_tax.tax_group_id.id == exentas.id:
                                monto_exentas += round(linea.balance, 0)
                                # if f.type in ('out_invoice', 'in_invoice'):
                                total_exentas += round(linea.balance, 0)
                                # else:
                                #     nc_total_exentas += round(linea.balance, 0)
                        elif len(linea.tax_ids) > 1:
                            # en caso que tenga impuesto compuesto ejemplo mitad 10% y mitad exento
                            impuesto_compuesto = True
                            mitad_subtotal = linea.balance / 2
                            monto_exentas += (mitad_subtotal)
                            total_exentas += (mitad_subtotal)
                            monto_gravada10 += mitad_subtotal
                            total_grav10 += monto_gravada10

                monto_gravada10 = abs(monto_gravada10)
                # total_grav10 = abs(total_grav10)
                # nc_total_grav10 = abs(nc_total_grav10)
                monto_gravada5 = abs(monto_gravada5)
                # total_grav5 = abs(total_grav5)
                # nc_total_grav5= abs(nc_total_grav5)
                monto_exentas = abs(monto_exentas)

                if not impuesto_compuesto:
                    if monto_gravada10 > 0:
                        monto_10 = monto_iva10 + monto_gravada10
                        ######monto_nuevo_iva10 = round(monto_10 / 11)
                        monto_nuevo_gravada_10 = round(monto_10 / 1.1)
                    else:
                        monto_nuevo_iva10 = monto_iva10
                        monto_nuevo_gravada_10 = monto_gravada10
                    if monto_gravada5 > 0:
                        monto_5 = monto_iva5 + monto_gravada5
                        monto_nuevo_iva5 = round(monto_5 / 21)
                        monto_nuevo_gravada_5 = round(monto_5 / 1.05)

                    else:
                        monto_nuevo_iva5 = monto_iva5
                        monto_nuevo_gravada_5 = monto_gravada5
                    impuestos.append(monto_nuevo_gravada_10)
                    impuestos.append(monto_nuevo_iva10)
                    impuestos.append(monto_nuevo_gravada_5)
                    impuestos.append(monto_nuevo_iva5)
                    impuestos.append(monto_exentas)
                else:
                    impuestos.append(monto_gravada10)
                    impuestos.append(monto_iva10)
                    impuestos.append(monto_gravada5)
                    impuestos.append(monto_iva5)
                    impuestos.append(monto_exentas)

                # Diccionario donde el key es la Factura anidadas a sus impuestos
                diccionario_facturas.setdefault(f, impuestos)

                # Se resetea los valores para la siguiente Factura
                impuestos = []
                monto_iva10 = monto_iva5 = monto_exentas = monto_gravada5 = monto_gravada10 = 0.0

            # Lista de totales de las facturas
            lista_totales.append(total_grav10)
            lista_totales.append(total_iva10)
            lista_totales.append(total_grav5)
            lista_totales.append(total_iva5)
            lista_totales.append(total_exentas)

            fac = diccionario_facturas.items()
            # -->FIN DE LA LOGICA DEL LIBRO IVA <--#

            # DATOS Y VARIABLES PARA EL TXT
            periodo = str(record.periodo) + str(record.mes)
            cantidad = len(facturas)
            resta_cantidad_ruc4 = resta_cantidad_ruc6 = resta_cantidad_ruc7 = resta_cantidad_ruc8 = 0
            nombre_mes = record.mes
            monto_total = 0
            # Lista donde estara los datos
            txt = []
            # txt.append('LINEA A SER REEMPLAZADA POR EL ENCABEZADO AL FINAL')
            #txt.append("\n")
            nombre = False
            gravada_10_ruc4 = gravada_10_ruc6 = gravada_10_ruc7 = gravada_10_ruc8 = 0
            iva_10_ruc4 = iva_10_ruc6 = iva_10_ruc7 = iva_10_ruc8 = 0
            gravada_5_ruc4 = gravada_5_ruc6 = gravada_5_ruc7 = gravada_5_ruc8 = 0
            iva_5_ruc4 = iva_5_ruc6 = iva_5_ruc7 = iva_5_ruc8 = 0
            iva_exento_ruc4 = iva_exento_ruc6 = iva_exento_ruc7 = iva_exento_ruc8 = 0
            for f in fac:

                # ---> VARIABLES QUE SE SETEAN EN BASE A SU CONDICION <-- #
                cod_identificacion= ''
                ruc = f[0].ruc_factura[:f[0].ruc_factura.find('-')]
                dv = f[0].ruc_factura[f[0].ruc_factura.find('-') + 1:]
                mon_ex = 'N'
                imputa_iva='S' if f[0].imputa_iva else 'N'
                imputa_ire='S' if f[0].imputa_ire else 'N'
                imputa_irp='S' if f[0].imputa_irp_rsp else 'N'
                no_imputa='S' if f[0].no_imputa else 'N'
                fact_aso=''
                timb_aso=''
                if f[0].move_type in ('in_refund','out_refund'):
                    if f[0].factura_afectada:
                        fact_aso=f[0].factura_afectada.nro_factura or ''
                        timb_aso=f[0].factura_afectada.timbrado or ''
                    elif f[0].linea_asiento_afectada_nc:
                        fact_aso = f[0].linea_asiento_afectada_nc.name or ''
                        timb_aso = f[0].linea_asiento_afectada_nc_timbrado or ''
                if f[0].currency_id != f[0].company_id.currency_id:
                    mon_ex='S'
                if f[0].partner_id.parent_id:
                    nombre = f[0].partner_id.parent_id.name
                    cod_identificacion = f[0].partner_id.parent_id.tipo_identificacion.codigo_rg90
                else:
                    nombre = f[0].partner_id.name
                    cod_identificacion = f[0].partner_id.tipo_identificacion.codigo_rg90
                #if f[0].tipo_comprobante.codigo_hechauka == 8:
                if f[0].partner_no_despachante:
                    nombre = f[0].partner_no_despachante.name
                    cod_identificacion = f[0].partner_id.tipo_identificacion.codigo_rg90

                if f[0].tipo_comprobante:
                    if f[0].tipo_comprobante.codigo_hechauka == 4:
                        #nombre = 'Proveedores del Exterior'
                        if f[0].partner_no_despachante:
                            nombre = f[0].partner_no_despachante.name
                        else:
                            nombre = f[0].partner_id.name
                        ruc = '99999901'
                        dv = '0'
                    if f[0].tipo_comprobante.codigo_hechauka in [1, 2, 3, 5]:
                        numero_timbrado = str(f[0].timbrado)
                    else:
                        numero_timbrado = '0'
                    tipo_documento = str(f[0].tipo_comprobante.codigo_rg90)
                if ruc == '44444401':
                    nombre = 'Importes consolidados'
                elif ruc == '66666601':
                    if record.company_id.exportador:
                        nombre = 'Clientes de Exportación'
                        cod_identificacion = 18
                    else:
                        nombre = 'Clientes del Exterior'
                        ruc = '88888801'
                        dv = '5'
                        cod_identificacion = 18
                elif f[0].fiscal_position_id:
                    if f[0].fiscal_position_id.tax_ids[0].tax_dest_id.tax_group_id.id == exentas.id:
                        nombre = 'Clientes del Exterior'
                        ruc = '77777701'
                        dv = '0'

                if f[0].nro_factura:
                    numero_documento = f[0].nro_factura
                else:
                    numero_documento = None
                fecha_documento = f[0].date
                fecha_documento = datetime.strptime(str(fecha_documento), '%Y-%m-%d').strftime("%d/%m/%Y")
                if f[0].tipo_comprobante.codigo_hechauka == 4:
                    gravada_10 = f[1][1] * 10
                    total_despacho = gravada_10 + f[1][1] + f[1][2] + f[1][3] + f[1][4]
                    m_iva_10 = f[1][1]
                    gravada_5 = f[1][2]
                    m_iva_5 = f[1][3]
                    m_iva_exento = f[1][4]
                    total_linea = total_despacho
                    if record.tipo == '221':
                        # total_linea=sum([l.credit for l in f[0].move_id.line_ids])
                        total_linea = gravada_5 + gravada_10 + m_iva_exento + m_iva_10 + m_iva_5
                    else:
                        total_linea = gravada_5 + gravada_10 + m_iva_exento
                else:
                    gravada_10 = f[1][0]
                    m_iva_10 = f[1][1]
                    gravada_5 = f[1][2]
                    m_iva_5 = f[1][3]
                    m_iva_exento = f[1][4]
                    if record.tipo == '221':
                        # total_linea=sum([l.credit for l in f[0].move_id.line_ids])
                        # total_linea = gravada_5 + gravada_10 + m_iva_exento + m_iva_10 + m_iva_5
                        total_linea = gravada_5 + gravada_10 + m_iva_exento + m_iva_10 + m_iva_5
                    else:
                        total_linea = gravada_5 + gravada_10 + m_iva_exento
                monto_total += total_linea

                tipo_operacion = 0
                condicion_compra = f[0].tipo_factura
                if condicion_compra == 1:
                    cantidad_cuotas = 0
                else:
                    cantidad_cuotas = 1
                if not condicion_compra and str(tipo_documento)=='109':
                    condicion_compra = 2
                else:
                    if str(tipo_documento)!='109':
                        if str(tipo_documento)==107:

                            condicion_compra = 1
                        else:
                            condicion_compra = ' '
                # --> FIN <--#
                # DATOS DE UNA LINEA
                # venta
                if dv:
                    dv='-'+dv
                else:
                    dv=''
                if record.tipo == 'rg90_ventas':
                    tipo_reporte='1'
                elif record.tipo=='rg90_compras':
                    tipo_reporte = '2'
                    #if ruc not in ('44444401', '66666601', '88888801', '77777701'):
                if str(cod_identificacion) == '0':

                    cod_identificacion=11
                if str(ruc)=='44444401':
                    cod_identificacion = 15
                elif str(ruc) in ('99999901','88888801','77777701'):
                    cod_identificacion = 17


                if tipo_reporte=='1':
                    data = [
                        tipo_reporte,
                        str(cod_identificacion),
                        str(ruc),
                        str(nombre),
                        str(tipo_documento),
                        str(fecha_documento),
                        str(numero_timbrado),
                        str(numero_documento),

                        str(int(gravada_10)+int(m_iva_10)),
                        #str(int(m_iva_10)),
                        str(int(gravada_5)+int(m_iva_5)),
                        #str(int(m_iva_5)),
                        str(int(m_iva_exento)),
                        str(int(gravada_10)+int(m_iva_10)+int(gravada_5)+int(m_iva_5)+int(m_iva_exento)),
                        # str(tipo_operacion),
                        str(condicion_compra),
                        str(mon_ex),
                        str(imputa_iva),
                        str(imputa_ire),
                        str(imputa_irp),
                        str(fact_aso),
                        str(timb_aso),

                    ]
                elif tipo_reporte=='2':
                    data = [
                        tipo_reporte,
                        str(cod_identificacion),
                        str(ruc),
                        str(nombre),
                        str(tipo_documento),
                        str(fecha_documento),
                        str(numero_timbrado),
                        str(numero_documento),

                        str(int(gravada_10) + int(m_iva_10)),
                        # str(int(m_iva_10)),
                        str(int(gravada_5) + int(m_iva_5)),
                        # str(int(m_iva_5)),
                        str(int(m_iva_exento)),
                        str(int(gravada_10) + int(m_iva_10) + int(gravada_5) + int(m_iva_5) + int(m_iva_exento)),
                        # str(tipo_operacion),
                        str(condicion_compra),
                        str(mon_ex),
                        str(imputa_iva),
                        str(imputa_ire),
                        str(imputa_irp),
                        str(no_imputa),
                        str(fact_aso),
                        str(timb_aso),

                    ]
                # SE AGREGA TABULADOR A LA LINEA
                fila = ("\t".join(data))
                # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
                txt.append(fila)
                # SE LE AGREGA SALTO DE LINEA AL TXT
                txt.append("\n")

            total_linea_ruc4 = gravada_5_ruc4 + gravada_10_ruc4 + iva_exento_ruc4 + iva_10_ruc4 + iva_5_ruc4
            monto_total = monto_total - total_linea_ruc4
            total_linea_ruc4 = gravada_5_ruc4 + gravada_10_ruc4 + iva_exento_ruc4 + int(
                gravada_10_ruc4 / 10) + int(gravada_5_ruc4 / 20)
            monto_total = monto_total + total_linea_ruc4
            total_linea_ruc6 = gravada_5_ruc6 + gravada_10_ruc6 + iva_exento_ruc6 + iva_10_ruc6 + iva_5_ruc6
            total_linea_ruc7 = gravada_5_ruc7 + gravada_10_ruc7 + iva_exento_ruc7 + iva_10_ruc7 + iva_5_ruc7
            total_linea_ruc8 = gravada_5_ruc8 + gravada_10_ruc8 + iva_exento_ruc8 + iva_10_ruc8 + iva_5_ruc8
            if total_linea_ruc4 > 0:
                data = [
                    '2',
                    str('44444401'),
                    str('7'),
                    str('Importes consolidados'),
                    str(0),
                    str(0),
                    # str(nro_factura_4),
                    str(fecha_4),
                    str(int(gravada_10_ruc4)),
                    # str(int(iva_10_ruc4)),
                    str(int(gravada_10_ruc4 / 10)),
                    str(int(gravada_5_ruc4)),
                    str(int(gravada_5_ruc4 / 20)),
                    # str(int(iva_5_ruc4)),
                    str(int(iva_exento_ruc4)),
                    str(int(total_linea_ruc4)),
                    # str(tipo_operacion),
                    str(1),
                    str(0),
                    str(0),
                    # str(timbrado_4),
                ]
                # SE AGREGA TABULADOR A LA LINEA
                fila = ("\t".join(data))
                # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
                txt.append(fila)
                # SE LE AGREGA SALTO DE LINEA AL TXT
                txt.append("\n")
            if total_linea_ruc6 > 0:
                data = [
                    '2',
                    str('66666601'),
                    str('6'),
                    str('Clientes de Exportación'),
                    str(1),
                    str(nro_factura_6),
                    str(fecha_6),
                    str(int(gravada_10_ruc6)),
                    str(int(iva_10_ruc6)),
                    str(int(gravada_5_ruc6)),
                    str(int(iva_5_ruc6)),
                    str(int(iva_exento_ruc6)),
                    str(int(total_linea_ruc6)),
                    # str(tipo_operacion),
                    str(1),
                    str(0),
                    str(timbrado_6),
                ]
                # SE AGREGA TABULADOR A LA LINEA
                fila = ("\t".join(data))
                # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
                txt.append(fila)
                # SE LE AGREGA SALTO DE LINEA AL TXT
                txt.append("\n")
            if total_linea_ruc7 > 0:
                data = [
                    '2',
                    str('77777701'),
                    str('0'),
                    str('Ventas a Agentes Diplomáticos'),
                    str(1),
                    str(nro_factura_7),
                    str(fecha_7),
                    str(int(gravada_10_ruc7)),
                    str(int(iva_10_ruc7)),
                    str(int(gravada_5_ruc7)),
                    str(int(iva_5_ruc7)),
                    str(int(iva_exento_ruc7)),
                    str(int(total_linea_ruc7)),
                    # str(tipo_operacion),
                    str(1),
                    str(0),
                    str(timbrado_7),
                ]
                # SE AGREGA TABULADOR A LA LINEA
                fila = ("\t".join(data))
                # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
                txt.append(fila)
                # SE LE AGREGA SALTO DE LINEA AL TXT
                txt.append("\n")

            if total_linea_ruc8 > 0:
                data = [
                    '2',
                    str('88888801'),
                    str('5'),
                    str('Clientes del Exterior'),
                    str(1),
                    str(nro_factura_8),
                    str(fecha_8),
                    str(int(gravada_10_ruc8)),
                    str(int(iva_10_ruc8)),
                    str(int(gravada_5_ruc8)),
                    str(int(iva_5_ruc8)),
                    str(int(iva_exento_ruc8)),
                    str(int(total_linea_ruc8)),
                    # str(tipo_operacion),
                    str(1),
                    str(0),
                    str(timbrado_8),
                ]
                # SE AGREGA TABULADOR A LA LINEA
                fila = ("\t".join(data))
                # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
                txt.append(fila)
                # SE LE AGREGA SALTO DE LINEA AL TXT
                txt.append("\n")
        elif record.tipo =='rg90_ingre':
            #Traer los datos de tipo de comprobante ingreso
            #Traer los recibos confirmados del mes que recibe el parametro
            account_recibo=request.env['account.recibo'].search([('state','=','confirmado'),('fecha', '>=', fecha_inicio),
                       ('fecha', '<=', fecha_fin),('company_id','=',record.company_id.id)])
            tipo_reporte='3'
            txt=[]
            periodo = str(record.periodo) + str(record.mes)

            nombre_mes = record.mes
            for recibos in account_recibo:
                facturas=recibos.pagos_facturas_ids.filtered(lambda r:r.invoice_id.tipo_factura=='2')
                facturas_credit=facturas.mapped('invoice_id')
                fecha_documento = recibos.fecha
                fecha_documento = datetime.strptime(str(fecha_documento), '%Y-%m-%d').strftime("%d/%m/%Y")
                for fact in facturas_credit:

                    data = [
                        tipo_reporte,
                        str(203),
                        str(fecha_documento),
                        str(recibos.name),
                        str(recibos.partner_id.tipo_identificacion.codigo_rg90),
                        str(recibos.partner_id.ruc or ''),
                        str(recibos.partner_id.name),
                        str(0),
                        str(0),
                        str(int(recibos.total_cobros)),
                        str('S' if recibos.company_id.imputa_ire else 'N'),
                        str('S' if recibos.company_id.imputa_irp_rsp else 'N'),
                        '',
                        str(fact.nro_factura or ''),
                        str(fact.timbrado or '')
                    ]

                    fila = ("\t".join(data))
                    # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
                    txt.append(fila)
                    # SE LE AGREGA SALTO DE LINEA AL TXT
                    txt.append("\n")
        elif record.tipo =='rg90_egre':
            # Traer los datos de tipo de comprobante egreso
            account_recibo = request.env['account.orden.pago'].search(
                [('state', '=', 'confirmado'), ('fecha', '>=', fecha_inicio),
                 ('fecha', '<=', fecha_fin),('company_id','=',record.company_id.id)])
            tipo_reporte = '4'
            txt = []
            periodo = str(record.periodo) + str(record.mes)

            nombre_mes = record.mes
            for recibos in account_recibo:
                facturas = recibos.orden_pagos_facturas_ids.filtered(lambda r: r.invoice_id.tipo_factura == '2')
                if not facturas:
                    contado=record.env.ref('account.account_payment_term_immediate')
                    facturas = recibos.orden_pagos_facturas_ids.filtered(lambda r: r.invoice_id.invoice_payment_term_id != contado)
                facturas_credit = facturas.mapped('invoice_id')
                fecha_documento = recibos.fecha
                fecha_documento = datetime.strptime(str(fecha_documento), '%Y-%m-%d').strftime("%d/%m/%Y")
                for fact in facturas_credit:

                    data = [
                        tipo_reporte,
                        str(201),
                        str(fecha_documento),
                        str(recibos.recibo_proveedor or recibos.name),
                        str(recibos.partner_id.tipo_identificacion.codigo_rg90),
                        str(recibos.partner_id.ruc or ''),
                        str(recibos.partner_id.name),
                        str(int(recibos.total_pagos)),
                        str('N'),
                        str('S' if recibos.company_id.imputa_ire else 'N'),
                        str('S' if recibos.company_id.imputa_irp_rsp else 'N'),
                        'N',
                        'N',
                        'N',
                        'N',
                        'N',
                        str(fact.nro_factura or ''),
                        str(fact.timbrado or '')
                    ]

                    fila = ("\t".join(data))
                    # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
                    txt.append(fila)
                    # SE LE AGREGA SALTO DE LINEA AL TXT
                    txt.append("\n")

        if tipo_reporte=='1':
            arch='_V0001'
        elif tipo_reporte=='2':
            arch='_C0001'
        elif tipo_reporte=='3':
            arch='_I0001'
        else:
            arch='_E0001'

        filename = str(record.company_id.ruc)+'_REG_'+str(nombre_mes) + str(record.periodo) + arch

        # path = os.path.abspath(__file__ + "/../../")
        # nombre = filename
        # file_dir = "static/src"
        # file = nombre + '.zip'
        # file_name = "static/src"
        #
        # with open(os.path.join(path + "/" + file_dir, file), 'w') as fp:
        #     fp.write("")
        # # file_name_zip = file_name + ".zip"
        # zipfilepath = os.path.join(path, file_name + '/' + file)
        # # creating zip file in above mentioned path
        # zipObj = ZipFile(zipfilepath, "w")
        # #xml = dicttoxml(loads(jsonstr), attr_type=False, custom_root='estadosFinancieros')
        # #jsonstr = jsonstr.encode("utf-8")
        # zipObj.writestr(nombre + '.txt', txt)
        # #zipObj.writestr(nombre + '.json', jsonstr)
        # zipObj.close()

        # code snipet for downloading zip file
        # if platform == "linux" or platform == "linux2":
        # # linux
        # elif platform == "darwin":
        # # OS X
        # el
        # with open("file.txt", "w") as output:
        #     output.write(str(txt))

        if record.solo_txt:
            filename=filename+'.txt'
            return request.make_response(
                txt,
                [('Content-Type', 'text/plain'),
                 ('Content-Disposition', content_disposition(filename))])
        else:
            if platform == "win32":
                path = os.path.abspath(__file__ + "\\..\\..\\")
                nombre = filename
                file_dir = "static\\src"
                file = nombre + '.zip'
                file_name = "static\\src"
                text='file.txt'

                with open(os.path.join(path + "\\" + file_dir, file), 'w') as fp:
                    fp.write("")

                # with open(os.path.join(path + "\\" + file_dir, text), 'w') as output:
                #     output.write(str(txt))
                # file_name_zip = file_name + ".zip"

                zipfilepath = os.path.join(path, file_name + '\\' + file)
                # creating zip file in above mentioned path

                zipObj = ZipFile(zipfilepath, "w")
                # xml = dicttoxml(loads(jsonstr), attr_type=False, custom_root='estadosFinancieros')
                # jsonstr = jsonstr.encode("utf-8")

                contenido = ("".join(txt)).encode('utf-8')

                archivo = base64.b64encode(contenido)

                zipObj.writestr(nombre + '.txt', contenido)
                # zipObj.writestr(nombre + '.json', jsonstr)

                zipObj.close()

                with open(os.path.join(path + "\\" + file_dir, file), 'rb') as fp:


                    return request.make_response(
                            fp.read(),
                            [('Content-Type', 'pk'),
                             ('Content-Disposition', content_disposition(filename+'.zip'))])
                # return {
                #     'type': 'ir.actions.act_url',
                #     #'url': str('\\rg90\\static\\src\\'+nombre+'.zip'),
                #     'url': 'www.google.com',
                #     'target': 'new',
                # }



            else:
                path = os.path.abspath(__file__ + "/../../")
                nombre = filename
                file_dir = "static/src"
                file = nombre + '.zip'
                file_name = "static/src"
                text = 'file.txt'

                with open(os.path.join(path + "/" + file_dir, file), 'w') as fp:
                    fp.write("")
                # with open(os.path.join(path + "/" + file_dir, text), 'w') as output:
                #     output.write(str(txt))
                # file_name_zip = file_name + ".zip"
                zipfilepath = os.path.join(path, file_name + '/' + file)
                # creating zip file in above mentioned path
                zipObj = ZipFile(zipfilepath, "w")
                # xml = dicttoxml(loads(jsonstr), attr_type=False, custom_root='estadosFinancieros')
                # jsonstr = jsonstr.encode("utf-8")
                #zipObj.writestr(nombre + '.txt', txt)
                contenido = ("".join(txt)).encode('utf-8')

                archivo = base64.b64encode(contenido)

                zipObj.writestr(nombre + '.txt', contenido)
                # zipObj.writestr(nombre + '.json', jsonstr)
                zipObj.close()

                with open(os.path.join(path + "/" + file_dir, file), 'rb') as fp:


                    return request.make_response(
                            fp.read(),
                            [('Content-Type', 'pk'),
                             ('Content-Disposition', content_disposition(filename+'.zip'))])







