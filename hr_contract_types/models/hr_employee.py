from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = "hr.contract"

    contract_type_test = fields.Many2one('hr.contract.type', string="Contrato empleado")


