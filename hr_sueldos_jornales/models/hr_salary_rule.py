from odoo import api, fields, models, _




class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    salario_contrato = fields.Boolean(string="Salario del Contrato", help="Puede marcar esta opción si se trata de la regla que hace referencia al salario del contrato")
    salario_basico = fields.Boolean(string="Salario Básico", help="Puede marcar esta opción si se trata de la regla que hace referencia al salario del basico")
    h_30 = fields.Boolean(string="Hora Extra 30%", help="Puede marcar esta opción si se trata de una regla que se aplica a las Horas Extra al 30%, el monto de la misma sera utilizada en el reporte de Sueldos y Jornales")
    h_50 = fields.Boolean(string="Hora Extra 50%", help="Puede marcar esta opción si se trata de una regla que se aplica a las Horas Extra al 50%, el monto de la misma sera utilizada en el reporte de Sueldos y Jornales")
    h_100 = fields.Boolean(string="Hora Extra 100%", help="Puede marcar esta opción si se trata de una regla que se aplica a las Horas Extra al 100%, el monto de la misma sera utilizada en el reporte de Sueldos y Jornales")
    es_concepto_aguinaldo = fields.Boolean(string="Es concepto de aguinaldo?", help="Puede marcar esta opción si se trata de una regla que se aplica al concepto de aguinaldo")
    aguinaldo = fields.Boolean(string="Es la regla salarial de Aguinaldo", help="Puede marcar esta opción si se trata de una regla que es Aguinaldo")
    aguinaldo_proporcional_desvinculacion = fields.Boolean(string="Aguinaldo proporcional Desvinculación", help="Puede marcar esta opción si se trata de una regla que se aplica a el Aguinaldo, el monto de la misma sera utilizada en el reporte de Sueldos y Jornales")
    beneficios = fields.Boolean(string="Beneficios", help="Puede marcar esta opción si se trata de una regla que se aplica a el Beneficio, corresponde a beneficios recibidos durante el año y en concepto de liquidaciones por despido mas pre-aviso, el monto de la misma sera utilizada en el reporte de Sueldos y Jornales")
    bonificaciones = fields.Boolean(string="Bonificación Familiar", help="Puede marcar esta opción si se trata de una regla que se aplica a las Bonificaciones Familiares, el monto de la misma sera utilizada en el reporte de Sueldos y Jornales")
    concepto_bonificaciones = fields.Boolean(string="Concepto de Bonificación", help="Puede marcar esta opción si se trata de una regla que se aplica a un conceptp de Bonificacion , el monto de la misma sera utilizada en el reporte de Sueldos y Jornales")
    vacaciones = fields.Boolean(string="Vacaciones", help="Puede marcar esta opción si se trata de una regla que se aplica a las Vacaciones, el monto de la misma sera utilizada en el reporte de Sueldos y Jornales")
    gratificacion_unica=fields.Boolean(string="Gratificacion por unica vez", help="Puede marcar esta opción si se trata de una regla que se aplica a las Gratificaciones por unica vez, el monto de la misma sera utilizada en el reporte de Sueldos y Jornales")
