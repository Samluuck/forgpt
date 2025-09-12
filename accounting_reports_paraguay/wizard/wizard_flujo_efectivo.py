# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time, collections
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import logging
import operator
import io
import json
import os
import tempfile
import xlsxwriter
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception, content_disposition
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class WizardFlujoEfectivo(models.TransientModel):
    _name = "flujo_efectivo.wizard"

    fecha_inicio = fields.Date(string="Fecha desde")
    fecha_fin = fields.Date(string="Fecha hasta", default=fields.Date.today())
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self._get_default_company())

    @api.model
    def _get_default_company(self):
        return self.env.company.id

    def print_report_xlsx(self):
        data = {}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin', 'company_id'])[0]
        return {
            'type': 'ir.actions.act_url',
            'url': '/getFFEE/xls/' + str(self.id),
            'target': 'current'
        }

    def check_report(self):
        data = {}
        data['form'] = self.read(['fecha_inicio', 'fecha_fin'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['fecha_inicio', 'fecha_fin'])[0])
        return self.env.ref('accounting_reports_paraguay.flujo_efectivo_id').report_action(self, data)

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
        fi = datetime.strptime(str(fecha), '%Y-%m-%d')
        anio = fi.year
        return anio

    def obtener_anio_anterior(self, fecha):
        fi = datetime.strptime(str(fecha), '%Y-%m-%d')
        fecha_inicio_ant = fi - relativedelta(years=1)
        anio = fecha_inicio_ant.year
        return anio

    def formatear_fecha(self, fecha):
        fi = datetime.strptime(str(fecha), '%Y-%m-%d')
        fd = datetime.strftime(fi, '%d/%m/%Y')
        return fd

    def preparar_movimientos(self, fecha_inicio, fecha_final):
        anexo3_obj = self.env['account_reports_paraguay.anexo3']
        anexo3_id = anexo3_obj.search([('company_id', '=', self.company_id.id)])
        datos, datos_ant = anexo3_id.preparar_datos(fecha_inicio, fecha_final)
        # datos = anexo3_id.preparar_datos(fecha_inicio, fecha_final)
        # datos_ant = datos
        # _logger.warning('datos de preparar datos %s', datos)
        return datos, datos_ant, anexo3_id

    def obtener_valor(self, id_operacion, fecha_inicio, fecha_final, es_actual):
        """
        :param id_operacion: pueden recibirse las siguientes operaciones:
        * 1 : ventas netas
        * 2 : pagos a proveedores locales
        * 3 : pago a proveedores del exterior
        * 4 : efectivo pagado a empleados
        * 5 : efectivo generado por otras operaciones
        * 6 : pago de impuestos
        * 7 : aumento de inversiones temporales
        * 8 : aumento de inversiones a largo plazo
        * 9 : aumento de propiedad
        * 10 : aporte de capital
        * 11 : aumento de prestamos
        * 12 : dividendos pagados
        * 13 : aumento de intereses
        * 14: aumento de efectivo y equivalentes
        * 15 efectivo y sus equivalentes al comienzo del periodo
        :param fecha_inicio: fecha
        :param fecha_final: fecha
        :param es_actual: booleano para saber si es el anio actual o no.
        :return:
        Valor numerico de la operacion
        """

        anexo3_obj = self.env['account_reports_paraguay.anexo3']
        _logger.warning('self %s', self)
        _logger.warning('self company %s', self.company_id)
        anexo3_id = anexo3_obj.search([('company_id', '=', self.company_id.id)])
        # if not es_actual:
        #     fecha_inicio='2022-01-01'
        #     fecha_final='2022-12-31'
        if len(anexo3_id) > 0:
            print(f"obtener_valor: fecha_inicio={fecha_inicio}, fecha_final={fecha_final}, es_actual={es_actual}")
            valor = anexo3_id.obtener_valor(id_operacion, fecha_inicio, fecha_final, es_actual)
        else:
            raise ValidationError(
                'Favor asegurarse de completar el formulario de configuracion del anexo 3. Contactar con el administrador')

        return valor


class ReporteFLujoEfectivo(models.AbstractModel):
    _name = 'report.accounting_reports_paraguay.flujo_efectivo_report'

    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        # movimientos = self.get_datos_balance(docs.fecha_inicio, docs.fecha_fin, docs.company_id)
        movimientos = []
        print(f"_get_report_values: fecha_inicio={docs.fecha_inicio}, fecha_final={docs.fecha_fin}")

        docargs = {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'movimientos': movimientos,
        }
        return docargs

    def get_datos_balance(self, fecha_inicio, fecha_fin, company_id):
        """
        La idea es un dicionario que tenga la cuenta y el total sumado
        :param fecha_inicio:
        :param fecha_fin:
        :param company_id:
        :return:
        """
        print(f"get_datos_balance: fecha_inicio={fecha_inicio}, fecha_final={fecha_fin}")
        cuentas = list()
        resultados = list()
        domain = []
        domain_ant = []
        domain_resultado = []
        domain_resultado_ant = []

        activo = self.env['account.account'].search([('code', '=ilike', ('1%'))])
        pasivo = self.env['account.account'].search([('code', '=ilike', ('2%'))])
        patrimonio = self.env['account.account'].search([('code', '=ilike', ('3%'))])
        ingreso = self.env['account.account'].search([('code', '=ilike', ('4%'))])
        egreso = self.env['account.account'].search([('code', '=ilike', ('5%'))])
        for cue in activo:
            cuentas.append(cue.id)

        for cue in pasivo:
            cuentas.append(cue.id)
        for cue in patrimonio:
            cuentas.append(cue.id)

        for resu in ingreso:
            resultados.append(resu.id)

        for resu in egreso:
            resultados.append(resu.id)

        # Se prepara el domain para los movimientos del anio de busqueda
        domain += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio), ('date', '<=', fecha_fin),
                   ('parent_state', '=', 'posted'), ('account_id', 'in', cuentas)]

        # Se realiza el proceso para calcular cual es el anio anterior al de busqueda y luego se crea el domain
        fi = datetime.strptime(str(fecha_inicio), '%Y-%m-%d')
        ff = datetime.strptime(str(fecha_fin), '%Y-%m-%d')
        fecha_inicio_ant = fi - relativedelta(years=1)
        fecha_fin_ant = ff - relativedelta(years=1)

        domain_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
                       ('date', '<=', fecha_fin_ant), ('parent_state', '=', 'posted'), ('account_id', 'in', cuentas)]

        # Se hace el domain para el resultado del anio de busqueda y del anio anterior
        domain_resultado += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio),
                             ('date', '<=', fecha_fin), ('parent_state', '=', 'posted'),
                             ('account_id', 'in', resultados)]

        domain_resultado_ant += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio_ant),
                                 ('date', '<=', fecha_fin_ant), ('parent_state', '=', 'posted'),
                                 ('account_id', 'in', resultados)]

        movimientos = self.env['account.move.line'].search(domain, order='account_id')
        movimientos_ant = self.env['account.move.line'].search(domain_ant, order='account_id')
        movimientos_resultado = self.env['account.move.line'].search(domain_resultado, order='account_id')
        movimientos_resultado_ant = self.env['account.move.line'].search(domain_resultado_ant, order='account_id')

        padres = list()
        ccc = list()
        ddd = list()
        final = list()
        codigo_actual = ''
        suma = 0
        nro = 0
        cod = None

        # Se trae todas la cuentas que se encuentran en el plan contable, se agrega el context show_parent_account = True para que pueda traer las cuentas tipo vista
        cuentas = self.env['account.account'].with_context(show_parent_account=True).search(
            [('deprecated', '=', False), ('company_id', '=', company_id.id)])

        # Se agregan a una lista todas las cuentas del plan contable y las cuentas que tienen movimiento en el anio de busqueda ya se le va poniendo el saldo
        for a in cuentas.sorted(key=lambda r: r.code, reverse=True):
            movi = movimientos.filtered(lambda r: r.account_id.id == a.id)
            # raise ValidationError('aaa %s' % movi)
            total = sum(movi.mapped('balance'))
            total_ant = 0

            vals = {
                'code': a.code,
                'total': total,
                'total_ant': total_ant,
                'account_id': a.id,
                'parent_id': a.parent_id.id,
                'name': a.name,
                'padre': False
            }
            ccc.append(vals)
        # Como todas las cuentas del plan contable ya fueron agregadas a la lista ccc entonces se procede a cargarle el monto del anio anterior a las cuentas que tienen movimiento el anio anterior
        for b in cuentas.sorted(key=lambda r: r.code, reverse=True):
            movi = movimientos_ant.filtered(lambda r: r.account_id.id == b.id)
            # raise ValidationError('aaa %s' % movi)
            total_ant = sum(movi.mapped('balance'))

            # Esta función busca que cuenta coincide con la cuenta actual y busca en la lista ccc
            encon = list(filter(lambda r: r['account_id'] == b.id, ccc))
            # raise ValidationError('aaa %s' % encon[0]['total'])
            if encon:
                encon[0]['total_ant'] += total_ant

        # Ahora se va a cargar las cuentas de resultados
        tipo_cuenta_resultado = self.env.ref('account.data_unaffected_earnings').id
        # Para poder identificar la cuenta de resultados el tipo de cuenta debe ser Ganancias En el año actual

        cuenta_resultado = self.env['account.account'].search([('user_type_id', '=', tipo_cuenta_resultado)], limit=1)

        encon = list(filter(lambda r: r['account_id'] == cuenta_resultado.id, ccc))
        total_resultado = sum(movimientos_resultado.mapped('balance'))
        total_resultado_ant = sum(movimientos_resultado_ant.mapped('balance'))

        if encon:
            encon[0]['total'] += total_resultado
            encon[0]['total_ant'] += total_resultado_ant

        # Se suman los saldos de las cuentas a sus cuentas padre
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
        for a in ccc[::-1]:
            if int(a['total']) != 0 or int(a['total_ant']) != 0:
                final.append(a)

        _logger.warning('get datos balance %s', final)
        final = []
        return final


class DownloadXLS(http.Controller):
    @http.route('/getFFEE/xls/<int:id>', auth='public')
    def generarXLSX(self, id=None, **kw):
        record = request.env['flujo_efectivo.wizard'].browse(id)
        _logger.warning('record flujo ef wiz %s', record)
        moves, moves_ant, anexo = record.preparar_movimientos(record.fecha_inicio, record.fecha_fin)
        fi = datetime.strptime(str(record.fecha_inicio), '%Y-%m-%d')
        fecha_inicio_ant = fi - relativedelta(years=1)  # Año anterior
        fin = datetime.strptime(str(record.fecha_fin), '%Y-%m-%d')
        fecha_fin_ant = fin - relativedelta(years=1)

        # Función auxiliar para verificar condiciones
        def verificar_condicion(move, tipo, fecha_inicio, fecha_fin):
            # fi = datetime.strptime(str(record.fecha_inicio), '%Y-%m-%d')
            # fecha_inicio_ant = fi - relativedelta(years=2)  # Año anterior
            # fin = datetime.strptime(str(record.fecha_fin), '%Y-%m-%d')
            # fecha_fin_ant = fin - relativedelta(years=2)
            if tipo == 'saldo_inicial' and move['apertura'] and datetime.strptime(str(move['date']),
                                                                                  '%Y-%m-%d') == fecha_inicio:
                return True
            if tipo == 'saldo_final' and move['cierre'] and datetime.strptime(str(move['date']),
                                                                              '%Y-%m-%d') == fecha_fin:
                return True
            if tipo == 'rango' and not move['apertura'] and not move[
                'cierre'] and fecha_inicio <= datetime.strptime(str(move['date']), '%Y-%m-%d') <= fecha_fin:
                return True
            # if tipo == 'rango_ant' and not move['cierre'] and not move['resultado'] and fecha_inicio_ant <= datetime.strptime(str(move['date']), '%Y-%m-%d') <= fecha_fin_ant:
            #     return True
            return False

        # Función para procesar cuentas
        def procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin):
            valor_total = 0
            for cuentas_ids, tipo, suma in cuentas:
                suma_grupo = 0
                for cuenta in cuentas_ids:
                    if cuenta.id in moves:
                        for move in moves.get(cuenta.id, []):
                            if verificar_condicion(move, tipo, fecha_inicio, fecha_fin):
                                suma_grupo += move['balance']

                # Aplicar el factor de suma al total acumulado
                valor_total += suma * suma_grupo

                _logger.warning(f"Procesado: {tipo}, suma grupo {suma_grupo}, suma {suma}")
            return valor_total

        def obtener_datos(anexo, moves, id_operacion, fecha_inicio=False, fecha_fin=False):
            _logger.warning('obtener datos self es %s', anexo)
            dict_cuentas = {}
            valor_total = 0
            valor = 0
            if id_operacion == 1:
                cuentas = [
                    (anexo.saldo_inicial_clientes, 'saldo_inicial', -1),
                    (anexo.ventas, 'rango', 1),
                    (anexo.descuentos_concedidos, 'rango', -1),
                    (anexo.saldo_final_anticipo_clientes, 'saldo_final', -1),
                    (anexo.saldo_inicial_tarjetas_credito, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_otras_cuentas_ventas, 'saldo_inicial', 1),
                    (anexo.saldo_final_otras_cuentas_ventas, 'saldo_final', 1),
                    (anexo.saldo_final_clientes, 'saldo_final', -1),
                    (anexo.saldo_inicial_anticipos_clientes, 'saldo_inicial', -1),
                    (anexo.saldo_final_tarjetas_credito, 'saldo_final', -1),
                ]

                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                valor_total *= -1

                _logger.warning('Valor final calculado: %s', valor_total)

            if id_operacion == 2:  # Reemplaza N con el número de operación correspondiente
                cuentas = [
                    (anexo.saldo_inicial_anticipo_proveedores, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_gastos_pagados_adelantado, 'saldo_inicial', 1),
                    (anexo.saldo_final_proveedores_locales, 'saldo_final', 1),
                    (anexo.saldo_final_otros_acreedores, 'saldo_final', 1),
                    (anexo.saldo_inicial_mercaderias, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_otras_cuentas_pago_proveedores_locales, 'saldo_inicial', 1),
                    (anexo.saldo_final_otras_cuentas_pago_proveedores_locales, 'saldo_final', 1),
                    (anexo.saldo_final_anticipo_proveedores, 'saldo_final', 1),
                    (anexo.saldo_inicial_proveedores_locales, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_otros_acreedores, 'saldo_inicial', 1),
                    (anexo.saldo_final_gastos_pagados_adelantado, 'saldo_final', 1),
                    (anexo.saldo_final_mercaderias, 'saldo_final', 1),
                    (anexo.costo_ventas, 'rango', -1),
                ]

                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 3:  # pagos a proveedores del exterior
                cuentas = [
                    (anexo.saldo_inicial_anticipo_proveedores_exterior, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_gastos_pagados_adelantado_exterior, 'saldo_inicial', 1),
                    (anexo.saldo_final_proveedores_exterior, 'saldo_final', 1),
                    (anexo.saldo_inicial_mercaderias_exterior, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_otras_cuentas_pago_proveedores_exterior, 'saldo_inicial', 1),
                    (anexo.saldo_final_otras_cuentas_pago_proveedores_exterior, 'saldo_final', 1),
                    (anexo.saldo_final_anticipo_proveedores_exterior, 'saldo_final', 1),
                    (anexo.saldo_inicial_proveedores_exterior, 'saldo_inicial', 1),
                    (anexo.saldo_final_gastos_pagados_adelantado_exterior, 'saldo_final', 1),
                    (anexo.saldo_final_mercaderias_exterior, 'saldo_final', 1),
                    (anexo.costo_ventas_exterior, 'rango', 1),
                ]
                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 4:  # efectivo pagado a empleados
                cuentas = [
                    (anexo.saldo_final_obligaciones_laborales, 'saldo_final', 1),
                    (anexo.saldo_final_otras_cuentas_efectivo_pagado_empleados, 'saldo_final', 1),
                    (anexo.saldo_inicial_obligaciones_laborales, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_otras_cuentas_efectivo_pagado_empleados, 'saldo_inicial', 1),
                    (anexo.sueldos_jornales, 'rango', 1),
                    (anexo.aporte_patronal, 'rango', 1),
                    (anexo.aguinaldos, 'rango', 1),
                ]

                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                valor_total *= -1
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 5:  # efectivo generado (usado) por otras actividades operativas
                cuentas = [
                    (anexo.agua_luz_telefono_internet, 'rango', 1),
                    (anexo.alquileres_pagados, 'rango', 1),
                    (anexo.combustibles_lubricantes, 'rango', 1),
                    (anexo.comisiones_gastos_bancarios, 'rango', 1),
                    (anexo.comisiones_sobre_ventas, 'rango', 1),
                    (anexo.donaciones_contribuciones, 'rango', 1),
                    (anexo.fletes_pagados, 'rango', 1),
                    (anexo.gastos_cobranzas, 'rango', 1),
                    (anexo.gastos_representacion, 'rango', 1),
                    (anexo.gastos_pagados_exterior, 'rango', 1),
                    (anexo.honorarios_profesionales, 'rango', 1),
                    (anexo.juicios_gastos_judiciales, 'rango', 1),
                    (anexo.movilidad, 'rango', 1),
                    (anexo.otros_gastos_ventas, 'rango', 1),
                    (anexo.publicidad_propaganda, 'rango', 1),
                    (anexo.remuneracion_personal_superior, 'rango', 1),
                    (anexo.reparacion_mantenimiento, 'rango', 1),
                    (anexo.seguros_pagados, 'rango', 1),
                    (anexo.utiles_oficina, 'rango', 1),
                    (anexo.viaticos_vendedores, 'rango', 1),
                    (anexo.saldo_inicial_otras_cuentas_activo, 'saldo_inicial', -1),
                    (anexo.saldo_final_otras_cuentas_pasivo, 'saldo_final', -1),
                    (anexo.saldo_final_otras_cuentas_activo, 'saldo_final', -1),
                    (anexo.saldo_inicial_otras_cuentas_pasivo, 'saldo_inicial', -1),
                    (anexo.gastos_no_deducibles, 'rango', 1),
                ]

                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                valor_total *= -1
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 6:  # pago de impuestos
                cuentas = [
                    (anexo.saldo_inicial_anticipos_retenciones, 'saldo_inicial', 1),
                    (anexo.saldo_final_sset, 'saldo_final', 1),
                    (anexo.saldo_final_iva_pagar, 'saldo_final', 1),
                    (anexo.saldo_inicial_iva_credito_fiscal, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_retencion_iva_credito, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_iva_pagar, 'saldo_inicial', 1),
                    (anexo.saldo_final_iva_credito_fiscal, 'saldo_final', 1),
                    (anexo.saldo_final_retencion_iva_credito, 'saldo_final', 1),
                    (anexo.impuesto_ejercicio, 'saldo_final', 1),
                    (anexo.pago_impuesto_renta, 'saldo_final', 1),
                    (anexo.saldo_final_anticipos_retenciones, 'saldo_final', 1),
                    (anexo.saldo_inicial_sset, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_otras_cuentas_pago_impuestos, 'saldo_inicial', 1),
                    (anexo.saldo_final_otras_cuentas_pago_impuestos, 'saldo_final', 1),
                    (anexo.multas, 'saldo_final', 1),
                ]

                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 7:  # aumento/disminución neto/a de inversiones temporarias
                cuentas = [
                    (anexo.saldo_inicial_inversiones_temporarias, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_otros_activos_corto_plazo, 'saldo_inicial', 1),
                    (anexo.saldo_final_inversiones_temporarias, 'saldo_final', 1),
                    (anexo.saldo_final_otros_activos_corto_plazo, 'saldo_final', 1),
                ]

                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 8:  # aumento/disminución neto/a de inversiones a largo plazo
                cuentas = [
                    (anexo.saldo_inicial_inversiones_largo_plazo, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_otros_activos_largo_plazo, 'saldo_inicial', 1),
                    (anexo.saldo_final_inversiones_largo_plazo, 'saldo_final', 1),
                    (anexo.saldo_final_otros_activos_largo_plazo, 'saldo_final', 1),
                    (anexo.saldo_final_otras_cuentas_inversiones_largo_plazo, 'saldo_final', 1)
                ]

                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 9:  # AUMENTO/DISMINUCIÓN NETO/A DE PROPIEDAD, PLANTA Y EQUIPO
                cuentas = [
                    (anexo.saldo_inicial_propiedad_planta_equipo, 'saldo_inicial', 1),
                    (anexo.saldo_inicial_otras_cuentas_propiedad_planta_equipo, 'rango', 1),
                    (anexo.saldo_final_reservas_revaluo, 'saldo_final', 1),
                    (anexo.utilidad_perdida_venta_activos_fijos, 'saldo_final', 1),
                    (anexo.depreciaciones_ejercicio, 'saldo_final', 1),
                    (anexo.amortizacion_ejercicio, 'saldo_final', 1),
                    (anexo.saldo_final_propiedad_planta_equipo, 'saldo_final', 1),
                    (anexo.saldo_inicial_reservas_revaluo, 'saldo_inicial', 1)
                ]

                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 10:  # aporte de capital
                cuentas = [
                    (anexo.saldo_final_capital, 'saldo_final', 1),
                    (anexo.saldo_inicial_capital, 'saldo_inicial', 1),
                ]

                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 11:  # aumento/disminución neto/a de préstamos
                cuentas = [
                    (anexo.saldo_final_prestamos, 'saldo_final', 1),
                    (anexo.saldo_inicial_prestamos, 'saldo_inicial', 1),
                ]

                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 12:  # dividendos pagados
                cuentas = [
                    (anexo.saldo_inicial_dividendos_pagar, 'saldo_inicial', 1),
                    (anexo.saldo_final_dividendos_pagar, 'saldo_final', 1)
                ]
                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 13:  # aumento/disminución neto/a de intereses
                cuentas = [
                    (anexo.saldo_inicial_intereses_pagar, 'saldo_inicial', 1),
                    (anexo.saldo_final_intereses_pagar, 'saldo_final', 1),
                    (anexo.otros_intereses_bancarios, 'saldo_final', 1),
                ]
                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 14:  # efecto diferencia de cambio
                cuentas = [
                    (anexo.diferencias_cambios, 'rango', 1)
                ]
                valor_total = procesar_cuentas(cuentas, moves, fecha_inicio, fecha_fin)
                valor_total *= -1
                _logger.warning('Valor final calculado: %s', valor_total)

            elif id_operacion == 15:  # efectivo y sus equivalentes al comienzo del periodo
                # cuentas = [
                #         (anexo.disponibilidades, 'rango_ant', 1)
                #     ]
                cuentas = [
                    (anexo.disponibilidades, 1)
                ]
                account_move_obj = request.env['account.move.line']
                fecha_inicio = datetime.strptime(str(fecha_inicio), '%Y-%m-%d %H:%M:%S')
                fecha_fin = datetime.strptime(str(fecha_fin), '%Y-%m-%d %H:%M:%S')
                fecha_i = fecha_inicio - relativedelta(years=1)
                fecha_u = fecha_fin - relativedelta(years=1)
                _logger.warning('fecha inicio u %s', fecha_i)
                _logger.warning('fecha fin u %s', fecha_u)
                movess = account_move_obj.search([
                    ('date', '>=', fecha_i),
                    ('date', '<=', fecha_u),
                    ('move_id.cierre', '=', False),
                    ('move_id.resultado', '=', False),
                    ('move_id.state', '=', 'posted')
                ])

                valor_total = sum(
                    movess.filtered(lambda r: r.account_id in anexo.disponibilidades).mapped('balance'))

                _logger.warning('Valor final calculado: %s', valor_total)

            precision = 0
            rounding_method = 'HALF-UP'
            valor_total = float_round(valor_total, precision_digits=precision, rounding_method=rounding_method)

            return valor_total

        valores_actual = []
        valores_anterior = []

        def procesar_datos_recursivamente(moves, moves_ant, anexo, num_bloque, fi, fin, fecha_inicio_ant,
                                          fecha_fin_ant):
            """
            Función recursiva que procesa los datos para los arrays valores_actual y valores_anterior.

            :param moves: Datos actuales.
            :param moves_ant: Datos anteriores.
            :param anexo: Información adicional asociada a los movimientos.
            :param num_bloque: El número del bloque a procesar (se pasa de manera dinámica).
            :param fi: Fecha de inicio para los datos actuales.
            :param fin: Fecha de fin para los datos actuales.
            :param fecha_inicio_ant: Fecha de inicio para los datos anteriores.
            :param fecha_fin_ant: Fecha de fin para los datos anteriores.
            :return: Dos arrays con los valores calculados, uno para valores_actual y otro para valores_anterior.
            """
            valores_actual = []  # Array para los valores actuales
            valores_anterior = []  # Array para los valores anteriores

            for i in range(1, 15):
                valor = obtener_datos(anexo, moves, i, fi, fin)
                valores_actual.append(valor)

                valor_anterior = obtener_datos(anexo, moves_ant, i, fecha_inicio_ant, fecha_fin_ant)
                valores_anterior.append(valor_anterior)

            return valores_actual, valores_anterior

        valores_actual, valores_anterior = procesar_datos_recursivamente(moves, moves_ant, anexo, 1, fi, fin,
                                                                         fecha_inicio_ant, fecha_fin_ant)
        _logger.warning('valores actual %s', valores_actual)
        _logger.warning('valores anterior %s', valores_anterior)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:

            workbook = xlsxwriter.Workbook(temp_file.name)
            sheet = workbook.add_worksheet('3_Estado_de_Flujo_de_Efectivo')

            bold_left_9 = workbook.add_format({

                'bold': True,
                'align': 'left',
                'font_size': 9,
                'border': 1,
                'font_name': 'Times New Roman'
            })
            not_bold_left_9 = workbook.add_format({
                'align': 'left',
                'font_size': 9,
                'border': 1,
                'font_name': 'Times New Roman'
            })
            bold_right_9 = workbook.add_format({
                'bold': True,
                'align': 'right',
                'font_size': 9,
                'border': 1,
                'font_name': 'Times New Roman'
            })
            not_bold_right_9 = workbook.add_format({
                'align': 'right',
                'font_size': 9,
                'border': 1,
                'font_name': 'Times New Roman'
            })
            bold_center_9 = workbook.add_format({
                'bold': True,
                'align': 'center',
                'font_size': 9,
                'border': 1,
                'font_name': 'Times New Roman',
            })

            bold_center_7 = workbook.add_format({
                'bold': True,
                'align': 'center',
                'font_size': 7,
                'border': 1,
                'font_name': 'Times New Roman'
            })
            not_bold_center = workbook.add_format({
                'bold': False,
                'align': 'center',
                'font_size': 9,
                'border': 1,
                'font_name': 'Times New Roman'
            })

            not_bold_center_lg = workbook.add_format({
                'bold': False,
                'align': 'center',
                'font_size': 9,
                'border': 1,
                'bg_color': '#D3D3D3',
                'font_name': 'Times New Roman'
            })

            not_bold_center_g = workbook.add_format({
                'bold': False,
                'align': 'center',
                'font_size': 9,
                'border': 1,
                'bg_color': '#808080',
                'font_name': 'Times New Roman'
            })

            sheet.set_default_row(15)
            sheet.set_column('A:F', 11)
            merge_format = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'})
            # CABECERAS Y SUS DATOS
            sheet.merge_range('A1:F2', 'ANEXO 3', merge_format)
            sheet.merge_range('A3:F4', 'ESTADO DE FLUJO DE EFECTIVO', merge_format)
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

            # DATOS
            i = 14
            sheet.merge_range('A14:F14', '', bold_center_9)
            # sheet.write('E14', record.obtener_anio_actual(record.fecha_inicio), bold_center_9)
            # sheet.write('F14', record.obtener_anio_anterior(record.fecha_inicio), bold_center_9)

            actividades_operativas_actual = 0
            actividades_operativas_anterior = 0
            actividades_inversion_actual = 0
            actividades_inversion_anterior = 0
            actividades_financiamiento_actual = 0
            actividades_financiamiento_anterior = 0
            cambio_actual = 0
            cambio_anterior = 0
            valor_total_actual = 0
            valor_total_anterior = 0

            sheet.merge_range(i, 0, i, 3, 'FLUJO DE EFECTIVO POR ACTIVIDADES OPERATIVAS', not_bold_center_g)
            sheet.write(i, 4, record.obtener_anio_actual(record.fecha_inicio), not_bold_center_g)
            sheet.write(i, 5, record.obtener_anio_anterior(record.fecha_inicio), not_bold_center_g)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'VENTAS NETAS (COBRO NETO)', bold_left_9)
            # valor = int(record.obtener_valor(1, record.fecha_inicio, record.fecha_fin, True))
            # valor = int(obtener_datos(anexo,moves,1, fi, fin))
            valor = valores_actual[0]
            _logger.warning('valor uno %s', valor)
            # raise ValidationError('si')
            actividades_operativas_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,1, fecha_inicio_ant, fecha_fin_ant))
            valor_anterior = valores_anterior[0]
            _logger.warning('valor ant %s', valor_anterior)
            # raise ValidationError('si')
            actividades_operativas_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'PAGO A PROVEEDORES LOCALES (PAGO NETO)', bold_left_9)
            # valor = int(obtener_datos(anexo,moves,2, fi, fin))
            valor = valores_actual[1]
            actividades_operativas_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,2, fecha_inicio_ant, fecha_fin_ant))
            valor_anterior = valores_anterior[1]
            actividades_operativas_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'PAGO A PROVEEDORES DEL EXTERIOR (PAGO NETO)', bold_left_9)
            # valor = int(obtener_datos(anexo,moves,3, fi, fin))
            valor = valores_actual[2]
            valor_anterior = valores_anterior[2]
            actividades_operativas_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,3, fecha_inicio_ant, fecha_fin_ant))
            actividades_operativas_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'EFECTIVO PAGADO A EMPLEADOS', bold_left_9)
            valor = valores_actual[3]
            valor_anterior = valores_anterior[3]
            # valor = int(obtener_datos(anexo,moves,4, fi, fin))
            actividades_operativas_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,4, fecha_inicio_ant, fecha_fin_ant))
            actividades_operativas_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'EFECTIVO GENERADO (USADO) POR OTRAS ACTIVIDADES OPERATIVAS',
                              bold_left_9)
            valor = valores_actual[4]
            valor_anterior = valores_anterior[4]
            # valor = int(obtener_datos(anexo,moves,5, fi, fin))
            actividades_operativas_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,5, fecha_inicio_ant, fecha_fin_ant))
            actividades_operativas_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'PAGO DE IMPUESTOS', bold_left_9)
            valor = valores_actual[5]
            valor_anterior = valores_anterior[5]
            # valor = int(obtener_datos(anexo,moves,6, fi, fin))
            actividades_operativas_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,6, fecha_inicio_ant, fecha_fin_ant))
            actividades_operativas_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'EFECTIVO NETO POR ACTIVIDADES OPERATIVAS', not_bold_center_lg)
            sheet.write(i, 4, record.agregar_punto_de_miles(actividades_operativas_actual), not_bold_center_lg)
            sheet.write(i, 5, record.agregar_punto_de_miles(actividades_operativas_anterior),
                        not_bold_center_lg)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'FLUJO DE EFECTIVO POR ACTIVIDADES DE INVERSIÓN', not_bold_center_g)
            sheet.write(i, 4, record.obtener_anio_actual(record.fecha_inicio), not_bold_center_g)
            sheet.write(i, 5, record.obtener_anio_anterior(record.fecha_inicio), not_bold_center_g)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'AUMENTO/DISMINUCIÓN NETO/A DE INVERSIONES TEMPORARIAS', bold_left_9)
            valor = valores_actual[6]
            valor_anterior = valores_anterior[6]
            # valor = int(obtener_datos(anexo,moves,7, fi, fin))
            actividades_inversion_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,7, fecha_inicio_ant, fecha_fin_ant))
            actividades_inversion_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'AUMENTO/DISMINUCIÓN NETO/A DE INVERSIONES A LARGO PLAZO',
                              bold_left_9)
            valor = valores_actual[7]
            valor_anterior = valores_anterior[7]
            # valor = int(obtener_datos(anexo,moves,8, fi, fin))
            actividades_inversion_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,8, fecha_inicio_ant, fecha_fin_ant))
            actividades_inversion_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'AUMENTO/DISMINUCIÓN NETO/A DE PROPIEDAD, PLANTA Y EQUIPO',
                              bold_left_9)
            valor = valores_actual[8]
            valor_anterior = valores_anterior[8]
            # valor = int(obtener_datos(anexo,moves,9, fi, fin))
            actividades_inversion_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,9, fecha_inicio_ant, fecha_fin_ant))
            actividades_inversion_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'EFECTIVO NETO POR ACTIVIDADES DE INVERSIÓN', not_bold_center_lg)
            sheet.write(i, 4, record.agregar_punto_de_miles(actividades_inversion_actual), not_bold_center_lg)
            sheet.write(i, 5, record.agregar_punto_de_miles(actividades_inversion_anterior), not_bold_center_lg)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'FLUJO DE EFECTIVO POR ACTIVIDADES DE FINANCIAMIENTO',
                              not_bold_center_g)
            sheet.write(i, 4, record.obtener_anio_actual(record.fecha_inicio), not_bold_center_g)
            sheet.write(i, 5, record.obtener_anio_anterior(record.fecha_inicio), not_bold_center_g)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'APORTE DE CAPITAL', bold_left_9)
            valor = valores_actual[9]
            valor_anterior = valores_anterior[9]
            # valor = int(obtener_datos(anexo,moves,10, fi, fin))
            actividades_financiamiento_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,10, fecha_inicio_ant, fecha_fin_ant))
            actividades_financiamiento_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'AUMENTO/DISMINUCIÓN NETO/A DE PRÉSTAMOS', bold_left_9)
            valor = valores_actual[10]
            valor_anterior = valores_anterior[10]
            # valor = int(obtener_datos(anexo,moves,11, fi, fin))
            actividades_financiamiento_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,11, fecha_inicio_ant, fecha_fin_ant))
            actividades_financiamiento_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'DIVIDENDOS PAGADOS', bold_left_9)
            valor = valores_actual[11]
            valor_anterior = valores_anterior[11]
            # valor = int(obtener_datos(anexo,moves,12, fi, fin))
            actividades_financiamiento_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,12, fecha_inicio_ant, fecha_fin_ant))
            actividades_financiamiento_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'AUMENTO/DISMINUCIÓN NETO/A DE INTERESES', bold_left_9)
            valor = valores_actual[12]
            valor_anterior = valores_anterior[12]
            # valor = int(obtener_datos(anexo,moves,13, fi, fin))
            actividades_financiamiento_actual += valor
            # valor_anterior = int(obtener_datos(anexo,moves_ant,13, fecha_inicio_ant, fecha_fin_ant))
            actividades_financiamiento_anterior += valor_anterior
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'EFECTIVO NETO POR ACTIVIDADES DE FINANCIAMIENTO', not_bold_center_lg)
            sheet.write(i, 4, record.agregar_punto_de_miles(actividades_financiamiento_actual),
                        not_bold_center_lg)
            sheet.write(i, 5, record.agregar_punto_de_miles(actividades_financiamiento_anterior),
                        not_bold_center_lg)

            i += 1

            sheet.merge_range(i, 0, i, 3,
                              'EFECTO DE LAS GANANCIAS O PÉRDIDAS POR DIFERENCIAS DE TIPO DE CAMBIO',
                              not_bold_center_g)
            cambio_actual = valores_actual[13]
            cambio_anterior = valores_anterior[13]
            # cambio_actual = int(obtener_datos(anexo,moves,14, fi, fin))
            # cambio_anterior = int(obtener_datos(anexo,moves_ant,14, fecha_inicio_ant, fecha_fin_ant))
            sheet.write(i, 4, record.agregar_punto_de_miles(cambio_actual), not_bold_center_g)
            sheet.write(i, 5, record.agregar_punto_de_miles(cambio_anterior), not_bold_center_g)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'AUMENTO/DISMINUCIÓN NETO/A DE EFECTIVOS Y SUS EQUIVALENTES',
                              bold_left_9)
            valor_total_actual = actividades_operativas_actual + actividades_inversion_actual + actividades_financiamiento_actual + cambio_actual
            valor_total_anterior = actividades_operativas_anterior + actividades_inversion_anterior + actividades_financiamiento_anterior + cambio_anterior
            ######
            sheet.write(i, 4, record.agregar_punto_de_miles(valor_total_actual), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_total_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'EFECTIVO Y SUS EQUIVALENTES AL COMIENZO DEL PERIODO', not_bold_center)
            # valor = valores_actual[14]
            # valor_anterior = valores_anterior[14]
            valor = obtener_datos(anexo, moves, 15, fi, fin)
            valor_anterior = obtener_datos(anexo, moves_ant, 15, fecha_inicio_ant, fecha_fin_ant)
            sheet.write(i, 4, record.agregar_punto_de_miles(valor), not_bold_center)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_anterior), not_bold_center)

            i += 1

            sheet.merge_range(i, 0, i, 3, 'EFECTIVO Y SUS EQUIVALENTES AL CIERRE DEL PERIODO', not_bold_center_lg)
            sheet.write(i, 4, record.agregar_punto_de_miles(valor_total_actual + valor), not_bold_center_lg)
            sheet.write(i, 5, record.agregar_punto_de_miles(valor_total_anterior + valor_anterior),
                        not_bold_center_lg)

            workbook.close()
            temp_file_path = temp_file.name

        new_report_from = record.fecha_inicio.strftime('%d-%m-%Y')
        new_report_to = record.fecha_fin.strftime('%d-%m-%Y')
        filename = f"FFEE {new_report_from} al {new_report_to}.xlsx"

        with open(temp_file_path, 'rb') as file:
            file_content = file.read()

        os.unlink(temp_file_path)

        return request.make_response(file_content,
                                     [('Content-Type',
                                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                                      ('Content-Disposition', content_disposition(filename))])