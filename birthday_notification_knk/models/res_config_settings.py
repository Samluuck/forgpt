from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    send_contact_birthday_notification = fields.Boolean(related="company_id.send_contact_birthday_notification", readonly=False)
    send_employee_birthday_notification = fields.Boolean(related="company_id.send_employee_birthday_notification", readonly=False)
