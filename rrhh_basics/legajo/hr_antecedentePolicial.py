from odoo import models, fields, api, exceptions
class EspecimenFirma(models.Model):
    _name="hr.antecedentepolicial"

    fecha_actual = fields.Date(string="Fecha Actualizada", default=fields.Date.today)
    documento_antecedente = fields.Binary(string="Adjuntar Documento")
    policial_id=fields.Many2one('hr.employee',
                                 ondelete="cascade", string="Empleado")