from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError
class CV(models.Model):
    _name="hr.cv"

    fecha_actual = fields.Date(string="Fecha Actualizada", default=fields.Date.today)
    documento = fields.Binary(string="Adjuntar Documento")
    curriculum_id = fields.Many2one('hr.employee', ondelete="cascade", string="Empleado")