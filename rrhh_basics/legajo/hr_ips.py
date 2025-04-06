from odoo import models, fields, api, exceptions


class Ips(models.Model):
    _name="hr.ips"

    ips = fields.Binary(string="Adjuntar Ips")
    ips_id=fields.Many2one('hr.employee',ondelete="cascade", string="Empleado")
