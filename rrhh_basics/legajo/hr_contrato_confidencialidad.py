from odoo import models, fields, api, exceptions

class ContratoConfidencial(models.Model):
    _name='hr.confidencial'


    contrato_confidencial_documento = fields.Binary(string="Adjuntar Contrato Confidencial")
    confidencial_id = fields.Many2one('hr.employee', ondelete="cascade", string="Empleado")


