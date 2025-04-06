from odoo import api, fields, models, _




class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    salario_neto = fields.Boolean(string="Salario Neto", help="Puede marcar esta opción si se trata de la regla que hace referencia al salario NETO")
