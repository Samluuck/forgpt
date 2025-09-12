# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time,collections
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import logging
import operator
import io
import xlsxwriter
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception,content_disposition

_logger = logging.getLogger(__name__)

class WizardReportLibroIVACompra(models.TransientModel):
    _name = "resultados.wizard.resultados"


    fecha_inicio = fields.Date(string="Fecha desde")
    fecha_fin = fields.Date(string="Fecha hasta", default=fields.Date.today())
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self._get_default_company())
    ver_borrador = fields.Boolean(string='Incluir asientos en Borrador')

    @api.model
    def _get_default_company(self):
        return self.env.company.id

    def print_xls(self):
        data={}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin','company_id'])[0]
        return {
            'type': 'ir.actions.act_url',
            'url': '/getEERR/xls/' + str(self.id),
            'target': 'current'
        }

    # @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['fecha_inicio', 'fecha_fin'])[0])
        return self.env.ref('accounting_reports_paraguay.resultados_id').report_action(self, data)

    def agregar_punto_de_miles(self, numero):
        if numero >= 0:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
        else:
            numero*=-1
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
            numero_con_punto='-'+numero_con_punto
        num_return = numero_con_punto
        return num_return

    def convertir_guaranies(self, factura):
        rate = self.env['res.currency.rate'].search(
            [('currency_id', '=', factura.currency_id.id), ('name', '=', str(factura.date_invoice))])
        monto = factura.amount_total * (1 / rate.rate)
        monto = self.agregar_punto_de_miles(monto, 1)
        return monto

    def obtener_anio_actual(self,fecha):
        fi = datetime.strptime(str(fecha), '%Y-%m-%d')
        anio = fi.year
        return anio

    def obtener_anio_anterior(self,fecha):
        fi = datetime.strptime(str(fecha), '%Y-%m-%d')
        fecha_inicio_ant = fi - relativedelta(years=1)
        anio = fecha_inicio_ant.year
        return anio

    def formatear_fecha(self,fecha):
        fi = datetime.strptime(str(fecha), '%Y-%m-%d')
        fd = datetime.strftime(fi, '%d/%m/%Y')

        return fd



class ReporteEERR(models.AbstractModel):
    _name = 'report.accounting_reports_paraguay.resultados_report'

    # @api.multi
    def _get_report_values(self, docids, data=None):
        model = 'resultados.wizard.resultados'
        docs = self.env[model].browse(self.env.context.get('active_id'))

        movimientos = self.get_datos_balance(docs.fecha_inicio, docs.fecha_fin, docs.company_id,'PDF')


        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'movimientos': movimientos,


        }
        return docargs

    def get_datos_balance(self, fecha_inicio, fecha_fin,company_id,type):
        """
        La idea es un dicionario que tenga la cuenta y el total sumado


        :param fecha_inicio:
        :param fecha_fin:
        :param company_id:
        :return:
        """


        cuentas = list()
        domain=[]
        domain_ant=[]
        tipo_ingreso = self.env.ref('account.data_account_type_revenue').id
        tipo_egreso = self.env.ref('account.data_account_type_expenses').id
        tipo_depreciacion = self.env.ref('account.data_account_type_depreciation').id
        tipo_otro_ingreso = self.env.ref('account.data_account_type_other_income').id
        tipo_costo = self.env.ref('account.data_account_type_direct_costs').id
        cuentas_ingresos=self.env['account.account.type'].search([('internal_group','=','income')])
        cuentas_egresos=self.env['account.account.type'].search([('internal_group','=','expense')])
        if cuentas_ingresos:
            ingresos = self.env['account.account'].search([('user_type_id', 'in', (cuentas_ingresos.ids))])
        else:
            ingresos = self.env['account.account'].search([('user_type_id','in',(tipo_ingreso,tipo_otro_ingreso))])
        if cuentas_egresos:
            egresos = self.env['account.account'].search([('user_type_id', 'in', (cuentas_egresos.ids))])
        else:
            egresos = self.env['account.account'].search([('user_type_id','in',(tipo_egreso,tipo_costo,tipo_depreciacion))])

        for cue in ingresos:
            cuentas.append(cue.id)

        for cue in egresos:
            cuentas.append(cue.id)

        if type == 'PDF':
            docs = self.env['resultados.wizard.resultados'].browse(self.env.context.get('active_id'))
        else:
            docs = self
        if docs.ver_borrador:
            domain += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio), ('date', '<=', fecha_fin),
                       ('move_id.state', 'in', ('posted', 'draft')), ('move_id.cierre', '=', False),
                       ('move_id.resultado', '=', False), ('account_id', 'in', cuentas)]
        else:
            domain += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio), ('date', '<=', fecha_fin),
                       ('move_id.state', '=', 'posted'), ('move_id.cierre', '=', False),
                       ('move_id.resultado', '=', False), ('account_id', 'in', cuentas)]

        fi = datetime.strptime(str(fecha_inicio), '%Y-%m-%d')
        ff = datetime.strptime(str(fecha_fin), '%Y-%m-%d')
        fecha_inicio_ant = fi - relativedelta(years=1)
        fecha_fin_ant = ff - relativedelta(years=1)

        if docs.ver_borrador:
            domain_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
                           ('date', '<=', fecha_fin_ant),
                           ('move_id.state', 'in', ('posted', 'draft')), ('move_id.cierre', '=', False),
                           ('move_id.resultado', '=', False), ('account_id', 'in', cuentas)]
        else:
            domain_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
                           ('date', '<=', fecha_fin_ant),
                           ('move_id.state', '=', 'posted'), ('move_id.cierre', '=', False),
                           ('move_id.resultado', '=', False), ('account_id', 'in', cuentas)]

        movimientos = self.env['account.move.line'].search(domain,order='account_id')
        movimientos_ant = self.env['account.move.line'].search(domain_ant,order='account_id')
        dic=collections.OrderedDict()
        padres = list()
        ccc = list()
        ddd = list()
        final = list()
        codigo_actual=''
        suma=0
        nro=0
        cod = None

        cuentas = self.env['account.account'].with_context(show_parent_account=True).search([('deprecated','=',False),('company_id','=',company_id.id),('group_id','!=',False)])
        grupo = self.env['account.group'].search([('code_prefix_start','!=',False),('company_id','in',(company_id.id,None,False))])
        cuent=cuentas.sorted(key=lambda r:r.code)
        # _logger.info('estadores1')
        for g in grupo.sorted(key=lambda  r:int(r.code_prefix_start)):
            #domain_2 = domain + [('account_id', '=', b.id)]
            # _logger.info('estadores2')
            domain_grup = domain + [('account_id.group_id', '=', g.id)]
            movi_grup = self.env['account.move.line'].search(domain_grup)
            # movi_grup = movimientos.filtered(lambda r: r.account_id.group_id.id == g.id)
            # _logger.info('estadores3')
            tipo=None
            if int(g.code_prefix_start) in (5,10,11,13,15):
                tipo='MENOS'
            elif int(g.code_prefix_start) == 7:
                tipo='MAS'
            deb_grup=0
            cred_grup=0
            for deb in movi_grup:
                deb_grup+= int(round(deb.debit))
            for cred in movi_grup:
                cred_grup+= int(round(cred.credit))

            total_grup = deb_grup - cred_grup
            total_ant_grup = 0

            vals = {
                'code': g.code_prefix_start,
                'group_id':g.id,
                'total': total_grup,
                'total_ant': total_ant_grup,
                'account_id': None,
                'parent_id': None,
                'name': str(g.name),
                'padre': True,
                'group': g.code_prefix_start,
                'group_name': g.name,
                'tipo':tipo

            }
            ccc.append(vals)
            # _logger.info('estadores4')
            for a in cuent.filtered(lambda r: r.group_id.id == g.id):
                domain_2 = domain + [('account_id', '=', a.id)]
                movi = self.env['account.move.line'].search(domain_2)
                # movi = movimientos.filtered(lambda r: r.account_id.id == a.id)
                debi = 0
                credi = 0
                for deb in movi:
                    debi += int(round(deb.debit))
                for cred in movi:
                    credi += int(round(cred.credit))

                total = debi - credi
                total_ant = 0

                vals = {
                    'code': a.cod_eerr or a.code,
                    'group_id':None,
                    'total': total,
                    'total_ant':total_ant,
                    'account_id': a.id,
                    'parent_id':a.parent_id.id,
                    'name':a.name,
                    'padre':False,
                    'group':a.group_id.code_prefix_start,
                    'group_name':a.group_id.name,

                }
                ccc.append(vals)

            for b in cuent.filtered(lambda r: r.group_id.id == g.id):
                domain_2_ant = domain_ant + [('account_id', '=', b.id)]
                movi = self.env['account.move.line'].search(domain_2_ant)
                # movi = movimientos_ant.filtered(lambda r: r.account_id.id == b.id)
                debiant = 0
                crediant = 0
                for deb in movi:
                    debiant += int(round(deb.debit))
                for cred in movi:
                    crediant += int(round(cred.credit))
                total_ant = debiant - crediant
                encon = list(filter(lambda r: r['account_id'] == b.id, ccc))
                if encon:
                    encon[0]['total_ant'] += total_ant
                encon_grup = list(filter(lambda r: r['group_id'] == g.id, ccc))
                if encon_grup:
                    encon_grup[0]['total_ant'] += total_ant

        for i in reversed(ccc):
            codi = i['code']
            totali = i['total']
            totali_ant = i['total_ant']
            encon = list(filter(lambda r: r['account_id'] == i['parent_id'], ccc))
            if encon:
                if not encon[0]['group_id']:
                    encon[0]['total'] += int(round(totali))
                    encon[0]['total_ant'] += int(round(totali_ant))
                    encon[0]['padre'] = True
                    encon[0]['tipo'] = None
        cc4 =  list(filter(lambda r: r['code'] == '4' and r['group_id'] != False, ccc))
        cc5 =  list(filter(lambda r: r['code'] == '5' and r['group_id'] != False, ccc))
        cc6_edit = list(filter(lambda r: r['code'] == '6' and r['group_id'] != False, ccc))
        _logger.info('cc4')
        _logger.info(cc4)
        _logger.info('cc5')
        _logger.info(cc5)
        cc6 = cc4[0]['total']+cc5[0]['total']
        cc6_ant = cc4[0]['total_ant']+cc5[0]['total_ant']
        cc6_edit[0]['total']=cc6
        cc6_edit[0]['total_ant']=cc6_ant
        cc7 = list(filter(lambda r: r['code'] == '7' and r['group_id'] != False, ccc))
        cc8 = list(filter(lambda r: r['code'] == '8' and r['group_id'] != False, ccc))
        cc9_edit = list(filter(lambda r: r['code'] == '9' and r['group_id'] != False, ccc))
        cc9 = cc6 + cc7[0]['total'] + cc8[0]['total']
        cc9_ant = cc6_ant + cc7[0]['total_ant'] + cc8[0]['total_ant']
        cc9_edit[0]['total'] = cc9
        cc9_edit[0]['total_ant'] = cc9_ant
        cc10 = list(filter(lambda r: r['code'] == '10' and r['group_id'] != False, ccc))
        cc11 = list(filter(lambda r: r['code'] == '11' and r['group_id'] != False, ccc))
        cc12_edit = list(filter(lambda r: r['code'] == '12' and r['group_id'] != False, ccc))
        cc12 = cc9 +cc10[0]['total'] + cc11[0]['total']
        cc12_ant = cc9_ant + cc10[0]['total_ant'] + cc11[0]['total_ant']
        cc12_edit[0]['total'] = cc12
        cc12_edit[0]['total_ant'] = cc12_ant
        cc13 = list(filter(lambda r: r['code'] == '13' and r['group_id'] != False, ccc))
        cc14 = list(filter(lambda r: r['code'] == '14' and r['group_id'] != False, ccc))
        cc15 = list(filter(lambda r: r['code'] == '15' and r['group_id'] != False, ccc))
        cc16_edit = list(filter(lambda r: r['code'] == '16' and r['group_id'] != False, ccc))
        cc16 = cc12 + cc13[0]['total'] + cc14[0]['total'] + cc15[0]['total']
        cc16_ant = cc12_ant + cc13[0]['total_ant'] + cc14[0]['total_ant'] + cc15[0]['total_ant']
        cc16_edit[0]['total'] = cc16
        cc16_edit[0]['total_ant'] = cc16_ant

        cc17 = list(filter(lambda r: r['code'] == '17' and r['group_id'] != False, ccc))
        cc18_edit = list(filter(lambda r: r['code'] == '18' and r['group_id'] != False, ccc))

        cc18 = cc16 + cc17[0]['total']
        cc18_ant = cc16_ant + cc17[0]['total_ant']
        cc18_edit[0]['total'] = cc18
        cc18_edit[0]['total_ant'] = cc18_ant

        cc19 = list(filter(lambda r: r['code'] == '19' and r['group_id'] != False, ccc))
        cc20_edit = list(filter(lambda r: r['code'] == '20' and r['group_id'] != False, ccc))

        cc20 = cc18 + cc19[0]['total']
        cc20_ant = cc18_ant + cc19[0]['total_ant']
        cc20_edit[0]['total'] = cc20
        cc20_edit[0]['total_ant'] = cc20_ant

        for a in ccc:
            if a['total'] !=0 or a['total_ant']!=0:
                final.append(a)


        return final

class DownloadXLS(http.Controller):
    @http.route('/getEERR/xls/<int:id>', auth='public')
    def generarXLSX(self, id=None, **kw):
        record = request.env['resultados.wizard.resultados'].browse(id)

        # SE LLAMA A LA CLASE Y SU FUNCION QUE HACE LOS CALCULOS DEL BALANCE, DONDE OCURRE LA MAGIA
        movimientos=ReporteEERR.get_datos_balance(record,record.fecha_inicio,record.fecha_fin,record.company_id,'XLSX')

        # _logger.info('movimientos')
        # _logger.info(movimientos)
        fp = io.BytesIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        sheet = workbook.add_worksheet('Balance')
        bold_left_9 = workbook.add_format({

            'bold': True,
            'align': 'left',
            'font_size':9,
            'border': 1,
            'font_name':'Times New Roman'
        })
        not_bold_left_9 = workbook.add_format({
            'align': 'left',
            'font_size':9,
            'border': 1,
            'font_name':'Times New Roman'
        })
        bold_right_9 = workbook.add_format({
            'bold': True,
            'align': 'right',
            'font_size':9,
            'border': 1,
            'font_name':'Times New Roman'
        })
        not_bold_right_9 = workbook.add_format({
            'align': 'right',
            'font_size':9,
            'border': 1,
            'font_name':'Times New Roman'
        })
        bold_center_9 = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size':9,
            'border': 1,
            'font_name':'Times New Roman',
        })

        bold_center_7 = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size':7,
            'border': 1,
            'font_name':'Times New Roman'
        })
        not_bold_center = workbook.add_format({
            'bold': False,
            'align':'center',
            'font_size':9,
            'border': 1,
            'font_name':'Times New Roman'
        })
        sheet.set_default_row(10)
        sheet.set_column('A:F', 11)
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'})
        # CABECERAS Y SUS DATOS
        sheet.merge_range('A1:F2', 'ANEXO 2', merge_format)
        sheet.merge_range('A3:F4', 'ESTADOS DE RESULTADOS', merge_format)
        sheet.merge_range('A5:F5', '', merge_format)
        sheet.merge_range('A6:D6', '1- Identificacion del Contribuyente', bold_center_9)
        sheet.merge_range('E6:F6', '2- Ejercicio Fiscal', bold_center_9)
        sheet.merge_range('E6:F6', '2- Ejercicio Fiscal', bold_center_9)
        sheet.merge_range('A7:B7', 'Razon Social', bold_center_9)
        sheet.merge_range('C7:D7', 'Identificador RUC', bold_center_9)
        sheet.merge_range('A8:B8', record.company_id.razon_social, bold_center_9)
        sheet.merge_range('C8:D8', record.company_id.ruc, bold_center_9)
        sheet.write('E7', 'Desde', bold_center_9)
        sheet.write('F7', 'Hasta', bold_center_9)
        sheet.write('E8', record.formatear_fecha(record.fecha_inicio), bold_center_9)
        sheet.write('F8', record.formatear_fecha(record.fecha_fin), bold_center_9)
        sheet.merge_range('A9:F9', '', bold_center_9)
        sheet.merge_range('A10:B10', '3- Identificacion del Represetante Legal', bold_center_9)
        sheet.merge_range('C10:D10', '3- Identificacion del Contador', bold_center_9)
        sheet.merge_range('E10:F10', '3- Identificacion del Auditor', bold_center_9)
        sheet.merge_range('A11:B11', 'Apellido/Nombre', bold_center_9)
        sheet.write('C11', 'Apellido/Nombre', bold_center_7)
        sheet.write('D11', 'Identificador RUC', bold_center_7)
        sheet.write('E11', 'Apellido/Nombre', bold_center_7)
        sheet.write('F11', 'Identificador RUC', bold_center_7)
        sheet.merge_range('A12:B12', record.company_id.representante_legal, bold_center_9)
        sheet.write('C12', record.company_id.contador, bold_center_7)
        sheet.write('D12', record.company_id.ruc_contador, bold_center_7)
        sheet.write('E12', record.company_id.auditor, bold_center_7)
        sheet.write('F12', record.company_id.ruc_auditor, bold_center_7)

        #DATOS
        i = 14
        sheet.merge_range('A14:D14', '', bold_center_9)
        sheet.write('E14', record.obtener_anio_actual(record.fecha_inicio), bold_center_9)
        sheet.write('F14', record.obtener_anio_anterior(record.fecha_inicio), bold_center_9)

        for m in movimientos:
            if m['padre'] == True:
                sheet.write(i, 0, m['code'], bold_left_9)
                sheet.merge_range(i, 1, i, 3, m['name'], bold_left_9)
                sheet.write(i, 4, abs(int(round(m['total']))), bold_right_9)
                sheet.write(i, 5, abs(int(round(m['total_ant']))), bold_right_9)
            else:
                sheet.write(i, 0, m['code'], not_bold_left_9)
                sheet.merge_range(i, 1, i, 3, m['name'], not_bold_left_9)
                sheet.write(i, 4, abs(int(round(m['total']))), not_bold_right_9)
                sheet.write(i, 5, abs(int(round(m['total_ant']))), not_bold_right_9)
            i += 1

        workbook.close()
        fp.seek(0)
        new_report_from = record.fecha_inicio.strftime('%d-%m-%Y')
        new_report_to = record.fecha_fin.strftime('%d-%m-%Y')
        filename = 'EERR ' + str(new_report_from) + ' al ' + str(new_report_to) + '.xlsx'
        return request.make_response(fp.read(),
                                     [('Content-Type',
                                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                                      ('Content-Disposition', content_disposition(filename))])
