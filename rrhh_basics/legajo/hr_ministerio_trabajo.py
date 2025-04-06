from odoo import models, fields, api, exceptions


class MInisterioTrabajo(models.Model):
    _name="hr.ministerio"

    ministerio_trabajo = fields.Binary(string="Adjuntar Inscripción a Ministerio de trabajo")
    trabajo_id=fields.Many2one('hr.employee',ondelete="cascade", string="Empleado")
