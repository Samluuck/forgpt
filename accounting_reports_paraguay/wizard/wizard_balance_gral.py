# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time,collections
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import logging
import operator
import io
from datetime import date,datetime
import xlsxwriter
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception,content_disposition
from . import wizard_resultados
_logger = logging.getLogger(__name__)

class WizardReportLibroIVACompra(models.TransientModel):
    _name = "balance.wizard.balance"


    fecha_inicio = fields.Date(string="Fecha desde")
    fecha_fin = fields.Date(string="Fecha hasta", default=fields.Date.today())
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self._get_default_company())
    ver_borrador = fields.Boolean(string='Incluir asientos en Borrador')
    ver_ingre_gas = fields.Boolean(string="Incluir Cuentas de Ingresos y Gastos")
    no_ver_comparativo=fields.Boolean(string="No ver saldos del año anterior")


    @api.model
    def _get_default_company(self):
        return self.env.company.id

    def print_xls(self):
        data={}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin','company_id'])[0]
        return {
            'type': 'ir.actions.act_url',
            'url': '/getBalance/xls/' + str(self.id),
            'target': 'current'
        }

    # @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['fecha_inicio', 'fecha_fin'])[0])
        return self.env.ref('accounting_reports_paraguay.balance_id').report_action(self, data)

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

class ReporteBalance(models.AbstractModel):
    _name = 'report.accounting_reports_paraguay.balance_report'





    # @api.multi
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
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
        resultados = list()
        domain=[]
        domain_ant=[]
        domain_resultado=[]
        domain_resultado_ant=[]

        ############### TIPOS DE CUENTA ACTIVOS ##############################
        asset_type = self.env['account.account.type'].search([('internal_group', '=', 'asset')])



        tipo_cobrar = self.env.ref('account.data_account_type_receivable').id
        tipo_banco_caja= self.env.ref('account.data_account_type_liquidity').id
        tipo_act_corriente= self.env.ref('account.data_account_type_current_assets').id
        tipo_act_no_corriente= self.env.ref('account.data_account_type_non_current_assets').id
        tipo_prepago= self.env.ref('account.data_account_type_prepayments').id
        tipo_act_fijo= self.env.ref('account.data_account_type_fixed_assets').id
        ###########################################################################

        ################# TIPOS DE CUENTAS PASIVOS ##################################
        liability_type = self.env['account.account.type'].search([('internal_group', '=', 'liability')])

        tipo_pagar = self.env.ref('account.data_account_type_payable').id
        tipo_tc = self.env.ref('account.data_account_type_credit_card').id
        tipo_pas_corriente = self.env.ref('account.data_account_type_current_liabilities').id
        tipo_pas_no_corriente = self.env.ref('account.data_account_type_non_current_liabilities').id

        ###############################################################################

        ################# TIPOS DE CUENTAS PATRIMONIO ##################################
        equity_type = self.env['account.account.type'].search([('internal_group', '=', 'equity')])

        tipo_patrimonio = self.env.ref('account.data_account_type_equity').id
        tipo_ganancia_actual = self.env.ref('account.data_unaffected_earnings').id

        ###############################################################################

        # _logger.info('balance1')
        activo = self.env['account.account'].with_context(show_parent_account=True).search([('user_type_id','in',(asset_type.ids)),('company_id','=',company_id.id)])
        pasivo = self.env['account.account'].with_context(show_parent_account=True).search([('user_type_id','in',(liability_type.ids)),('company_id','=',company_id.id)])
        patrimonio = self.env['account.account'].with_context(show_parent_account=True).search([('user_type_id','in',(equity_type.ids)),('company_id','=',company_id.id)])

        for cue in activo:

            cuentas.append(cue.id)

        for cue in pasivo:

            cuentas.append(cue.id)
        for cue in patrimonio:

            cuentas.append(cue.id)




        # _logger.info('balance2')
        # Se prepara el domain para los movimientos del anio de busqueda
        # domain+=[('company_id','=',company_id.id),('date', '>=', fecha_inicio),('date', '<=', fecha_fin),('parent_state','=','posted'),('account_id','in',cuentas)]
        model = self.env.context.get('active_model')
        if type == 'PDF':
            docs = self.env[model].browse(self.env.context.get('active_id'))
        else:
            docs=self
        # _logger.info('ver_ingre_gas %s' % docs.ver_ingre_gas)
        if docs.ver_ingre_gas:
            income_type=self.env['account.account.type'].search([('internal_group','=','income')])
            expense_type=self.env['account.account.type'].search([('internal_group','=','expense')])
            ingresos = self.env['account.account'].with_context(show_parent_account=True).search([('user_type_id', 'in', (income_type.ids)), ('company_id', '=', company_id.id)])
            gastos = self.env['account.account'].with_context(show_parent_account=True).search([('user_type_id', 'in', (expense_type.ids)), ('company_id', '=', company_id.id)])
            # _logger.info('ingresos %s' % ingresos)
            for cuein in ingresos:
                cuentas.append(cuein.id)
            # _logger.info('gasto %s' % gastos )
            for cuega in gastos:
                cuentas.append(cuega.id)
        if docs.ver_borrador:

            domain += [('company_id', '=', company_id.id),
                       ('date', '>=', fecha_inicio), ('date', ' <= ', fecha_fin),
                       ('parent_state', 'in', ('posted', 'draft')), ('account_id', 'in', cuentas)]
        else:
            domain += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio), ('date', '<=', fecha_fin),
                       ('move_id.state', '=', 'posted'), ('move_id.cierre', '=', False), ('account_id', 'in', cuentas)]

        # Se realiza el proceso para calcular cual es el anio anterior al de busqueda y luego se crea el domain
        fi=datetime.strptime(str(fecha_inicio), '%Y-%m-%d')
        ff=datetime.strptime(str(fecha_fin), '%Y-%m-%d')
        fecha_inicio_ant= fi - relativedelta(years=1)
        fecha_fin_ant= ff -  relativedelta(years=1)
        # _logger.info('balance3')
        # domain_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant), ('date', '<=', fecha_fin_ant),
        #            ('parent_state', '=', 'posted'), ('account_id', 'in', cuentas)]

        if docs.ver_borrador:

            domain_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
                           ('date', '<=', fecha_fin_ant),
                           ('parent_state', 'in', ('posted', 'draft')), ('account_id', 'in', cuentas)]
        else:

            domain_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
                           ('date', '<=', fecha_fin_ant),
                           ('move_id.state', '=', 'posted'), ('move_id.cierre', '=', False), ('move_id.resultado', '=', False), ('account_id', 'in', cuentas)]

        #Se hace el domain para el resultado del anio de busqueda y del anio anterior
        # domain_resultado += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
        #                      ('date', '<=', fecha_fin), ('parent_state', '=', 'posted'),
        #                      ('account_id', 'in', resultados)]
        #
        # domain_resultado_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
        #                      ('date', '<=', fecha_fin_ant), ('parent_state', '=', 'posted'),
        #                      ('account_id', 'in', resultados)]

        if docs.ver_borrador:
            domain_resultado += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
                                 ('date', '<=', fecha_fin), ('move_id.state', 'in', ('posted', 'draft')),
                                 ('account_id', 'in', resultados)]

            domain_resultado_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
                                     ('date', '<=', fecha_fin_ant), ('move_id.state', 'in', ('posted', 'draft')),
                                     ('account_id', 'in', resultados)]




        else:

            domain_resultado += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
                                 ('date', '<=', fecha_fin), ('move_id.state', '=', 'posted'), ('move_id.cierre', '=', False), ('move_id.resultado', '=', False),
                                 ('account_id', 'in', resultados)]

            domain_resultado_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
                                     ('date', '<=', fecha_fin_ant), ('move_id.state', '=', 'posted'), ('move_id.cierre', '=', False), ('move_id.resultado', '=', False),
                                     ('account_id', 'in', resultados)]

        # _logger.info('balance4')
        movimientos = self.env['account.move.line'].search(domain,order='account_id')
        # _logger.info('balance5')
        if not docs.no_ver_comparativo:
            movimientos_ant = self.env['account.move.line'].search(domain_ant,order='account_id')
        else:
            movimientos_ant=None
        # _logger.info('balance6')
        movimientos_resultado = self.env['account.move.line'].search(domain_resultado,order='account_id')
        # _logger.info('balance7')
        if not docs.no_ver_comparativo:
            movimientos_resultado_ant = self.env['account.move.line'].search(domain_resultado_ant,order='account_id')
        else:
            movimientos_resultado_ant = None
        # _logger.info('balance8')





        padres = list()
        ccc = list()
        ddd = list()
        final = list()
        codigo_actual=''
        suma=0
        nro=0
        cod = None

        # _logger.info('balance9')
        # Se trae todas la cuentas que se encuentran en el plan contable, se agrega el context show_parent_account = True para que pueda traer las cuentas tipo vista
        cuentas = self.env['account.account'].with_context(show_parent_account=True).search([('deprecated','=',False),('company_id','=',company_id.id)])
        # _logger.info('balance10')
        # Se agregan a una lista todas las cuentas del plan contable y las cuentas que tienen movimiento en el anio de busqueda ya se le va poniendo el saldo
        for a in cuentas.sorted(key=lambda r:r.code, reverse = True):
            domain_2 = domain + [('account_id', '=', a.id)]
            movi = self.env['account.move.line'].search(domain_2)
            #movi = movimientos.filtered(lambda r: r.account_id.id == a.id)
            # raise ValidationError('aaa %s' % movi)
            deb = sum(movi.mapped('debit'))
            cred = sum(movi.mapped('credit'))
            total = deb-cred
            total_ant = 0
            # if total != 0:
            #     _logger.info('ssss %s' % movi)
            vals = {
                'code': a.code,
                'total': total,
                'total_ant':total_ant,
                'account_id': a.id,
                'parent_id':a.parent_id.id,
                'name':a.name,
                'padre':False

            }
            ccc.append(vals)
        # Como todas las cuentas del plan contable ya fueron agregadas a la lista ccc entonces se procede a cargarle el monto del anio anterior a las cuentas que tienen movimiento el anio anterior
        # _logger.info('balance11')
        if docs.no_ver_comparativo:
            total_ant=0
        else:
            for b in cuentas.sorted(key=lambda r:r.code, reverse = True):
                domain_2_ant = domain_ant + [('account_id', '=', b.id)]
                movi = self.env['account.move.line'].search(domain_2_ant)
                # movi = movimientos_ant.filtered(lambda r: r.account_id.id == b.id)
                # raise ValidationError('aaa %s' % movi)
                debant = sum(movi.mapped('debit'))
                credant = sum(movi.mapped('credit'))
                total_ant = debant - credant

                # Esta función busca que cuenta coincide con la cuenta actual y busca en la lista ccc
                encon = list(filter(lambda r: r['account_id'] == b.id, ccc))
                # raise ValidationError('aaa %s' % encon[0]['total'])
                if encon:

                    encon[0]['total_ant'] += total_ant

        #Ahora se va a cargar las cuentas de resultados
        # _logger.info('balance12')
        if docs.ver_ingre_gas:
            try:
                tcr = self.env.ref('__export__.account_account_type_48_3af42435')
            except:
                tcr= None
            if tcr:
                tipo_cuenta_resultado=tcr.id
                cuenta_resultado = self.env['account.account'].search([('user_type_id', '=', tipo_cuenta_resultado),('name','ilike','ejercicio'), ('company_id', '=', company_id.id)], limit=1)
            else:
                tipo_cuenta_resultado = self.env.ref('account.data_unaffected_earnings').id
                cuenta_resultado = self.env['account.account'].search(
                    [('user_type_id', '=', tipo_cuenta_resultado), ('company_id', '=', company_id.id)], limit=1)
        else:
            tipo_cuenta_resultado = self.env.ref('account.data_unaffected_earnings').id
        # Para poder identificar la cuenta de resultados el tipo de cuenta debe ser Ganancias En el año actual

            cuenta_resultado = self.env['account.account'].search([('user_type_id','=',tipo_cuenta_resultado),('company_id','=',company_id.id)],limit=1)
        # _logger.info('balance13')
        encon = list(filter(lambda r: r['account_id'] == cuenta_resultado.id, ccc))
        #total_resultado =0

        #for resul in movimientos_resultado:
        #    total_resultado += int(round(resul.balance))
        recordre = self.env['resultados.wizard.resultados']
        # _logger.info('balance14')
        if not docs.ver_ingre_gas:
            try:
                finalres = wizard_resultados.ReporteEERR.get_datos_balance(recordre, fecha_inicio, fecha_fin, company_id, 'otro')
        # _logger.info('balance15')
        # total_resultado = finalres
                cc20_edit = list(filter(lambda r: r['code'] == '20' and r['group_id'] != False, finalres))
                total_resultado = int(round(cc20_edit[0]['total']))
                if docs.no_ver_comparativo:
                    total_resultado_ant =0
                else:
                    total_resultado_ant = sum(movimientos_resultado_ant.mapped('balance'))
                # _logger.info('balance16')
                if encon:
                    encon[0]['total'] = total_resultado
                    if docs.no_ver_comparativo:
                        encon[0]['total_ant'] = 0
                    else:
                        encon[0]['total_ant'] = total_resultado_ant
            except:
                if encon:
                    encon[0]['total'] = 0
                    encon[0]['total_ant'] = 0
        else:
            resultados=list()
            for cuein in ingresos:
                resultados.append(cuein.id)
            # _logger.info('gasto %s' % gastos )
            for cuega in gastos:
                resultados.append(cuega.id)
            domain_res = [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
             ('date', '<=', fecha_fin), ('move_id.state', '=', 'posted'),
             ('account_id', 'in', resultados)]
            movi_res = self.env['account.move.line'].search(domain_res)
            # movi = movimientos.filtered(lambda r: r.account_id.id == a.id)
            # raise ValidationError('aaa %s' % movi)
            deb = sum(movi_res.mapped('debit'))
            cred = sum(movi_res.mapped('credit'))
            total = deb - cred
            finalres= total
            # cc20_edit = list(filter(lambda r: r['code'] == '20' and r['group_id'] != False, finalres))
            total_resultado = int(round(finalres))
            if encon:
                encon[0]['total'] = total_resultado
        #Se suman los saldos de las cuentas a sus cuentas padre
        # _logger.info('balance17')
        for i in ccc:

            codi = i['code']
            totali = i['total']
            totali_ant = i['total_ant']
            encon = list(filter(lambda r: r['account_id'] == i['parent_id'], ccc))
            # raise ValidationError('aaa %s' % encon[0]['total'])
            if encon:

                encon[0]['total'] += totali
                encon[0]['total_ant'] += totali_ant
                encon[0]['padre'] = True

        # Se guarda en una lista solo las cuentas que tienen saldo distinto a cero
        # _logger.info('balance18')
        for a in ccc[::-1]:
            if int(a['total']) !=0 or int(a['total_ant']) !=0:
                # encon = list(filter(lambda r: r['code'] == a.code, activo))
                pasiv = pasivo.filtered(lambda r: r.code == a['code'])
                neto = patrimonio.filtered(lambda r: r.code == a['code'])


                if len(pasiv)>0:
                  a['total']= a['total']*-1
                  a['total_ant']= a['total_ant']*-1
                elif len(neto)>0:
                    a['total'] = a['total'] * -1
                    a['total_ant'] = a['total_ant'] * -1


                final.append(a)

        # _logger.info('balance19')
        return final



class DownloadXLS(http.Controller):
    @http.route('/getBalance/xls/<int:id>', auth='public')
    def generarXLSX(self, id=None, **kw):
        record = request.env['balance.wizard.balance'].browse(id)

        # SE LLAMA A LA CLASE Y SU FUNCION QUE HACE LOS CALCULOS DEL BALANCE, DONDE OCURRE LA MAGIA
        movimientos=ReporteBalance.get_datos_balance(record,record.fecha_inicio,record.fecha_fin,record.company_id,'XLSX')


        fp = io.BytesIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        sheet = workbook.add_worksheet('Balance')
        if record.ver_ingre_gas:
            border=0
        else:
            border=1

        bold_left_9 = workbook.add_format({
            'bold': True,
            'align': 'left',
            'font_size':9,
            'border': border,
            'font_name':'Times New Roman'
        })
        not_bold_left_9 = workbook.add_format({
            'align': 'left',
            'font_size':9,
            'border': border,
            'font_name':'Times New Roman'
        })
        bold_right_9 = workbook.add_format({
            'bold': True,
            'align': 'right',
            'font_size':9,
            'border': border,
            'font_name':'Times New Roman',
            'num_format': '#,##0',
        })
        not_bold_right_9 = workbook.add_format({
            'align': 'right',
            'font_size':9,
            'border': border,
            'font_name':'Times New Roman',
            'num_format': '#,##0',
        })
        # floating_point_bordered = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        bold_center_9 = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size':9,
            'border': border,
            'font_name':'Times New Roman',
        })

        bold_center_7 = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size':7,
            'border': border,
            'font_name':'Times New Roman'
        })
        not_bold_center = workbook.add_format({
            'bold': False,
            'align':'center',
            'font_size':9,
            'border': border,
            'font_name':'Times New Roman'
        })
        sheet.set_default_row(10)
        sheet.set_column('A:F', 11)
        merge_format = workbook.add_format({
            'bold': 1,
            'border': border,
            'align': 'center',
            'valign': 'vcenter'})
        # CABECERAS Y SUS DATOS
        if record.ver_ingre_gas:
            sheet.merge_range('A1:E2', 'BALANCE GENERAL', merge_format)
            sheet.merge_range('A3:E3', '', merge_format)
            sheet.merge_range('A4:C4', '1- Identificacion del Contribuyente', bold_center_9)
            sheet.merge_range('D4:E4', '2- Ejercicio Fiscal', bold_center_9)
            sheet.merge_range('A5:B5', 'Razon Social', bold_center_9)
            sheet.write('C5', 'Identificador RUC', bold_center_9)
            sheet.merge_range('A6:B6', record.company_id.razon_social, bold_center_9)
            sheet.write('C6', record.company_id.ruc, bold_center_9)
            sheet.write('D5', 'Desde', bold_center_9)
            sheet.write('E5', 'Hasta', bold_center_9)
            sheet.write('D6', record.formatear_fecha(record.fecha_inicio), bold_center_9)
            sheet.write('E6', record.formatear_fecha(record.fecha_fin), bold_center_9)

            i = 7
        else:
            sheet.merge_range('A1:F2', 'ANEXO 1', merge_format)
            sheet.merge_range('A3:F4', 'BALANCE GENERAL', merge_format)
            sheet.merge_range('A5:F5', '', merge_format)
            sheet.merge_range('A6:D6', '1- Identificacion del Contribuyente', bold_center_9)
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
            sheet.merge_range('A10:B10', '3- Identificacion del Representante Legal', bold_center_9)
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

        if not record.no_ver_comparativo:
            sheet.write('E14', record.obtener_anio_actual(record.fecha_inicio), bold_center_9)
            sheet.write('F14', record.obtener_anio_anterior(record.fecha_inicio), bold_center_9)

        if record.ver_ingre_gas:
            res_i = 0
            activo = 0
            pasivo = 0
            patrimonio = 0
            ganancia = 0
            gastos = 0
            resultado_uno = 0
            resultado_dos = 0
            asset_type = record.env['account.account.type'].search([('internal_group', '=', 'asset')])
            liability_type = record.env['account.account.type'].search([('internal_group', '=', 'liability')])
            equity_type = record.env['account.account.type'].search([('internal_group', '=', 'equity')])
            income_type = record.env['account.account.type'].search([('internal_group', '=', 'income')])
            expense_type = record.env['account.account.type'].search([('internal_group', '=', 'expense')])
            activosc = record.env['account.account'].with_context(show_parent_account=True).search(
                [('user_type_id', 'in', (asset_type.ids)), ('company_id', '=', record.company_id.id)])
            pasivosc = record.env['account.account'].with_context(show_parent_account=True).search(
                [('user_type_id', 'in', (liability_type.ids)), ('company_id', '=', record.company_id.id)])
            patrimonioc = record.env['account.account'].with_context(show_parent_account=True).search(
                [('user_type_id', 'in', (equity_type.ids)), ('company_id', '=', record.company_id.id)])
            ingresosc = record.env['account.account'].with_context(show_parent_account=True).search(
                [('user_type_id', 'in', (income_type.ids)), ('company_id', '=', record.company_id.id)])
            gastosc = record.env['account.account'].with_context(show_parent_account=True).search(
                [('user_type_id', 'in', (expense_type.ids)), ('company_id', '=', record.company_id.id)])
        else:
            res_i = 0
            activo = 0
            pasivo = 0
            patrimonio = 0
            ganancia = 0
            gastos = 0
            resultado_uno = 0
            resultado_dos = 0
            asset_type = record.env['account.account.type'].search([('internal_group', '=', 'asset')])
            liability_type = record.env['account.account.type'].search([('internal_group', '=', 'liability')])
            equity_type = record.env['account.account.type'].search([('internal_group', '=', 'equity')])
            income_type = record.env['account.account.type'].search([('internal_group', '=', 'income')])
            expense_type = record.env['account.account.type'].search([('internal_group', '=', 'expense')])
            activosc = record.env['account.account'].with_context(show_parent_account=True).search(
                [('user_type_id', 'in', (asset_type.ids)), ('company_id', '=', record.company_id.id)])
            pasivosc = record.env['account.account'].with_context(show_parent_account=True).search(
                [('user_type_id', 'in', (liability_type.ids)), ('company_id', '=', record.company_id.id)])
            patrimonioc = record.env['account.account'].with_context(show_parent_account=True).search(
                [('user_type_id', 'in', (equity_type.ids)), ('company_id', '=', record.company_id.id)])

        for m in movimientos:
            if m['padre'] == True:
                sheet.write(i, 0, m['code'], bold_left_9)
                if record.ver_ingre_gas:
                    if m['account_id'] in (ingresosc.ids):
                        sheet.merge_range(i, 1, i, 3, m['name'], bold_left_9)
                        sheet.write(i, 4, (int(round(m['total'] * -1))), bold_right_9)
                    else:
                        sheet.merge_range(i, 1, i, 3, m['name'], bold_left_9)
                        sheet.write(i, 4, (int(round(m['total']))), bold_right_9)
                else:
                    sheet.merge_range(i, 1, i, 3, m['name'], bold_left_9)
                    sheet.write(i, 4, (int(round(m['total']))), bold_right_9)

                if not record.no_ver_comparativo:
                    print('total_ant', m['total_ant'])
                    sheet.write(i, 5, (int(m['total_ant'])), not_bold_right_9)
            else:
                monto = (int(round(m['total'])))
                if m['account_id'] in (activosc.ids):
                    activo += (int(round(m['total'])))
                elif m['account_id'] in (pasivosc.ids):
                    pasivo += (int(round(m['total'])))
                elif m['account_id'] in (patrimonioc.ids):
                    patrimonio += (int(round(m['total'])))
                if record.ver_ingre_gas:
                    if m['account_id'] in (ingresosc.ids):
                        monto = (int(round(m['total'])) * -1)
                        ganancia += (int(round(m['total'])))
                    elif m['account_id'] in (gastosc.ids):
                        gastos += (int(round(m['total'])))

                sheet.write(i, 0, m['code'], not_bold_left_9)
                sheet.merge_range(i, 1, i, 3, m['name'], not_bold_left_9)

                sheet.write(i, 4, monto, not_bold_right_9)
                if not record.no_ver_comparativo:
                    sheet.write(i, 5, (int(m['total_ant'])), not_bold_right_9)
            i += 1
        i += 2

        # i = i + 4


        # for m in movimientos:
        #     activo = m['total1']
        #     pasivo = m['total2']
        #     patrimonio = m['total10']
        #     operativo = m['total4']
        #     costos = m['total5']
        #     resultado_uno = (activo - (pasivo + patrimonio))
        #     resultado_dos = (operativo - costos)
        if record.ver_ingre_gas:
            resultado_uno = activo - (pasivo + patrimonio)
            resultado_dos = (ganancia * -1) - (gastos)

            sheet.write(i, 2, 'Resumen   de   Balance   General', merge_format)
            sheet.write(i + 1, 0, 'Total Activo:', merge_format)
            sheet.write_number(i + 1, 2, (activo), bold_right_9)
            sheet.write(i + 2, 0, 'Total Pasivo:', merge_format)
            sheet.write_number(i + 2, 2, (pasivo), bold_right_9)
            sheet.write(i + 3, 0, 'Total Patrimonio Neto:', merge_format)
            sheet.write_number(i + 3, 2, (patrimonio), bold_right_9)
            sheet.write(i + 4, 0, 'Diferencia: {Activo-(Pasivo+P.Neto)}:', merge_format)
            sheet.write_number(i + 4, 2, (resultado_uno), bold_right_9)
            sheet.write(i + 6, 0, 'Total Ingreso:', merge_format)
            sheet.write_number(i + 6, 2, (ganancia), bold_right_9)
            sheet.write(i + 7, 0, 'Total Egreso:', merge_format)
            sheet.write_number(i + 7, 2, (gastos), bold_right_9)
            sheet.write(i + 8, 0, 'Resultado:', merge_format)
            sheet.write_number(i + 8, 2, (resultado_dos), bold_right_9)

        workbook.close()
        fp.seek(0)
        new_report_from = record.fecha_inicio.strftime('%d-%m-%Y')
        new_report_to = record.fecha_fin.strftime('%d-%m-%Y')
        filename = 'Balance ' + str(new_report_from) + ' al ' + str(new_report_to) + '.xlsx'
        return request.make_response(fp.read(),
                                     [('Content-Type',
                                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                                      ('Content-Disposition', content_disposition(filename))])
