
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, datetime, time
from dateutil.parser import parse

class hr_grupo_familiar_documento(models.Model):
    _name="hr.grupo_familiar_documento"

    documento_id=fields.Many2one('hr.grupo_familiar',
                                      ondelete='cascade', string="Empleado",readonly=True)
    descripcion=fields.Text(string="Descripción")
    documento=fields.Binary(string="Adjuntar documento")
