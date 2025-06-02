from odoo import fields, models, api


class FleeVehicleReparto (models.Model):
    _inherit = 'fleet.vehicle'

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id)
    


