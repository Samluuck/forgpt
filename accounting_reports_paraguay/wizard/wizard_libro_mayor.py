# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time, collections
import io
import logging
from datetime import date,datetime
import xlsxwriter
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception,content_disposition
import pytz
_logger = logging.getLogger(__name__)

from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle, Image

from reportlab.lib import colors

try :
    from reportlab.lib.pagesizes import A4, cm
except:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm

try:
    # from reportlab.lib.pagesizes import A4
    # from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import getSampleStyleSheet
except ImportError:
    _logger.warning('Error en cargar reportlab')

class WizardReportLibroMayor(models.TransientModel):
    _name = "libro_mayor.wizard.libro_mayor"

    tipo = fields.Selection([('xlsx','XLSX'),('pdf','PDF')],string="Tipo de archivo",default='pdf')
    desde = fields.Date(string="Fecha desde")
    hasta = fields.Date(string="Fecha hasta")
    account_ids = fields.Many2many('account.account',string="Cuentas a filtrar",help="Dejar vacio en caso de que no desee filtrar cuentas")
    partner_id = fields.Many2one('res.partner',string="Empresa",help="Dejar vacio en caso de que no desee filtrar por empresa")
    mostrar_cuenta_analitica=fields.Boolean(string="Mostrar cuenta analítica")
    mostrar_filtro=fields.Boolean(default=True,string='Mostrar Filtros')
    mostrar_titulo = fields.Boolean(string="Mostrar Titulo")
    mostrar_fecha = fields.Boolean(string="Mostrar Fecha")
    mostrar_empresa = fields.Boolean(string="Mostrar Empresa")
    mostrar_monedas = fields.Boolean(string="Mostrar Monedas")
    company_id = fields.Many2one('res.company',string='Compania',default=lambda self: self.env.company)

    # @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['desde','hasta','tipo','account_ids','mostrar_filtro'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['desde','hasta','tipo','account_ids','mostrar_filtro'])[0])
        if self.tipo == 'pdf':
            # return self.env.ref('accounting_reports_paraguay.report_libro_mayor_id').report_action(self, data)
            return {
                'type': 'ir.actions.act_url',
                'url': '/getLibroMayor/pdf/' + str(self.id),
                'target': 'current'
            }
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': '/getLibroMayor/'+str(self.id),
                'target': 'current'
            }
    def cantidad_cuenta(self,account_id,partner_id):
        domain=[('account_id','=',account_id),('date', '>=', self.desde), ('date', '<=', self.hasta)]
        if partner_id:
            domain+=[('partner_id','=',partner_id)]
        cantidad = self.env['account.move.line'].search_count(domain)
        return cantidad

    def agregar_punto_de_miles(self, numero):
        if numero >= 0:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
        else:
            numero*=-1
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
            numero_con_punto='-'+numero_con_punto
        num_return = numero_con_punto
        return num_return

    def saldo_al_dia(self,account_id):
        periodo_fiscal = self.company_id.fiscalyear_last_month
        fi = datetime.strptime(str(self.desde), '%Y-%m-%d')
        anio = fi.year
        if not periodo_fiscal == 12:
            mes = periodo_fiscal + 1
            anio = anio - 1
        else:
            mes = 1
        fecha_inicio_anio = str(anio) + '-' + str(mes) + '-01'
        fi = datetime.strptime(fecha_inicio_anio, '%Y-%m-%d')
        lineas_asiento = self.env['account.move.line'].search(
            [('move_id.date', '>=', fi), ('move_id.date', '<', self.desde),
             ('move_id.state', '=', 'posted'),
             ('account_id', '=', account_id.id)])
        total = sum(lineas_asiento.mapped('balance'))
        return total


class ReporteLibroMayor(models.AbstractModel):
    _name = 'report.accounting_reports_paraguay.libro_mayor_paraguay_report'

    # @api.multi
    def _get_report_values(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        if docs.account_ids:
            lineas_asiento = self.env['account.move.line'].search([('date', '>=', docs.desde), ('date', '<=', docs.hasta), ('move_id.state', '=', 'posted'),('account_id','in',docs.account_ids.mapped('id'))])
        else:
            lineas_asiento = self.env['account.move.line'].search([('move_id.date', '>=', docs.desde), ('move_id.date', '<=', docs.hasta), ('move_id.state', '=', 'posted')])
        lineas_asiento = lineas_asiento.sorted(key=lambda p: ( p.account_id.code,p.move_id.date,p.move_id.num_asiento))


        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'time': time,
            'lineas': lineas_asiento
        }


        return docargs


class DownloadXLS(http.Controller):
    @http.route('/getLibroMayor/<int:id>', auth='public')
    def generarXLSX(self, id=None, **kw):
        record = request.env['libro_mayor.wizard.libro_mayor'].browse(id)
        user = record.env.user
        tz = pytz.timezone(user.partner_id.tz) or pytz.utc
        fecha_actual=pytz.utc.localize(datetime.now()).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S")
        desde=record.desde.strftime('%d/%m/%Y')
        hasta=record.hasta.strftime('%d/%m/%Y')
        filtro_fecha = 'Fecha:' + str(fecha_actual)
        move_actual = None
        i = 3
        fp = io.BytesIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        domain=[]
        domain+=[('move_id.company_id', '=', record.company_id.id), ('move_id.date', '>=', record.desde)
            ,('move_id.date', '<=', record.hasta), ('move_id.state', '=', 'posted'),('balance','!=',0)]

        if record.partner_id:
            domain += [('partner_id', 'in', record.partner_id.mapped('id'))]

        if record.account_ids:
            domain+=[('account_id', 'in', record.account_ids.mapped('id'))]


        lineas_asiento=request.env['account.move.line'].search(domain)
        total_debe=0
        total_haber=0
        #int(round(
        for l in lineas_asiento.filtered(lambda r: r.debit != 0):
            total_debe+=int(round(l.debit))
        for l in lineas_asiento.filtered(lambda r: r.credit != 0):
            total_haber+=int(round(l.credit))
        #total_debe = sum([l.debit for l in lineas_asiento.filtered(lambda r: r.debit != 0)])
        #total_haber = sum([l.credit for l in lineas_asiento.filtered(lambda r: r.credit != 0)])
        total_balance = total_debe - total_haber
        lineas_asiento = lineas_asiento.filtered(lambda r: r.balance != 0)
        lineas_asiento = lineas_asiento.sorted(key=lambda p: (p.account_id.code, p.move_id.date,p.move_id.num_asiento,p.credit))
        nom_com=record.company_id.name or 'notie'
        sheet = workbook.add_worksheet('Libro Mayor' + nom_com)
        bold = workbook.add_format({'bold': True, 'fg_color': 'gray', 'align': 'center'})
        bold_2 = workbook.add_format({'bold': True, 'align': 'center'})
        bold_left = workbook.add_format({'bold': True, 'align': 'left'})
        border = workbook.add_format({'border': 1})
        # Create a format to use in the merged range.
        num_format = workbook.add_format({'num_format': '#,##'})
        num_format_bold = workbook.add_format({ 'bold': 1,'num_format': '#,##'})
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#F15F40',
            'font_color': 'white'})
        merge_filtro = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            })
        filtro_desde='Desde: '+desde+' Hasta: '+hasta
        sheet.merge_range('A1:F1', 'LIBRO MAYOR', merge_format)
        sheet.merge_range('A2:D2', filtro_desde, merge_filtro)
        sheet.merge_range('E2:F2', filtro_fecha, merge_filtro)
        sheet.set_column('A:B', 10)
        sheet.set_column('C:C', 50)
        sheet.set_column('D:F', 15)
        sheet.write(2, 0, 'Fecha', bold)
        sheet.write(2, 1, 'Ref.', bold)
        sheet.write(2, 2, 'Detalles', bold)
        sheet.write(2, 3, 'Debito', bold)
        sheet.write(2, 4, 'Credito', bold)
        sheet.write(2, 5, 'Saldos', bold)
        a=6
        if record.mostrar_empresa:
            sheet.set_column('G:I', 15)
            sheet.write(2, a, 'Empresas', bold)
            a+=1
        if record.mostrar_monedas:
            sheet.write(2, a, 'Monto Moneda', bold)
            a+=1
            sheet.write(2, a, 'Moneda', bold)
            a+=1

        if record.mostrar_cuenta_analitica:
            sheet.write(2, a, 'Cuenta analítica', bold)
            a+=1
        acumulador = 0
        cuenta_actual = None
        debito_total = 0
        credito_total = 0
        saldo_total = 0
        saldo_cuenta = 0

        for l in lineas_asiento:
            ref = ''
            if l.partner_id:
                ref = l.partner_id.name.strip()
            if l.move_id.ref:
                if ref:
                    ref += ' / ' + l.move_id.ref.strip()
                else:
                    ref = l.move_id.ref.strip()
            else:
                if l.name:
                    ref=l.name.strip()
                else:
                    ref=''
            operacion = ''

            try:
                if l.payment_id:
                    operacion = l.payment_id.name
                elif l.move_id.nro_factura:
                    operacion = l.move_id.nro_factura
                elif l.move_id.nro:
                    operacion = l.move_id.nro
                elif l.move_id.stock_move_id.picking_id:
                    operacion = l.move_id.stock_move_id.picking_id.name
            except:
                    operacion=''
            if operacion:
                ref += ' ' + '(' + operacion + ')'
            if l.account_id != cuenta_actual:
                acumulador = 0
                cuenta_actual = l.account_id
                debito_total = 0
                credito_total = 0
                saldo_cuenta = 0
                # sheet.write(i,0,l.account_id.code + ' , ' + l.account_id.name,bold_2)
                sheet.merge_range(i,0,i,2,l.account_id.code + ' , ' + l.account_id.name,bold_left)
                saldo = DownloadPDF.obtener_acumulado_anio(record,request, l.account_id, record.desde, record.partner_id)
                sheet.write(i, 5, saldo, num_format)
                i = i + 1
                sheet.write(i, 0, str(l.move_id.date.strftime('%d-%m-%Y')))
                sheet.write(i, 1, l.move_id.num_asiento)
                sheet.write(i, 2, ref)
                sheet.write(i,3,int(round(l.debit)),num_format)
                sheet.write(i,4,int(round(l.credit)),num_format)
                saldo_cuenta = saldo_cuenta + int(round(l.balance))+saldo
                sheet.write(i,5,saldo_cuenta,num_format)
                debito_total = int(round(l.debit)) + debito_total
                credito_total = int(round(l.credit)) + credito_total
                acumulador = acumulador + 1
                i+=1
            else:
                sheet.write(i, 0, str(l.move_id.date.strftime('%d-%m-%Y')))
                sheet.write(i, 1, l.move_id.num_asiento)
                sheet.write(i, 2, ref)
                sheet.write_number(i, 3, int(round(l.debit)),num_format)
                sheet.write_number(i, 4, int(round(l.credit)),num_format)
                saldo_cuenta = saldo_cuenta + int(round(l.balance))
                sheet.write_number(i, 5, saldo_cuenta,num_format)
                a=6
                if record.mostrar_empresa:
                    if l.name and 'Deposito Boleta Nro.' in l.name:
                        depo1=l.name[21:]
                        depo2=depo1[:depo1.find(' ')]
                        deposito=request.env['depositos.cheques'].search([('name','=',depo2),('tipo_deposito','=','cheque')])
                        if deposito:
                            try:
                                if deposito.cheques[0]:
                                    cheque=deposito.cheques[0]
                                    partner=cheque.source_partner_id
                                    if partner:
                                        sheet.write(i, a, partner.name)
                                        a += 1
                            except IndexError:
                                pass
                    else:
                        sheet.write(i, a, l.partner_id.name)
                        a+=1
                if record.mostrar_monedas:
                    moneda=l.currency_id
                    if not moneda:
                        moneda=user.company_id.currency_id
                    sheet.write_number(i, a, l.amount_currency,num_format)
                    a += 1
                    sheet.write(i, a, moneda.name)
                    a += 1
                if record.mostrar_cuenta_analitica:
                    cuenta_analitica = l.analytic_account_id
                    if cuenta_analitica:
                        sheet.write(i, a, l.analytic_account_id.name)
                    else:
                        sheet.write(i, a, "")

                debito_total = int(round(l.debit)) + debito_total
                credito_total = int(round(l.credit)) + credito_total
                acumulador = acumulador + 1
                i = i + 1
            if acumulador == record.cantidad_cuenta(l.account_id.id,record.partner_id.id):
                sheet.write(i,2,'TOTALES:',bold_2)
                sheet.write(i,3,debito_total ,num_format_bold)
                sheet.write(i,4,credito_total ,num_format_bold)
                sheet.write(i,5,saldo_cuenta ,num_format_bold)
                i=i+1
        i = i + 2
        sheet.write(i, 2, 'TOTALES:', bold_2)
        sheet.write(i, 3, total_debe, num_format_bold)
        sheet.write(i, 4, total_haber, num_format_bold)
        sheet.write(i, 5, total_balance, num_format_bold)

        workbook.close()
        fp.seek(0)
        new_report_from = record.desde.strftime('%d-%m-%Y')
        new_report_to = record.hasta.strftime('%d-%m-%Y')
        filename = 'Libro mayor del ' + str(new_report_from) + ' al ' + str(new_report_to) + '.xlsx'
        return request.make_response(fp.read(),
                                     [('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                                      ('Content-Disposition', content_disposition(filename))])

class DownloadPDF(http.Controller):
    def obtener_acumulado_anio(self, request, account_id, fecha_ini,partner_id):

        # periodo_fiscal = request.env.company.fiscalyear_last_month
        periodo_fiscal = account_id.company_id.fiscalyear_last_month or request.env.company.fiscalyear_last_month
        fi = datetime.strptime(str(fecha_ini), '%Y-%m-%d')
        anio = fi.year
        if not periodo_fiscal == '12':
            mes = int(periodo_fiscal) + 1
            anio = anio - 1
        else:
            mes = 1
        fecha_inicio_anio = str(anio) + '-' + str(mes) + '-01'
        fi = datetime.strptime(fecha_inicio_anio, '%Y-%m-%d')
        if partner_id:
            lineas_asiento = request.env['account.move.line'].search(
                [('move_id.date', '>=', fecha_inicio_anio), ('move_id.date', '<', fecha_ini),
                 ('move_id.state', '=', 'posted'),
                 ('account_id', '=', account_id.id),('partner_id','=',partner_id.id)])

        else:
            lineas_asiento = request.env['account.move.line'].search(
                [('move_id.date', '>=', fecha_inicio_anio), ('move_id.date', '<', fecha_ini),
                 ('move_id.state', '=', 'posted'),
                 ('account_id', '=', account_id.id)])

        total = sum(lineas_asiento.mapped('balance'))
        return total

    def agregar_punto_de_miles(self, numero):
        numero = round(numero)
        if numero >= 0:
            numero_con_punto = '.'.join(
                [str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
        else:
            numero *= -1
            numero_con_punto = '.'.join(
                [str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
            numero_con_punto = '-' + numero_con_punto
        num_return = numero_con_punto
        return num_return

    @http.route('/getLibroMayor/pdf/<int:id>', auth='public')
    def generarPDF(self, id=None, **kw):

        record = request.env['libro_mayor.wizard.libro_mayor'].browse(id)
        domain=[]
        domain+=[('company_id', '=', record.company_id.id), ('move_id.date', '>=', record.desde)
            ,('move_id.date', '<=', record.hasta), ('move_id.state', '=', 'posted')]
        if record.partner_id:
            domain += [('partner_id', 'in', record.partner_id.mapped('id'))]

        if record.account_ids:
            # lineas_asiento = request.env['account.move.line'].search(
            #     [('company_id', '=', record.company_id.id), ('move_id.date', '>=', record.desde),
            #      ('move_id.date', '<=', record.hasta), ('move_id.state', '=', 'posted'),
            #      ('account_id', 'in', record.account_ids.mapped('id'))])
            domain+=[('account_id', 'in', record.account_ids.mapped('id'))]

        # else:
        #     lineas_asiento = request.env['account.move.line'].search(
        #         [('company_id', '=', record.company_id.id), ('move_id.date', '>=', record.desde),
        #          ('move_id.date', '<=', record.hasta),
        #          ('move_id.state', '=', 'posted')])
        lineas_asiento=request.env['account.move.line'].search(domain)


        lineas_asiento=lineas_asiento.filtered(lambda r:r.balance != 0 )
        lineas_asiento = lineas_asiento.sorted(key=lambda p: (p.account_id.code, p.move_id.date,p.move_id.num_asiento,p.credit))

        total_debe = 0
        total_haber = 0
        # int(round(
        for l in lineas_asiento.filtered(lambda r: r.debit != 0):
            total_debe += int(round(l.debit))
        for l in lineas_asiento.filtered(lambda r: r.credit != 0):
            total_haber += int(round(l.credit))
        #total_debe=sum([l.debit for l in lineas_asiento.filtered(lambda r:r.debit !=0)])
        #total_haber=sum([l.credit for l in lineas_asiento.filtered(lambda r:r.credit !=0)])
        total_balance=total_debe-total_haber

        diccionario_linea = collections.OrderedDict()
        cuenta_actual = ''
        lineas = []
        ban = 0

        for l in lineas_asiento:
            if ban == 0:
                cuenta_actual = l.account_id
                ban = 1
            if cuenta_actual != l.account_id:
                # if lineas:
                saldo = self.obtener_acumulado_anio(request, cuenta_actual, record.desde,record.partner_id)
                diccionario_linea.setdefault(cuenta_actual, [lineas, saldo])
                lineas = []
                lineas.append(l)
                cuenta_actual = l.account_id
            else:
                lineas.append(l)
        if len(lineas_asiento)>0:
            saldo = self.obtener_acumulado_anio(request, cuenta_actual, record.desde,record.partner_id)
            diccionario_linea.setdefault(cuenta_actual, [lineas, saldo])
        diccionario_linea = diccionario_linea.items()

        # reporte pdf con reportlab
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4, bottomup=0)

        width, heigth = A4
        user = record.env.user
        tz = pytz.timezone(user.partner_id.tz) or pytz.utc
        fecha_actual=pytz.utc.localize(datetime.now()).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S")
        cabecera=('FECHA','REF','DETALLE','DEBITO','CREDITO','SALDO')
        desde=record.desde.strftime('%d/%m/%Y')
        hasta=record.hasta.strftime('%d/%m/%Y')
        mje_filtro='LIBRO MAYOR'

        if record.mostrar_titulo:
            filtro_titulo = 'LIBRO MAYOR'
        else:
            filtro_titulo = ''
        if record.mostrar_fecha:
            filtro_desde='Desde: '+str(desde) + ' Hasta: '+str(hasta)
        else:
            filtro_desde = ''
        if record.mostrar_filtro:
            filtro_fecha='Fecha:'  +str(fecha_actual)
        else:
            filtro_fecha = ''
        #filtro_titulo='LIBRO MAYOR'


        filtro=(mje_filtro)
        detalles = []
        LINEAS = 52
        LINEAS_AUX = LINEAS
        cant_aux = 0  # auxiliar para las cantidad de lineas del reporte
        i = 0
        SIZE_FUENTE=7
        cantidad_de_lineas = i  # CANTIDAD DE LINEAS DEL REPORTE

        # INFORMACION O GUIA
        #  Comando coo ini  coo fin
        # ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        #            col fil col fil
        suma_debito = 0
        suma_credito = 0
        inicial = 0
        list_table = []

        move_actual = ''
        suma_debe = 0
        suma_credito = 0
        primera = 0
        x = 1.5
        y = 2
        nueva_pagina=True
        saltar_pagina=False
        transporte_debe=0
        transporte_haber=0
        saldo_anterior=0
        cantidad_letras=75
        cuenta_anterior=''
        ban_cuenta=0
        for dic in diccionario_linea:
            if ban_cuenta==0:
                cuenta_anterior=dic[0].name
                ban_cuenta=1

            cuenta = ['',dic[0].display_name, '', '', '', self.agregar_punto_de_miles(dic[1][1])]
            saldo_cuenta = dic[1][1]
            ban = 0
            transporte_debe = 0
            transporte_haber = 0
            for l in dic[1][0]:

                i += 1
                ref = ''
                if l.partner_id:
                    try:
                        ref = l.partner_id.name.strip()
                    except:
                        ref=''
                if l.move_id.ref:
                    if ref:
                        ref += ' / ' + l.move_id.ref.strip()
                    else:
                        ref =  l.move_id.ref.strip()
                else:
                    if l.name:
                        ref=l.name.strip()
                    else:
                        ref=''
                operacion = ''
                try:
                    if l.payment_id:
                        operacion = l.payment_id.name
                    elif l.move_id.nro_factura:
                        operacion = l.move_id.nro_factura
                    elif l.move_id.nro:
                        operacion = l.move_id.nro
                    elif l.move_id.stock_move_id.picking_id:
                        operacion = l.move_id.stock_move_id.picking_id.name
                except:
                    operacion=''
                if operacion:
                    ref+=' '+'('+operacion+')'
                else:
                    ref+=' '+'('+l.move_id.name+')'


                #si hay un cambio de cuenta
                if ban == 0:
                    ban = 1
                    if primera == 0:

                        if record.mostrar_filtro or record.mostrar_fecha or record.mostrar_titulo:
                            #IMPRESION DE FILTRO
                            c.setFont("Helvetica", 8)
                            c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                            c.setFont("Helvetica-Bold", 8)
                            c.drawString(10.5*cm, 1.5*cm, filtro_titulo)
                            c.drawString(9.2*cm, 1.8*cm, filtro_desde)


                        #IMPRESION DE LA CABECERA DE LA HOJA
                        list_table = []
                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                        list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                        table = Table([cabecera],
                                      colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                      rowHeights=(0.5 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        y = y + 0.5

                        cant_aux += 1
                        primera = 1

                    else:
                        cant_aux += 1
                        if cant_aux == LINEAS:
                            saltar_pagina=True


                        totales = ['TOTALES ' + cuenta_anterior, '', '', self.agregar_punto_de_miles(suma_debito),
                                   self.agregar_punto_de_miles(suma_credito),
                                   '']
                        suma_debito = 0
                        suma_credito = 0
                        list_table=[]
                        detalles=[]
                        detalles.append(totales)
                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                        list_table.append(('ALIGN', (0, 0), (0, 0), 'LEFT'))
                        list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                        # list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                        list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                        table = Table(detalles,
                                      colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                      rowHeights=(0.5 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        y = y + 0.5
                        if saltar_pagina:
                            cant_aux = 0
                            c.showPage()
                            y = 2

                            if record.mostrar_filtro or record.mostrar_fecha or record.mostrar_titulo:
                                # IMPRESION DE FILTRO
                                c.setFont("Helvetica", 8)
                                c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                                c.setFont("Helvetica-Bold", 8)
                                c.drawString(10.5 * cm, 1.5 * cm, filtro_titulo)
                                c.drawString(9.2 * cm, 1.8 * cm, filtro_desde)
                                # # IMPRESION DE FILTRO
                                # c.setFont("Helvetica-Bold", 8)
                                # c.drawString(3.5 * cm, 1.5 * cm, filtro_titulo)
                                # c.drawString(2.5 * cm, 1.8 * cm, filtro_desde)
                                # c.drawString(17 * cm, 1.8 * cm, filtro_fecha)

                            # IMPRESION DE LA CABECERA DE LA HOJA
                            list_table = []
                            list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                            list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                            list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                            list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                            table = Table([cabecera],
                                          colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                          rowHeights=(0.5 * cm))
                            table.setStyle(TableStyle(list_table))
                            table.wrapOn(c, width, heigth)
                            table.drawOn(c, x * cm, y * cm)
                            y = y + 0.5
                            cant_aux += 1

                            saltar_pagina=False
                            transporte_debe=0
                            transporte_haber=0

                    # IMPRIMOS EL NOMBRE DE LA CUENTA Y SU SALDO

                    cant_aux += 1
                    #Si solo queda una linea para agregar la cuenta con su saldo se salta a la proxima hoja
                    if cant_aux == LINEAS or cant_aux+1 == LINEAS:
                        cant_aux = 0
                        c.showPage()
                        y=2
                        transporte_debe = 0
                        transporte_haber = 0

                        if record.mostrar_filtro or record.mostrar_fecha or record.mostrar_titulo:
                            # IMPRESION DE FILTRO
                            c.setFont("Helvetica", 8)
                            c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                            c.setFont("Helvetica-Bold", 8)
                            c.drawString(10.5 * cm, 1.5 * cm, filtro_titulo)
                            c.drawString(9.2 * cm, 1.8 * cm, filtro_desde)

                        # if record.mostrar_filtro:
                        #     # IMPRESION DE FILTRO
                        #     c.setFont("Helvetica-Bold", 8)
                        #     c.drawString(3.5 * cm, 1.5 * cm, filtro_titulo)
                        #     c.drawString(2.5 * cm, 1.8 * cm, filtro_desde)
                        #     c.drawString(17 * cm, 1.8 * cm, filtro_fecha)

                        #Se genera la cabecera de la nueva hoja
                        list_table = []
                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                        list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                        table = Table([cabecera],
                                      colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                      rowHeights=(0.5 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        y = y + 0.5
                        cant_aux += 1

                    list_table = []
                    detalles = []
                    list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                    list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                    list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                    list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                    detalles.append(cuenta)
                    table = Table(detalles,
                                  colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                  rowHeights=(0.5 * cm))
                    table.setStyle(TableStyle(list_table))
                    table.wrapOn(c, width, heigth)
                    table.drawOn(c, x * cm, y * cm)
                    y = y + 0.5

                    # SE IMPRIME EL MOVIMIENTO DE LA CUENTA

                    cant_aux += 1
                    # si cant_aux es igual a la cantidad de lineas significa que ya se debe agregar el transporte
                    # y pasar la otra linea el movimiento
                    if cant_aux == LINEAS:
                        cant_aux = 0
                        transporte = ['TRANSPORTE', '', '', self.agregar_punto_de_miles(transporte_debe),
                                   self.agregar_punto_de_miles(transporte_haber),
                                   self.agregar_punto_de_miles()]
                        list_table=[]
                        detalles=[]
                        detalles.append(transporte)
                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                        list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                        # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                        table = Table(detalles,
                                      colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                      rowHeights=(0.5 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        c.showPage()
                        y = 2

                        if record.mostrar_filtro or record.mostrar_fecha or record.mostrar_titulo:
                            # IMPRESION DE FILTRO
                            c.setFont("Helvetica", 8)
                            c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                            c.setFont("Helvetica-Bold", 8)
                            c.drawString(10.5 * cm, 1.5 * cm, filtro_titulo)
                            c.drawString(9.2 * cm, 1.8 * cm, filtro_desde)

                        # if record.mostrar_filtro:
                        #     # IMPRESION DE FILTRO
                        #     c.setFont("Helvetica-Bold", 8)
                        #     c.drawString(3.5 * cm, 1.5 * cm, filtro_titulo)
                        #     c.drawString(2.5 * cm, 1.8 * cm, filtro_desde)
                        #     c.drawString(17 * cm, 1.8 * cm, filtro_fecha)

                        #Se imprime la cabecera de la nueva hoja
                        list_table = []
                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                        list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                        list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                        table = Table([cabecera],
                                      colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                      rowHeights=(0.5 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        y = y + 0.5

                        # Se imprime de nuevo el transporte en la nueva pagina
                        list_table = []
                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-1, -1), 'RIGHT'))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                        # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))

                        table = Table(detalles,
                                      colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                      rowHeights=(0.5 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        y = y + 0.5
                        cant_aux+=2

                    debito = self.agregar_punto_de_miles(l.debit)
                    suma_debito += int(round(l.debit))
                    transporte_debe += int(round(l.debit))
                    credito = self.agregar_punto_de_miles(int(round(l.credit)))
                    suma_credito += int(round(l.credit))
                    transporte_haber += int(round(l.credit))
                    diferencia = (int(round(l.debit)) - int(round(l.credit)))
                    saldo_cuenta += diferencia
                    fecha = datetime.strptime(str(l.move_id.date), "%Y-%m-%d").strftime('%d/%m/%Y')
                    fin=0
                    if len(ref)>cantidad_letras:
                        letras=''
                        tam = int(len(ref) / cantidad_letras)+1
                        utlimo_espacio = 0
                        inicio = 0
                        for cant in range(0, tam):
                            inicio = utlimo_espacio
                            fin = inicio + cantidad_letras
                            pal = ref[inicio:fin]
                            if len(pal) >= cantidad_letras:
                                i = 0
                                for r in pal:
                                    i += 1
                                    if r.isspace():
                                        utlimo_espacio = i
                                fin = utlimo_espacio + inicio
                                utlimo_espacio = fin
                                letras = ref[inicio:fin]
                            else:
                                letras = pal

                            # SE IMPRIME LA LINEA
                            if fin <len(ref):
                                if inicio==0:
                                    lista_letras=[fecha, l.move_id.num_asiento, letras, '', '','']
                                else:
                                    lista_letras = ['', '', letras, '', '', '']
                                list_table = []
                                detalles = []
                                detalles.append(lista_letras)
                                list_table.append(('FONTNAME', (0, 0), (0, 0), 'Times-Bold'))
                                list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                                list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                                list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                                list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                                table = Table(detalles,
                                              colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                              rowHeights=(0.5 * cm))
                                table.setStyle(TableStyle(list_table))
                                table.wrapOn(c, width, heigth)
                                table.drawOn(c, x * cm, y * cm)
                                y = y + 0.5

                                cant_aux+=1
                                # si cant_aux es igual a la cantidad de lineas significa que ya se debe agregar el transporte
                                # y pasar la otra linea el movimiento
                                if cant_aux == LINEAS:
                                    cant_aux = 0
                                    if cant + 1 == tam:
                                        transporte = ['TRANSPORTE', '', '', self.agregar_punto_de_miles(transporte_debe),
                                                  self.agregar_punto_de_miles(transporte_haber),'']
                                    else:
                                        transporte = ['TRANSPORTE', '', '', self.agregar_punto_de_miles(transporte_debe - l.debit),
                                                  self.agregar_punto_de_miles(transporte_haber - l.credit),'']

                                    list_table = []
                                    detalles = []
                                    detalles.append(transporte)
                                    list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                                    list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                                    list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                                    list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                                    # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                                    table = Table(detalles,
                                                  colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                                  rowHeights=(0.5 * cm))
                                    table.setStyle(TableStyle(list_table))
                                    table.wrapOn(c, width, heigth)
                                    table.drawOn(c, x * cm, y * cm)
                                    c.showPage()
                                    y = 2

                                    if record.mostrar_filtro or record.mostrar_fecha or record.mostrar_titulo:
                                        # IMPRESION DE FILTRO
                                        c.setFont("Helvetica", 8)
                                        c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                                        c.setFont("Helvetica-Bold", 8)
                                        c.drawString(10.5 * cm, 1.5 * cm, filtro_titulo)
                                        c.drawString(9.2 * cm, 1.8 * cm, filtro_desde)

                                    # if record.mostrar_filtro:
                                    #     # IMPRESION DE FILTRO
                                    #     c.setFont("Helvetica-Bold", 8)
                                    #     c.drawString(3.5 * cm, 1.5 * cm, filtro_titulo)
                                    #     c.drawString(2.5 * cm, 1.8 * cm, filtro_desde)
                                    #     c.drawString(17 * cm, 1.8 * cm, filtro_fecha)

                                    # Se imprime la cabecera de la nueva hoja
                                    list_table = []
                                    list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                                    list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                                    list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                                    list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                                    list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                                    table = Table([cabecera],
                                                  colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                                  rowHeights=(0.5 * cm))
                                    table.setStyle(TableStyle(list_table))
                                    table.wrapOn(c, width, heigth)
                                    table.drawOn(c, x * cm, y * cm)
                                    y = y + 0.5

                                    # Se imprime de nuevo el transporte en la nueva pagina
                                    list_table = []
                                    list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                                    list_table.append(('ALIGN', (0, 0), (-1, -1), 'RIGHT'))
                                    list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                                    # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))

                                    table = Table(detalles,
                                                  colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                                  rowHeights=(0.5 * cm))
                                    table.setStyle(TableStyle(list_table))
                                    table.wrapOn(c, width, heigth)
                                    table.drawOn(c, x * cm, y * cm)
                                    y = y + 0.5
                                    cant_aux += 2
                    else:
                        letras=ref


                    if fin==0:
                        this_s = [fecha, l.move_id.num_asiento, letras, debito, credito,
                              self.agregar_punto_de_miles(saldo_cuenta)]
                    else:
                        this_s = ['', '', letras, debito, credito,
                              self.agregar_punto_de_miles(saldo_cuenta)]
                    list_table=[]
                    detalles=[]
                    detalles.append(this_s)
                    list_table.append(('FONTNAME', (0, 0), (0, 0), 'Times-Bold'))
                    list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                    list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                    list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                    list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                    table = Table(detalles,
                                  colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                  rowHeights=(0.5 * cm))
                    table.setStyle(TableStyle(list_table))
                    table.wrapOn(c, width, heigth)
                    table.drawOn(c, x * cm, y * cm)
                    y = y + 0.5

                # SI NO HAY CAMBIO DE CUENTA IMPRIMIR SUS MOVIMIENTOS
                else:
                    cant_aux += 1
                    # si cant_aux es igual a la cantidad de lineas significa que ya se debe agregar el transporte
                    # y pasar la otra linea el movimiento
                    if cant_aux == LINEAS:
                        cant_aux = 0
                        transporte = ['TRANSPORTE', '', '', self.agregar_punto_de_miles(transporte_debe),
                                      self.agregar_punto_de_miles(transporte_haber),
                                      '']
                        list_table = []
                        detalles = []
                        detalles.append(transporte)
                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                        list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                        # list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                        # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                        table = Table(detalles,
                                      colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                      rowHeights=(0.5 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        c.showPage()
                        y = 2

                        if record.mostrar_filtro or record.mostrar_fecha or record.mostrar_titulo:
                            # IMPRESION DE FILTRO
                            c.setFont("Helvetica", 8)
                            c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                            c.setFont("Helvetica-Bold", 8)
                            c.drawString(10.5 * cm, 1.5 * cm, filtro_titulo)
                            c.drawString(9.2 * cm, 1.8 * cm, filtro_desde)

                        # if record.mostrar_filtro:
                        #     # IMPRESION DE FILTRO
                        #     c.setFont("Helvetica-Bold", 8)
                        #     c.drawString(3.5*cm, 1.5*cm, filtro_titulo)
                        #     c.drawString(2.5*cm, 1.8*cm, filtro_desde)
                        #     c.drawString(17*cm, 1.8*cm, filtro_fecha)

                        # Se imprime la cabecera de la nueva hoja
                        list_table = []
                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                        list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                        table = Table([cabecera],
                                      colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                      rowHeights=(0.5 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        y = y + 0.5

                        # Se imprime de nuevo el transporte en la nueva pagina
                        list_table = []
                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                        list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                        # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                        table = Table(detalles,
                                      colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                      rowHeights=(0.5 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        y = y + 0.5
                        cant_aux += 2

                    debito = self.agregar_punto_de_miles(int(round(l.debit)))
                    suma_debito += int(round(l.debit))
                    transporte_debe += int(round(l.debit))
                    credito = self.agregar_punto_de_miles(int(round(l.credit)))
                    suma_credito += int(round(l.credit))
                    transporte_haber += int(round(l.credit))
                    diferencia = (int(round(l.debit)) - int(round(l.credit)))
                    saldo_cuenta += diferencia
                    saldo_anterior=saldo_cuenta
                    fecha = datetime.strptime(str(l.move_id.date), "%Y-%m-%d").strftime('%d/%m/%Y')
                    fin = 0
                    if len(ref)>cantidad_letras:
                        letras=''
                        tam=int(len(ref)/cantidad_letras)+1
                        utlimo_espacio = 0
                        inicio=0
                        for cant in range(0,tam):
                            inicio=utlimo_espacio
                            fin=inicio+cantidad_letras
                            pal = ref[inicio:fin]
                            if len(pal) >= cantidad_letras:
                                i = 0
                                for r in pal:
                                    i += 1
                                    if r.isspace():
                                        utlimo_espacio = i
                                fin=utlimo_espacio+inicio
                                utlimo_espacio = fin
                                letras = ref[inicio:fin]
                            else:
                                letras=pal
                            # SE IMPRIME LA LINEA
                            if fin < len(ref):
                                if inicio == 0:
                                    lista_letras = [fecha, l.move_id.num_asiento, letras, '', '', '']
                                else:
                                    lista_letras = ['', '', letras, '', '', '']
                                list_table = []
                                detalles = []
                                detalles.append(lista_letras)
                                list_table.append(('FONTNAME', (0, 0), (0, 0), 'Times-Bold'))
                                list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                                list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                                list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                                list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                                table = Table(detalles,
                                              colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                              rowHeights=(0.5 * cm))
                                table.setStyle(TableStyle(list_table))
                                table.wrapOn(c, width, heigth)
                                table.drawOn(c, x * cm, y * cm)
                                y = y + 0.5

                                cant_aux += 1
                                # si cant_aux es igual a la cantidad de lineas significa que ya se debe agregar el transporte
                                # y pasar la otra linea el movimiento
                                if cant_aux == LINEAS:
                                    cant_aux = 0
                                    # antes de hacer el salto de pagina se verifica si es la ultima linea de la referencia para ver si el monto
                                    # del transporte se debe restar o no por la ultima suma (se corrige bug ticket 623)
                                    if cant+1 ==tam:
                                        transporte = ['TRANSPORTE', '', '', self.agregar_punto_de_miles(transporte_debe),
                                                  self.agregar_punto_de_miles(transporte_haber),'']
                                    else:
                                        transporte = ['TRANSPORTE', '', '', self.agregar_punto_de_miles(transporte_debe-l.debit),
                                                  self.agregar_punto_de_miles(transporte_haber-l.credit),'']
                                    list_table = []
                                    detalles = []
                                    detalles.append(transporte)
                                    list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                                    list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                                    list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                                    list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                                    # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                                    table = Table(detalles,
                                                  colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                                  rowHeights=(0.5 * cm))
                                    table.setStyle(TableStyle(list_table))
                                    table.wrapOn(c, width, heigth)
                                    table.drawOn(c, x * cm, y * cm)
                                    c.showPage()
                                    y = 2

                                    if record.mostrar_filtro or record.mostrar_fecha or record.mostrar_titulo:
                                        # IMPRESION DE FILTRO
                                        c.setFont("Helvetica", 8)
                                        c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                                        c.setFont("Helvetica-Bold", 8)
                                        c.drawString(10.5 * cm, 1.5 * cm, filtro_titulo)
                                        c.drawString(9.2 * cm, 1.8 * cm, filtro_desde)

                                    # if record.mostrar_filtro:
                                    #     # IMPRESION DE FILTRO
                                    #     c.setFont("Helvetica-Bold", 8)
                                    #     c.drawString(3.5 * cm, 1.5 * cm, filtro_titulo)
                                    #     c.drawString(2.5 * cm, 1.8 * cm, filtro_desde)
                                    #     c.drawString(17 * cm, 1.8 * cm, filtro_fecha)

                                    # Se imprime la cabecera de la nueva hoja
                                    list_table = []
                                    list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                                    list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                                    list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                                    list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                                    list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                                    table = Table([cabecera],
                                                  colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                                  rowHeights=(0.5 * cm))
                                    table.setStyle(TableStyle(list_table))
                                    table.wrapOn(c, width, heigth)
                                    table.drawOn(c, x * cm, y * cm)
                                    y = y + 0.5

                                    # Se imprime de nuevo el transporte en la nueva pagina
                                    list_table = []
                                    list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                                    list_table.append(('ALIGN', (0, 0), (-1, -1), 'RIGHT'))
                                    list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                                    # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))

                                    table = Table(detalles,
                                                  colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                                  rowHeights=(0.5 * cm))
                                    table.setStyle(TableStyle(list_table))
                                    table.wrapOn(c, width, heigth)
                                    table.drawOn(c, x * cm, y * cm)
                                    y = y + 0.5
                                    cant_aux += 2
                    else:
                        letras=ref
                    if fin==0:
                        this_s = [fecha, l.move_id.num_asiento, letras, debito, credito,
                              self.agregar_punto_de_miles(saldo_cuenta)]
                    else:
                        this_s = ['', '', letras, debito, credito,
                              self.agregar_punto_de_miles(saldo_cuenta)]
                    list_table=[]
                    detalles=[]
                    detalles.append(this_s)
                    list_table.append(('FONTNAME', (0, 0), (0, 0), 'Times-Bold'))
                    list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                    list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
                    list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
                    list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                    table = Table(detalles,
                                  colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                                  rowHeights=(0.5 * cm))
                    table.setStyle(TableStyle(list_table))
                    table.wrapOn(c, width, heigth)
                    table.drawOn(c, x * cm, y * cm)
                    y = y + 0.5
                if cuenta_anterior != dic[0].name:
                    cuenta_anterior=dic[0].name



        totales = ['TOTALES ' + cuenta_anterior, '', '', self.agregar_punto_de_miles(suma_debito),
                   self.agregar_punto_de_miles(suma_credito),
                   '']
        suma_debito = 0
        suma_credito = 0
        list_table = []
        detalles = []
        detalles.append(totales)
        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
        list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
        list_table.append(('ALIGN', (0, 0), (0, 0), 'LEFT'))
        list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
        # list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
        list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
        list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
        table = Table(detalles,
                      colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                      rowHeights=(0.5 * cm))
        table.setStyle(TableStyle(list_table))
        table.wrapOn(c, width, heigth)
        table.drawOn(c, x * cm, y * cm)
        cant_aux=+1
        if cant_aux == LINEAS:
            c.showPage()
            y = 2

            if record.mostrar_filtro or record.mostrar_fecha or record.mostrar_titulo:
                # IMPRESION DE FILTRO
                c.setFont("Helvetica", 8)
                c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                c.setFont("Helvetica-Bold", 8)
                c.drawString(10.5 * cm, 1.5 * cm, filtro_titulo)
                c.drawString(9.2 * cm, 1.8 * cm, filtro_desde)

            # if record.mostrar_filtro:
            #     # IMPRESION DE FILTRO
            #     c.setFont("Helvetica-Bold", 8)
            #     c.drawString(3.5 * cm, 1.5 * cm, filtro_titulo)
            #     c.drawString(2.5 * cm, 1.8 * cm, filtro_desde)
            #     c.drawString(17 * cm, 1.8 * cm, filtro_fecha)

            # Se imprime la cabecera de la nueva hoja
            list_table = []
            list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
            list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
            list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
            list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
            list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
            table = Table([cabecera],
                          colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                          rowHeights=(0.5 * cm))
            table.setStyle(TableStyle(list_table))
            table.wrapOn(c, width, heigth)
            table.drawOn(c, x * cm, y * cm)
            y = y + 1.5
            totales = ['TOTALES', '', '', self.agregar_punto_de_miles(total_debe),
                       self.agregar_punto_de_miles(total_haber),self.agregar_punto_de_miles(total_balance)]
            list_table = []
            detalles = []
            detalles.append(totales)
            list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
            list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
            list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
            # list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
            list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
            list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
            table = Table(detalles,
                          colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                          rowHeights=(0.5 * cm))
            table.setStyle(TableStyle(list_table))
            table.wrapOn(c, width, heigth)
            table.drawOn(c, x * cm, y * cm)
        else:
            y = y + 1.5
            totales = ['TOTALES', '', '', self.agregar_punto_de_miles(total_debe),
                       self.agregar_punto_de_miles(total_haber), self.agregar_punto_de_miles(total_balance)]
            list_table = []
            detalles = []
            detalles.append(totales)
            list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
            list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
            list_table.append(('ALIGN', (3, 0), (-1, -1), 'RIGHT'))
            # list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
            list_table.append(('FONTSIZE', (0, 0), (-1, -1), SIZE_FUENTE))
            list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
            table = Table(detalles,
                          colWidths=[2 * cm, 1 * cm, 10 * cm, 2 * cm, 2 * cm, 2 * cm],
                          rowHeights=(0.5 * cm))
            table.setStyle(TableStyle(list_table))
            table.wrapOn(c, width, heigth)
            table.drawOn(c, x * cm, y * cm)












        c.save()
        _logger.info('cantidad de lineas asiento')
        _logger.info(len(lineas_asiento))
        _logger.info('cantidad de lineas asiento recorridas')
        _logger.info(i)
        # print('cantidad de lineas asiento')
        # print(len(lineas_asiento))
        # print('cantidad de lineas asiento recorridas')
        # print(i)
        pdf = buffer.getvalue()
        buffer.close()
        print(type(c))


        new_report_from = record.desde.strftime('%d-%m-%Y')
        new_report_to = record.hasta.strftime('%d-%m-%Y')
        filename = 'Libro mayor del ' + str(new_report_from) + ' al ' + str(new_report_to) + '.pdf'
        return request.make_response(
            pdf,
            [('Content-Type', 'application/pdf'),
             ('Content-Disposition', content_disposition(filename))])



