from odoo import api, fields, models, tools, _, exceptions
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta,date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    caution_ids = fields.One2many('hr.cautions','employee_id')
    cautions_qty = fields.Integer(compute="compute_cautions",store=True)

    @api.depends('caution_ids')
    def compute_cautions(self):
        print("holaaaaaaaaaaaaa")
        for rec in self:
            if rec.caution_ids:
                rec.cautions_qty = len(rec.caution_ids)
