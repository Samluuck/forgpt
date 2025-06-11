from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    presale_ids = fields.One2many('presale.order', 'lead_id', string='Presale Orders')
    presale_id = fields.Many2one('presale.order', string="Preventa Asociada")
    presale_count = fields.Integer(string="Cotizaciones", compute="_compute_presale_count")
    requiere_preventa = fields.Boolean(string="Requiere Preventa")

    @api.depends('presale_ids')
    def _compute_presale_count(self):
        for lead in self:
            lead.presale_count = len(lead.presale_ids)

    def action_confirm_preventa(self):
        self.ensure_one()
        stage = self.env['crm.stage'].search([('name', '=', 'Preventa (Cotizador)')], limit=1)
        if stage:
            self.stage_id = stage.id

        seq = self.env['ir.sequence'].next_by_code('presale.order') or 'PS001'
        new_presale = self.env['presale.order'].create({
            'name': "%s - %s" % (seq, self.name),
            'partner_id': self.partner_id.id if self.partner_id else False,
            'lead_id': self.id,
        })
        self.presale_id = new_presale.id

    def action_view_presale_orders(self):
        self.ensure_one()
        action = self.env.ref('presale.action_presale_order').read()[0]
        action['domain'] = [('lead_id', '=', self.id)]
        action['context'] = {'default_lead_id': self.id}
        return action
