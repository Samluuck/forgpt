from odoo import models, fields, api, exceptions


class ReglamientoInterno(models.Model):
    _name="hr.reglamento"

    reglamento_interno = fields.Binary(string="Adjuntar Reglamento Interno")
    interno_id=fields.Many2one('hr.employee',ondelete="cascade", string="Empleado")