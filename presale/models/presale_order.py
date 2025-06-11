from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PresaleOrder(models.Model):
    _name = 'presale.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Presale Order'

    name = fields.Char(string='Nombre del Pedido', required=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    lead_id = fields.Many2one('crm.lead', string='Oportunidad')
    date_order = fields.Datetime(string='Fecha del Pedido', default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('approved', 'Aprobado'),
    ], string='Estado', default='draft', tracking=True)
    commercials_ids = fields.Many2one(
        'res.users',
        string='Comercial'
    )
    crear_presupuesto = fields.Boolean(string="Crear Presupuesto")
    presupuesto_id = fields.Many2one('sale.order', string="Presupuesto de Venta")
    equipo_de_venta = fields.Char(string="Equipo de Venta")
    ejecutivo = fields.Char(string="Ejecutivo")
    fecha_vencimiento = fields.Date(string="Fecha de Vencimiento")
    forma_pago = fields.Char(string="Forma de Pago")
    margen = fields.Char(string="Margen")
    condiciones_pago = fields.Text(string="Condiciones de Pago")
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)
    impuestos = fields.Float(string="Impuestos", compute="_compute_impuestos", store=True)
    total = fields.Float(string="Total", compute="_compute_total", store=True)
    order_item_ids = fields.One2many('presale.order.item', 'presale_order_id', string="Líneas del Pedido")
    cuenta_analitica = fields.Many2one(
        'account.analytic.account',
        string='Cuenta Analítica',
        help='Cuenta analítica asociada a este pedido.',
        ondelete='set null',
        index=True,
    )
    lista_precios = fields.Char(string="Lista de Precios")

    @api.depends('order_item_ids.subtotal')
    def _compute_subtotal(self):
        for order in self:
            order.subtotal = sum(line.subtotal for line in order.order_item_ids)

    @api.depends('order_item_ids')
    def _compute_impuestos(self):
        for order in self:
            order.impuestos = 0.0

    @api.depends('subtotal', 'impuestos')
    def _compute_total(self):
        for order in self:
            order.total = order.subtotal + order.impuestos

    def action_confirm(self):
        for order in self:
            order.state = 'confirmed'
        return True

    def action_approve(self):

        for order in self:
            if order.crear_presupuesto:
                if not order.presupuesto_id:
                    # Caso 1: No existe la venta asociada → se crea la Orden de Venta
                    nuevo_presupuesto = self.env['sale.order'].create({
                        'partner_id': order.partner_id.id,
                        'origin': order.name,
                        'presale_id': order.id,
                    })
                    order.presupuesto_id = nuevo_presupuesto.id

                else:
                    # Caso 2: Existe la Orden de Venta asociada
                    if order.presupuesto_id.state == 'draft':
                        # Si la orden está en borrador, solicitar confirmación si no se ha confirmado aún
                        if not self.env.context.get('update_confirmed', False):
                            return {
                                'name': _('Actualizar Orden de Venta'),
                                'type': 'ir.actions.act_window',
                                'res_model': 'presale.update.wizard',
                                'view_mode': 'form',
                                'target': 'new',
                                'context': {'default_presale_id': order.id},
                            }
                        else:
                            # Si se confirmó la actualización, se actualizan los datos en la Orden de Venta
                            order.presupuesto_id.write({
                                'partner_id': order.partner_id.id,
                                'origin': order.name,
                            })
                    else:
                        # Si la Orden de Venta existe y NO está en draft, se lanza el error desde la preventa.
                        raise UserError(_("La Orden de Venta ya no está en borrador y no puede ser actualizada."))
            order.state = 'approved'
        return True

class PresaleUpdateWizard(models.TransientModel):
    _name = 'presale.update.wizard'
    _description = 'Wizard para actualizar la Orden de Venta desde la Preventa'

    presale_id = fields.Many2one('presale.order', string="Preventa", required=True)

    def action_confirm_update(self):
        return self.presale_id.with_context(update_confirmed=True).action_approve()

    def action_cancel_update(self):
        return {'type': 'ir.actions.act_window_close'}