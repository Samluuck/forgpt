from odoo import models, fields, api

class HrContractOvertime(models.Model):
    _inherit = 'hr.contract'

    over_hour = fields.Monetary(
        string='Salario hora',
        compute='_compute_salary_components',
        readonly=True,
        store=True
    )
    over_day = fields.Monetary(
        string='Salario diario',
        compute='_compute_salary_components',
        readonly=True,
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('wage')
    def _compute_salary_components(self):
        for record in self:
            if record.wage:
                record.over_day = record.wage / 30
                record.over_hour = record.over_day / 8
            else:
                record.over_day = 0.0
                record.over_hour = 0.0
