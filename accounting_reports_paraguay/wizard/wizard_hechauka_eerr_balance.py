# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time,collections
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import logging
import operator
import math
import json
import base64
from dicttoxml import dicttoxml
from json import loads
from zipfile import ZipFile
import os
import random
import string



_logger = logging.getLogger(__name__)

class WizardReporthechauka(models.TransientModel):
    _name = "hechauka.wizard.balance"

    fecha_inicio = fields.Date(string="Fecha desde")
    fecha_fin = fields.Date(string="Fecha hasta", default=fields.Date.today())
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self._get_default_company())
    txt_filename = fields.Char()
    txt_binary = fields.Binary()


    def get_file_name(self):
        cadena = ''
        cadena += 'EF'
        periodo = self.fecha_inicio.year
        cadena += str(periodo)
        digits = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        cadena += '_'
        cadena += digits
        cadena += '_'
        cadena += self.env.company.ruc
        cadena += '_948'
        return cadena



    def obtener_datos(self):

        balance,resultado = self.get_datos_balance(self.fecha_inicio,self.fecha_fin,self.company_id)
        patrimonio,totales = self.get_datos_estado(self.fecha_inicio,self.fecha_fin,self.company_id)
        anio_act = self.obtener_anio_actual(self.fecha_fin)
        # _logger.info('balanceo %s' % balance)
        # _logger.info('resultadoo %s' % resultado)
        # _logger.info('patrimonioo %s' % patrimonio)
        # _logger.info('totpatrimonioo %s' % totales)
        if not self.env.company.ruc_representante or not self.env.company.dv_representante :
            raise ValidationError('Debe cargar Ruc y DV de Representante Legal en los Datos de compañia')
        if not self.env.company.representante_legal:
            raise ValidationError('Debe cargar Representante Legal en los Datos de compañia')
        if not self.env.company.ruc_contador or not self.env.company.contador :
            raise ValidationError('Debe cargar Nombre de Contador y RUC en los Datos de compañia')
        jsonstr = """{ 
  "periodo": " """+str(anio_act)+""" ",
  "ruc": " """+self.env.company.ruc+'-'+self.env.company.dv +"""",
  "version": "3.2.1",
  "detalle": {
    "periodo": " """+str(anio_act)+""" ",
    "representante": {
        "ruc": " """+self.env.company.ruc_representante+""" ",
        "dv": " """+self.env.company.dv_representante+""" ",
        "nombre": " """+self.env.company.representante_legal+""" "
    },
    "contador": {
        "identificador": " """+self.env.company.ruc_contador+""" ",
        "nombre": " """+self.env.company.contador+""" "
    }
  },
  "estadosResultado": {
    "rubros": """ + json.dumps(resultado, indent=4) + """,
    "periodo": " """+str(anio_act)+""" "
   },
  "balance": {
    "rubros": """ + json.dumps(balance, indent=4) + """,
    "periodo": " """+str(anio_act)+""" "
  },
  "patrimonio": {
    "rubros": [],
    "periodo": " """+str(anio_act)+""" ",
    "cuentas": """ + json.dumps(patrimonio, indent=4) + """,  
    "totales":""" + json.dumps(totales, indent=4) + """ }
}"""
        # getting working module where your current python file (model.py) exists
        path = os.path.abspath(__file__ + "/../../")
        nombre = self.get_file_name()
        file_dir = "static/src"
        file = nombre + '.zip'
        file_name = "static/src"

        with open(os.path.join(path + "/"+ file_dir, file), 'w') as fp:
            fp.write("")
        # file_name_zip = file_name + ".zip"
        zipfilepath = os.path.join(path, file_name+'/'+file)
        # creating zip file in above mentioned path
        zipObj = ZipFile(zipfilepath, "w")
        xml = dicttoxml(loads(jsonstr),attr_type=False,custom_root='estadosFinancieros')
        jsonstr = jsonstr.encode("utf-8")
        zipObj.writestr(nombre+'.xml',xml)
        zipObj.writestr(nombre+'.json',jsonstr)
        zipObj.close()


        # code snipet for downloading zip file
        return {
            'type': 'ir.actions.act_url',
            'url': str('/accounting_reports_paraguay/static/src/'+nombre+'.zip'),
             'target': 'new',
        }






    @api.model
    def _get_default_company(self):
        return self.env.company.id

    # @api.multi
    def check_report(self):
        data = {}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['fecha_inicio', 'fecha_fin'])[0])
        return self.env.ref('accounting_reports_paraguay.estado_patrimonio_id').report_action(self, data)

    def agregar_punto_de_miles(self, numero):
        if numero >= 0:
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[
                               ::-1]
        else:
            numero *= -1
            numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[
                               ::-1]
            numero_con_punto = '-' + numero_con_punto
        num_return = numero_con_punto
        return num_return

    def convertir_guaranies(self, factura):
        rate = self.env['res.currency.rate'].search(
            [('currency_id', '=', factura.currency_id.id), ('name', '=', str(factura.date_invoice))])
        monto = factura.amount_total * (1 / rate.rate)
        monto = self.agregar_punto_de_miles(monto, 1)
        return monto

    def obtener_anio_actual(self, fecha):
        # fi = datetime.strptime(fecha, '%Y-%m-%d')
        fi = fecha
        anio = fi.year
        return anio

    def obtener_anio_anterior(self, fecha):
        # fi = datetime.strptime(fecha, '%Y-%m-%d')
        fi = fecha
        fecha_inicio_ant = fi - relativedelta(years=1)
        anio = fecha_inicio_ant.year
        return anio

    def formatear_fecha(self, fecha):
        # fi = datetime.strptime(fecha, '%Y-%m-%d')
        fi = fecha
        fd = datetime.strftime(fi, '%d/%m/%Y')

        return fd



    def get_datos_balance(self, fecha_inicio, fecha_fin,company_id):
        """
        La idea es un dicionario que tenga la cuenta y el total sumado



        :param fecha_inicio:
        :param fecha_fin:
        :param company_id:
        :return:
        """

        cuentas = list()
        bala = list()
        resultados = list()
        domain=[]
        domain_ant=[]
        domain_resultado=[]
        domain_resultado_ant=[]


        activo = self.env['account.account'].with_context(show_parent_account=True).search([('code','=ilike',('1%'))])
        pasivo = self.env['account.account'].with_context(show_parent_account=True).search([('code','=ilike',('2%'))])
        patrimonio = self.env['account.account'].with_context(show_parent_account=True).search([('code','=ilike',('3%'))])
        ingreso = self.env['account.account'].with_context(show_parent_account=True).search([('code','=ilike',('4%'))])
        egreso = self.env['account.account'].with_context(show_parent_account=True).search([('code','=ilike',('5%'))])
        for cue in activo:

            cuentas.append(cue.id)

        for cue in pasivo:

            cuentas.append(cue.id)
        for cue in patrimonio:

            cuentas.append(cue.id)

        bala=cuentas
        for resu in ingreso:

            resultados.append(resu.id)

        for resu in egreso:

            resultados.append(resu.id)


        # Se prepara el domain para los movimientos del anio de busqueda
        # domain+=[('company_id','=',company_id.id),('date', '>=', fecha_inicio),('date', '<=', fecha_fin),('parent_state','=','posted'),('account_id','in',cuentas)]
        # docs = self.env[self.model].browse(self.env.context.get('active_id'))
        # if docs.ver_borrador:
        #
        #     domain += [('company_id', '=', company_id.id),
        #                ('date', '>=', fecha_inicio), ('date', ' <= ', fecha_fin),
        #                ('parent_state', 'in', ('posted', 'draft')), ('account_id', 'in', cuentas)]
        # else:
        domain += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio), ('date', '<=', fecha_fin),
                       ('move_id.state', '=', 'posted'), ('account_id', 'in', cuentas)]


        # Se realiza el proceso para calcular cual es el anio anterior al de busqueda y luego se crea el domain
        fi=datetime.strptime(str(fecha_inicio), '%Y-%m-%d')
        ff=datetime.strptime(str(fecha_fin), '%Y-%m-%d')
        fecha_inicio_ant= fi - relativedelta(years=1)
        fecha_fin_ant= ff -  relativedelta(years=1)

        # domain_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant), ('date', '<=', fecha_fin_ant),
        #            ('parent_state', '=', 'posted'), ('account_id', 'in', cuentas)]

        # if docs.ver_borrador:
        #
        #     domain_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
        #                    ('date', '<=', fecha_fin_ant),
        #                    ('parent_state', 'in', ('posted', 'draft')), ('account_id', 'in', cuentas)]
        # else:

        # domain_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
        #                ('date', '<=', fecha_fin_ant),
        #                ('move_id.state', '=', 'posted'), ('account_id', 'in', cuentas)]

        #Se hace el domain para el resultado del anio de busqueda y del anio anterior
        # domain_resultado += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
        #                      ('date', '<=', fecha_fin), ('parent_state', '=', 'posted'),
        #                      ('account_id', 'in', resultados)]
        #
        # domain_resultado_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
        #                      ('date', '<=', fecha_fin_ant), ('parent_state', '=', 'posted'),
        #                      ('account_id', 'in', resultados)]

        # if docs.ver_borrador:
        #     domain_resultado += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
        #                          ('date', '<=', fecha_fin), ('move_id.state', 'in', ('posted', 'draft')),
        #                          ('account_id', 'in', resultados)]
        #
        #     domain_resultado_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
        #                              ('date', '<=', fecha_fin_ant), ('move_id.state', 'in', ('posted', 'draft')),
        #                              ('account_id', 'in', resultados)]




        # else:


        domain_resultado += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
                             ('date', '<=', fecha_fin), ('move_id.state', '=', 'posted'),
                             ('account_id', 'in', resultados)]

            # domain_resultado_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
            #                          ('date', '<=', fecha_fin_ant), ('move_id.state', '=', 'posted'),
            #                          ('account_id', 'in', resultados)]


        movimientos = self.env['account.move.line'].search(domain,order='account_id')
        # movimientos_ant = self.env['account.move.line'].search(domain_ant,order='account_id')
        movimientos_resultado = self.env['account.move.line'].search(domain_resultado,order='account_id')
        # movimientos_resultado_ant = self.env['account.move.line'].search(domain_resultado_ant,order='account_id')






        padres = list()
        ccc = list()
        ddd = list()
        final = list()
        final_res = list()
        codigo_actual=''
        suma=0
        nro=0
        cod = None

        # Se trae todas la cuentas que se encuentran en el plan contable, se agrega el context show_parent_account = True para que pueda traer las cuentas tipo vista

        cuentas = self.env['account.account'].with_context(show_parent_account=True).search([('deprecated','=',False),('company_id','=',company_id.id)])
        # cuentas_res = self.env['account.account'].with_context(show_parent_account=True).search([('deprecated','=',False),('company_id','=',company_id.id)])

        # Se agregan a una lista todas las cuentas del plan contable y las cuentas que tienen movimiento en el anio de busqueda ya se le va poniendo el saldo

        #CUENTAS DEL ESTADO DE RESULTADOS
        for b in cuentas.filtered(lambda g: g.id in resultados).sorted(key=lambda r:r.code, reverse = True):
            movi = movimientos_resultado.filtered(lambda r: r.account_id.id == b.id)
            # raise ValidationError('aaa %s' % movi)

            deb = sum(movi.mapped('debit'))
            cred = sum(movi.mapped('credit'))
            total = deb-cred

            total_ant = 0
            # if total != 0:
            #     _logger.info('ssss %s' % movi)
            if b.cod_eerr:
                puntos = b.cod_eerr.find('.')
            else:
                puntos = b.code.find('.')
            nivel = 0
            if puntos != -1:
                if b.cod_eerr:
                    nivel = b.cod_eerr.count('.')
                else:
                    nivel = b.code.count('.')
            else:
                if b.cod_eerr:
                    nivel = math.floor(len(b.cod_eerr) / 2)
                else:
                    nivel = math.floor(len(b.code) / 2)
            # nivel = len(a.code)
            vals = {
                'codigo': b.cod_eerr or b.code,
                'descripcion': b.name,
                'formula': '',
                'monto': int(total),
                'codigoPadre': b.parent_id.cod_eerr or b.parent_id.code or "0",
                "esHoja": False,
                "soloLectura": True,
                'nivel': nivel
                # 'account_id': b.id,
                #'parent_id':b.parent_id.id,
                #'padre':False
            }
            ddd.append(vals)
        #Cuentas DEL BALANCE
        for a in cuentas.filtered(lambda g: g.id in bala).sorted(key=lambda r:r.code, reverse = True):
            movi = movimientos.filtered(lambda r: r.account_id.id == a.id)
            # raise ValidationError('aaa %s' % movi)
            deb = sum(movi.mapped('debit'))
            cred = sum(movi.mapped('credit'))
            total = deb-cred
            total_ant = 0
            # if total != 0:
            #     _logger.info('ssss %s' % movi)
            puntos = a.code.find('.')
            nivel = 0
            if puntos != -1:
                nivel = a.code.count('.')
            else:
                nivel = math.floor(len(a.code) / 2)
            # nivel = len(a.code)
            vals = {
                'codigo': a.code,
                'descripcion': a.name,
                'formula': '',
                'monto': int(total),
                'codigoPadre': a.parent_id.code or "0",
                "esHoja": False,
                "soloLectura": True,
                'nivel': nivel
                # 'account_id': a.id,

                # 'code': a.code,
                # 'total': total,
                # 'total_ant':total_ant,
                #
                # 'parent_id':a.parent_id.id,
                # 'parent_code': a.parent_id.code or "0",
                # 'name':a.name,
                # 'formula':'""',
                # 'nivel':nivel,
                # "esHoja": False,
                # "soloLectura": True,
                # 'padre':False

            }
            ccc.append(vals)
        # Como todas las cuentas del plan contable ya fueron agregadas a la lista ccc entonces se procede a cargarle el monto del anio anterior a las cuentas que tienen movimiento el anio anterior
        # for b in cuentas.sorted(key=lambda r:r.code, reverse = True):
        #     movi = movimientos_ant.filtered(lambda r: r.account_id.id == b.id)
        #     # raise ValidationError('aaa %s' % movi)
        #     debant = sum(movi.mapped('debit'))
        #     credant = sum(movi.mapped('credit'))
        #     total_ant = debant - credant
        #
        #     # Esta función busca que cuenta coincide con la cuenta actual y busca en la lista ccc
        #     encon = list(filter(lambda r: r['account_id'] == b.id, ccc))
        #     # raise ValidationError('aaa %s' % encon[0]['total'])
        #     if encon:
        #
        #         encon[0]['total_ant'] += total_ant

        #Ahora se va a cargar las cuentas de resultados


        tipo_cuenta_resultado = self.env.ref('account.data_unaffected_earnings').id
        # Para poder identificar la cuenta de resultados el tipo de cuenta debe ser Ganancias En el año actual

        cuenta_resultado = self.env['account.account'].search([('user_type_id','=',tipo_cuenta_resultado)],limit=1)

        encon = list(filter(lambda r: r['codigo'] == cuenta_resultado.code, ccc))
        total_resultado = sum(movimientos_resultado.mapped('balance'))
        # total_resultado_ant = sum(movimientos_resultado_ant.mapped('balance'))


        if encon:
            encon[0]['monto'] += total_resultado
            # encon[0]['total_ant'] += total_resultado_ant

        #Se suman los saldos de las cuentas a sus cuentas padre

        for i in ccc:

            codi = i['codigo']
            totali = i['monto']
            # totali_ant = i['total_ant']
            encon = list(filter(lambda r: r['codigo'] == i['codigoPadre'], ccc))
            # raise ValidationError('aaa %s' % encon[0]['total'])
            if encon:

                encon[0]['monto'] += totali
                # encon[0]['total_ant'] += totali_ant
                # encon[0]['padre'] = True
        for u in ddd:

            codi = u['codigo']
            totali = u['monto']
            # totali_ant = i['total_ant']
            encon = list(filter(lambda r: r['codigo'] == u['codigoPadre'], ddd))
            # raise ValidationError('aaa %s' % encon[0]['total'])
            if encon:

                encon[0]['monto'] += totali
                # encon[0]['total_ant'] += totali_ant
                # encon[0]['padre'] = True

        # Se guarda en una lista solo las cuentas que tienen saldo distinto a cero

        for a in ccc[::-1]:
            if int(a['monto']) !=0:
                # encon = list(filter(lambda r: r['code'] == a.code, activo))
                pasiv = pasivo.filtered(lambda r: r.code == a['codigo'])
                neto = patrimonio.filtered(lambda r: r.code == a['codigo'])


                if len(pasiv)>0:
                  a['monto']= a['monto']*-1
                  # a['total_ant']= a['total_ant']*-1
                elif len(neto)>0:
                    a['monto'] = a['monto'] * -1
                    # a['total_ant'] = a['total_ant'] * -1


                final.append(a)
        for b in ddd[::-1]:
            if int(b['monto']) !=0:
                # encon = list(filter(lambda r: r['code'] == a.code, activo))
                ingre = ingreso.filtered(lambda r: r.code == b['codigo'])
                neto = patrimonio.filtered(lambda r: r.code == b['codigo'])


                if len(ingre)>0:
                  b['monto']= b['monto']*-1
                  # a['total_ant']= a['total_ant']*-1
                elif len(neto)>0:
                    b['monto'] = a['total'] * -1
                    # a['total_ant'] = a['total_ant'] * -1


                final_res.append(b)



        return final,final_res

    def get_datos_estado(self, fecha_inicio,fecha_fin,company_id):
        """
        La idea es un dicionario que tenga la cuenta y el total sumado



        :param fecha_inicio:
        :param fecha_fin:
        :param company_id:
        :return:
        """


        cuentas = list()
        resultados = list()
        reservas_list=list()
        capital_list = list()
        lista_final = list()
        lista_final_p = list()
        lista_final_total = list()
        domain=[]
        domain_ant=[]
        domain_resultado=[]
        domain_resultado_ant=[]
        ingreso = self.env['account.account'].search([('code', '=ilike', ('4%'))])
        egreso = self.env['account.account'].search([('code', '=ilike', ('5%'))])


        for resu in ingreso:

            resultados.append(resu.id)

        for resu in egreso:

            resultados.append(resu.id)

        domain_resultado += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
                             ('date', '<=', fecha_fin), ('parent_state', '=', 'posted'),
                             ('account_id', 'in', resultados)]
        movimientos_resultado = self.env['account.move.line'].search(domain_resultado, order='account_id')
        total_resultado = sum(movimientos_resultado.mapped('balance'))

        datos_anexo = self.env['account_reports_paraguay.anexo4'].search([('company_id','=',self.env.company.id)])

        cuenta_integracion_capital = datos_anexo.capital_integrado
        for int_cap in cuenta_integracion_capital:
            capital_list.append(int_cap.id)

        reserva_legal = datos_anexo.reserva_legal

        reserva_de_revaluo = datos_anexo.reserva_de_revaluo

        otras_reservas = datos_anexo.otras_reservas
        for otr in otras_reservas:
            reservas_list.append(otr.id)

        resultados_acumulados = datos_anexo.resultados_acumulados

        resultados_del_ejercicio = datos_anexo.resultados_del_ejercicio

        dividendos_a_pagar = datos_anexo.dividendos_a_pagar

        # fi = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fi = fecha_inicio
        fecha_inicio_ant = fi - relativedelta(years=1)
        anio = fecha_inicio_ant.year

        capital_inicio_anterior = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio_ant), ('account_id', 'in', capital_list), ('parent_state', '=', 'posted')])
        rl_inicio_anterior = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio_ant), ('account_id', '=', reserva_legal.id), ('parent_state', '=', 'posted')])
        rdr_inicio_anterior = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio_ant), ('account_id', '=', reserva_de_revaluo.id),
             ('parent_state', '=', 'posted')])
        otr_inicio_anterior = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio_ant), ('account_id', 'in', reservas_list), ('parent_state', '=', 'posted')])
        ra_inicio_anterior = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio_ant), ('account_id', '=', resultados_acumulados.id),
             ('parent_state', '=', 'posted')])
        re_inicio_anterior = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio_ant), ('account_id', '=', resultados_del_ejercicio.id),
             ('parent_state', '=', 'posted')])
        dap_inicio_anterior = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio_ant), ('account_id', '=', dividendos_a_pagar.id),
             ('parent_state', '=', 'posted')])

        capital_mov_anterior = self.env['account.move.line'].search(
            [('date', '>', fecha_inicio_ant), ('date', '<', fecha_inicio), ('account_id', 'in', capital_list),
             ('parent_state', '=', 'posted')])
        rl_mov_anterior = self.env['account.move.line'].search(
            [('date', '>', fecha_inicio_ant), ('date', '<', fecha_inicio), ('account_id', '=', reserva_legal.id),
             ('parent_state', '=', 'posted')])
        rdr_mov_anterior = self.env['account.move.line'].search(
            [('date', '>', fecha_inicio_ant), ('date', '<', fecha_inicio), ('account_id', '=', reserva_de_revaluo.id),
             ('parent_state', '=', 'posted')])
        otr_mov_anterior = self.env['account.move.line'].search(
            [('date', '>', fecha_inicio_ant), ('date', '<', fecha_inicio), ('account_id', 'in', reservas_list),
             ('parent_state', '=', 'posted')])
        ra_mov_anterior = self.env['account.move.line'].search(
            [('date', '>=', fecha_inicio_ant), ('date', '<', fecha_inicio),
             ('account_id', '=', resultados_acumulados.id), ('parent_state', '=', 'posted')])
        re_mov_anterior = self.env['account.move.line'].search(
            [('date', '>=', fecha_inicio_ant), ('date', '<', fecha_inicio),
             ('account_id', '=', resultados_del_ejercicio.id), ('parent_state', '=', 'posted')])
        dap_mov_anterior = self.env['account.move.line'].search(
            [('date', '>', fecha_inicio_ant), ('date', '<', fecha_inicio), ('account_id', '=', dividendos_a_pagar.id),
             ('parent_state', '=', 'posted')])

        capital_inicio_actual = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio), ('account_id', 'in', capital_list), ('parent_state', '=', 'posted')])
        # print (capital_inicio_actual)
        rl_inicio_actual = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio), ('account_id', '=', reserva_legal.id), ('parent_state', '=', 'posted')])
        rdr_inicio_actual = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio), ('account_id', '=', reserva_de_revaluo.id), ('parent_state', '=', 'posted')])
        otr_inicio_actual = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio), ('account_id', 'in', reservas_list), ('parent_state', '=', 'posted')])
        ra_inicio_actual = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio), ('account_id', '=', resultados_acumulados.id),
             ('parent_state', '=', 'posted')])
        re_inicio_actual = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio), ('account_id', '=', resultados_del_ejercicio.id),
             ('parent_state', '=', 'posted')])
        dap_inicio_actual = self.env['account.move.line'].search(
            [('date', '=', fecha_inicio), ('account_id', '=', dividendos_a_pagar.id), ('parent_state', '=', 'posted')])

        capital_mov_actual = self.env['account.move.line'].search(
            [('date', '>', fecha_inicio), ('date', '<=', fecha_fin), ('account_id', 'in', capital_list),
             ('parent_state', '=', 'posted')])
        rl_mov_actual = self.env['account.move.line'].search(
            [('date', '>', fecha_inicio), ('date', '<=', fecha_fin), ('account_id', '=', reserva_legal.id),
             ('parent_state', '=', 'posted')])
        rdr_mov_actual = self.env['account.move.line'].search(
            [('date', '>', fecha_inicio), ('date', '<=', fecha_fin), ('account_id', '=', reserva_de_revaluo.id),
             ('parent_state', '=', 'posted')])
        otr_mov_actual = self.env['account.move.line'].search(
            [('date', '>', fecha_inicio), ('date', '<=', fecha_fin), ('account_id', 'in', reservas_list),
             ('parent_state', '=', 'posted')])
        ra_mov_actual = self.env['account.move.line'].search(
            [('date', '>=', fecha_inicio), ('date', '<=', fecha_fin), ('account_id', '=', resultados_acumulados.id),
             ('parent_state', '=', 'posted')])
        re_mov_actual = self.env['account.move.line'].search(
            [('date', '>=', fecha_inicio), ('date', '<=', fecha_fin), ('account_id', '=', resultados_del_ejercicio.id),
             ('parent_state', '=', 'posted')])
        dap_mov_actual = self.env['account.move.line'].search(
            [('date', '>', fecha_inicio), ('date', '<=', fecha_fin), ('account_id', '=', dividendos_a_pagar.id),
             ('parent_state', '=', 'posted')])

        vals = { 'id':1,
                'name':'cian',
                 'total': sum(capital_inicio_anterior.mapped('balance'))

                }


        lista_final.append(vals)

        vals = {'id': 2,
                'name': 'rlian',
                'total': sum(rl_inicio_anterior.mapped('balance'))

                }
        lista_final.append(vals)

        vals = {'id': 3,
                'name': 'rdrian',
                'total': sum(rdr_inicio_anterior.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 4,
                'name': 'otrian',
                'total': sum(otr_inicio_anterior.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 5,
                'name': 'raian',
                'total': sum(ra_inicio_anterior.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 6,
                'name': 'reian',
                'total': sum(re_inicio_anterior.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 7,
                'name': 'dapian',
                'total': sum(dap_inicio_anterior.mapped('balance'))

                }

        lista_final.append(vals)


        vals = {'id': 8,
                'name': 'cman',
                'total': sum(capital_mov_anterior.mapped('balance'))

                }
        # print(capital_mov_anterior)
        # print(vals)
        lista_final.append(vals)


        vals = {'id': 9,
                'name': 'rlman',
                'total': sum(rl_mov_anterior.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 10,
                'name': 'rdrman',
                'total': sum(rdr_mov_anterior.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 11,
                'name': 'otrman',
                'total': sum(otr_mov_anterior.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 12,
                'name': 'raman',
                'total': sum(re_inicio_anterior.mapped('balance'))

                        }
        # print(vals)
        # print(ra_mov_anterior)
        lista_final.append(vals)


        vals = {'id': 13,
                'name': 'reman',
                'total': sum(re_mov_anterior.mapped('balance'))

                }
        # print(vals)
        # print(ra_mov_anterior)

        lista_final.append(vals)


        vals = {'id': 14,
                'name': 'dapman',
                'total': sum(dap_mov_anterior.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 15,
                'name': 'ciac',
                'total': sum(capital_inicio_actual.mapped('balance'))

                }
        # print (vals)
        lista_final.append(vals)


        vals = {'id': 16,
                'name': 'rliac',
                'total': sum(rl_inicio_actual.mapped('balance'))

                }
        # print(vals)
        lista_final.append(vals)


        vals = {'id': 17,
                'name': 'rdriac',
                'total': sum(rdr_inicio_actual.mapped('balance'))

                }
        # print(vals)
        lista_final.append(vals)


        vals = {'id': 18,
                'name': 'otriac',
                'total': sum(otr_inicio_actual.mapped('balance'))

                }
        # print(vals)
        lista_final.append(vals)


        vals = {'id': 19,
                'name': 'raiac',
                'total': sum(ra_inicio_actual.mapped('balance'))

                }
        # print(vals)
        lista_final.append(vals)


        vals = {'id': 20,
                'name': 'reiac',
                'total': sum(re_inicio_actual.mapped('balance'))

                }
        # print(vals)
        lista_final.append(vals)


        vals = {'id': 21,
                'name': 'dapiac',
                'total': sum(dap_inicio_actual.mapped('balance'))

                }
        # print(vals)
        lista_final.append(vals)


        vals = {'id': 22,
                'name': 'cmac',
                'total': sum(capital_mov_actual.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 23,
                'name': 'rlmac',
                'total': sum(rl_mov_actual.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 24,
                'name': 'rdrmac',
                'total': sum(rdr_mov_actual.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 25,
                'name': 'otrmac',
                'total': sum(otr_mov_actual.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 26,
                'name': 'ramac',
                'total': sum(re_inicio_actual.mapped('balance'))

                }
        lista_final.append(vals)


        vals = {'id': 27,
                'name': 'remac',
                'total': total_resultado

                }
        lista_final.append(vals)


        vals = {'id': 28,
                'name': 'dapmac',
                'total': sum(dap_mov_actual.mapped('balance'))

                }
        lista_final.append(vals)


        re_anterior= sum(capital_inicio_anterior.mapped('balance')) + \
        sum(rl_inicio_anterior.mapped('balance')) + \
        sum(rdr_inicio_anterior.mapped('balance')) + \
        sum(otr_inicio_anterior.mapped('balance')) + \
        sum(ra_inicio_anterior.mapped('balance')) + \
        sum(re_inicio_anterior.mapped('balance')) + \
        sum(dap_inicio_anterior.mapped('balance')) + \
        sum(capital_mov_anterior.mapped('balance')) + \
        sum(rl_mov_anterior.mapped('balance')) + \
        sum(rdr_mov_anterior.mapped('balance')) + \
        sum(otr_mov_anterior.mapped('balance')) + \
        sum(ra_mov_anterior.mapped('balance')) - \
        sum(ra_mov_anterior.mapped('balance')) + \
        sum(re_mov_anterior.mapped('balance')) - \
        sum(dap_mov_anterior.mapped('balance'))

        vals = {'id': 29,
                'name': 're_anterior',
                'total': re_anterior

                }
        lista_final.append(vals)

        re_actual = sum(capital_inicio_actual.mapped('balance')) + \
                      sum(rl_inicio_actual.mapped('balance')) + \
                      sum(rdr_inicio_actual.mapped('balance')) + \
                      sum(otr_inicio_actual.mapped('balance')) + \
                      sum(ra_inicio_actual.mapped('balance')) + \
                      sum(dap_inicio_actual.mapped('balance')) + \
                      sum(capital_mov_actual.mapped('balance')) + \
                      sum(rl_mov_actual.mapped('balance')) + \
                      sum(rdr_mov_actual.mapped('balance')) + \
                      sum(otr_mov_actual.mapped('balance')) + \
                      total_resultado + \
                      sum(dap_mov_actual.mapped('balance')) - \
                      sum(dap_inicio_actual.mapped('balance')) + \
                      sum(re_inicio_actual.mapped('balance'))




        # sum(re_inicio_actual.mapped('balance'))
        # sum(ra_mov_actual.mapped('balance'))
        # sum(ra_mov_actual.mapped('balance'))
        vals = {'id': 30,
                'name': 're_final',
                'total': re_actual
                }
        lista_final.append(vals)

        vale={'cuenta':'SALDO AL INICIO DEL EJERCICIO',
              'codigoCuenta':"SALDO_INICIO",
              "capitalIntegrado":abs(int(lista_final[14]['total'])),
              "reservasLegal":abs(int(lista_final[15]['total'])),
              "reservasDeRevaluo":abs(int(lista_final[16]['total'])),
              "otrasReservas":abs(int(lista_final[17]['total'])),
              "resultadosAcumulados": abs(int(lista_final[18]['total'])),
               "resultadosDelEjercicio": abs(int(lista_final[19]['total'])),
               "patrimonio": abs(int(lista_final[28]['total'])),
            }
        lista_final_p.append(vale)
        vale={'cuenta':'MOVIMIENTOS  DEL EJERCICIO',
              'codigoCuenta':"MOVIMIENTOS_EJERCICIO",
              "capitalIntegrado":0,
              "reservasLegal":0,
              "reservasDeRevaluo":0,
              "otrasReservas":0,
              "resultadosAcumulados": 0,
               "resultadosDelEjercicio": 0,
               "patrimonio": 0
            }
        lista_final_p.append(vale)

        vale={'cuenta':'INTEGRACIÓN DE CAPITAL',
              'codigoCuenta':"NTEGRACION_CAPITAL",
              "capitalIntegrado":abs(int(lista_final[21]['total'])),
              "reservasLegal":0,
              "reservasDeRevaluo":0,
              "otrasReservas":0,
              "resultadosAcumulados": 0,
               "resultadosDelEjercicio": 0,
               "patrimonio": 0
            }
        lista_final_p.append(vale)

        vale={"cuenta": "TRANSFERENCIA A DIVIDENDOS A PAGAR",
              "codigoCuenta": "TRANSFERENCIA_A_PAGAR",
              "capitalIntegrado":0,
              "reservasLegal":0,
              "reservasDeRevaluo":0,
              "otrasReservas":0,
              "resultadosAcumulados": -1*abs(int(lista_final[27]['total'])),
               "resultadosDelEjercicio": 0,
               "patrimonio": 0
            }
        lista_final_p.append(vale)
        vale={"cuenta": "TRANSFERENCIA A RESULTADOS ACUMULADOS",
                "codigoCuenta": "TRANSFERENCIA_RESULTADOS_ACUMULADOS",
              "capitalIntegrado":0,
              "reservasLegal":0,
              "reservasDeRevaluo":0,
              "otrasReservas":0,
              "resultadosAcumulados": abs(int(lista_final[25]['total'])),
               "resultadosDelEjercicio": -1*abs(int(lista_final[25]['total'])),
               "patrimonio": 0
            }
        lista_final_p.append(vale)

        vale={"cuenta": "AJUSTES/ DESAFECTAC. DE RESULT. ACUMULADOS",
        "codigoCuenta": "AJUSTES_RESULTADOS_ACUMULADOS",
              "capitalIntegrado":0,
              "reservasLegal":0,
              "reservasDeRevaluo":0,
              "otrasReservas":0,
              "resultadosAcumulados": 0,
               "resultadosDelEjercicio": 0,
               "patrimonio": 0
            }
        lista_final_p.append(vale)

        vale={"cuenta": "RESERVA LEGAL",
                "codigoCuenta": "RESERVA_LEGAL",
              "capitalIntegrado":0,
              "reservasLegal":abs(int(lista_final[22]['total'])),
              "reservasDeRevaluo":0,
              "otrasReservas":0,
              "resultadosAcumulados": 0,
               "resultadosDelEjercicio": 0,
               "patrimonio": 0
            }
        lista_final_p.append(vale)

        vale={"cuenta": "RESERVA DE REVALÚO",
        "codigoCuenta": "RESERVA_REVALUO",
              "capitalIntegrado":0,
              "reservasLegal":0,
              "reservasDeRevaluo":abs(int(lista_final[23]['total'])),
              "otrasReservas":0,
              "resultadosAcumulados": 0,
               "resultadosDelEjercicio": 0,
               "patrimonio": 0
            }
        lista_final_p.append(vale)
        vale={"cuenta": "OTRAS RESERVAS",
        "codigoCuenta": "OTRAS_RESERVAS",
              "capitalIntegrado":0,
              "reservasLegal":0,
              "reservasDeRevaluo":0,
              "otrasReservas":abs(int(lista_final[24]['total'])),
              "resultadosAcumulados": 0,
               "resultadosDelEjercicio": 0,
               "patrimonio": 0
            }
        lista_final_p.append(vale)
        vale={"cuenta": "RESULTADO DEL EJERCICIO",
            "codigoCuenta": "RESULTADO_EJERCICIO",
              "capitalIntegrado":0,
              "reservasLegal":0,
              "reservasDeRevaluo":0,
              "otrasReservas":0,
              "resultadosAcumulados": 0,
               "resultadosDelEjercicio": abs(int(lista_final[26]['total'])),
               "patrimonio": 0
            }
        lista_final_p.append(vale)

        valores= {
          "capitalIntegrado": abs(int(lista_final[14]['total'])+int(lista_final[21]['total'])),
          "reservasLegal": abs(int(lista_final[15]['total'])+int(lista_final[22]['total'])),
          "reservasDeRevaluo": abs(int(lista_final[16]['total'])+int(lista_final[23]['total'])),
          "otrasReservas": abs(int(lista_final[17]['total'])+int(lista_final[24]['total'])),
          "resultadosAcumulado": abs(int(lista_final[18]['total'])+int(lista_final[25]['total'])),
          "resultadosDelEjercicio": -1*int(lista_final[26]['total'])
        }
        lista_final_total.append(valores)



        return lista_final_p,valores
