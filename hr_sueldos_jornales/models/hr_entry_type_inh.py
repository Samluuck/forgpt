from odoo import fields, models, exceptions, api


class HrLeaveTypeInh(models.Model):
    _inherit = "hr.work.entry.type"

    es_ausencia_descontada = fields.Boolean(string='Es una ausencia que se descuenta de los dias trabajados?',help="Este campo debemos marcar en caso de que la ausencia sea descontada de la cantidad de dias trabajados")
