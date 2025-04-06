from odoo import models, fields, api, exceptions
class EspecimenFirma(models.Model):
    _name="hr.especimen"

    fecha_actual = fields.Date(string="Fecha Actualizada", default=fields.Date.today)
    documento = fields.Binary(string="Adjuntar Documento")
    especimen_id=fields.Many2one('hr.employee',
                                 ondelete="cascade", string="Empleado")