from odoo import api, fields, models, tools, _, exceptions



class HrEmployee(models.AbstractModel):
    _inherit = 'hr.employee.base'

    calcula_vacaciones = fields.Boolean(string="Calcular vacaciones?",help="Si no se encuentra marcado, no se calcularan automaticamente las vacaciones para este empleado.",default=True)
    dias_vacaciones_no_utilizados = fields.Integer(string='Días de Vacaciones No Utilizados', default=0)
    ultimo_anio_calculado = fields.Integer(string='Último Año de Cálculo de Vacaciones', default=0)

    asignacion_vacaciones = fields.Boolean(string="Asignación de Vacaciones", default=False,help="Este check cambia de estado a verdadero en caso de que el empleado tenga ya una asignacion de vacaciones.",tracking= True)