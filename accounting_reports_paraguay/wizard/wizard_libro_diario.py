# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time, collections
import io
from odoo.exceptions import ValidationError
import xlsxwriter
import logging
from datetime import date

import base64
import xlwt
import base64
import xlsxwriter
from io import StringIO
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception,content_disposition
_logger = logging.getLogger(__name__)
import werkzeug
from datetime import date,datetime
import pytz


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

class WizardReportLibroDiario(models.TransientModel):
    _name = "libro_diario.wizard.libro_diario"

    periodo = fields.Integer(string="Periodo fiscal")
    renumerar = fields.Boolean(string="Renumerar asientos", help="Marcar en caso que se requiera renumerar los asientos")
    journal_ids = fields.Many2many('account.journal',string="Diarios",default=lambda self: self._get_default_journals())
    tipo = fields.Selection([('xlsx','XLSX'),('pdf','PDF')],string="Tipo de archivo",default='pdf')
    desde = fields.Date(string="Fecha desde")
    hasta = fields.Date(string="Fecha hasta")
    mostrar_numeracion = fields.Boolean(string="Mostrar Nro. de página")
    mostrar_filtro=fields.Boolean(default=True,string='Mostrar Filtros')
    mostrar_titulo = fields.Boolean(string="Mostrar Titulo")
    mostrar_fecha = fields.Boolean(string="Mostrar Fecha")
    mostrar_encabezado = fields.Boolean(string="Mostrar Encabezado")
    company_id = fields.Many2one(
        'res.company',
        string="Compañía",
        default=lambda self: self.env.company
    )



    def _get_default_journals(self):
        journals = self.env['account.journal'].search([('company_id','=',self.env.company.id)])
        return journals.mapped('id')

    
    def check_report(self):
        data = {}
        data['form'] = self.read(['periodo','renumerar','journal_ids','tipo'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['periodo','renumerar','journal_ids','tipo'])[0])
        if self.tipo == 'pdf':
            return {
                'type': 'ir.actions.act_url',
                'url': '/getLibroDiario/pdf/' + str(self.id),
                'target': 'current'
            }
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': '/getLibroDiario/'+str(self.id),
                'target': 'current'
            }
    def print_report_xlsx(self):
        data = {}
        data['form'] = self.read(['periodo','renumerar','journal_ids','tipo'])[0]
        data['form'].update(self.read(['periodo', 'renumerar', 'journal_ids', 'tipo'])[0])

        return self.env['report'].get_action(self, 'accounting_reports_paraguay.libro_diario_paraguay_report_xlsx', data=data)

    def agregar_punto_de_miles(self, numero):
        if numero >= 0:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
        else:
            numero*=-1
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
            numero_con_punto='-'+numero_con_punto
        num_return = numero_con_punto
        return num_return

    def pdf_completo(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/getLibroDiario/pdf/' + str(self.id),
            'target': 'current'
        }


class ReporteLibroDiario(models.AbstractModel):
    _name = 'report.accounting_reports_paraguay.libro_diario_paraguay_report'

    
    def _get_report_values(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        for diarios in docs.journal_ids:
            _logger.info('diario %s' % diarios.name)
        lineas_asiento = self.env['account.move.line'].search([('move_id.date', '>=', docs.desde), ('move_id.date', '<=', docs.hasta), ('move_id.state', '=', 'posted'),('journal_id', 'in', docs.journal_ids.mapped('id'))])
        # lineas_asiento = self.env['account.move.line'].search([('move_id','=',311)])
        if docs.renumerar:
            if len(lineas_asiento) > 0:
                lineas_asiento[0].move_id.with_context(company_id=lineas_asiento[0].move_id.company_id).renumerar_asientos(docs.periodo)
        lineas_asiento = lineas_asiento.sorted(lambda x : x.move_id.num_asiento)


        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'time': time,
            'lineas': lineas_asiento
        }


        return docargs


class DownloadXLS(http.Controller):
    @http.route('/getLibroDiario/<int:id>', auth='public')
    def generarXLSX(self, id=None, **kw):
        record = request.env['libro_diario.wizard.libro_diario'].browse(id)
        move_actual = None
        i = 2
        fp = io.BytesIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        lineas_asiento = request.env['account.move.line'].search(
            [('move_id.date', '>=', record.desde),('move_id.company_id','=',record.journal_ids[0].company_id.id) ,('move_id.date', '<=', record.hasta), ('move_id.state', '=', 'posted'),
             ('journal_id', 'in', record.journal_ids.mapped('id'))])
        lineas_asiento = lineas_asiento.filtered(lambda r: r.balance != 0)
        lineas_asiento = lineas_asiento.sorted(key=lambda x: (x.move_id.num_asiento, x.prioridad, x.account_id.code))
        if record.renumerar:
            if len(lineas_asiento) > 0:
                lineas_asiento[0].move_id.with_context(company_id=lineas_asiento[0].move_id.company_id).renumerar_asientos(record.periodo)
        sheet = workbook.add_worksheet('Libro Diario')
        bold = workbook.add_format({'bold': True, 'fg_color': 'gray', 'align': 'center'})
        border = workbook.add_format({'border': 1})
        # Create a format to use in the merged range.
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#F15F40',
            'font_color': 'white'})
        sheet.merge_range('A1:E1', 'LIBRO DIARIO', merge_format)
        sheet.set_column('A:E', 25)
        sheet.write(1, 0, 'Asiento', bold)
        sheet.write(1, 1, 'Fecha', bold)
        sheet.write(1, 2, 'Cuenta', bold)
        sheet.write(1, 3, 'Descripción', bold)
        sheet.write(1, 4, 'Operación', bold)
        sheet.write(1, 5, 'Debe', bold)
        sheet.write(1, 6, 'Haber', bold)
        date_format = workbook.add_format({'num_format': 'dd/mm/yy'})

        for l in lineas_asiento:
            if len(l.move_id.line_ids.filtered(lambda r: r.balance != 0)) > 1:
                if l.move_id != move_actual:
                    move_actual = l.move_id
                    ref = ''
                    if l.partner_id or l.move_id.partner_id:
                        ref += l.partner_id.name +  ' / ' if l.partner_id else l.move_id.partner_id.name + ' / '
                    if l.move_id.ref:
                        ref += l.move_id.ref
                    else:
                        ref += l.name or ' / '
                    ref = " ".join(ref.split())
                    operacion = '('
                    oper = False
                    try:
                        if l.payment_id:
                            operacion += l.payment_id.name
                            oper = True
                        elif l.move_id.nro_factura:
                            operacion += l.move_id.nro_factura
                            oper = True
                        elif l.move_id.nro:
                            operacion += l.move_id.nro
                            oper = True
                        elif l.move_id.stock_move_id.picking_id:
                            operacion += l.move_id.stock_move_id.picking_id.name
                            oper = True
                    except:
                        operacion+=''
                    operacion += ')'
                    sheet.write(i,0,l.move_id.num_asiento)
                    sheet.write(i,1,l.move_id.date,date_format)
                    sheet.write(i,3,ref)
                    if oper:
                        sheet.write(i,4,operacion)
                    i = i + 1
                    sheet.write(i, 0, l.account_id.code)
                    sheet.write(i, 2, l.account_id.name)
                    sheet.write(i, 3, l.name)
                    sheet.write(i, 5, l.debit)
                    sheet.write(i, 6, l.credit)
                else:
                    sheet.write(i, 0, l.account_id.code)
                    sheet.write(i, 2, l.account_id.name)
                    sheet.write(i, 3, l.name)
                    sheet.write(i, 5, l.debit)
                    sheet.write(i, 6, l.credit)
            i = i + 1
        workbook.close()
        fp.seek(0)
        return request.make_response(fp.read(),
                                     [('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                                      ('Content-Disposition', content_disposition('libro_diario.xlsx'))])

class DownloadPDF(http.Controller):
        def obtener_acumulado_anio(self, request, account_id, fecha_ini):

            periodo_fiscal = request.env.company.fiscalyear_last_month
            fi = datetime.strptime(fecha_ini, '%Y-%m-%d')
            anio = fi.year
            if not periodo_fiscal == 12:
                mes = periodo_fiscal + 1
                anio = anio - 1
            else:
                mes = 1
            fecha_inicio_anio = str(anio) + '-' + str(mes) + '-01'
            fi = datetime.strptime(fecha_inicio_anio, '%Y-%m-%d')
            lineas_asiento = request.env['account.move.line'].search(
                [('display_type','=', False),('move_id.date', '>=', fecha_inicio_anio), ('move_id.date', '<', fecha_ini),
                 ('move_id.state', '=', 'posted'),
                 ('account_id', '=', account_id.id)])


            total = sum(lineas_asiento.mapped('balance'))
            return total

        def agregar_punto_de_miles(self, numero):
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

        def getOperacion(self,line):
            oper = False
            operacion = ''
            try:
                if line.payment_id:
                    operacion += line.payment_id.name
                    return operacion
                elif line.move_id.nro_factura:
                    operacion += line.move_id.nro_factura
                    return operacion
                elif line.move_id.nro:
                    operacion += line.move_id.nro
                    return operacion
                elif line.move_id.stock_move_id.picking_id:
                    operacion += line.move_id.stock_move_id.picking_id.name
                    return operacion
                else:
                    trf = request.env['transferencias.entre.cuentas'].search([('move_id','=',line.move_id.id)])
                    if len(trf) > 0:
                        operacion += trf[0].name
                        return operacion
                    dep = request.env['depositos.cheques'].search([('asiento_contable','=',line.move_id.id)])
                    if len(dep) > 0:
                        operacion += dep[0].name
                        return operacion
            except:
                return operacion




        # IMPRESION DE CABECERA DE ASIENTO


        @http.route('/getLibroDiario/pdf/<int:id>', auth='public')
        def generarPDF(self, id=None, **kw):
            record = request.env['libro_diario.wizard.libro_diario'].browse(id)

            lineas_asiento = request.env['account.move.line'].search(
                [ ('display_type','=', False),('move_id.date', '>=', record.desde),
                 ('move_id.date', '<=', record.hasta), ('move_id.state', '=', 'posted'),
                 ('journal_id', 'in', record.journal_ids.mapped('id'))])
            if record.renumerar:
                if len(lineas_asiento) > 0:
                    lineas_asiento[0].move_id.with_context(company_id=lineas_asiento[0].move_id.company_id).renumerar_asientos(record.periodo)
            # lineas_asiento = lineas_asiento.sorted(key=lambda x: (x.move_id.num_asiento, x.prioridad, x.account_id.code))
            lineas_asiento = lineas_asiento.sorted(key=lambda x: (x.move_id.num_asiento, x.prioridad))
            pag = 0
            user = record.env.user

            tz = pytz.timezone(user.partner_id.tz) or pytz.utc
            fecha_actual = pytz.utc.localize(datetime.now()).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S")
            desde = record.desde.strftime('%d/%m/%Y')
            hasta = record.hasta.strftime('%d/%m/%Y')
            # lineas_asiento = lineas_asiento.filtered(lambda x:x.move_id.num_asiento == 2685)
            # reporte pdf con reportlab
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4,bottomup=0)

            width, heigth = A4

            cabecera = ('ASIENTO', 'FECHA', 'DESCRIPCIÓN','DEBE', 'HABER')

            detalles = []
            LINEAS = 72
            LINEAS_AUX = LINEAS
            cant_aux = 0  # auxiliar para las cantidad de lineas del reporte
            i = 0
            cantidad_de_lineas = i # CANTIDAD DE LINEAS DEL REPORTE

            # INFORMACION O GUIA
            #  Comando coo ini  coo fin
            # ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            #            col fil col fil
            suma_debito = 0
            suma_credito = 0
            inicial = 0
            list_table = []
            total_debito_asiento = 0
            total_credito_asiento = 0
            salto_de_linea = 0
            cant_caracteres = 50
            cant_linea_caracteres = 50
            move_actual = ''
            suma_debe = 0
            suma_credito = 0
            primera = 0
            altura = 0.35
            x=1.5
            y = 2
            filtro_nombre_company = False
            filtro_ruc_company = False

            if record.mostrar_encabezado:
                # Obtiene la compañía desde el wizard o usa la activa como respaldo
                company = getattr(record, 'company_id', request.env.company)
                filtro_nombre_company = company.name
                filtro_ruc_company = getattr(company, 'ruc', False)  # Usa getattr para evitar errores si el campo no existe
            if record.mostrar_titulo:
                filtro_titulo = 'LIBRO DIARIO'
            else:
                filtro_titulo = ''
            if record.mostrar_fecha:
                filtro_desde = 'Desde: ' + str(desde) + ' Hasta: ' + str(hasta)
            else:
                filtro_desde = ''
            if record.mostrar_filtro:
                filtro_fecha = 'Fecha:' + str(fecha_actual)
            else:
                filtro_fecha = ''
            oper = False
            for l in lineas_asiento:
                 if len(l.move_id.line_ids.filtered(lambda r: r.balance != 0)) > 1:
                    if l.name:
                        texto_linea = l.name[0:cant_linea_caracteres]
                    else:
                        texto_linea = ''
                    if cant_aux == 0:
                        if record.mostrar_filtro or record.mostrar_fecha or record.mostrar_titulo or record.mostrar_encabezado:
                            # IMPRESION DE FILTRO
                            c.setFont("Helvetica", 8)
                            c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                            c.setFont("Helvetica-Bold", 8)
                            c.drawString(10.5 * cm, 1.5 * cm, filtro_titulo)
                        if record.mostrar_encabezado:
                            # SE IMPRIME NOMBRE COMPAÑIA
                            c.drawString(100, 30, filtro_nombre_company)
                            c.drawString(9.2 * cm, 1.8 * cm, filtro_desde)


                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
                        list_table.append(('ALIGN', (5, 1), (-1, -1), 'RIGHT'))
                        # list_table.append(('LINEBELOW',(0,1), (0,-1),1,colors.black))
                        list_table.append(('GRID', (0, 0), (-1, -1), 1, colors.black))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), 7))
                        list_table.append(('VALIGN', (0, 0), (-1, -1), 'BOTTOM'))
                        table = Table([cabecera],
                                      colWidths=[2 * cm, 5 * cm, 7 * cm,  1.75 * cm, 1.75 * cm],
                                      rowHeights=(0.33 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x*cm, y*cm)
                        y = y + altura
                        cant_aux = +1
                        list_table = []
                        if primera > 0:
                            detalles = []
                            debito = self.agregar_punto_de_miles(suma_debito)
                            credito = self.agregar_punto_de_miles(suma_credito)
                            this_s = ['Transporte', '', '', debito, credito]
                            detalles.append(this_s)
                            if record.mostrar_filtro or record.mostrar_fecha or record.mostrar_titulo:
                                # IMPRESION DE FILTRO
                                c.setFont("Helvetica", 8)
                                c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                                c.setFont("Helvetica-Bold", 8)
                                c.drawString(10.5 * cm, 1.5 * cm, filtro_titulo)
                                c.drawString(9.2 * cm, 1.8 * cm, filtro_desde)

                                # c.setFont("Helvetica-Bold", 8)
                                # c.drawString(10.5 * cm, 1.5 * cm, filtro_titulo)
                                # c.drawString(9.2 * cm, 1.8 * cm, filtro_desde)
                                # c.drawString(17 * cm, 1.8 * cm, filtro_fecha)
                            list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                            list_table.append(('ALIGN', (0, 0), (-3, 0), 'CENTER'))
                            list_table.append(('ALIGN', (3, 0), (4, 0), 'RIGHT'))
                            list_table.append(('FONTSIZE', (0, 0), (-1, -1), 6))
                            table = Table(detalles,
                                          colWidths=[2 * cm, 5 * cm, 7 * cm, 1.75 * cm, 1.75 * cm],
                                          rowHeights=(0.33 * cm))
                            table.setStyle(TableStyle(list_table))
                            table.wrapOn(c, width, heigth)
                            table.drawOn(c, x * cm, y * cm)
                            y = y + altura
                            cant_aux = +1
                    if move_actual != l.move_id:
                        cont = 0
                        total_credito_asiento = 0
                        total_debito_asiento = 0
                        oper = False
                        detalles = []
                        move_actual = l.move_id
                        i += 1
                        if l.name:
                            if len(l.name) > 31:
                                det = l.name[0:31]
                            else:
                                det = l.name
                        else:
                            det = ''

                        if len(l.account_id.name) > 50:
                            det2 = l.account_id.name[0:50]
                        else:
                            det2 = l.account_id.name
                        ref = ''
                        if l.partner_id or l.move_id.partner_id:
                            ref += l.partner_id.name + ' / ' if l.partner_id else l.move_id.partner_id.name + ' / '
                        if l.move_id.ref:
                            ref +=  l.move_id.ref
                        else:
                            ref +=  l.name or ' / '
                        ref = " ".join(ref.split())
                        # IMPRESION DE CABECERA DE ASIENTO
                        string= ref
                        if len(string) <= cant_caracteres:
                            oper = self.getOperacion(l)
                            if oper:
                                if not oper in string:
                                    string += ' / ' + oper
                            else:
                                if not l.move_id.name in string:
                                    string += ' / ' + l.move_id.name

                        j = [l.move_id.num_asiento, l.move_id.date,string[0:cant_caracteres], '' ,'']
                        detalles.append(j)

                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Helvetica'))
                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                        list_table.append(('ALIGN', (5, 1), (-1, -1), 'RIGHT'))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), 7))
                        # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                        table = Table(detalles,
                                      colWidths=[2* cm, 5 * cm, 7 * cm,  1.75 * cm, 1.75 * cm],
                                      rowHeights=(0.33 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        y= y + altura
                        cant_aux += 1
                        detalles = []
                        if len(string) > cant_caracteres:
                            #IMPRIMIR SEGUNDA LINEA EN CASO DE REFERENCIAS LARGAS
                            string2 = string
                            if not (len(string2) > cant_caracteres * 2):
                                oper = self.getOperacion(l)
                                if oper:
                                    if not oper in string:
                                        string += ' / ' + oper
                                else:
                                    if not l.move_id.name in string:
                                        string += ' / ' + l.move_id.name
                            list_table = []
                            j = ['', '', string[cant_caracteres:cant_caracteres * 2], '', '']
                            detalles.append(j)

                            list_table.append(('FONTNAME', (0,   0), (-1, 0), 'Helvetica'))
                            list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                            list_table.append(('ALIGN', (5, 1), (-1, -1), 'RIGHT'))
                            # list_table.append(('GRID', (0, 0), (-2, -2), 1, colors.black))
                            list_table.append(('FONTSIZE', (0, 0), (-1, -1), 7))
                            # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                            table = Table(detalles,
                                          colWidths=[2 * cm, 5 * cm, 7 * cm, 1.75 * cm, 1.75 * cm],
                                          rowHeights=(0.33 * cm))
                            table.setStyle(TableStyle(list_table))
                            table.wrapOn(c, width, heigth)
                            table.drawOn(c, x * cm, y * cm)
                            y = y + altura
                            cant_aux += 1
                            detalles = []
                            if len(string) > cant_caracteres * 2:
                                string2 = string
                                if not (len(string2) > cant_caracteres * 3) and not oper:
                                    oper = self.getOperacion(l)
                                    if oper:
                                        if not oper in string:
                                            string += ' / ' + oper
                                    else:
                                        if not l.move_id.name in string:
                                            string += ' / ' + l.move_id.name
                                list_table = []
                                j = ['', '', string[cant_caracteres*2:cant_caracteres * 3], '', '']
                                detalles.append(j)

                                list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Helvetica'))
                                list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                                list_table.append(('ALIGN', (5, 1), (-1, -1), 'RIGHT'))
                                # list_table.append(('GRID', (0, 0), (-2, -2), 1, colors.black))
                                list_table.append(('FONTSIZE', (0, 0), (-1, -1), 7))
                                # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                                table = Table(detalles,
                                              colWidths=[2 * cm, 5 * cm, 7 * cm, 1.75 * cm, 1.75 * cm],
                                              rowHeights=(0.33 * cm))
                                table.setStyle(TableStyle(list_table))
                                table.wrapOn(c, width, heigth)
                                table.drawOn(c, x * cm, y * cm)
                                y = y + altura
                                cant_aux += 1
                                detalles = []
                                if len(string) > cant_caracteres * 3:
                                    string2 = string
                                    if not (len(string2) > cant_caracteres * 4) and not oper:
                                        oper = self.getOperacion(l)
                                        if oper:
                                            if not oper in string:
                                                string += ' / ' + oper
                                        else:
                                            if not l.move_id.name in string:
                                                string += ' / ' + l.move_id.name
                                    list_table = []
                                    j = ['', '', string[cant_caracteres * 3:cant_caracteres * 4], '', '']
                                    detalles.append(j)

                                    list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Helvetica'))
                                    list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                                    list_table.append(('ALIGN', (5, 1), (-1, -1), 'RIGHT'))
                                    # list_table.append(('GRID', (0, 0), (-2, -2), 1, colors.black))
                                    list_table.append(('FONTSIZE', (0, 0), (-1, -1), 7))
                                    # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                                    table = Table(detalles,
                                                  colWidths=[2 * cm, 5 * cm, 7 * cm, 1.75 * cm, 1.75 * cm],
                                                  rowHeights=(0.33 * cm))
                                    table.setStyle(TableStyle(list_table))
                                    table.wrapOn(c, width, heigth)
                                    table.drawOn(c, x * cm, y * cm)
                                    y = y + altura
                                    cant_aux += 1
                                    detalles = []
                                    if len(string) > cant_caracteres * 4:
                                        string2 = string
                                        if not (len(string2) > cant_caracteres * 5) and not oper:
                                            oper = self.getOperacion(l)
                                            if oper:
                                                if not oper in string:
                                                    string += ' / ' + oper
                                            else:
                                                if not l.move_id.name in string:
                                                    string += ' / ' + l.move_id.name
                                        list_table = []
                                        j = ['', '', string[cant_caracteres * 4:cant_caracteres * 5], '', '']
                                        detalles.append(j)

                                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Helvetica'))
                                        list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                                        list_table.append(('ALIGN', (5, 1), (-1, -1), 'RIGHT'))
                                        # list_table.append(('GRID', (0, 0), (-2, -2), 1, colors.black))
                                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), 7))
                                        # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                                        table = Table(detalles,
                                                      colWidths=[2 * cm, 5 * cm, 7 * cm, 1.75 * cm, 1.75 * cm],
                                                      rowHeights=(0.33 * cm))
                                        table.setStyle(TableStyle(list_table))
                                        table.wrapOn(c, width, heigth)
                                        table.drawOn(c, x * cm, y * cm)
                                        y = y + altura
                                        cant_aux += 1
                                        detalles = []
                                        if len(string) > cant_caracteres * 5:
                                            string2 = string
                                            if not (len(string2) > cant_caracteres * 6) and not oper:
                                                oper = self.getOperacion(l)
                                                if oper:
                                                    if not oper in string:
                                                        string += ' / ' + oper
                                                else:
                                                    if not l.move_id.name in string:
                                                        string += ' / ' + l.move_id.name
                                            list_table = []
                                            j = ['', '', string[cant_caracteres * 5:cant_caracteres * 6], '', '']
                                            detalles.append(j)

                                            list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Helvetica'))
                                            list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                                            list_table.append(('ALIGN', (5, 1), (-1, -1), 'RIGHT'))
                                            # list_table.append(('GRID', (0, 0), (-2, -2), 1, colors.black))
                                            list_table.append(('FONTSIZE', (0, 0), (-1, -1), 7))
                                            # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                                            table = Table(detalles,
                                                          colWidths=[2 * cm, 5 * cm, 7 * cm, 1.75 * cm, 1.75 * cm],
                                                          rowHeights=(0.33 * cm))
                                            table.setStyle(TableStyle(list_table))
                                            table.wrapOn(c, width, heigth)
                                            table.drawOn(c, x * cm, y * cm)
                                            y = y + altura
                                            cant_aux += 1
                                            detalles = []
                        # IMPRESION DE primera linea de asiento DE ASIENTO
                        if l.debit or l.credit > 0:
                            total_debito_asiento += l.debit
                            total_credito_asiento += l.credit
                            cont = cont + 1
                            list_table = []
                            debito = self.agregar_punto_de_miles(l.debit)
                            credito = self.agregar_punto_de_miles(l.credit)
                            this_s = [l.account_id.code, det2, texto_linea, debito, credito]
                            detalles.append(this_s)
                            suma_debito += round(l.debit)
                            suma_credito += round(l.credit)

                            list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Helvetica'))
                            list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                            list_table.append(('ALIGN', (3, 0), (4, 0), 'RIGHT'))
                            # list_table.append(('LINEBELOW',(0,1), (-1,-1),1,colors.black))
                            # list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                            list_table.append(('FONTSIZE', (0, 0), (-1, -1), 7))
                            # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                            table = Table(detalles,
                                          colWidths=[2* cm, 5 * cm, 7 * cm,  1.75 * cm, 1.75 * cm],
                                          rowHeights=(0.33 * cm))
                            table.setStyle(TableStyle(list_table))
                            table.wrapOn(c, width, heigth)
                            table.drawOn(c, x * cm, y * cm)
                            detalles = []
                            list_table = []
                            cant_aux += 1
                            y = y + altura

                    else:
                        if l.credit or l.debit > 0:
                            total_debito_asiento += l.debit
                            total_credito_asiento += l.credit
                            cont = cont + 1
                            list_table = []
                            detalles = []
                            if l.name:
                                if len(l.name) > 50:
                                    det = l.name[0:31]
                                else:
                                    det = l.name
                            else:
                                det = ''

                            if len(l.account_id.name) > 50:
                                det2 = l.account_id.name[0:70]
                            else:
                                det2 = l.account_id.name

                            debito = self.agregar_punto_de_miles(l.debit)

                            credito = self.agregar_punto_de_miles(l.credit)

                            fecha = datetime.strptime(str(l.move_id.date), "%Y-%m-%d").strftime('%d/%m/%Y')
                            this_s = [l.account_id.code, det2, texto_linea, debito, credito]
                            detalles.append(this_s)
                            suma_debito += round(l.debit)
                            suma_credito += round(l.credit)

                            list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Helvetica'))
                            list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                            list_table.append(('ALIGN', (3, 0), (4, 0), 'RIGHT'))
                            # list_table.append(('LINEBELOW',(0,1), (-1,-1),1,colors.black))
                            if cont == len(l.move_id.line_ids.filtered(lambda r: r.balance != 0)):
                                list_table.append(('GRID', (0, 0), (-3, -3), 0.5, colors.black))
                            list_table.append(('FONTSIZE', (0, 0), (-1, -1), 7))
                            # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                            table = Table(detalles,
                                          colWidths=[2 * cm, 5 * cm, 7 * cm,  1.75 * cm, 1.75 * cm],
                                          rowHeights=(0.33 * cm))
                            table.setStyle(TableStyle(list_table))
                            table.wrapOn(c, width, heigth)
                            table.drawOn(c, x* cm, y * cm)
                            detalles = []
                            list_table = []
                            cant_aux += 1
                            y = y + altura
                            if cont == len(l.move_id.line_ids.filtered(lambda r: r.balance != 0)):
                            #impresion de total de asientos
                                this_s = ['', '', 'Total asiento', self.agregar_punto_de_miles(total_debito_asiento),self.agregar_punto_de_miles(total_credito_asiento)]
                                detalles.append(this_s)
                                list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'))
                                list_table.append(('ALIGN', (0, 0), (-1, 0), 'LEFT'))
                                list_table.append(('ALIGN', (3, 0), (4, 0), 'RIGHT'))
                                list_table.append(('FONTSIZE', (0, 0), (-1, -1), 7))
                                # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                                table = Table(detalles,
                                              colWidths=[2 * cm, 5 * cm, 7 * cm, 1.75 * cm, 1.75 * cm],
                                              rowHeights=(0.33 * cm))
                                table.setStyle(TableStyle(list_table))
                                table.wrapOn(c, width, heigth)
                                table.drawOn(c, x * cm, y * cm)
                                detalles = []
                                list_table = []
                                cant_aux += 1
                                y = y + altura



                    if cant_aux >= LINEAS:
                        pag += 1
                        detalles = []
                        list_table = []
                        debito = self.agregar_punto_de_miles(suma_debito)
                        credito = self.agregar_punto_de_miles(suma_credito)
                        this_s = ['Transporte','', '', debito, credito]
                        detalles.append(this_s)

                        list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
                        list_table.append(('ALIGN', (0, 0), (-3, 0), 'CENTER'))
                        list_table.append(('ALIGN', (3, 0), (4, 0), 'RIGHT'))
                        # list_table.append(('LINEBELOW',(0,1), (-1,-1),1,colors.black))
                        # list_table.append(('GRID', (0, 0), (-1, 0), 1, colors.black))
                        list_table.append(('FONTSIZE', (0, 0), (-1, -1), 6))
                        # list_table.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
                        table = Table(detalles,
                                      colWidths=[2* cm, 5 * cm, 7 * cm, 1.75 * cm, 1.75 * cm],
                                      rowHeights=(0.33 * cm))
                        table.setStyle(TableStyle(list_table))
                        table.wrapOn(c, width, heigth)
                        table.drawOn(c, x * cm, y * cm)
                        if record.mostrar_numeracion:
                            c.setFont("Helvetica", 10)
                            c.drawString(500, 30, 'Pág ' + str(pag))
                        x = 1.5
                        y = 2
                        c.showPage()
                        detalles = []
                        list_table = []
                        cant_aux = 0
                        primera = 1
            detalles = []
            debito = self.agregar_punto_de_miles(suma_debito)
            credito = self.agregar_punto_de_miles(suma_credito)
            this_s = ['Totales', '', '', debito, credito]
            detalles.append(this_s)

            list_table.append(('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'))
            list_table.append(('ALIGN', (0, 0), (-3, 0), 'CENTER'))
            list_table.append(('ALIGN', (3, 0), (4, 0), 'RIGHT'))
            list_table.append(('FONTSIZE', (0, 0), (-1, -1), 6))
            table = Table(detalles,
                          colWidths=[4 * cm, 3 * cm, 7 * cm, 1.75 * cm, 1.75 * cm],
                          rowHeights=(0.33 * cm))
            table.setStyle(TableStyle(list_table))
            table.wrapOn(c, width, heigth)
            table.drawOn(c, x * cm, y * cm)
            y = y + altura
            pag += 1



            c.save()
            _logger.info(' asientocantidad de lineas')
            _logger.info(len(lineas_asiento))
            _logger.info('cantidad de lineas asiento recorridas')
            _logger.info(i)
            # print('cantidad de lineas asiento')
            # print(len(lineas_asiento))
            # print('cantidad de lineas asiento recorridas')
            # print(i)
            pdf = buffer.getvalue()
            buffer.close()
            return request.make_response(
                pdf,
                [('Content-Type', 'application/pdf'),
                 ('Content-Disposition', content_disposition('LIBRO_DIARIO_COMPLETO.pdf'))])




