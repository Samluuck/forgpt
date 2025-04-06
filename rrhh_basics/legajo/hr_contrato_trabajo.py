from odoo import models, fields, api, exceptions


class ContratoTrabajo(models.Model):
    _name="hr.contratotrabajo"

    contrato_trabajo = fields.Binary(string="Adjuntar Contrato de Trabajo")
    contrato_trabajo_id = fields.Many2one('hr.employee', ondelete="cascade", string="Empleado")
