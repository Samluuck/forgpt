from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError
class Titulo(models.Model):
    _name="hr.titulo"

    informe_anual = fields.Boolean('Profesión Función Pública')
    descripcion_titulo = fields.Char(string="Descripción ")
    carrera = fields.Char(string='Carrera')
    titulo_obtenido = fields.Char(string='Título Obtenido')
    institucion = fields.Char(string='Institución')
    documento = fields.Binary(string="Documento")
    titulo_id = fields.Many2one('hr.employee',
                                ondelete="cascade", string="Empleado")
