from odoo import fields, models, exceptions, api
from num2words import num2words



class HrEmployeeInh(models.Model):
    _inherit = "hr.leave"

    ciudad=fields.Char(string="Ciudad para cabecera del reporte de notificacion de vacaciones ",help="La ciudad que iria en la cabecera")
    fecha_notificacion = fields.Date(string='Fecha de la notificación de vacaciones:')
    fecha_retorno = fields.Date(string='Fecha de retorno:')



    #En el caso de que en una fecha solo quiera el año
    def mes_ano(self,fecha):
        ano = fecha.year
        return ano
    #Por si desean tener en el template el calculo salarial correspondiente a esos dias de vacaciones
    def sal_vac(self,salario,dias):
        salario_por_dia= salario/30
        dias_de_vacaciones= dias
        resultado= int(salario_por_dia*dias_de_vacaciones)
        return resultado

    def calcular_letras(self, numero):
        entero = int(numero)
        letras  = num2words(entero, lang='es')
        letras = '--'+' guaraníes ' + letras + '--'
        return letras