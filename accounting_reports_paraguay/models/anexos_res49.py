from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class Anexo3(models.Model):
    _name = 'account_reports_paraguay.anexo3'
    _description = 'Configuración de cuentas Anexo 3'

    # Definición de campos
    name = fields.Char(default="Configuración de cuentas Anexo 3", required=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Compañia', default=lambda self: self.env.company, required=True,
                                 tracking=True)
    saldo_inicial_clientes = fields.One2many('account.account', 'saldo_inicial_clientes_id', required=True,
                                             tracking=True, string="Saldo Inicial Clientes")
    ventas = fields.One2many('account.account', 'ventas_id', required=True, tracking=True, string="Ventas")
    descuentos_concedidos = fields.One2many('account.account', 'descuentos_concedidos_id', required=True, tracking=True,
                                            string="Descuentos Concedidos")
    saldo_final_anticipo_clientes = fields.One2many('account.account', 'saldo_final_anticipo_clientes_id',
                                                    required=True, tracking=True,
                                                    string="Saldo Final Anticipo de Clientes")
    saldo_inicial_tarjetas_credito = fields.One2many('account.account', 'saldo_inicial_tarjetas_credito_id',
                                                     required=True, tracking=True,
                                                     string="Saldo Inicial Tarjetas de Créditos")
    saldo_final_clientes = fields.One2many('account.account', 'saldo_final_clientes_id', required=True, tracking=True,
                                           string="Saldo Final Clientes")
    saldo_inicial_anticipos_clientes = fields.One2many('account.account', 'saldo_inicial_anticipos_clientes_id',
                                                       required=True, tracking=True,
                                                       string="Saldo Inicial Anticipos de Clientes")
    saldo_final_tarjetas_credito = fields.One2many('account.account', 'saldo_final_tarjetas_credito_id', required=True,
                                                   tracking=True, string="Saldo Final Tarjetas de Créditos")
    saldo_inicial_anticipo_proveedores = fields.One2many('account.account', 'saldo_inicial_anticipo_proveedores_id',
                                                         required=True, tracking=True,
                                                         string="Saldo Inicial Anticipo a Proveedores")
    saldo_inicial_gastos_pagados_adelantado = fields.One2many('account.account',
                                                              'saldo_inicial_gastos_pagados_adelantado_id',
                                                              required=True, tracking=True,
                                                              string="Saldo Inicial Gastos Pagados por Adelantado")
    saldo_final_proveedores_locales = fields.One2many('account.account', 'saldo_final_proveedores_locales_id',
                                                      required=True, tracking=True,
                                                      string="Saldo Final Proveedores Locales")
    saldo_final_otros_acreedores = fields.One2many('account.account', 'saldo_final_otros_acreedores_id', required=True,
                                                   tracking=True, string="Saldo Final Otros Acreedores")
    saldo_inicial_mercaderias = fields.One2many('account.account', 'saldo_inicial_mercaderias_id', required=True,
                                                tracking=True, string="Saldo Inicial Mercaderías")
    saldo_final_anticipo_proveedores = fields.One2many('account.account', 'saldo_final_anticipo_proveedores_id',
                                                       required=True, tracking=True,
                                                       string="Saldo Final Anticipo a Proveedores")
    saldo_inicial_proveedores_locales = fields.One2many('account.account', 'saldo_inicial_proveedores_locales_id',
                                                        required=True, tracking=True,
                                                        string="Saldo Inicial Proveedores Locales")
    saldo_inicial_otros_acreedores = fields.One2many('account.account', 'saldo_inicial_otros_acreedores_id',
                                                     required=True, tracking=True,
                                                     string="Saldo Inicial Otros Acreedores")
    saldo_final_gastos_pagados_adelantado = fields.One2many('account.account',
                                                            'saldo_final_gastos_pagados_adelantado_id', required=True,
                                                            tracking=True,
                                                            string="Saldo Final Gastos Pagados por Adelantado")
    saldo_final_mercaderias = fields.One2many('account.account', 'saldo_final_mercaderias_id', required=True,
                                              tracking=True, string="Saldo Final Mercaderías")
    costo_ventas = fields.One2many('account.account', 'costo_ventas_id', required=True, tracking=True,
                                   string="Costo de Ventas")
    saldo_inicial_anticipo_proveedores_exterior = fields.One2many('account.account',
                                                                  'saldo_inicial_anticipo_proveedores_exterior_id',
                                                                  required=True, tracking=True,
                                                                  string="Saldo Inicial Anticipo a Proveedores del Exterior")
    saldo_inicial_gastos_pagados_adelantado_exterior = fields.One2many('account.account',
                                                                       'saldo_inicial_gastos_pagados_adelantado_exterior_id',
                                                                       required=True, tracking=True,
                                                                       string="Saldo Inicial Gastos Pagados por Adelantado")
    saldo_final_proveedores_exterior = fields.One2many('account.account', 'saldo_final_proveedores_exterior_id',
                                                       required=True, tracking=True,
                                                       string="Saldo Final Proveedores del Exterior")
    saldo_inicial_mercaderias_exterior = fields.One2many('account.account', 'saldo_inicial_mercaderias_exterior_id',
                                                         required=True, tracking=True,
                                                         string="Saldo Inicial Mercaderías")
    saldo_final_anticipo_proveedores_exterior = fields.One2many('account.account',
                                                                'saldo_final_anticipo_proveedores_exterior_id',
                                                                required=True, tracking=True,
                                                                string="Saldo Final Anticipo a Proveedores del Exterior")
    saldo_inicial_proveedores_exterior = fields.One2many('account.account', 'saldo_inicial_proveedores_exterior_id',
                                                         required=True, tracking=True,
                                                         string="Saldo Inicial Proveedores del Exterior")
    saldo_final_gastos_pagados_adelantado_exterior = fields.One2many('account.account',
                                                                     'saldo_final_gastos_pagados_adelantado_exterior_id',
                                                                     required=True, tracking=True,
                                                                     string="Saldo Final Gastos Pagados por Adelantado")
    saldo_final_mercaderias_exterior = fields.One2many('account.account', 'saldo_final_mercaderias_exterior_id',
                                                       required=True, tracking=True, string="Saldo Final Mercaderías")
    costo_ventas_exterior = fields.One2many('account.account', 'costo_ventas_exterior_id', required=True, tracking=True,
                                            string="Costo de Ventas")
    saldo_final_obligaciones_laborales = fields.One2many('account.account', 'saldo_final_obligaciones_laborales_id',
                                                         required=True, tracking=True,
                                                         string="Saldo Final Obligaciones Laborales y Cargas Sociales")
    saldo_inicial_obligaciones_laborales = fields.One2many('account.account', 'saldo_inicial_obligaciones_laborales_id',
                                                           required=True, tracking=True,
                                                           string="Saldo Inicial Obligaciones Laborales y Cargas Sociales")
    sueldos_jornales = fields.One2many('account.account', 'sueldos_jornales_id', required=True, tracking=True,
                                       string="Sueldos y Jornales")
    aporte_patronal = fields.One2many('account.account', 'aporte_patronal_id', required=True, tracking=True,
                                      string="Aporte Patronal")
    aguinaldos = fields.One2many('account.account', 'aguinaldos_id', required=True, tracking=True,
                                 string="Aguinaldos e Indemnizaciones")
    agua_luz_telefono_internet = fields.One2many('account.account', 'agua_luz_telefono_internet_id', required=True,
                                                 tracking=True, string="Agua, Luz, Teléfono e Internet")
    alquileres_pagados = fields.One2many('account.account', 'alquileres_pagados_id', required=True, tracking=True,
                                         string="Alquileres Pagados")
    combustibles_lubricantes = fields.One2many('account.account', 'combustibles_lubricantes_id', required=True,
                                               tracking=True, string="Combustibles y Lubricantes")
    comisiones_gastos_bancarios = fields.One2many('account.account', 'comisiones_gastos_bancarios_id', required=True,
                                                  tracking=True, string="Comisiones y Gastos Bancarios")
    comisiones_sobre_ventas = fields.One2many('account.account', 'comisiones_sobre_ventas_id', required=True,
                                              tracking=True, string="Comisiones Pagadas sobre Ventas")
    donaciones_contribuciones = fields.One2many('account.account', 'donaciones_contribuciones_id', required=True,
                                                tracking=True, string="Donaciones y Contribuciones")
    fletes_pagados = fields.One2many('account.account', 'fletes_pagados_id', required=True, tracking=True,
                                     string="Fletes Pagados")
    gastos_cobranzas = fields.One2many('account.account', 'gastos_cobranzas_id', required=True, tracking=True,
                                       string="Gastos de Cobranzas")
    gastos_representacion = fields.One2many('account.account', 'gastos_representacion_id', required=True, tracking=True,
                                            string="Gastos de Representación")
    gastos_pagados_exterior = fields.One2many('account.account', 'gastos_pagados_exterior_id', required=True,
                                              tracking=True, string="Gastos Pagados en Exterior")
    honorarios_profesionales = fields.One2many('account.account', 'honorarios_profesionales_id', required=True,
                                               tracking=True, string="Honorarios Profesionales")
    juicios_gastos_judiciales = fields.One2many('account.account', 'juicios_gastos_judiciales_id', required=True,
                                                tracking=True, string="Juicios y Gastos Judiciales")
    movilidad = fields.One2many('account.account', 'movilidad_id', required=True, tracking=True, string="Movilidad")
    otros_gastos_ventas = fields.One2many('account.account', 'otros_gastos_ventas_id', required=True, tracking=True,
                                          string="Otros Gastos de Ventas")
    publicidad_propaganda = fields.One2many('account.account', 'publicidad_propaganda_id', required=True, tracking=True,
                                            string="Publicidad y Propaganda")
    remuneracion_personal_superior = fields.One2many('account.account', 'remuneracion_personal_superior_id',
                                                     required=True, tracking=True,
                                                     string="Remuneración de Personal Superior")
    reparacion_mantenimiento = fields.One2many('account.account', 'reparacion_mantenimiento_id', required=True,
                                               tracking=True, string="Reparación y Mantenimiento")
    seguros_pagados = fields.One2many('account.account', 'seguros_pagados_id', required=True, tracking=True,
                                      string="Seguros Pagados")
    utiles_oficina = fields.One2many('account.account', 'utiles_oficina_id', required=True, tracking=True,
                                     string="Útiles de Oficina")
    viaticos_vendedores = fields.One2many('account.account', 'viaticos_vendedores_id', required=True, tracking=True,
                                          string="Viáticos a Vendedores")
    gastos_no_deducibles = fields.One2many('account.account', 'gastos_no_deducibles_id', required=True, tracking=True,
                                           string="Gastos no Deducibles")
    saldo_inicial_anticipos_retenciones = fields.One2many('account.account', 'saldo_inicial_anticipos_retenciones_id',
                                                          required=True, tracking=True,
                                                          string="Saldo Inicial Anticipos y Retenciones")
    saldo_final_sset = fields.One2many('account.account', 'saldo_final_sset_id', required=True, tracking=True,
                                       string="Saldo Final SSET (Impuesto a la Renta a Pagar)")
    saldo_final_iva_pagar = fields.One2many('account.account', 'saldo_final_iva_pagar_id', required=True, tracking=True,
                                            string="Saldo Final IVA a Pagar")
    saldo_inicial_iva_credito_fiscal = fields.One2many('account.account', 'saldo_inicial_iva_credito_fiscal_id',
                                                       required=True, tracking=True,
                                                       string="Saldo Inicial IVA Crédito Fiscal")
    saldo_inicial_retencion_iva_credito = fields.One2many('account.account', 'saldo_inicial_retencion_iva_credito_id',
                                                          required=True, tracking=True,
                                                          string="Saldo Inicial Retención IVA (Crédito)")
    saldo_inicial_iva_pagar = fields.One2many('account.account', 'saldo_inicial_iva_pagar_id', required=True,
                                              tracking=True, string="Saldo Inicial IVA a Pagar")
    saldo_final_iva_credito_fiscal = fields.One2many('account.account', 'saldo_final_iva_credito_fiscal_id',
                                                     required=True, tracking=True,
                                                     string="Saldo Final IVA Crédito Fiscal")
    saldo_final_retencion_iva_credito = fields.One2many('account.account', 'saldo_final_retencion_iva_credito_id',
                                                        required=True, tracking=True,
                                                        string="Saldo Final Retención IVA (Crédito)")
    impuesto_ejercicio = fields.One2many('account.account', 'impuesto_ejercicio_id', required=True, tracking=True,
                                         string="Impuesto del Ejercicio")
    pago_impuesto_renta = fields.One2many('account.account', 'pago_impuesto_renta_id', required=True, tracking=True,
                                          string="Pago de Impuesto a la Renta")
    saldo_final_anticipos_retenciones = fields.One2many('account.account', 'saldo_final_anticipos_retenciones_id',
                                                        required=True, tracking=True,
                                                        string="Saldo Final Anticipos y Retenciones")
    saldo_inicial_sset = fields.One2many('account.account', 'saldo_inicial_sset_id', required=True, tracking=True,
                                         string="Saldo Inicial SSET (Impuesto a la Renta a Pagar)")
    multas = fields.One2many('account.account', 'multas_id', required=True, tracking=True, string="Multas")
    saldo_inicial_inversiones_temporarias = fields.One2many('account.account',
                                                            'saldo_inicial_inversiones_temporarias_id', required=True,
                                                            tracking=True,
                                                            string="Saldo Inicial Inversiones Temporarias")
    saldo_inicial_otros_activos_corto_plazo = fields.One2many('account.account',
                                                              'saldo_inicial_otros_activos_corto_plazo_id',
                                                              required=True, tracking=True,
                                                              string="Saldo Inicial Otros Activos a Corto Plazo")
    saldo_final_inversiones_temporarias = fields.One2many('account.account', 'saldo_final_inversiones_temporarias_id',
                                                          required=True, tracking=True,
                                                          string="Saldo Final Inversiones Temporarias")
    saldo_final_otros_activos_corto_plazo = fields.One2many('account.account',
                                                            'saldo_final_otros_activos_corto_plazo_id', required=True,
                                                            tracking=True,
                                                            string="Saldo Final Otros Activos a Corto Plazo")
    saldo_inicial_inversiones_largo_plazo = fields.One2many('account.account',
                                                            'saldo_inicial_inversiones_largo_plazo_id', required=True,
                                                            tracking=True,
                                                            string="Saldo Inicial Inversiones a Largo Plazo")
    saldo_inicial_otros_activos_largo_plazo = fields.One2many('account.account',
                                                              'saldo_inicial_otros_activos_largo_plazo_id',
                                                              required=True, tracking=True,
                                                              string="Saldo Inicial Otros Activos a Largo Plazo")
    saldo_final_inversiones_largo_plazo = fields.One2many('account.account', 'saldo_final_inversiones_largo_plazo_id',
                                                          required=True, tracking=True,
                                                          string="Saldo Final Inversiones a Largo Plazo")
    saldo_final_otros_activos_largo_plazo = fields.One2many('account.account',
                                                            'saldo_final_otros_activos_largo_plazo_id', required=True,
                                                            tracking=True,
                                                            string="Saldo Final Otros Activos a Largo Plazo")
    saldo_inicial_propiedad_planta_equipo = fields.One2many('account.account',
                                                            'saldo_inicial_propiedad_planta_equipo_id', required=True,
                                                            tracking=True,
                                                            string="Saldo Inicial Propiedad, Planta y Equipo")
    saldo_inicial_activos_intangibles = fields.One2many('account.account', 'saldo_inicial_activos_intangibles_id',
                                                        required=True, tracking=True,
                                                        string="Saldo Inicial Activos Intangibles")
    saldo_final_reservas_revaluo = fields.One2many('account.account', 'saldo_final_reservas_revaluo_id', required=True,
                                                   tracking=True, string="Saldo Final Reservas de Revalúo")
    utilidad_perdida_venta_activos_fijos = fields.One2many('account.account', 'utilidad_perdida_venta_activos_fijos_id',
                                                           required=True, tracking=True,
                                                           string="Utilidad/Pérdida en Venta de Activos Fijos")
    saldo_inicial_cargos_diferidos = fields.One2many('account.account', 'saldo_inicial_cargos_diferidos_id',
                                                     required=True, tracking=True,
                                                     string="Saldo Inicial Cargos Diferidos")
    depreciaciones_ejercicio = fields.One2many('account.account', 'depreciaciones_ejercicio_id', required=True,
                                               tracking=True, string="Depreciaciones del Ejercicio")
    saldo_inicial_reservas_revaluo = fields.One2many('account.account', 'saldo_inicial_reservas_revaluo_id',
                                                     required=True, tracking=True,
                                                     string="Saldo Inicial Reservas de Revalúo")
    amortizacion_ejercicio = fields.One2many('account.account', 'amortizacion_ejercicio_id', required=True,
                                             tracking=True, string="Amortización del Ejercicio")
    saldo_final_propiedad_planta_equipo = fields.One2many('account.account', 'saldo_final_propiedad_planta_equipo_id',
                                                          required=True, tracking=True,
                                                          string="Saldo Final Propiedad, Planta y Equipo")
    saldo_final_cargos_diferidos = fields.One2many('account.account', 'saldo_final_cargos_diferidos_id', required=True,
                                                   tracking=True, string="Saldo Final Cargos Diferidos")
    saldo_final_activos_intangibles = fields.One2many('account.account', 'saldo_final_activos_intangibles_id',
                                                      required=True, tracking=True,
                                                      string="Saldo Final Activos Intangibles")
    saldo_final_capital = fields.One2many('account.account', 'saldo_final_capital_id', required=True, tracking=True,
                                          string="Saldo Final Capital")
    saldo_inicial_capital = fields.One2many('account.account', 'saldo_inicial_capital_id', required=True, tracking=True,
                                            string="Saldo Inicial Capital")
    saldo_final_prestamos = fields.One2many('account.account', 'saldo_final_prestamos_id', required=True, tracking=True,
                                            string="Saldo Final Préstamos")
    saldo_inicial_prestamos = fields.One2many('account.account', 'saldo_inicial_prestamos_id', required=True,
                                              tracking=True, string="Saldo Inicial Préstamos")
    saldo_final_dividendos_pagar = fields.One2many('account.account', 'saldo_final_dividendos_pagar_id', required=True,
                                                   tracking=True, string="Saldo Final Dividendos a Pagar")
    saldo_final_resultado_acumulado = fields.One2many('account.account', 'saldo_final_resultado_acumulado_id',
                                                      required=True, tracking=True,
                                                      string="Saldo Final Resultado Acumulado")
    saldo_inicial_resultado_acumulado = fields.One2many('account.account', 'saldo_inicial_resultado_acumulado_id',
                                                        required=True, tracking=True,
                                                        string="Saldo Inicial Resultado Acumulado")
    saldo_inicial_dividendos_pagar = fields.One2many('account.account', 'saldo_inicial_dividendos_pagar_id',
                                                     required=True, tracking=True,
                                                     string="Saldo Inicial Dividendos a Pagar")
    saldo_final_intereses_pagar = fields.One2many('account.account', 'saldo_final_intereses_pagar_id', required=True,
                                                  tracking=True, string="Saldo Final Intereses a Pagar")
    saldo_inicial_intereses_pagar = fields.One2many('account.account', 'saldo_inicial_intereses_pagar_id',
                                                    required=True, tracking=True,
                                                    string="Saldo Inicial Intereses a Pagar")
    otros_intereses_bancarios = fields.One2many('account.account', 'otros_intereses_bancarios_id', required=True,
                                                tracking=True, string="Otros Intereses Bancarios")
    fecha_inicio = fields.Date(string='Fecha de Inicio', required=True)
    fecha_final = fields.Date(string='Fecha Final', required=True)
    ventas_netas_resultado = fields.Float(compute='_compute_ventas_netas', string="Ventas Netas (Resultado)")
    pago_proveedores_locales_resultado = fields.Float(compute='_compute_pago_proveedores_locales',
                                                      string="Pago a Proveedores Locales (Resultado)")
    pago_proveedores_exterior_resultado = fields.Float(compute='_compute_pago_proveedores_exterior',
                                                       string="Pago a Proveedores del Exterior (Resultado)")
    efectivo_pagado_empleados_resultado = fields.Float(compute='_compute_efectivo_pagado_empleados',
                                                       string="Efectivo Pagado a Empleados (Resultado)")
    efectivo_generado_resultado = fields.Float(compute='_compute_efectivo_generado',
                                               string="Efectivo Generado (Usado) por Otras Actividades Operativas (Resultado)")
    pago_impuestos_resultado = fields.Float(compute='_compute_pago_impuestos', string="Impuestos, tasas y patentes")
    inversiones_temporarias_resultado = fields.Float(compute='_compute_inversiones_temporarias',
                                                     string="Aumento/Disminución Neto/a de Inversiones Temporarias (Resultado)")
    inversiones_largo_plazo_resultado = fields.Float(compute='_compute_inversiones_largo_plazo',
                                                     string="Aumento/Disminución Neto/a de Inversiones a Largo Plazo (Resultado)")
    propiedad_planta_equipo_resultado = fields.Float(compute='_compute_propiedad_planta_equipo',
                                                     string="Aumento/Disminución Neto/a de Propiedad, Planta y Equipo (Resultado)")
    aporte_capital_resultado = fields.Float(compute='_compute_aporte_capital', string="Aporte de Capital (Resultado)")
    prestamos_resultado = fields.Float(compute='_compute_prestamos',
                                       string="Aumento/Disminución Neto/a de Préstamos (Resultado)")
    dividendos_pagados_resultado = fields.Float(compute='_compute_dividendos_pagados',
                                                string="Dividendos Pagados (Resultado)")
    intereses_resultado = fields.Float(compute='_compute_intereses',
                                       string="Aumento/Disminución Neto/a de Intereses (Resultado)")
    diferencias_cambios = fields.One2many('account.account', 'diferencias_cambios_id', required=True, tracking=True,
                                          string="EFECTO DE LAS GANANCIAS O PÉRDIDAS POR DIFERENCIAS DE TIPO DE CAMBIO ")
    disponibilidades = fields.One2many('account.account', 'disponibilidades_id', required=True, tracking=True,
                                       string="EFECTO DE LAS GANANCIAS O PÉRDIDAS POR DIFERENCIAS DE TIPO DE CAMBIO ")
    # VENTAS NETAS
    saldo_inicial_otras_cuentas_ventas = fields.One2many('account.account', 'saldo_inicial_otras_cuentas_ventas_id',
                                                         required=True, tracking=True,
                                                         string="Saldo Inicial Otras Cuentas (Ventas)")
    saldo_final_otras_cuentas_ventas = fields.One2many('account.account', 'saldo_final_otras_cuentas_ventas_id',
                                                       required=True, tracking=True,
                                                       string="Saldo Final Otras Cuentas (Ventas)")
    # PAGO A PROVEEDORES LOCALES
    saldo_inicial_otras_cuentas_pago_proveedores_locales = fields.One2many('account.account',
                                                                           'saldo_inicial_otras_cuentas_pago_proveedores_locales_id',
                                                                           required=True, tracking=True,
                                                                           string="Saldo Inicial Otras Cuentas (Pago Proveedores Locales)")
    saldo_final_otras_cuentas_pago_proveedores_locales = fields.One2many('account.account',
                                                                         'saldo_final_otras_cuentas_pago_proveedores_locales_id',
                                                                         required=True, tracking=True,
                                                                         string="Saldo Final Otras Cuentas (Pago Proveedores Locales)")
    # PAGO A PROVEEDORES DEL EXTERIOR
    saldo_inicial_otras_cuentas_pago_proveedores_exterior = fields.One2many('account.account',
                                                                            'saldo_inicial_otras_cuentas_pago_proveedores_exterior_id',
                                                                            required=True, tracking=True,
                                                                            string="Saldo Inicial Otras Cuentas (Pago Proveedores Exterior)")
    saldo_final_otras_cuentas_pago_proveedores_exterior = fields.One2many('account.account',
                                                                          'saldo_final_otras_cuentas_pago_proveedores_exterior_id',
                                                                          required=True, tracking=True,
                                                                          string="Saldo Final Otras Cuentas (Pago Proveedores Exterior)")
    # EFECTIVO PAGADO A EMPLEADOS
    saldo_inicial_otras_cuentas_efectivo_pagado_empleados = fields.One2many('account.account',
                                                                            'saldo_inicial_otras_cuentas_efectivo_pagado_empleados_id',
                                                                            required=True, tracking=True,
                                                                            string="Saldo Inicial Otras Cuentas (Efectivo Pagado a Empleados)")
    saldo_final_otras_cuentas_efectivo_pagado_empleados = fields.One2many('account.account',
                                                                          'saldo_final_otras_cuentas_efectivo_pagado_empleados_id',
                                                                          required=True, tracking=True,
                                                                          string="Saldo Final Otras Cuentas (Efectivo Pagado a Empleados)")
    # PAGO DE IMPUESTOS
    saldo_inicial_otras_cuentas_pago_impuestos = fields.One2many('account.account',
                                                                 'saldo_inicial_otras_cuentas_pago_impuestos_id',
                                                                 required=True, tracking=True,
                                                                 string="Saldo Inicial Otras Cuentas (Pago de Impuestos)")
    saldo_final_otras_cuentas_pago_impuestos = fields.One2many('account.account',
                                                               'saldo_final_otras_cuentas_pago_impuestos_id',
                                                               required=True, tracking=True,
                                                               string="Saldo Final Otras Cuentas (Pago de Impuestos)")
    # INVERSIONES TEMPORARIAS
    saldo_inicial_otras_cuentas_inversiones_temporarias = fields.One2many('account.account',
                                                                          'saldo_inicial_otras_cuentas_inversiones_temporarias_id',
                                                                          required=True, tracking=True,
                                                                          string="Saldo Inicial Otras Cuentas (Inversiones Temporarias)")
    saldo_final_otras_cuentas_inversiones_temporarias = fields.One2many('account.account',
                                                                        'saldo_final_otras_cuentas_inversiones_temporarias_id',
                                                                        required=True, tracking=True,
                                                                        string="Saldo Final Otras Cuentas (Inversiones Temporarias)")
    # INVERSIONES A LARGO PLAZO
    saldo_inicial_otras_cuentas_inversiones_largo_plazo = fields.One2many('account.account',
                                                                          'saldo_inicial_otras_cuentas_inversiones_largo_plazo_id',
                                                                          required=True, tracking=True,
                                                                          string="Saldo Inicial Otras Cuentas (Inversiones Largo Plazo)")
    saldo_final_otras_cuentas_inversiones_largo_plazo = fields.One2many('account.account',
                                                                        'saldo_final_otras_cuentas_inversiones_largo_plazo_id',
                                                                        required=True, tracking=True,
                                                                        string="Saldo Final Otras Cuentas (Inversiones Largo Plazo)")
    # PROPIEDAD, PLANTA Y EQUIPO
    saldo_inicial_otras_cuentas_propiedad_planta_equipo = fields.One2many('account.account',
                                                                          'saldo_inicial_otras_cuentas_propiedad_planta_equipo_id',
                                                                          required=True, tracking=True,
                                                                          string="Saldo Inicial Otras Cuentas (Propiedad, Planta y Equipo)")
    saldo_final_otras_cuentas_propiedad_planta_equipo = fields.One2many('account.account',
                                                                        'saldo_final_otras_cuentas_propiedad_planta_equipo_id',
                                                                        required=True, tracking=True,
                                                                        string="Saldo Final Otras Cuentas (Propiedad, Planta y Equipo)")
    # APORTE DE CAPITAL
    saldo_inicial_otras_cuentas_aporte_capital = fields.One2many('account.account',
                                                                 'saldo_inicial_otras_cuentas_aporte_capital_id',
                                                                 required=True, tracking=True,
                                                                 string="Saldo Inicial Otras Cuentas (Aporte de Capital)")
    saldo_final_otras_cuentas_aporte_capital = fields.One2many('account.account',
                                                               'saldo_final_otras_cuentas_aporte_capital_id',
                                                               required=True, tracking=True,
                                                               string="Saldo Final Otras Cuentas (Aporte de Capital)")
    # PRÉSTAMOS
    saldo_inicial_otras_cuentas_prestamos = fields.One2many('account.account',
                                                            'saldo_inicial_otras_cuentas_prestamos_id', required=True,
                                                            tracking=True,
                                                            string="Saldo Inicial Otras Cuentas (Préstamos)")
    saldo_final_otras_cuentas_prestamos = fields.One2many('account.account', 'saldo_final_otras_cuentas_prestamos_id',
                                                          required=True, tracking=True,
                                                          string="Saldo Final Otras Cuentas (Préstamos)")
    # DIVIDENDOS PAGADOS
    saldo_inicial_otras_cuentas_dividendos_pagados = fields.One2many('account.account',
                                                                     'saldo_inicial_otras_cuentas_dividendos_pagados_id',
                                                                     required=True, tracking=True,
                                                                     string="Saldo Inicial Otras Cuentas (Dividendos Pagados)")
    saldo_final_otras_cuentas_dividendos_pagados = fields.One2many('account.account',
                                                                   'saldo_final_otras_cuentas_dividendos_pagados_id',
                                                                   required=True, tracking=True,
                                                                   string="Saldo Final Otras Cuentas (Dividendos Pagados)")
    # INTERESES
    saldo_inicial_otras_cuentas_intereses = fields.One2many('account.account',
                                                            'saldo_inicial_otras_cuentas_intereses_id', required=True,
                                                            tracking=True,
                                                            string="Saldo Inicial Otras Cuentas (Intereses)")
    saldo_final_otras_cuentas_intereses = fields.One2many('account.account', 'saldo_final_otras_cuentas_intereses_id',
                                                          required=True, tracking=True,
                                                          string="Saldo Final Otras Cuentas (Intereses)")
    saldo_inicial_otras_cuentas_activo = fields.One2many('account.account', 'saldo_inicial_otras_cuentas_activo_id',
                                                         required=True, tracking=True,
                                                         string="Saldo Inicial Otras Cuentas del Activo")
    saldo_final_otras_cuentas_pasivo = fields.One2many('account.account', 'saldo_final_otras_cuentas_pasivo_id',
                                                       required=True, tracking=True,
                                                       string="Saldo Final Otras Cuentas del Pasivo")
    saldo_final_otras_cuentas_activo = fields.One2many('account.account', 'saldo_final_otras_cuentas_activo_id',
                                                       required=True, tracking=True,
                                                       string="Saldo Final Otras Cuentas del Activo")
    saldo_inicial_otras_cuentas_pasivo = fields.One2many('account.account', 'saldo_inicial_otras_cuentas_pasivo_id',
                                                         required=True, tracking=True,
                                                         string="Saldo Inicial Otras Cuentas del Pasivo")
    saldo_final_otras_cuentas_inversiones_largo_plazo = fields.One2many('account.account','saldo_final_otras_cuentas_inversiones_largo_plazo_id',required=True, tracking=True,string="Saldo Final Otras Cuentas (Inversiones Largo Plazo)")


    data_cache = fields.Char(string='Cache de Datos',
                             help='Diccionario con datos cacheados para calculos rapidos de busqueda de movimientos',
                             readonly=True)

    @api.model
    def preparar_datos(self, fecha_inicio, fecha_final):
        """
        Realiza una búsqueda de movimientos contables y organiza los datos en dos diccionarios:
        uno para el año actual y otro para el anterior.
        """
        account_move_obj = self.env['account.move.line']
        fi = datetime.strptime(str(fecha_inicio), '%Y-%m-%d')
        fecha_inicio_actual = fi
        fecha_inicio_anterior = fi - relativedelta(years=1)  # Año anterior
        fecha_inicio_anterior2 = fi - relativedelta(
            years=2)  # 2 años antes, para traer los asientos de cierre anteriores
        fin = datetime.strptime(str(fecha_final), '%Y-%m-%d')
        fecha_fin_ant = fin - relativedelta(years=1)

        # Buscar todos los movimientos dentro del rango de fechas
        all_moves = account_move_obj.search([
            ('date', '>=', fecha_inicio_anterior),  # Comenzamos desde el año anterior
            ('date', '<=', fecha_final),
            ('move_id.state', '=', 'posted'),('company_id','=',self.company_id.id)
        ])

        # _logger.warning('fecha inicial %s', fecha_inicio)
        # _logger.warning('fecha final %s', fecha_final)

        # Inicializar los diccionarios para los dos años
        datos_actual = {}
        datos_anterior = {}
        for move in all_moves:
            key = move.account_id.id  # Agrupar por ID de cuenta
            move_data = {
                'balance': move.balance,
                'date': move.date.strftime('%Y-%m-%d'),
                'move_id': move.move_id.id,
                'apertura': move.move_id.apertura,
                'cierre': move.move_id.cierre,
                'ref': move.ref,
                'account_id': move.account_id
            }

            fecha_move = move.date
            if fecha_move.year == fecha_inicio_actual.year:
                if key not in datos_actual:
                    datos_actual[key] = []
                datos_actual[key].append(move_data)
            elif fecha_move.year == fecha_inicio_anterior.year:
                if key not in datos_anterior:
                    datos_anterior[key] = []
                datos_anterior[key].append(move_data)

        return datos_actual, datos_anterior

    @api.depends('saldo_inicial_clientes', 'saldo_final_otras_cuentas_ventas', 'saldo_inicial_otras_cuentas_ventas',
                 'ventas', 'descuentos_concedidos', 'saldo_final_anticipo_clientes', 'saldo_inicial_tarjetas_credito',
                 'saldo_final_clientes', 'saldo_inicial_anticipos_clientes', 'saldo_final_tarjetas_credito',
                 'fecha_inicio', 'fecha_final')
    def _compute_ventas_netas(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_ventas_netas: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.ventas_netas_resultado = (
                        sum(record.saldo_inicial_clientes.mapped('balance')) +
                        sum(record.ventas.mapped('balance')) +
                        sum(record.descuentos_concedidos.mapped('balance')) -
                        sum(record.saldo_final_anticipo_clientes.mapped('balance')) +
                        sum(record.saldo_inicial_tarjetas_credito.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_ventas.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_ventas.mapped('balance')) +
                        sum(record.saldo_final_clientes.mapped('balance')) +
                        sum(record.saldo_inicial_anticipos_clientes.mapped('balance')) +
                        sum(record.saldo_final_tarjetas_credito.mapped('balance'))
                )
            except:
                record.ventas_netas_resultado = 0

    @api.depends('saldo_inicial_anticipo_proveedores', 'saldo_inicial_otros_acreedores', 'saldo_final_otros_acreedores',
                 'saldo_inicial_gastos_pagados_adelantado', 'saldo_final_proveedores_locales',
                 'saldo_final_otros_acreedores', 'saldo_inicial_mercaderias', 'saldo_final_anticipo_proveedores',
                 'saldo_inicial_proveedores_locales', 'saldo_inicial_otros_acreedores',
                 'saldo_final_gastos_pagados_adelantado', 'saldo_final_mercaderias', 'costo_ventas', 'fecha_inicio',
                 'fecha_final')
    def _compute_pago_proveedores_locales(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_pago_proveedores_locales: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.pago_proveedores_locales_resultado = (
                        sum(record.saldo_inicial_anticipo_proveedores.mapped('balance')) +
                        sum(record.saldo_inicial_gastos_pagados_adelantado.mapped('balance')) +
                        sum(record.saldo_final_proveedores_locales.mapped('balance')) +
                        sum(record.saldo_final_otros_acreedores.mapped('balance')) +
                        sum(record.saldo_inicial_mercaderias.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_pago_proveedores_locales.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_pago_proveedores_locales.mapped('balance')) +
                        sum(record.saldo_final_anticipo_proveedores.mapped('balance')) +
                        sum(record.saldo_inicial_proveedores_locales.mapped('balance')) +
                        sum(record.saldo_inicial_otros_acreedores.mapped('balance')) +
                        sum(record.saldo_final_gastos_pagados_adelantado.mapped('balance')) +
                        sum(record.saldo_final_mercaderias.mapped('balance')) +
                        sum(record.costo_ventas.mapped('balance'))
                )
            except:
                record.pago_proveedores_locales_resultado = 0

    @api.depends('saldo_inicial_anticipo_proveedores_exterior', 'saldo_final_otras_cuentas_pago_proveedores_exterior',
                 'saldo_inicial_otras_cuentas_pago_proveedores_exterior',
                 'saldo_inicial_gastos_pagados_adelantado_exterior', 'saldo_final_proveedores_exterior',
                 'saldo_inicial_mercaderias_exterior', 'saldo_final_anticipo_proveedores_exterior',
                 'saldo_inicial_proveedores_exterior', 'saldo_final_gastos_pagados_adelantado_exterior',
                 'saldo_final_mercaderias_exterior', 'costo_ventas_exterior', 'fecha_inicio', 'fecha_final')
    def _compute_pago_proveedores_exterior(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_pago_proveedores_exterior: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.pago_proveedores_exterior_resultado = (
                        sum(record.saldo_inicial_anticipo_proveedores_exterior.mapped('balance')) +
                        sum(record.saldo_inicial_gastos_pagados_adelantado_exterior.mapped('balance')) +
                        sum(record.saldo_final_proveedores_exterior.mapped('balance')) +
                        sum(record.saldo_inicial_mercaderias_exterior.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_pago_proveedores_exterior.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_pago_proveedores_exterior.mapped('balance')) +
                        sum(record.saldo_final_anticipo_proveedores_exterior.mapped('balance')) +
                        sum(record.saldo_inicial_proveedores_exterior.mapped('balance')) +
                        sum(record.saldo_final_gastos_pagados_adelantado_exterior.mapped('balance')) +
                        sum(record.saldo_final_mercaderias_exterior.mapped('balance')) +
                        sum(record.costo_ventas_exterior.mapped('balance'))
                )
            except:
                record.pago_proveedores_exterior_resultado = 0

    @api.depends('saldo_final_obligaciones_laborales', 'saldo_final_otras_cuentas_efectivo_pagado_empleados',
                 'saldo_inicial_otras_cuentas_efectivo_pagado_empleados', 'saldo_inicial_obligaciones_laborales',
                 'sueldos_jornales', 'aporte_patronal', 'aguinaldos', 'fecha_inicio', 'fecha_final')
    def _compute_efectivo_pagado_empleados(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_efectivo_pagado_empleados: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.efectivo_pagado_empleados_resultado = (
                        sum(record.saldo_final_obligaciones_laborales.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_efectivo_pagado_empleados.mapped('balance')) +
                        sum(record.saldo_inicial_obligaciones_laborales.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_efectivo_pagado_empleados.mapped('balance')) +
                        sum(record.sueldos_jornales.mapped('balance')) +
                        sum(record.aporte_patronal.mapped('balance')) +
                        sum(record.aguinaldos.mapped('balance'))
                )
            except:
                record.efectivo_pagado_empleados_resultado = 0

    @api.depends('agua_luz_telefono_internet', 'alquileres_pagados', 'combustibles_lubricantes',
                 'comisiones_gastos_bancarios', 'comisiones_sobre_ventas', 'donaciones_contribuciones',
                 'fletes_pagados', 'gastos_cobranzas', 'gastos_representacion', 'gastos_pagados_exterior',
                 'honorarios_profesionales', 'juicios_gastos_judiciales', 'movilidad', 'otros_gastos_ventas',
                 'publicidad_propaganda', 'remuneracion_personal_superior', 'reparacion_mantenimiento',
                 'seguros_pagados', 'utiles_oficina', 'viaticos_vendedores', 'gastos_no_deducibles', 'fecha_inicio',
                 'fecha_final')
    def _compute_efectivo_generado(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_efectivo_generado: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.efectivo_generado_resultado = -(
                        sum(record.agua_luz_telefono_internet.mapped('balance')) + \
                        sum(record.alquileres_pagados.mapped('balance')) + \
                        sum(record.combustibles_lubricantes.mapped('balance')) + \
                        sum(record.comisiones_gastos_bancarios.mapped('balance')) + \
                        sum(record.comisiones_sobre_ventas.mapped('balance')) + \
                        sum(record.donaciones_contribuciones.mapped('balance')) + \
                        sum(record.fletes_pagados.mapped('balance')) + \
                        sum(record.gastos_cobranzas.mapped('balance')) + \
                        sum(record.gastos_representacion.mapped('balance')) + \
                        sum(record.gastos_pagados_exterior.mapped('balance')) + \
                        sum(record.honorarios_profesionales.mapped('balance')) + \
                        sum(record.juicios_gastos_judiciales.mapped('balance')) + \
                        sum(record.movilidad.mapped('balance')) + \
                        sum(record.otros_gastos_ventas.mapped('balance')) + \
                        sum(record.publicidad_propaganda.mapped('balance')) + \
                        sum(record.remuneracion_personal_superior.mapped('balance')) + \
                        sum(record.reparacion_mantenimiento.mapped('balance')) + \
                        sum(record.seguros_pagados.mapped('balance')) + \
                        sum(record.utiles_oficina.mapped('balance')) + \
                        sum(record.viaticos_vendedores.mapped('balance')) + \
                        sum(record.gastos_no_deducibles.mapped('balance'))
                )
            except:
                record.efectivo_generado_resultado = 0

    @api.depends('saldo_inicial_anticipos_retenciones', 'saldo_inicial_otras_cuentas_pago_impuestos',
                 'saldo_final_otras_cuentas_pago_impuestos', 'saldo_final_sset', 'saldo_final_iva_pagar',
                 'saldo_inicial_iva_credito_fiscal', 'saldo_inicial_retencion_iva_credito', 'saldo_inicial_iva_pagar',
                 'saldo_final_iva_credito_fiscal', 'saldo_final_retencion_iva_credito', 'impuesto_ejercicio',
                 'pago_impuesto_renta', 'saldo_final_anticipos_retenciones', 'saldo_inicial_sset', 'multas',
                 'fecha_inicio', 'fecha_final')
    def _compute_pago_impuestos(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_pago_impuestos: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.pago_impuestos_resultado = (
                        sum(record.saldo_inicial_anticipos_retenciones.mapped('balance')) +
                        sum(record.saldo_final_sset.mapped('balance')) +
                        sum(record.saldo_final_iva_pagar.mapped('balance')) +
                        sum(record.saldo_inicial_iva_credito_fiscal.mapped('balance')) +
                        sum(record.saldo_inicial_retencion_iva_credito.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_pago_impuestos.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_pago_impuestos.mapped('balance')) +
                        sum(record.saldo_inicial_iva_pagar.mapped('balance')) +
                        sum(record.saldo_final_iva_credito_fiscal.mapped('balance')) +
                        sum(record.saldo_final_retencion_iva_credito.mapped('balance')) +
                        sum(record.impuesto_ejercicio.mapped('balance')) +
                        sum(record.pago_impuesto_renta.mapped('balance')) +
                        sum(record.saldo_final_anticipos_retenciones.mapped('balance')) +
                        sum(record.saldo_inicial_sset.mapped('balance')) +
                        sum(record.multas.mapped('balance'))
                )
            except:
                record.pago_impuestos_resultado = 0

    @api.depends('saldo_inicial_inversiones_temporarias', 'saldo_final_otras_cuentas_inversiones_temporarias',
                 'saldo_inicial_otras_cuentas_inversiones_temporarias', 'saldo_inicial_otros_activos_corto_plazo',
                 'saldo_final_inversiones_temporarias', 'saldo_final_otros_activos_corto_plazo', 'fecha_inicio',
                 'fecha_final')
    def _compute_inversiones_temporarias(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_inversiones_temporarias: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.inversiones_temporarias_resultado = (
                        sum(record.saldo_inicial_inversiones_temporarias.mapped('balance')) +
                        sum(record.saldo_inicial_otros_activos_corto_plazo.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_inversiones_temporarias.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_inversiones_temporarias.mapped('balance')) +
                        sum(record.saldo_final_inversiones_temporarias.mapped('balance')) +
                        sum(record.saldo_final_otros_activos_corto_plazo.mapped('balance'))
                )
            except:
                record.inversiones_temporarias_resultado = 0

    @api.depends('saldo_inicial_inversiones_largo_plazo', 'saldo_final_otras_cuentas_inversiones_largo_plazo',
                 'saldo_inicial_otras_cuentas_inversiones_largo_plazo', 'saldo_inicial_otros_activos_largo_plazo',
                 'saldo_final_inversiones_largo_plazo', 'saldo_final_otros_activos_largo_plazo', 'fecha_inicio',
                 'fecha_final')
    def _compute_inversiones_largo_plazo(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_inversiones_largo_plazo: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.inversiones_largo_plazo_resultado = (
                        sum(record.saldo_inicial_inversiones_largo_plazo.mapped('balance')) +
                        sum(record.saldo_inicial_otros_activos_largo_plazo.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_inversiones_largo_plazo.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_inversiones_largo_plazo.mapped('balance')) +
                        sum(record.saldo_final_inversiones_largo_plazo.mapped('balance')) +
                        sum(record.saldo_final_otros_activos_largo_plazo.mapped('balance'))
                )
            except:
                record.inversiones_largo_plazo_resultado = 0

    @api.depends('saldo_inicial_propiedad_planta_equipo', 'saldo_final_otras_cuentas_propiedad_planta_equipo',
                 'saldo_inicial_otras_cuentas_propiedad_planta_equipo', 'saldo_inicial_activos_intangibles',
                 'saldo_final_reservas_revaluo', 'utilidad_perdida_venta_activos_fijos',
                 'saldo_inicial_cargos_diferidos', 'depreciaciones_ejercicio', 'saldo_inicial_reservas_revaluo',
                 'amortizacion_ejercicio', 'saldo_final_propiedad_planta_equipo', 'saldo_final_cargos_diferidos',
                 'saldo_final_activos_intangibles', 'fecha_inicio', 'fecha_final')
    def _compute_propiedad_planta_equipo(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_propiedad_planta_equipo: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.propiedad_planta_equipo_resultado = (
                        sum(record.saldo_inicial_propiedad_planta_equipo.mapped('balance')) +
                        sum(record.saldo_inicial_activos_intangibles.mapped('balance')) +
                        sum(record.saldo_inicial_reservas_revaluo.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_propiedad_planta_equipo.mapped('balance')) +
                        sum(record.saldo_final_reservas_revaluo.mapped('balance')) +
                        sum(record.utilidad_perdida_venta_activos_fijos.mapped('balance')) +
                        sum(record.saldo_inicial_cargos_diferidos.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_propiedad_planta_equipo.mapped('balance')) +
                        sum(record.depreciaciones_ejercicio.mapped('balance')) +
                        sum(record.amortizacion_ejercicio.mapped('balance')) +
                        sum(record.saldo_final_propiedad_planta_equipo.mapped('balance')) +
                        sum(record.saldo_final_cargos_diferidos.mapped('balance')) +
                        sum(record.saldo_final_activos_intangibles.mapped('balance')) +
                        sum(record.saldo_inicial_reservas_revaluo.mapped('balance'))
                )
            except:
                record.propiedad_planta_equipo_resultado = 0

    @api.depends('saldo_final_capital', 'saldo_inicial_capital', 'saldo_inicial_otras_cuentas_aporte_capital',
                 'saldo_final_otras_cuentas_aporte_capital', 'fecha_inicio', 'fecha_final')
    def _compute_aporte_capital(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_aporte_capital: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.aporte_capital_resultado = (
                        sum(record.saldo_final_capital.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_aporte_capital.mapped('balance')) +
                        sum(record.saldo_inicial_capital.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_aporte_capital.mapped('balance'))
                )
            except:
                record.aporte_capital_resultado = 0

    @api.depends('saldo_final_prestamos', 'saldo_inicial_otras_cuentas_prestamos',
                 'saldo_final_otras_cuentas_prestamos', 'saldo_inicial_prestamos', 'fecha_inicio', 'fecha_final')
    def _compute_prestamos(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_prestamos: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.prestamos_resultado = (
                        sum(record.saldo_final_prestamos.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_prestamos.mapped('balance')) +
                        sum(record.saldo_inicial_prestamos.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_prestamos.mapped('balance'))
                )
            except:
                record.prestamos_resultado = 0

    @api.depends('saldo_final_dividendos_pagar', 'saldo_final_otras_cuentas_dividendos_pagados',
                 'saldo_inicial_otras_cuentas_dividendos_pagados', 'saldo_final_resultado_acumulado',
                 'saldo_inicial_resultado_acumulado', 'saldo_inicial_dividendos_pagar', 'fecha_inicio', 'fecha_final')
    def _compute_dividendos_pagados(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_dividendos_pagados: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.dividendos_pagados_resultado = (
                        sum(record.saldo_final_dividendos_pagar.mapped('balance')) +
                        sum(record.saldo_final_resultado_acumulado.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_dividendos_pagados.mapped('balance')) +
                        sum(record.saldo_inicial_resultado_acumulado.mapped('balance')) +
                        sum(record.saldo_inicial_dividendos_pagar.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_dividendos_pagados.mapped('balance'))
                )
            except:
                record.dividendos_pagados_resultado = 0

    @api.depends('saldo_final_intereses_pagar', 'saldo_final_otras_cuentas_intereses',
                 'saldo_inicial_otras_cuentas_intereses', 'saldo_inicial_intereses_pagar', 'otros_intereses_bancarios',
                 'fecha_inicio', 'fecha_final')
    def _compute_intereses(self):
        for record in self:
            try:
                fecha_inicial = record.fecha_inicio
                fecha_final = record.fecha_final
                print(f"_compute_intereses: fecha_inicio={fecha_inicial}, fecha_final={fecha_final}")
                record.intereses_resultado = (
                        sum(record.saldo_final_intereses_pagar.mapped('balance')) +
                        sum(record.saldo_final_otras_cuentas_intereses.mapped('balance')) +
                        sum(record.saldo_inicial_intereses_pagar.mapped('balance')) +
                        sum(record.otros_intereses_bancarios.mapped('balance')) +
                        sum(record.saldo_inicial_otras_cuentas_intereses.mapped('balance'))
                )
            except:
                record.intereses_resultado = 0

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)', "Solo puede tener una configuracion de Anexo 3 por compañia."),
    ]

    @api.model
    def obtener_valor(self, id_operacion, fecha_inicio, fecha_final, es_actual):
        valor = 0

        account_move_obj = self.env['account.move.line']

        # Determinar fechas
        if es_actual:
            fecha_inicial = fecha_inicio
            fecha_fin = fecha_final
        else:
            fi = datetime.strptime(str(fecha_inicio), '%Y-%m-%d')
            ff = datetime.strptime(str(fecha_final), '%Y-%m-%d')
            fecha_inicial = fi - relativedelta(years=1)
            fecha_fin = ff - relativedelta(years=1)

        # Movimientos del periodo actual (sin cierres ni resultados)
        moves = account_move_obj.search([
            ('date', '>=', fecha_inicial),
            ('date', '<=', fecha_fin),
            ('move_id.cierre', '=', False),
            ('move_id.resultado', '=', False),
            ('move_id.state', '=', 'posted')
        ])

        # Buscar movimientos de apertura del periodo actual
        moves_apertura = account_move_obj.search([
            ('date', '=', fecha_inicial),
            ('move_id.ref', 'ilike', 'apertura'),
            ('move_id.state', '=', 'posted')
        ])

        # Buscar movimientos de cierre del periodo anterior
        moves_cierre = account_move_obj.search([
            ('move_id.cierre', '=', True),
            ('date', '<', fecha_inicial),
            ('move_id.state', '=', 'posted')
        ])

        # Operaciones específicas
        if id_operacion == 1:  # VENTAS NETAS
            # Movimientos de apertura (fecha de inicio)
            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos de cierre (fecha de fin)
            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos normales (excluyendo apertura y cierre)
            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            # Calcular valor total
            valor = -1 * (
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_clientes).mapped(
                        'balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.ventas).mapped('balance')) -
                    sum(moves.filtered(lambda r: r.account_id in self.descuentos_concedidos).mapped('balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_anticipo_clientes).mapped(
                        'balance')) +
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_tarjetas_credito).mapped(
                        'balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_otras_cuentas_ventas).mapped('balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_otras_cuentas_ventas).mapped(
                        'balance')) -
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_clientes).mapped('balance')) +
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_anticipos_clientes).mapped(
                        'balance')) -
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_tarjetas_credito).mapped(
                        'balance'))
            )



        elif id_operacion == 2:  # Pagos a proveedores locales
            # Movimientos de apertura (fecha de inicio)
            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos de cierre (fecha de fin)
            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos normales (excluyendo apertura y cierre)
            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            # Calcular valor total
            valor = (
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_anticipo_proveedores).mapped('balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_gastos_pagados_adelantado).mapped('balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_proveedores_locales).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_otros_acreedores).mapped(
                        'balance')) +
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_mercaderias).mapped(
                        'balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_otras_cuentas_pago_proveedores_locales).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_otras_cuentas_pago_proveedores_locales).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_anticipo_proveedores).mapped(
                        'balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_proveedores_locales).mapped('balance')) +
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_otros_acreedores).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_gastos_pagados_adelantado).mapped('balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_mercaderias).mapped(
                        'balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.costo_ventas).mapped('balance'))
            )

        elif id_operacion == 3:  # Pagos a proveedores del exterior

            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos de cierre (fecha de fin)
            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos normales (excluyendo apertura y cierre)
            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            valor = (
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_anticipo_proveedores_exterior).mapped('balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_gastos_pagados_adelantado_exterior).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_proveedores_exterior).mapped(
                        'balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_mercaderias_exterior).mapped('balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_otras_cuentas_pago_proveedores_exterior).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_otras_cuentas_pago_proveedores_exterior).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_anticipo_proveedores_exterior).mapped('balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_proveedores_exterior).mapped('balance')) +
                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_gastos_pagados_adelantado_exterior).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_mercaderias_exterior).mapped(
                        'balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.costo_ventas_exterior).mapped('balance'))
            )

        elif id_operacion == 4:  # Efectivo pagado a empleados

            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos de cierre (fecha de fin)
            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos normales (excluyendo apertura y cierre)
            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            valor = -1 * (
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_obligaciones_laborales).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_otras_cuentas_efectivo_pagado_empleados).mapped(
                        'balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_obligaciones_laborales).mapped('balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_otras_cuentas_efectivo_pagado_empleados).mapped(
                        'balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.sueldos_jornales).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.aporte_patronal).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.aguinaldos).mapped('balance'))
            )

        elif id_operacion == 5:  # Efectivo generado por otras actividades operativas

            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos de cierre (fecha de fin)
            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos normales (excluyendo apertura y cierre)
            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            valor = -(
                    sum(moves.filtered(lambda r: r.account_id in self.agua_luz_telefono_internet).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.alquileres_pagados).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.combustibles_lubricantes).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.comisiones_gastos_bancarios).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.comisiones_sobre_ventas).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.donaciones_contribuciones).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.fletes_pagados).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.gastos_cobranzas).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.gastos_representacion).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.gastos_pagados_exterior).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.honorarios_profesionales).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.juicios_gastos_judiciales).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.movilidad).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.otros_gastos_ventas).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.publicidad_propaganda).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.remuneracion_personal_superior).mapped(
                        'balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.reparacion_mantenimiento).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.seguros_pagados).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.utiles_oficina).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.viaticos_vendedores).mapped('balance')) -
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_otras_cuentas_activo).mapped('balance')) -
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_otras_cuentas_pasivo).mapped(
                        'balance')) -
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_otras_cuentas_activo).mapped(
                        'balance')) -
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_otras_cuentas_pasivo).mapped('balance')) +
                    sum(moves.filtered(lambda r: r.account_id in self.gastos_no_deducibles).mapped('balance'))
            )

        elif id_operacion == 6:  # Pago de impuestos

            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos de cierre (fecha de fin)
            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos normales (excluyendo apertura y cierre)
            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            valor = (
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_anticipos_retenciones).mapped('balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_sset).mapped('balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_iva_pagar).mapped('balance')) +
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_iva_credito_fiscal).mapped(
                        'balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_retencion_iva_credito).mapped('balance')) +
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_iva_pagar).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_iva_credito_fiscal).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_retencion_iva_credito).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.impuesto_ejercicio).mapped('balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.pago_impuesto_renta).mapped('balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_anticipos_retenciones).mapped(
                        'balance')) +
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_sset).mapped('balance')) +
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_otras_cuentas_pago_impuestos).mapped('balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_otras_cuentas_pago_impuestos).mapped('balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.multas).mapped('balance'))
            )

        elif id_operacion == 7:  # Aumento/Disminución Neto/a de Inversiones Temporarias
            # Movimientos de apertura
            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos de cierre
            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            # Movimientos normales
            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            valor = (
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_inversiones_temporarias).mapped('balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_otros_activos_corto_plazo).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_inversiones_temporarias).mapped('balance')) +
                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_otros_activos_corto_plazo).mapped('balance'))
            )

        elif id_operacion == 8:  # Aumento/Disminución Neto/a de Inversiones a Largo Plazo
            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            valor = (
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_inversiones_largo_plazo).mapped('balance')) +
                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_otros_activos_largo_plazo).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_inversiones_largo_plazo).mapped('balance')) +
                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_otros_activos_largo_plazo).mapped('balance')) +
                    sum(moves_cierre.filtered(
                    lambda r: r.account_id in self.saldo_final_otras_cuentas_inversiones_largo_plazo).mapped('balance'))
            )

        elif id_operacion == 9:  # AUMENTO/DISMINUCIÓN NETO/A DE PROPIEDAD, PLANTA Y EQUIPO

            # Movimientos de apertura del periodo actual

            moves_apertura = account_move_obj.search([

                ('date', '=', fecha_inicial),

                ('move_id.cierre', '=', False),

                ('move_id.apertura', '=', True),

                ('move_id.state', '=', 'posted')

            ])

            # Movimientos de cierre del periodo actual

            moves_cierre = account_move_obj.search([

                ('date', '=', fecha_fin),

                ('move_id.cierre', '=', True),

                ('move_id.state', '=', 'posted')

            ])

            # Movimientos del periodo excluyendo cierres y aperturas

            moves = account_move_obj.search([

                ('date', '>=', fecha_inicial),

                ('date', '<=', fecha_fin),

                ('move_id.cierre', '=', False),

                ('move_id.apertura', '=', False),

                ('move_id.state', '=', 'posted')

            ])

            # Calcular el valor con los movimientos correspondientes

            valor = (

                    sum(moves_apertura.filtered(
                        lambda r: r.account_id in self.saldo_inicial_propiedad_planta_equipo).mapped('balance')) +

                    sum(moves.filtered(
                        lambda r: r.account_id in self.saldo_inicial_otras_cuentas_propiedad_planta_equipo).mapped(
                        'balance')) +

                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_reservas_revaluo).mapped(
                        'balance')) +

                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.utilidad_perdida_venta_activos_fijos).mapped('balance')) +

                    sum(moves_cierre.filtered(lambda r: r.account_id in self.depreciaciones_ejercicio).mapped(
                        'balance')) +

                    sum(moves_cierre.filtered(lambda r: r.account_id in self.amortizacion_ejercicio).mapped(
                        'balance')) +

                    sum(moves_cierre.filtered(
                        lambda r: r.account_id in self.saldo_final_propiedad_planta_equipo).mapped('balance')) +

                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_reservas_revaluo).mapped(
                        'balance'))

            )

        elif id_operacion == 10:  # Aporte de Capital
            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            valor = (
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_capital).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_capital).mapped('balance'))
            )

        elif id_operacion == 11:  # Aumento/Disminución Neto/a de Préstamos
            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            valor = (
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_prestamos).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_prestamos).mapped('balance'))
            )

        elif id_operacion == 12:  # Dividendos Pagados
            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            valor = (
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_dividendos_pagar).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_dividendos_pagar).mapped(
                        'balance'))
            )

        elif id_operacion == 13:  # Aumento/Disminución Neto/a de Intereses
            moves_apertura = account_move_obj.search([
                ('date', '=', fecha_inicial),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            moves_cierre = account_move_obj.search([
                ('date', '=', fecha_fin),
                ('move_id.cierre', '=', True),
                ('move_id.state', '=', 'posted')
            ])

            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin),
                ('move_id.cierre', '=', False),
                ('move_id.apertura', '=', False),
                ('move_id.state', '=', 'posted')
            ])

            valor = (
                    sum(moves_apertura.filtered(lambda r: r.account_id in self.saldo_inicial_intereses_pagar).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.saldo_final_intereses_pagar).mapped(
                        'balance')) +
                    sum(moves_cierre.filtered(lambda r: r.account_id in self.otros_intereses_bancarios).mapped(
                        'balance'))
            )


        elif id_operacion == 14:  # efecto diferencia de cambio
            # moves = account_move_obj.search(
            #         [('date', '>=', fecha_inicial), ('date', '<=', fecha_fin), ('move_id.state', '=', 'posted'),
            #          ('account_id', 'in', self.diferencias_cambios.mapped('id'))])
            valor = -1 * sum(moves.filtered(lambda r: r.account_id in self.diferencias_cambios).mapped('balance'))
            # valor = sum(moves.mapped('balance'))
        elif id_operacion == 15:  # efectivo y sus equivalentes al comienzo del periodo
            # moves = account_move_obj.search(
            #     [('date', '>=', fecha_inicial), ('date', '<=', fecha_fin), ('move_id.state', '=', 'posted'),
            #      ('account_id', 'in', self.disponibilidades.mapped('id'))])
            # valor = sum(moves.mapped('balance'))
            # fi = datetime.strptime(str(fecha_inicial), '%Y-%m-%d')
            # ff = datetime.strptime(str(fecha_fin), '%Y-%m-%d')
            fecha_inicial = fecha_inicial - relativedelta(years=1)
            fecha_fin = fecha_fin - relativedelta(years=1)

            moves = account_move_obj.search([
                ('date', '>=', fecha_inicial),
                ('date', '<=', fecha_fin), ('move_id.cierre', '=', False), ('move_id.resultado', '=', False),
                ('move_id.state', '=', 'posted')
            ])
            valor = sum(moves.filtered(lambda r: r.account_id in self.disponibilidades).mapped('balance'))
        precision = 0
        rounding_method = 'HALF-UP'
        _logger.warning("valor %s", valor)
        valor = float_round(valor, precision_digits=precision, rounding_method=rounding_method)
        _logger.warning('valor rounded %s', valor)

        return valor

    def actualizar_cuentas(self):
        for rec in self:
            """
            *****************************************************************************
            ********************* CREACION DE LISTAS  *********************************
            ***************************************************************************
            """
            ventas_netas = list()
            proveedores_locales = list()
            proveedores_exterior = list()
            efectivo_empleados = list()
            efectivo_generado = list()
            pago_impuestos = list()
            aumento_inversiones_temp = list()
            aumento_inversiones_largo = list()
            aumento_inversiones_propiedad = list()
            aporte_capital = list()
            aumento_prestamos = list()
            dividendos_pagados = list()
            aumento_intereses = list()

            company_domain = str(rec.company_id.id) + '_'

            """
            *****************************************************************************
            ********************* CUENTAS VENTAS NETAS *********************************
            ***************************************************************************
            """
            ventas_netas.append(self.env.ref('l10n_py.' + company_domain + '41111').id)
            ventas_netas.append(self.env.ref('l10n_py.' + company_domain + '41112').id)
            ventas_netas.append(self.env.ref('l10n_py.' + company_domain + '41121').id)
            ventas_netas.append(self.env.ref('l10n_py.' + company_domain + '41122').id)
            ventas_netas.append(self.env.ref('l10n_py.' + company_domain + '411991').id)
            ventas_netas.append(self.env.ref('l10n_py.' + company_domain + '411992').id)
            ventas_netas.append(self.env.ref('l10n_py.' + company_domain + '1131').id)
            ventas_netas.append(self.env.ref('l10n_py.' + company_domain + '1132').id)
            ventas_netas.append(self.env.ref('l10n_py.' + company_domain + '1133').id)
            ventas_netas.append(self.env.ref('l10n_py.' + company_domain + '2151').id)

            """
            *****************************************************************************
            ********************* PROVEEDORES LOCALES *********************************
            ***************************************************************************
            """

            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '41211').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '41212').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '41221').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '41222').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '41232').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '41233').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '41234').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '41235').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '11411').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '11412').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '11413').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '2111').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '2211').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '1217').id)
            proveedores_locales.append(self.env.ref('l10n_py.' + company_domain + '1261').id)

            # Continúa con la asignación de cuentas para los demás campos

            rec.ventas_netas = [(6, 0, ventas_netas)]
            rec.proveedores_locales = [(6, 0, proveedores_locales)]
            rec.proveedores_exterior = [(6, 0, proveedores_exterior)]
            rec.efectivo_empleados = [(6, 0, efectivo_empleados)]
            rec.efectivo_generado = [(6, 0, efectivo_generado)]
            rec.pago_impuestos = [(6, 0, pago_impuestos)]
            rec.aumento_inversiones_temp = [(6, 0, aumento_inversiones_temp)]
            rec.aumento_inversiones_largo = [(6, 0, aumento_inversiones_largo)]
            rec.aumento_inversiones_propiedad = [(6, 0, aumento_inversiones_propiedad)]
            rec.aporte_capital = [(6, 0, aporte_capital)]
            rec.aumento_prestamos = [(6, 0, aumento_prestamos)]
            rec.dividendos_pagados = [(6, 0, dividendos_pagados)]
            rec.aumento_intereses = [(6, 0, aumento_intereses)]

    @api.model
    def _get_default_company(self):
        company = self.env.company
        return company


class Anexo4(models.Model):
    _name = 'account_reports_paraguay.anexo4'

    name = fields.Char(default="Configuración de cuentas Anexo 4", required=True, tracking=True)
    capital_integrado = fields.One2many('account.account', 'anexo4_ids', string="Cuentas de Capital Integrado",
                                        required=True, tracking=True)
    reserva_legal = fields.Many2one('account.account', string="Cuenta de Reserva Legal", required=True, tracking=True)
    reserva_de_revaluo = fields.Many2one('account.account', string="Cuenta de Reserva de Revaluo", required=True,
                                         tracking=True)
    otras_reservas = fields.One2many('account.account', 'anexo4_id', string="Cuenta de Otras Reservas", tracking=True)
    resultados_acumulados = fields.Many2one('account.account', string="Cuenta de Resultados Acumulados", required=True,
                                            tracking=True)
    resultados_del_ejercicio = fields.Many2one('account.account', string="Cuenta de Resultados del Ejercicio",
                                               required=True, tracking=True)
    dividendos_a_pagar = fields.Many2one('account.account', string="Cuenta de Dividendos a Pagar", required=True,
                                         tracking=True)
    company_id = fields.Many2one('res.company', 'Compañia', default=lambda self: self._get_default_company(),
                                 required=True, tracking=True)

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)', "Solo puede tener una configuracion de Anexo 4 por compañia."),
    ]

    @api.model
    def _get_default_company(self):
        company = self.env.company
        return company


class Anexo5(models.Model):
    _name = 'account_reports_paraguay.anexo5'

    name = fields.Char(default="Configuración de cuentas Anexo 5")
    datos_entidad_1 = fields.One2many('anexo5_datos_entidad', 'anexo5_id')
    base_preparacion_2 = fields.One2many('anexo5_base_preparacion', 'anexo5_id')
    politicas_contables_3 = fields.One2many('anexo5_politicas_contables', 'anexo5_id',
                                            help="Políticas contables significativas respecto a la valuación, exposición y reconocimiento de los elementos de los Estados Financieros")
    cuentas_patrimoniales_4 = fields.One2many('account.account', 'cuentas_patrimoniales_anexo5_id')
    cuentas_patrimoniales4 = fields.One2many('anexo5_cuentas_patrimoniales', 'anexo5_id')
    cuentas_resultados_5 = fields.One2many('account.account', 'cuentas_resultados_anexo5_id')
    detalle_rentas_exentas_6 = fields.One2many('account.account', 'detalle_rentas_exentas_anexo5_id')
    rentas_exentas_7 = fields.One2many('anexo5_rentas_exentas', 'anexo5_id')
    identificacion_partes_8 = fields.One2many('anexo5_identificacion_partes', 'anexo5_id')
    hechos_posteriores_9 = fields.One2many('anexo5_hechos_posteriores', 'anexo5_id')
    otras_notas_10 = fields.One2many('anexo5_otras_notas', 'anexo5_id')
    periodo = fields.Char(copy=False)
    relato = fields.Text(string="Descripción")
    company_id = fields.Many2one('res.company', 'Compañia', default=lambda self: self._get_default_company(),
                                 required=True, tracking=True)

    @api.model
    def _get_default_company(self):
        company = self.env.company
        return company

    @api.constrains('company_id', 'periodo')
    def verficar_duplicado(self):
        if self.periodo:
            eeff = self.env['account_reports_paraguay.anexo5'].search(
                [('company_id', '=', self.env.company.id), ('periodo', '=', self.periodo)])
            if len(eeff) > 1:
                raise ValidationError('Solo puede tener una configuracion de Anexo 5 por compañia y periodo ')

