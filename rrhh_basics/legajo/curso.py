from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError
class Curso(models.Model):
    _name="hr.curso"
    _rec_name="descripcion"

    descripcion = fields.Char(string="Descripción")
    institucion = fields.Char(string='Institución')
    nombre_tipo_capacitacion = fields.Char(string='Tipo De Capacitación')
    observacion = fields.Char(string='Observación')
    documento = fields.Binary(string="Documento")
    fecha_inicio = fields.Date(string="Fecha Inicio", default=fields.Date.today)
    fecha_final = fields.Date(string="Fecha Final", default=fields.Date.today)
    carga_horaria = fields.Integer(string="Carga Horaria")
    curso_id = fields.Many2one('hr.employee',
                               ondelete="cascade", string="Empleado")
