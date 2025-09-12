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

class WizardReportLibroestado_patrimonio(models.TransientModel):
    _name = "estado_patrimonio.wizard.estado_patrimonio"


    fecha_inicio = fields.Date(string="Fecha desde")
    fecha_fin = fields.Date(string="Fecha hasta", default=fields.Date.today())
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self._get_default_company())


    @api.model
    def _get_default_company(self):
        return self.env.company.id

    def print_report_xlsx(self):
        data={}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin','company_id'])[0]
        return {
            'type': 'ir.actions.act_url',
            'url': '/getEEPP/xls/' + str(self.id),
            'target': 'current'
        }

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
        # fi = datetime.strptime(fecha, '%Y-%m-%d')
        fi = fecha
        anio = fi.year
        return anio
    def obtener_anio_anterior(self,fecha):
        # fi = datetime.strptime(fecha, '%Y-%m-%d')
        fi = fecha
        fecha_inicio_ant = fi - relativedelta(years=1)
        anio = fecha_inicio_ant.year
        return anio

    def formatear_fecha(self,fecha):
        # fi = datetime.strptime(fecha, '%Y-%m-%d')
        fi = fecha
        fd = datetime.strftime(fi, '%d/%m/%Y')

        return fd

class ReporteLibroCompras(models.AbstractModel):
    _name = 'report.accounting_reports_paraguay.estado_patrimonio_report'





    # @api.multi
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        movimientos = self.get_datos_estado(docs.fecha_inicio,docs.fecha_fin, docs.company_id)


        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'movimientos': movimientos,


        }
        return docargs

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
        capital_list=list()
        lista_final = list()
        domain=[]
        domain_ant=[]
        domain_resultado=[]
        domain_resultado_ant=[]
        #ingreso = self.env['account.account'].search([('code', '=ilike', ('4%'))])
        #egreso = self.env['account.account'].search([('code', '=ilike', ('5%'))])
        tipo_ingreso = self.env.ref('account.data_account_type_revenue').id
        tipo_egreso = self.env.ref('account.data_account_type_expenses').id
        tipo_depreciacion = self.env.ref('account.data_account_type_depreciation').id
        tipo_otro_ingreso = self.env.ref('account.data_account_type_other_income').id
        tipo_costo = self.env.ref('account.data_account_type_direct_costs').id
        ingreso = self.env['account.account'].search([('user_type_id', 'in', (tipo_ingreso, tipo_otro_ingreso))])
        egreso = self.env['account.account'].search(
            [('user_type_id', 'in', (tipo_egreso, tipo_costo, tipo_depreciacion))])

        for resu in ingreso:

            resultados.append(resu.id)

        for resu in egreso:

            resultados.append(resu.id)

        domain_resultado += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
                             ('date', '<=', fecha_fin), ('parent_state', '=', 'posted'),
                             ('account_id', 'in', resultados)]
        movimientos_resultado = self.env['account.move.line'].search(domain_resultado, order='account_id')
        total_resultado = sum(movimientos_resultado.mapped('balance'))

        datos_anexo = self.env['account_reports_paraguay.anexo4'].search([('company_id','=',company_id.id)])

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
        ff = fecha_fin
        fecha_inicio_ant = fi - relativedelta(years=1)
        fecha_fin_ant = ff - relativedelta(years=1)
        anio = fecha_inicio_ant.year


        capital_inicio_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date','=',fecha_inicio_ant),('account_id','in',capital_list),('parent_state','=','posted')])
        rl_inicio_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date','=',fecha_inicio_ant),('account_id','=',reserva_legal.id),('parent_state','=','posted')])
        rdr_inicio_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date','=',fecha_inicio_ant),('account_id','=',reserva_de_revaluo.id),('parent_state','=','posted')])
        otr_inicio_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date','=',fecha_inicio_ant),('account_id','in',reservas_list),('parent_state','=','posted')])
        ra_inicio_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date','=',fecha_inicio_ant),('account_id','=',resultados_acumulados.id),('parent_state','=','posted')]) #,('id','!=',4169143)])# TEMPORAL TEST traemos id especifico para test, al parecer el asiento pertenece a otra cuenta, simulamos el cambio excluyendo manualmente

        _logger.warning('ra inicio anterior %s resul acum id %s', ra_inicio_anterior, resultados_acumulados.id)
        # si no tiene movimientos de apertura traemos el de cierre del anho anterior
        if not ra_inicio_anterior:
            _logger.warning('no asiento inicio %s', ra_inicio_anterior)
            ra_inicio_anterior = self.env['account.move.line'].search([
                ('company_id', '=', company_id.id),
                ('move_id.cierre', '=', True),
                ('date', '=', fecha_fin_ant - relativedelta(years=1)),
                ('account_id', '=', resultados_acumulados.id),
                ('parent_state', '=', 'posted')
            ])
            _logger.warning("buscamos cierre anterior %s", ra_inicio_anterior)
            # TODO: verificar si necesitamos cambiar el signo cuando busca el cierre anterior en vez del apertura

        re_inicio_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date','=',fecha_inicio_ant),('account_id','=',resultados_del_ejercicio.id),('parent_state','=','posted')])
        # re_inicio_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('id','=',4169143),('parent_state','=','posted')]) #TEMPORAL TEST simulamos el cambio y traemos el asiento para test a esta cuenta

        _logger.warning('re inicio anterior %s', re_inicio_anterior)
        # si no tiene movimientos de apertura traemos el de cierre del anho anterior
        if not re_inicio_anterior:
            _logger.warning('no asiento inicio %s', re_inicio_anterior)
            re_inicio_anterior = self.env['account.move.line'].search([
                ('company_id', '=', company_id.id),
                ('move_id.cierre', '=', True),
                ('date', '=', fecha_fin_ant - relativedelta(years=1)),
                ('account_id', '=', resultados_del_ejercicio.id),
                ('parent_state', '=', 'posted')
            ])
            _logger.warning("buscamos cierre anterior %s", re_inicio_anterior)
            #TODO: verificar si necesitamos cambiar el signo cuando busca el cierre anterior en vez del apertura
        dap_inicio_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date','=',fecha_inicio_ant),('account_id','=',dividendos_a_pagar.id),('parent_state','=','posted')])

        capital_mov_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', False),('move_id.cierre', '=', False),('date','>=',fecha_inicio_ant),('date', '<=', fecha_fin_ant),('debit','=', 0),('account_id','in',capital_list),('parent_state','=','posted')]) # solo trae si esta en el haber
        rl_mov_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', False),('move_id.cierre', '=', False),('date','>=',fecha_inicio_ant),('date', '<=', fecha_fin_ant),('account_id','=',reserva_legal.id),('parent_state','=','posted')])
        rdr_mov_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', False),('move_id.cierre', '=', False),('date','>=',fecha_inicio_ant),('date', '<=', fecha_fin_ant),('account_id','=',reserva_de_revaluo.id),('parent_state','=','posted')])
        otr_mov_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', False),('move_id.cierre', '=', False),('date','>=',fecha_inicio_ant),('date', '<=', fecha_fin_ant),('account_id','in',reservas_list),('parent_state','=','posted')])
        ra_mov_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.cierre', '=', False),('date','>=',fecha_inicio_ant),('date', '<=', fecha_fin_ant),('account_id','=',resultados_acumulados.id),('parent_state','=','posted')])
        re_mov_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.cierre', '=', True),('date', '=', fecha_fin_ant),('debit','>', 0),('account_id','=',resultados_del_ejercicio.id),('parent_state','=','posted')]) #traemos el asiento de resultado que esta en el cierre pero solo del debe
        # re_mov_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('id', '=', 6903438)]) #TEMPORAL TEST traemos id especifico de posible asiento que su cuenta pertenece a res ejercicio y esta en acumulado, revisar acumulado, ahi excluimos y traemos aca para testeo


        _logger.warning('re mov anterior %s', re_mov_anterior)
        # si no tiene movimientos de apertura traemos el de cierre del anho anterior
        # if not re_mov_anterior:
        #     _logger.warning('no asiento cierre %s', re_mov_anterior)
        #     re_mov_anterior = self.env['account.move.line'].search([
        #         ('company_id', '=', company_id.id),
        #         ('move_id.cierre', '=', True),
        #         ('date', '=', fecha_fin_ant - relativedelta(years=1)),
        #         ('account_id', '=', resultados_del_ejercicio.id),
        #         ('parent_state', '=', 'posted')
        #     ])
        #     _logger.warning("buscamos cierre anterior %s", re_mov_anterior)
        #     # TODO: verificar si necesitamos cambiar el signo cuando busca el cierre anterior en vez del apertura

        dap_mov_anterior = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', False),('move_id.cierre', '=', False),('date','>=',fecha_inicio_ant),('date', '<=', fecha_fin_ant),('account_id','=',dividendos_a_pagar.id),('parent_state','=','posted')])

        capital_inicio_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date', '=', fecha_inicio), ('account_id', 'in', capital_list),('parent_state','=','posted')])
        # print (capital_inicio_actual)
        rl_inicio_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date', '=', fecha_inicio), ('account_id', '=', reserva_legal.id),('parent_state','=','posted')])
        rdr_inicio_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date', '=', fecha_inicio), ('account_id', '=', reserva_de_revaluo.id),('parent_state','=','posted')])
        otr_inicio_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date', '=', fecha_inicio), ('account_id', 'in', reservas_list),('parent_state','=','posted')])
        ra_inicio_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date', '=', fecha_inicio), ('account_id', '=', resultados_acumulados.id),('parent_state','=','posted')])
        # ra_inicio_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date', '=', fecha_inicio), ('account_id', '=', resultados_acumulados.id),('parent_state','=','posted'),('id','!=', 6901797)]) #TEMPORAL TEST excluimos id especifico que correspondera a ejercicio, REVISAR SIGNO
        _logger.warning('ra inicio actual %s', ra_inicio_actual)
        # si no tiene movimientos de apertura traemos el de cierre del anho anterior
        if not ra_inicio_actual:
            _logger.warning('no asiento inicio %s', ra_inicio_actual)
            ra_inicio_actual = self.env['account.move.line'].search([
                ('company_id', '=', company_id.id),
                ('move_id.cierre', '=', True),
                ('date', '=', fecha_fin - relativedelta(years=1)),
                ('account_id', '=', resultados_acumulados.id),
                ('parent_state', '=', 'posted')
            ])
            _logger.warning("buscamos cierre anterior %s", ra_inicio_actual)
            # TODO: verificar si necesitamos cambiar el signo cuando busca el cierre anterior en vez del apertura
        re_inicio_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date', '=', fecha_inicio), ('account_id', '=', resultados_del_ejercicio.id),('parent_state','=','posted')])
        # re_inicio_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('id','=',6901797)]) #TEMPORAL TEST traemos aca id especifico de apunte que probablemente su cuenta pertenece a ejercicio y esta en acumulado, abajo cambiamos signo, revisar tambien
        _logger.warning('re inicio actual %s', re_inicio_actual)
        # si no tiene movimientos de apertura traemos el de cierre del anho anterior
        if not re_inicio_actual:
            _logger.warning('no asiento inicio %s', re_inicio_actual)
            re_inicio_actual = self.env['account.move.line'].search([
                ('company_id', '=', company_id.id),
                ('move_id.cierre', '=', True),
                ('date', '=', fecha_fin - relativedelta(years=1)),
                ('account_id', '=', resultados_del_ejercicio.id),
                ('parent_state', '=', 'posted')
            ])
            _logger.warning("buscamos cierre anterior %s", re_inicio_actual)
            # TODO: verificar si necesitamos cambiar el signo cuando busca el cierre anterior en vez del apertura
        dap_inicio_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', True),('date', '=', fecha_inicio), ('account_id', '=', dividendos_a_pagar.id),('parent_state','=','posted')])


        capital_mov_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', False),('move_id.cierre', '=', False),('date', '>=', fecha_inicio),('date', '<=', fecha_fin), ('account_id', 'in', capital_list),('parent_state','=','posted')])
        rl_mov_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', False),('move_id.cierre', '=', False),('date', '>=', fecha_inicio),('date', '<=', fecha_fin), ('account_id', '=', reserva_legal.id),('parent_state','=','posted')])
        rdr_mov_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', False),('move_id.cierre', '=', False),('date', '>=', fecha_inicio),('date', '<=', fecha_fin), ('account_id', '=', reserva_de_revaluo.id),('parent_state','=','posted')])
        otr_mov_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', False),('move_id.cierre', '=', False),('date', '>=', fecha_inicio),('date', '<=', fecha_fin), ('account_id', 'in', reservas_list),('parent_state','=','posted')])
        ra_mov_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.cierre', '=', False),('date', '>=', fecha_inicio),('date', '<=', fecha_fin), ('account_id', '=', resultados_acumulados.id),('parent_state','=','posted')])
        re_mov_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.cierre', '=', True),('date', '=', fecha_fin),('debit','>', 0), ('account_id', '=', resultados_del_ejercicio.id),('parent_state','=','posted')]) # del cierre buscamos el debe de resultado
        dap_mov_actual = self.env['account.move.line'].search([('company_id','=',company_id.id),('move_id.apertura', '=', False),('move_id.cierre', '=', False),('date', '>=', fecha_inicio),('date', '<=', fecha_fin), ('account_id', '=', dividendos_a_pagar.id),('parent_state','=','posted')])

        total_resultado = sum(re_mov_actual.mapped('balance'))

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
                'total': -1 * sum(ra_inicio_anterior.mapped('balance')) #TEMPORAL TEST cambiamos signo

                }
        lista_final.append(vals)


        vals = {'id': 6,
                'name': 'reian',
                'total': -1 * sum(re_inicio_anterior.mapped('balance')) #TEMPORAL TEST cambiamos signo

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

        _logger.warning("ra inicio actual %s",sum(ra_inicio_actual.mapped('balance')))
        vals = {'id': 19,
                'name': 'raiac',
                'total': -1 * sum(ra_inicio_actual.mapped('balance')) #TEMPORAL TEST le cambiamos signo

                }
        # print(vals)
        lista_final.append(vals)


        vals = {'id': 20,
                'name': 'reiac',
                'total': -1 * sum(re_inicio_actual.mapped('balance')) #TEMPORAL TEST cambiamos signo porque pasara al debe cuando cambie la cuenta

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

        _logger.warning("re inicio actual %s", sum(re_inicio_actual.mapped('balance')))
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
        _logger.warning("29 re actual %s", re_actual)




        # sum(re_inicio_actual.mapped('balance'))
        # sum(ra_mov_actual.mapped('balance'))
        # sum(ra_mov_actual.mapped('balance'))
        vals = {'id': 30,
                'name': 're_final',
                'total': re_actual
                }
        lista_final.append(vals)



        vals = {'id': 31,
                'name': 're_ant_0',
                'total': abs(lista_final[14]['total']) + abs(lista_final[15]['total']) + abs(lista_final[16]['total']) + abs(lista_final[17]['total']) + lista_final[18]['total'] + lista_final[19]['total']
                }
        lista_final.append(vals)







        return lista_final


class DownloadXLS(http.Controller):
    @http.route('/getEEPP/xls/<int:id>', auth='public')
    def generarXLSX(self, id=None, **kw):
        record = request.env['estado_patrimonio.wizard.estado_patrimonio'].browse(id)
        _logger.warning('record estado patrimonio wiz %s', record)

        movimientos=ReporteLibroCompras.get_datos_estado(record,record.fecha_inicio,record.fecha_fin,record.company_id) #,'XLSX')

        _logger.warning('movimientos %s', movimientos)
        _logger.warning('cantidad elementos %s', len(movimientos))

        fp = io.BytesIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        sheet = workbook.add_worksheet('3_Estado de cambios del P. Neto')
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

        bold_center_9lg = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size':9,
            'bg_color': '#D3D3D3',
            'border': 1,
            'font_name':'Times New Roman',
        })

        formula_suma_horizontal = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size':9,
            'bg_color': '#D3D3D3',
            'border': 1,
            'font_name':'Times New Roman',
            'num_format': '#.##0',
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

        not_bold_center_lg = workbook.add_format({
            'bold': False,
            'align':'center',
            'font_size':9,
            'border': 1,
            'bg_color': '#D3D3D3',
            'font_name':'Times New Roman'
        })

        not_bold_center_g = workbook.add_format({
            'bold': False,
            'align':'center',
            'font_size':9,
            'border': 1,
            'bg_color': '#808080',
            'font_name':'Times New Roman'
        })
        
        sheet.set_default_row(15)
        sheet.set_column('A:I', 11)
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'})
        # CABECERAS Y SUS DATOS
        sheet.merge_range('A1:I2', 'ANEXO 4', merge_format)
        sheet.merge_range('A3:I4', 'ESTADO DE CAMBIOS DEL PATRIMONIO NETO', merge_format)
        sheet.merge_range('A5:I5', '', merge_format)
        sheet.merge_range('A6:G6', '1- Identificacion del Contribuyente', bold_center_9)
        sheet.merge_range('H6:I6', '2- Ejercicio Fiscal', bold_center_9)
        sheet.merge_range('A7:D7', 'Razon Social', bold_center_9)
        sheet.merge_range('E7:G7', 'Identificador RUC', bold_center_9)
        sheet.merge_range('A8:D8', record.company_id.razon_social, bold_center_9)
        sheet.merge_range('E8:G8', record.company_id.ruc, bold_center_9)
        sheet.write('H7', 'Desde', bold_center_9)
        sheet.write('I7', 'Hasta', bold_center_9)
        sheet.write('H8', record.formatear_fecha(record.fecha_inicio), bold_center_9)
        sheet.write('I8', record.formatear_fecha(record.fecha_fin), bold_center_9)
        sheet.merge_range('A9:I9', '', bold_center_9)
        sheet.merge_range('A10:C10', '3- Identificacion del Representante Legal', bold_center_9)
        sheet.merge_range('D10:F10', '4- Identificacion del Contador', bold_center_9)
        sheet.merge_range('G10:I10', '5- Identificacion del Auditor', bold_center_9)
        sheet.merge_range('A11:C11', 'Apellido/Nombre', bold_center_9)
        sheet.merge_range('D11:E11', 'Apellido/Nombre', bold_center_7)
        sheet.write('F11', 'Identificador RUC', bold_center_7)
        sheet.write('G11', 'Apellido/Nombre', bold_center_7)
        sheet.merge_range('H11:I11', 'Identificador RUC', bold_center_7)
        sheet.merge_range('A12:C12', record.company_id.representante_legal, bold_center_9)
        sheet.merge_range('D12:E12', record.company_id.contador, bold_center_7)
        sheet.write('F12', record.company_id.ruc_contador, bold_center_7)
        sheet.write('G12', record.company_id.auditor, bold_center_7)
        sheet.merge_range('H12:I12', record.company_id.ruc_auditor, bold_center_7)
        
        sheet.merge_range('A13:I13', '', bold_center_9)
        
        sheet.merge_range('A14:B15', 'CUENTAS', bold_center_9lg)
        sheet.write('C14', 'CAPITAL', bold_center_9lg)
        sheet.merge_range('D14:F14', 'RESERVAS', bold_center_9lg)
        sheet.merge_range('G14:H14', 'RESULTADOS', bold_center_9lg)
        sheet.merge_range('I14:I15', 'PATRIMONIO NETO', bold_center_9lg)
        sheet.write('C15', 'INTEGRADO', bold_center_9lg)
        sheet.write('D15', 'LEGAL', bold_center_9lg)
        sheet.write('E15', 'DE REVALUO', bold_center_9lg)
        sheet.write('F15', 'OTRAS RESERVAS', bold_center_9lg)
        sheet.write('G15', 'ACUMULADOS', bold_center_9lg)
        sheet.write('H15', 'DEL EJERCICIO', bold_center_9lg)


        row = 16
        # o = record

        # Bloque 1: SALDO AL INICIO DEL EJERCICIO
        sheet.merge_range(f'A{row}:B{row}', f'SALDO AL INICIO DEL EJERCICIO {record.obtener_anio_anterior(record.fecha_inicio)}', bold_center_9lg)
        _logger.warning('movimientos 0 total es %s', record.agregar_punto_de_miles(abs(int(movimientos[0]['total']))))
        sheet.write(f'C{row}', record.agregar_punto_de_miles(abs(int(movimientos[0]['total']))), bold_center_9lg)
        sheet.write(f'D{row}', record.agregar_punto_de_miles(abs(int(movimientos[1]['total']))), bold_center_9lg)
        sheet.write(f'E{row}', record.agregar_punto_de_miles(abs(int(movimientos[2]['total']))), bold_center_9lg)
        sheet.write(f'F{row}', record.agregar_punto_de_miles(int(movimientos[3]['total'])), bold_center_9lg)
        sheet.write(f'G{row}', record.agregar_punto_de_miles(int(movimientos[4]['total'])), bold_center_9lg)
        sheet.write(f'H{row}', record.agregar_punto_de_miles(int(movimientos[5]['total'])), bold_center_9lg)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(
            abs(int(movimientos[0]['total'])) +
            abs(int(movimientos[1]['total'])) +
            abs(int(movimientos[2]['total'])) +
            int(movimientos[3]['total']) +
            int(movimientos[4]['total']) +
            int(movimientos[5]['total'])),
            bold_center_9lg)
        row += 1

        
        # Bloque 2: MOVIMIENTOS DEL EJERCICIO
        sheet.merge_range(f'A{row}:B{row}', f'MOVIMIENTOS DEL EJERCICIO {record.obtener_anio_anterior(record.fecha_inicio)}', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', '', bold_center_9)
        row += 1
        
        # Bloque 3: INTEGRACIÓN DE CAPITAL
        sheet.merge_range(f'A{row}:B{row}', 'INTEGRACIÓN DE CAPITAL', bold_center_9)
        sheet.write(f'C{row}', record.agregar_punto_de_miles(abs(int(movimientos[7]['total']))), bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', record.agregar_punto_de_miles(-1 * abs(int(movimientos[7]['total']))), bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', '0', bold_center_9)
        row += 1
        
        # Bloque 4: TRANSFERENCIA A DIVIDENDOS A PAGAR
        sheet.merge_range(f'A{row}:B{row}', 'TRANSFERENCIA A DIVIDENDOS A PAGAR', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', record.agregar_punto_de_miles(-1 * abs(int(movimientos[13]['total']))), bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(-1 * abs(int(movimientos[13]['total']))), bold_center_9)
        row += 1
        
        # Bloque 5: TRANSFERENCIA A RESULTADOS ACUMULADOS
        sheet.merge_range(f'A{row}:B{row}', 'TRANSFERENCIA A RESULTADOS ACUMULADOS', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', record.agregar_punto_de_miles(abs(int(movimientos[11]['total']))), bold_center_9)
        sheet.write(f'H{row}', record.agregar_punto_de_miles(-1 * abs(int(movimientos[11]['total']))), bold_center_9)
        sheet.write(f'I{row}', '0', bold_center_9)
        row += 1

        # Bloque 6: AJUSTES/ DESAFECTAC. DE RESULT. ACUMULADOS
        sheet.merge_range(f'A{row}:B{row}', 'AJUSTES/ DESAFECTAC. DE RESULT. ACUMULADOS', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', '0', bold_center_9)
        row += 1
        
        # Bloque 7: RESERVA LEGAL
        sheet.merge_range(f'A{row}:B{row}', 'RESERVA LEGAL', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', record.agregar_punto_de_miles(abs(int(movimientos[8]['total']))), bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(abs(int(movimientos[8]['total']))), bold_center_9)
        row += 1
        
        # Bloque 8: RESERVA DE REVALÚO
        sheet.merge_range(f'A{row}:B{row}', 'RESERVA DE REVALÚO', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', record.agregar_punto_de_miles(abs(int(movimientos[9]['total']))), bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(abs(int(movimientos[9]['total']))), bold_center_9)
        row += 1
        
        # Bloque 9: OTRAS RESERVAS
        sheet.merge_range(f'A{row}:B{row}', 'OTRAS RESERVAS', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', record.agregar_punto_de_miles(abs(int(movimientos[10]['total']))), bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(abs(int(movimientos[10]['total']))), bold_center_9)
        row += 1
        
        # Bloque 10: RESULTADO DEL EJERCICIO
        sheet.merge_range(f'A{row}:B{row}', 'RESULTADO DEL EJERCICIO', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        # sheet.write(f'H{row}', record.agregar_punto_de_miles(-1 * int(movimientos[12]['total'])), bold_center_9) #ORIGINAL
        sheet.write(f'H{row}', record.agregar_punto_de_miles(int(movimientos[12]['total'])), bold_center_9) #TEMPORAL TEST saco el cambio de signo, (segun tests realizados se debe sacar para que calcule correctamente)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(int(movimientos[12]['total'])), bold_center_9)
        row += 1
        
        # Bloque 11: SALDO AL CIERRE DEL EJERCICIO
        sheet.merge_range(f'A{row}:B{row}', f'SALDO AL CIERRE DEL EJERCICIO {record.obtener_anio_anterior(record.fecha_inicio)} e INICIO DEL EJERCICIO {record.obtener_anio_actual(record.fecha_inicio)}', bold_center_9lg)
        sheet.write(f'C{row}', record.agregar_punto_de_miles(abs(int(movimientos[14]['total']))), bold_center_9lg)
        sheet.write(f'D{row}', record.agregar_punto_de_miles(abs(int(movimientos[15]['total']))), bold_center_9lg)
        sheet.write(f'E{row}', record.agregar_punto_de_miles(abs(int(movimientos[16]['total']))), bold_center_9lg)
        sheet.write(f'F{row}', record.agregar_punto_de_miles(abs(int(movimientos[17]['total']))), bold_center_9lg)
        sheet.write(f'G{row}', record.agregar_punto_de_miles(int(movimientos[18]['total'])), bold_center_9lg)
        sheet.write(f'H{row}', record.agregar_punto_de_miles(int(movimientos[19]['total'])), bold_center_9lg)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(abs(int(movimientos[30]['total']))), bold_center_9lg)
        row += 1
        
        # Bloque 12: MOVIMIENTOS DEL EJERCICIO (ANIO ACTUAL)
        sheet.merge_range(f'A{row}:B{row}', f'MOVIMIENTOS DEL EJERCICIO {record.obtener_anio_actual(record.fecha_inicio)}', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', '', bold_center_9)
        row += 1
        
        # Bloque 13: INTEGRACIÓN DE CAPITAL (ANIO ACTUAL)
        sheet.merge_range(f'A{row}:B{row}', 'INTEGRACIÓN DE CAPITAL', bold_center_9)
        sheet.write(f'C{row}', record.agregar_punto_de_miles(abs(int(movimientos[21]['total']))), bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', record.agregar_punto_de_miles(-1 * abs(int(movimientos[21]['total']))), bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', '0', bold_center_9)
        row += 1
        
        # Bloque 14: TRANSFERENCIA A DIVIDENDOS A PAGAR (ANIO ACTUAL)
        sheet.merge_range(f'A{row}:B{row}', 'TRANSFERENCIA A DIVIDENDOS A PAGAR', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', record.agregar_punto_de_miles(-1 * abs(int(movimientos[27]['total']))), bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(-1 * abs(int(movimientos[27]['total']))), bold_center_9)
        row += 1
        
        # Bloque 15: TRANSFERENCIA A RESULTADOS ACUMULADOS (ANIO ACTUAL)
        sheet.merge_range(f'A{row}:B{row}', 'TRANSFERENCIA A RESULTADOS ACUMULADOS', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', record.agregar_punto_de_miles(abs(int(movimientos[25]['total']))), bold_center_9)
        sheet.write(f'H{row}', record.agregar_punto_de_miles(-1 * abs(int(movimientos[25]['total']))), bold_center_9)
        sheet.write(f'I{row}', '0', bold_center_9)
        row += 1

        # Bloque 16: AJUSTES/ DESAFECTAC. DE RESULT. ACUMULADOS
        sheet.merge_range(f'A{row}:B{row}', 'AJUSTES/ DESAFECTAC. DE RESULT. ACUMULADOS', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', '0', bold_center_9)
        row += 1
        
        # Bloque 17: RESERVA LEGAL
        sheet.merge_range(f'A{row}:B{row}', 'RESERVA LEGAL', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', record.agregar_punto_de_miles(abs(int(movimientos[22]['total']))), bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(abs(int(movimientos[22]['total']))), bold_center_9)
        row += 1
        
        # Bloque 18: RESERVA DE REVALÚO
        sheet.merge_range(f'A{row}:B{row}', 'RESERVA DE REVALÚO', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', record.agregar_punto_de_miles(abs(int(movimientos[23]['total']))), bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(abs(int(movimientos[23]['total']))), bold_center_9)
        row += 1
        
        # Bloque 19: OTRAS RESERVAS
        sheet.merge_range(f'A{row}:B{row}', 'OTRAS RESERVAS', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', record.agregar_punto_de_miles(abs(int(movimientos[24]['total']))), bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', '', bold_center_9)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(abs(int(movimientos[24]['total']))), bold_center_9)
        row += 1
        
        # Bloque 20: RESULTADO DEL EJERCICIO
        sheet.merge_range(f'A{row}:B{row}', 'RESULTADO DEL EJERCICIO', bold_center_9)
        sheet.write(f'C{row}', '', bold_center_9)
        sheet.write(f'D{row}', '', bold_center_9)
        sheet.write(f'E{row}', '', bold_center_9)
        sheet.write(f'F{row}', '', bold_center_9)
        sheet.write(f'G{row}', '', bold_center_9)
        sheet.write(f'H{row}', record.agregar_punto_de_miles(int(movimientos[26]['total'])), bold_center_9)
        sheet.write(f'I{row}', record.agregar_punto_de_miles(int(movimientos[26]['total'])), bold_center_9)
        row += 1
        
        # Bloque 21: SALDO AL CIERRE DEL EJERCICIO
        sheet.merge_range(f'A{row}:B{row}', f'SALDO AL CIERRE DEL EJERCICIO {record.obtener_anio_actual(record.fecha_inicio)}', bold_center_9lg)
        sheet.write(f'C{row}', record.agregar_punto_de_miles(abs(int(movimientos[14]['total'])+int(movimientos[21]['total']))), bold_center_9lg)
        sheet.write(f'D{row}', record.agregar_punto_de_miles(abs(int(movimientos[15]['total'])+int(movimientos[22]['total']))), bold_center_9lg)
        sheet.write(f'E{row}', record.agregar_punto_de_miles(abs(int(movimientos[16]['total'])+int(movimientos[23]['total']))), bold_center_9lg)
        sheet.write(f'F{row}', record.agregar_punto_de_miles(abs(int(movimientos[17]['total'])+int(movimientos[24]['total']))), bold_center_9lg)
        sheet.write(f'G{row}', record.agregar_punto_de_miles(int(movimientos[18]['total'])+int(movimientos[21]['total'])+abs(int(movimientos[25]['total']))), bold_center_9lg)
        sheet.write(f'H{row}', record.agregar_punto_de_miles(int(movimientos[26]['total'])), bold_center_9lg)
        # sheet.write(f'I{row}', record.agregar_punto_de_miles((abs(int(movimientos[29]['total'])))-(abs(int(movimientos[18]['total'])+int(movimientos[25]['total'])))), bold_center_9lg)
        total_suma = (
                abs(int(movimientos[14]['total'])+int(movimientos[21]['total'])) +
                abs(int(movimientos[15]['total'])+int(movimientos[22]['total'])) +
                abs(int(movimientos[16]['total'])+int(movimientos[23]['total'])) +
                abs(int(movimientos[17]['total'])+int(movimientos[24]['total'])) +
                int(movimientos[18]['total'])+int(movimientos[21]['total'])+abs(int(movimientos[25]['total'])) +
                int(movimientos[26]['total'])
        )

        sheet.write(
            f'I{row}',
            record.agregar_punto_de_miles(total_suma),
            bold_center_9lg
        )
        row += 1



        workbook.close()
        fp.seek(0)
        new_report_from = record.fecha_inicio.strftime('%d-%m-%Y')
        new_report_to = record.fecha_fin.strftime('%d-%m-%Y')
        filename = 'Estado de Patrimonio Neto ' + str(new_report_from) + ' al ' + str(new_report_to) + '.xlsx'
        return request.make_response(fp.read(),
                                     [('Content-Type',
                                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                                      ('Content-Disposition', content_disposition(filename))])
