from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    hide_peppol_fields = fields.Boolean(string="Hide PEPPOL Fields", default=True)
    is_coa_installed = fields.Boolean(string="Is COA Installed", default=False)