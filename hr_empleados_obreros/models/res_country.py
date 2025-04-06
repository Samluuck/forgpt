from odoo import fields, models, exceptions, api




class HrResCountryInh(models.Model):
    _inherit = "res.country"

    gentilicio = fields.Char(string='Nacionalidad', tracking=True)