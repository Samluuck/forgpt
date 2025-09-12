from odoo import models, fields, api

class Account(models.Model):
    _inherit = 'account.account'

    # Campos existentes
    ventas_netas_id = fields.Many2one('account_reports_paraguay.anexo3', string="Ventas Netas")
    proveedores_locales_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    proveedores_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    efectivo_empleados_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    efectivo_generado_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    pago_impuestos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    aumento_inversiones_temp_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    aumento_inversiones_largo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    aumento_inversiones_propiedad_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    aporte_capital_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    aumento_prestamos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    dividendos_pagados_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    aumento_intereses_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    diferencias_cambios_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    disponibilidades_id = fields.Many2one('account_reports_paraguay.anexo3', string="Anexo 3")
    anexo4_id = fields.Many2one('account_reports_paraguay.anexo4', string="Anexo 4")
    anexo4_ids = fields.Many2one('account_reports_paraguay.anexo4', string="Anexo 4 Reserva")
    cuentas_patrimoniales_anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")
    cuentas_resultados_anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")
    detalle_rentas_exentas_anexo5_id = fields.Many2one('account_reports_paraguay.anexo5', string="Anexo 5")
    cod_eerr = fields.Char(string="Cod. Para Estado de Resultados RES49")
    saldo_final_otras_cuentas_inversiones_largo_plazo_id = fields.Many2one(
        'account_reports_paraguay.anexo3',
        string="Saldo Final Otras Cuentas (Inversiones Largo Plazo)"
    )

    # VENTAS NETAS (COBROS NETO)
    saldo_inicial_clientes_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Clientes")
    ventas_id = fields.Many2one('account_reports_paraguay.anexo3', string="Ventas")
    descuentos_concedidos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Descuentos Concedidos")
    saldo_final_anticipo_clientes_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Anticipo de Clientes")
    saldo_inicial_tarjetas_credito_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Tarjetas de Créditos")
    saldo_final_clientes_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Clientes")
    saldo_inicial_anticipos_clientes_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Anticipos de Clientes")
    saldo_final_tarjetas_credito_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Tarjetas de Créditos")
    otras_cuentas_ventas_netas_id = fields.Many2one('account_reports_paraguay.anexo3', string="Otras Cuentas Ventas Netas")

    # PAGO A PROVEEDORES LOCALES (PAGO NETO)
    saldo_inicial_anticipo_proveedores_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Anticipo a Proveedores")
    saldo_inicial_gastos_pagados_adelantado_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Gastos Pagados por Adelantado")
    saldo_final_proveedores_locales_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Proveedores Locales")
    saldo_final_otros_acreedores_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otros Acreedores")
    saldo_inicial_mercaderias_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Mercaderías")
    saldo_final_anticipo_proveedores_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Anticipo a Proveedores")
    saldo_inicial_proveedores_locales_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Proveedores Locales")
    saldo_inicial_otros_acreedores_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otros Acreedores")
    saldo_final_gastos_pagados_adelantado_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Gastos Pagados por Adelantado")
    saldo_final_mercaderias_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Mercaderías")
    costo_ventas_id = fields.Many2one('account_reports_paraguay.anexo3', string="Costo de Ventas")

    # PAGO A PROVEEDORES DEL EXTERIOR (PAGO NETO)
    saldo_inicial_anticipo_proveedores_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Anticipo a Proveedores del Exterior")
    saldo_inicial_gastos_pagados_adelantado_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Gastos Pagados por Adelantado")
    saldo_final_proveedores_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Proveedores del Exterior")
    saldo_inicial_mercaderias_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Mercaderías")
    saldo_final_anticipo_proveedores_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Anticipo a Proveedores del Exterior")
    saldo_inicial_proveedores_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Proveedores del Exterior")
    saldo_final_gastos_pagados_adelantado_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Gastos Pagados por Adelantado")
    saldo_final_mercaderias_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Mercaderías")
    costo_ventas_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Costo de Ventas")

    # EFECTIVO PAGADO A EMPLEADOS
    saldo_final_obligaciones_laborales_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Obligaciones Laborales y Cargas Sociales")
    saldo_inicial_obligaciones_laborales_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Obligaciones Laborales y Cargas Sociales")
    sueldos_jornales_id = fields.Many2one('account_reports_paraguay.anexo3', string="Sueldos y Jornales")
    aporte_patronal_id = fields.Many2one('account_reports_paraguay.anexo3', string="Aporte Patronal")
    aguinaldos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Aguinaldos e Indemnizaciones")

    # EFECTIVO GENERADO (USADO) POR OTRAS ACTIVIDADES OPERATIVAS
    agua_luz_telefono_internet_id = fields.Many2one('account_reports_paraguay.anexo3', string="Agua, Luz, Teléfono e Internet")
    alquileres_pagados_id = fields.Many2one('account_reports_paraguay.anexo3', string="Alquileres Pagados")
    combustibles_lubricantes_id = fields.Many2one('account_reports_paraguay.anexo3', string="Combustibles y Lubricantes")
    comisiones_gastos_bancarios_id = fields.Many2one('account_reports_paraguay.anexo3', string="Comisiones y Gastos Bancarios")
    comisiones_sobre_ventas_id = fields.Many2one('account_reports_paraguay.anexo3', string="Comisiones Pagadas sobre Ventas")
    donaciones_contribuciones_id = fields.Many2one('account_reports_paraguay.anexo3', string="Donaciones y Contribuciones")
    fletes_pagados_id = fields.Many2one('account_reports_paraguay.anexo3', string="Fletes Pagados")
    gastos_cobranzas_id = fields.Many2one('account_reports_paraguay.anexo3', string="Gastos de Cobranzas")
    gastos_representacion_id = fields.Many2one('account_reports_paraguay.anexo3', string="Gastos de Representación")
    gastos_pagados_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Gastos Pagados en Exterior")
    honorarios_profesionales_id = fields.Many2one('account_reports_paraguay.anexo3', string="Honorarios Profesionales")
    juicios_gastos_judiciales_id = fields.Many2one('account_reports_paraguay.anexo3', string="Juicios y Gastos Judiciales")
    movilidad_id = fields.Many2one('account_reports_paraguay.anexo3', string="Movilidad")
    otros_gastos_ventas_id = fields.Many2one('account_reports_paraguay.anexo3', string="Otros Gastos de Ventas")
    publicidad_propaganda_id = fields.Many2one('account_reports_paraguay.anexo3', string="Publicidad y Propaganda")
    remuneracion_personal_superior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Remuneración de Personal Superior")
    reparacion_mantenimiento_id = fields.Many2one('account_reports_paraguay.anexo3', string="Reparación y Mantenimiento")
    seguros_pagados_id = fields.Many2one('account_reports_paraguay.anexo3', string="Seguros Pagados")
    utiles_oficina_id = fields.Many2one('account_reports_paraguay.anexo3', string="Útiles de Oficina")
    viaticos_vendedores_id = fields.Many2one('account_reports_paraguay.anexo3', string="Viáticos a Vendedores")
    gastos_no_deducibles_id = fields.Many2one('account_reports_paraguay.anexo3', string="Gastos no Deducibles")

    # PAGO DE IMPUESTOS
    saldo_inicial_anticipos_retenciones_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Anticipos y Retenciones")
    saldo_final_sset_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final SSET (Impuesto a la Renta a Pagar)")
    saldo_final_iva_pagar_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final IVA a Pagar")
    saldo_inicial_iva_credito_fiscal_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial IVA Crédito Fiscal")
    saldo_inicial_retencion_iva_credito_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Retención IVA (Crédito)")
    saldo_inicial_iva_pagar_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial IVA a Pagar")
    saldo_final_iva_credito_fiscal_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final IVA Crédito Fiscal")
    saldo_final_retencion_iva_credito_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Retención IVA (Crédito)")
    impuesto_ejercicio_id = fields.Many2one('account_reports_paraguay.anexo3', string="Impuesto del Ejercicio")
    pago_impuesto_renta_id = fields.Many2one('account_reports_paraguay.anexo3', string="Pago de Impuesto a la Renta")
    saldo_final_anticipos_retenciones_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Anticipos y Retenciones")
    saldo_inicial_sset_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial SSET (Impuesto a la Renta a Pagar)")
    multas_id = fields.Many2one('account_reports_paraguay.anexo3', string="Multas")

    # AUMENTO/DISMINUCIÓN NETO/A DE INVERSIONES TEMPORARIAS
    saldo_inicial_inversiones_temporarias_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Inversiones Temporarias")
    saldo_inicial_otros_activos_corto_plazo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otros Activos a Corto Plazo")
    saldo_final_inversiones_temporarias_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Inversiones Temporarias")
    saldo_final_otros_activos_corto_plazo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otros Activos a Corto Plazo")

    # AUMENTO/DISMINUCIÓN NETO/A DE INVERSIONES A LARGO PLAZO
    saldo_inicial_inversiones_largo_plazo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Inversiones a Largo Plazo")
    saldo_inicial_otros_activos_largo_plazo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otros Activos a Largo Plazo")
    saldo_final_inversiones_largo_plazo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Inversiones a Largo Plazo")
    saldo_final_otros_activos_largo_plazo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otros Activos a Largo Plazo")

    # AUMENTO/DISMINUCIÓN NETO/A DE PROPIEDAD, PLANTA Y EQUIPO
    saldo_inicial_propiedad_planta_equipo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Propiedad, Planta y Equipo")
    saldo_inicial_activos_intangibles_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Activos Intangibles")
    saldo_final_reservas_revaluo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Reservas de Revalúo")
    utilidad_perdida_venta_activos_fijos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Utilidad/Pérdida en Venta de Activos Fijos")
    saldo_inicial_cargos_diferidos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Cargos Diferidos")
    depreciaciones_ejercicio_id = fields.Many2one('account_reports_paraguay.anexo3', string="Depreciaciones del Ejercicio")
    saldo_inicial_reservas_revaluo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Reservas de Revalúo")
    amortizacion_ejercicio_id = fields.Many2one('account_reports_paraguay.anexo3', string="Amortización del Ejercicio")
    saldo_final_propiedad_planta_equipo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Propiedad, Planta y Equipo")
    saldo_final_cargos_diferidos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Cargos Diferidos")
    saldo_final_activos_intangibles_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Activos Intangibles")

    # APORTE DE CAPITAL
    saldo_final_capital_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Capital")
    saldo_inicial_capital_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Capital")

    # AUMENTO/DISMINUCIÓN NETO/A DE PRÉSTAMOS
    saldo_final_prestamos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Préstamos")
    saldo_inicial_prestamos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Préstamos")

    # DIVIDENDOS PAGADOS
    saldo_final_dividendos_pagar_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Dividendos a Pagar")
    saldo_final_resultado_acumulado_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Resultado Acumulado")
    saldo_inicial_resultado_acumulado_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Resultado Acumulado")
    saldo_inicial_dividendos_pagar_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Dividendos a Pagar")

    # AUMENTO/DISMINUCIÓN NETO/A DE INTERESES
    saldo_final_intereses_pagar_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Intereses a Pagar")
    saldo_inicial_intereses_pagar_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Intereses a Pagar")
    otros_intereses_bancarios_id = fields.Many2one('account_reports_paraguay.anexo3', string="Otros Intereses Bancarios")

    # Ventas Netas
    saldo_inicial_otras_cuentas_ventas_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Ventas)")
    saldo_final_otras_cuentas_ventas_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Ventas)")

    # Pago a Proveedores Locales
    saldo_inicial_otras_cuentas_pago_proveedores_locales_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Pago Proveedores Locales)")
    saldo_final_otras_cuentas_pago_proveedores_locales_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Pago Proveedores Locales)")

    # Pago a Proveedores del Exterior
    saldo_inicial_otras_cuentas_pago_proveedores_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Pago Proveedores Exterior)")
    saldo_final_otras_cuentas_pago_proveedores_exterior_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Pago Proveedores Exterior)")

    # Efectivo Pagado a Empleados
    saldo_inicial_otras_cuentas_efectivo_pagado_empleados_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Efectivo Pagado a Empleados)")
    saldo_final_otras_cuentas_efectivo_pagado_empleados_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Efectivo Pagado a Empleados)")

    # Pago de Impuestos
    saldo_inicial_otras_cuentas_pago_impuestos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Pago de Impuestos)")
    saldo_final_otras_cuentas_pago_impuestos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Pago de Impuestos)")

    # Inversiones Temporarias
    saldo_inicial_otras_cuentas_inversiones_temporarias_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Inversiones Temporarias)")
    saldo_final_otras_cuentas_inversiones_temporarias_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Inversiones Temporarias)")

    # Inversiones a Largo Plazo
    saldo_inicial_otras_cuentas_inversiones_largo_plazo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Inversiones Largo Plazo)")
    saldo_final_otras_cuentas_inversiones_largo_plazo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Inversiones Largo Plazo)")

    # Propiedad, Planta y Equipo
    saldo_inicial_otras_cuentas_propiedad_planta_equipo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Propiedad, Planta y Equipo)")
    saldo_final_otras_cuentas_propiedad_planta_equipo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Propiedad, Planta y Equipo)")

    # Aporte de Capital
    saldo_inicial_otras_cuentas_aporte_capital_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Aporte de Capital)")
    saldo_final_otras_cuentas_aporte_capital_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Aporte de Capital)")

    # Préstamos
    saldo_inicial_otras_cuentas_prestamos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Préstamos)")
    saldo_final_otras_cuentas_prestamos_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Préstamos)")

    # Dividendos Pagados
    saldo_inicial_otras_cuentas_dividendos_pagados_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Dividendos Pagados)")
    saldo_final_otras_cuentas_dividendos_pagados_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Dividendos Pagados)")

    # Intereses
    saldo_inicial_otras_cuentas_intereses_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas (Intereses)")
    saldo_final_otras_cuentas_intereses_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas (Intereses)")
    saldo_inicial_otras_cuentas_activo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas del Activo")
    saldo_final_otras_cuentas_pasivo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas del Pasivo")
    saldo_final_otras_cuentas_activo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Final Otras Cuentas del Activo")
    saldo_inicial_otras_cuentas_pasivo_id = fields.Many2one('account_reports_paraguay.anexo3', string="Saldo Inicial Otras Cuentas del Pasivo")
