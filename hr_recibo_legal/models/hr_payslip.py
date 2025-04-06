from odoo import models, fields, api



class hr_payroll_run_ext(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(models.Model,self).fields_view_get(view_id, view_type, toolbar, submenu)
        return res


    def fecha(self,fecha):
        dia= fecha.day
        mes = fecha.month
        ano = fecha.year
        junto = " / ".join([str(dia),'de',str(mes),'del',str(ano)])
        return junto

    def agregar_punto_de_miles(self, numero):
        numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in
                                     range(0, len(str(int(numero))), 3)])[::-1]
        num_return = numero_con_punto
        return num_return

    def elimina_letra(self,cadena):
        remover_cadena = "SLIP/"
        cadena =cadena.replace(remover_cadena,'')
        print(cadena)
        return cadena
class HrSalaryRules(models.Model):
    _inherit = 'hr.salary.rule'

    es_descuento = fields.Boolean("Es una regla salarial de descuento?",help="Este campo nos ayuda a tener diferenciado a un Ingreso de un Descuento para el recibo salarial")
    es_ingreso = fields.Boolean("Es una regla salarial de ingreso?",help="Este campo nos ayuda a tener diferenciado a un Ingreso de un Descuento para el recibo salarial")
    es_ips = fields.Boolean("Es la regla salarial de IPS?",help="Este campo nos ayuda a tener diferenciado el campo correspondiente a IPS")
    es_horas_extras = fields.Boolean("Es la regla salarial de Horas Extras?",help="Este campo nos ayuda a tener diferenciado el campo correspondiente a las Horas Extras")
    es_comision = fields.Boolean("Es la regla salarial de Comisiones?",help="Este campo nos ayuda a tener diferenciado el campo correspondiente a las Comisiones")
    es_otro_ingreso = fields.Boolean("Es la regla salarial corespondiente a Otros Ingresos?",help="Este campo nos ayuda a tener diferenciados los campos correspondientes a Otros Ingresos")
    es_otro_descuento = fields.Boolean("Es la regla salarial corespondiente a Otros Descuento?",help="Este campo nos ayuda a tener diferenciados los campos correspondientes a Otros Descuentos")
    es_salario_neto = fields.Boolean("Es la regla salarial corespondiente a Salario Neto?",help="Este campo nos ayuda a tener diferenciado al campo de Salario Neto")
    es_subtotal = fields.Boolean("Es la regla salaraial de subtotal, es decir lo que le corresponde por los dias trabajados", help="Este campo corresponde a la regla de subtotal")



class WeRecibo(models.Model):
    _inherit = "hr.work.entry.type"

    es_ausencia = fields.Boolean(string='¿Esta Ausencia descuenta el nro de dias trabajados?',help="Debemos completar este campo en caso de que al tener esta ausencia al empleado se le descuenta el numero de dias trabajados")
