from odoo import models, fields

class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    es_corrido = fields.Boolean(string="Es Corrido", help="Indica si este tipo de ausencia debe contarse como días corridos, incluyendo fines de semana.")