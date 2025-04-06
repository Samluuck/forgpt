from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError

class Cedula(models.Model):
    _name='hr.cedula'

    fecha_vencimiento = fields.Date(string="Fecha Vencimiento", default=fields.Date.today)
    documento = fields.Binary(string="Adjuntar Documento")
    alerta = fields.Boolean('Alerta Vencimiento')
    identidad_id = fields.Many2one('hr.employee',
                                      ondelete='cascade', string="Empleado")




