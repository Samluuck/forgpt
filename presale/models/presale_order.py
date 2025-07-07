from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PresaleOrder(models.Model):
    _name = 'presale.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Presale Order'
    _order = 'date_order desc, id desc'
    _check_company_auto = True

    # ✅ MEJORA: Campos básicos optimizados con índices estratégicos
    name = fields.Char(string='Nombre del Pedido', required=True, copy=False, index=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, tracking=True, index=True)
    lead_id = fields.Many2one('crm.lead', string='Oportunidad', index=True, tracking=True)
    date_order = fields.Datetime(string='Fecha del Pedido', default=fields.Datetime.now, required=True, index=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('approved', 'Aprobado'),
        ('cancelled', 'Cancelado'),  # ✅ MEJORA: Agregar estado cancelado
    ], string='Estado', default='draft', tracking=True, index=True)
    
    # ✅ MEJORA: Campos de usuario optimizados
    commercials_ids = fields.Many2one('res.users', string='Comercial', index=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user, index=True)
    
    # ✅ MEJORA: Campos de negocio optimizados
    crear_presupuesto = fields.Boolean(string="Crear Presupuesto", default=True)
    presupuesto_id = fields.Many2one('sale.order', string="Presupuesto de Venta", readonly=True, copy=False)
    equipo_de_venta_id = fields.Many2one('equipo.venta', string="Equipo de Venta", index=True)
    ejecutivo = fields.Char(string="Ejecutivo", tracking=True)
    fecha_vencimiento = fields.Date(string="Fecha de Vencimiento", tracking=True)
    forma_pago = fields.Char(string="Forma de Pago")
    margen = fields.Char(string="Margen")
    condiciones_pago = fields.Text(string="Condiciones de Pago")
    lista_precios = fields.Char(string="Lista de Precios")
    
    # ✅ MEJORA: Campos financieros optimizados con mejor precisión
    subtotal = fields.Monetary(string="Subtotal", compute="_compute_amounts", store=True, tracking=True)
    impuestos = fields.Monetary(string="Impuestos", compute="_compute_amounts", store=True)
    total = fields.Monetary(string="Total", compute="_compute_amounts", store=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', 
                                  default=lambda self: self.env.company.currency_id, required=True)
    
    # ✅ MEJORA: Relaciones optimizadas
    order_item_ids = fields.One2many('presale.order.item', 'presale_order_id', string="Líneas del Pedido", copy=True)
    cuenta_analitica = fields.Many2one('account.analytic.account', string='Cuenta Analítica',
                                       help='Cuenta analítica asociada a este pedido.',
                                       ondelete='set null', index=True)
    
    # ✅ MEJORA: Campos computed adicionales para reportes
    item_count = fields.Integer(string="N° Ítems", compute="_compute_item_count", store=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    # ✅ MEJORA: SQL Constraints
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'El nombre de la preventa debe ser único por compañía.'),
        ('positive_total', 'CHECK(total >= 0)', 'El total debe ser mayor o igual a cero.'),
    ]

    # ✅ MEJORA: Computed fields optimizados con batch processing
    @api.depends('order_item_ids', 'order_item_ids.subtotal')
    def _compute_amounts(self):
        # Usar read_group para mejor rendimiento
        if not self:
            return
            
        # Obtener subtotales agrupados
        item_data = self.env['presale.order.item'].read_group(
            [('presale_order_id', 'in', self.ids)],
            ['presale_order_id', 'subtotal:sum'],
            ['presale_order_id']
        )
        
        subtotals = {data['presale_order_id'][0]: data['subtotal'] for data in item_data}
        
        for order in self:
            subtotal = subtotals.get(order.id, 0.0)
            order.subtotal = subtotal
            order.impuestos = 0.0  # Implementar cálculo de impuestos si es necesario
            order.total = subtotal + order.impuestos

    @api.depends('order_item_ids')
    def _compute_item_count(self):
        item_data = self.env['presale.order.item'].read_group(
            [('presale_order_id', 'in', self.ids)],
            ['presale_order_id'],
            ['presale_order_id']
        )
        counts = {data['presale_order_id'][0]: data['presale_order_id_count'] for data in item_data}
        
        for order in self:
            order.item_count = counts.get(order.id, 0)

    # ✅ MEJORA: Validaciones optimizadas
    @api.constrains('date_order', 'fecha_vencimiento')
    def _check_dates(self):
        for order in self:
            if order.fecha_vencimiento and order.fecha_vencimiento < order.date_order.date():
                raise ValidationError("La fecha de vencimiento no puede ser anterior a la fecha del pedido.")

    @api.constrains('order_item_ids')
    def _check_order_items(self):
        for order in self:
            if order.state in ('confirmed', 'approved') and not order.order_item_ids:
                raise ValidationError("No se puede confirmar una preventa sin ítems.")

    # ✅ MEJORA: Métodos de acción optimizados
    def action_confirm(self):
        """Confirmar preventa con validaciones"""
        self._check_can_confirm()
        return self.write({'state': 'confirmed'})
    
    def action_approve(self):
        """Aprobar preventa y crear presupuesto si es necesario"""
        self._check_can_approve()
        
        for order in self:
            if order.crear_presupuesto:
                order._handle_sale_order_creation()
            order.state = 'approved'
        return True

    def action_cancel(self):
        """Cancelar preventa"""
        if any(order.state == 'approved' for order in self):
            raise UserError("No se pueden cancelar preventas aprobadas.")
        return self.write({'state': 'cancelled'})

    def action_draft(self):
        """Volver a borrador"""
        return self.write({'state': 'draft'})

    # ✅ MEJORA: Métodos privados optimizados
    def _check_can_confirm(self):
        """Validar que se puede confirmar"""
        for order in self:
            if order.state != 'draft':
                raise UserError(f"Solo se pueden confirmar preventas en borrador. ({order.name})")
            if not order.order_item_ids:
                raise UserError(f"No se puede confirmar una preventa sin ítems. ({order.name})")

    def _check_can_approve(self):
        """Validar que se puede aprobar"""
        for order in self:
            if order.state not in ('draft', 'confirmed'):
                raise UserError(f"Solo se pueden aprobar preventas confirmadas. ({order.name})")

    def _handle_sale_order_creation(self):
        """Manejar la creación o actualización de la orden de venta"""
        self.ensure_one()
        
        if not self.presupuesto_id:
            # Crear nueva orden de venta
            self.presupuesto_id = self._create_sale_order()
        else:
            # Validar y actualizar orden existente
            if self.presupuesto_id.state == 'draft':
                if not self.env.context.get('update_confirmed', False):
                    return self._show_update_wizard()
                else:
                    self._update_sale_order()
            else:
                raise UserError(_("La Orden de Venta ya no está en borrador y no puede ser actualizada."))

    def _create_sale_order(self):
        """Crear una nueva orden de venta"""
        return self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'presale_id': self.id,
            'user_id': self.user_id.id,
            'date_order': self.date_order,
        })

    def _update_sale_order(self):
        """Actualizar orden de venta existente"""
        self.presupuesto_id.write({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'user_id': self.user_id.id,
        })

    def _show_update_wizard(self):
        """Mostrar wizard de confirmación de actualización"""
        return {
            'name': _('Actualizar Orden de Venta'),
            'type': 'ir.actions.act_window',
            'res_model': 'presale.update.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_presale_id': self.id},
        }

    # ✅ MEJORA: Override de métodos del ORM
    @api.model_create_multi
    def create(self, vals_list):
        """Create optimizado con generación de secuencia"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New') or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('presale.order') or _('New')
        return super().create(vals_list)

    def copy(self, default=None):
        """Copy optimizado"""
        default = dict(default or {})
        default.update({
            'name': _('%s (Copia)') % self.name,
            'state': 'draft',
            'presupuesto_id': False,
        })
        return super().copy(default)

    def unlink(self):
        """Unlink con validaciones"""
        if any(order.state not in ('draft', 'cancelled') for order in self):
            raise UserError("Solo se pueden eliminar preventas en borrador o canceladas.")
        return super().unlink()

    # ✅ MEJORA: Métodos de utilidad para reportes
    def _get_order_summary(self):
        """Obtener resumen de la orden para reportes"""
        self.ensure_one()
        return {
            'total_items': self.item_count,
            'categories': self.order_item_ids.mapped('category'),
            'total_amount': self.total,
            'currency': self.currency_id.name,
        }

    # ✅ MEJORA: Action para ver presupuesto relacionado
    def action_view_sale_order(self):
        """Abrir orden de venta relacionada"""
        self.ensure_one()
        if not self.presupuesto_id:
            raise UserError("No hay presupuesto asociado a esta preventa.")
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.presupuesto_id.id,
            'target': 'current',
        }
        
 ##################################### TEMPLATE ##################################################################       
    # Agregar estos métodos al modelo presale.order en tu archivo presale_order.py

    def action_create_item_from_template(self):
        """Crear nuevo ítem desde plantilla"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Crear Ítem desde Plantilla',
            'res_model': 'presale.item.from.template.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_presale_order_id': self.id,
            }
        }

    def action_manage_item_templates(self):
        """Abrir vista para gestionar plantillas de ítems"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gestionar Plantillas de Ítems',
            'res_model': 'presale.order.item',
            'view_mode': 'kanban,tree,form',
            'domain': [('create_item_template', '=', True)],
            'context': {
                'default_create_item_template': True,
                'search_default_item_templates': 1,
            },
            'view_ids': [
                (0, 0, {'view_mode': 'kanban', 'view_id': self.env.ref('presale.presale_item_template_kanban_view').id}),
                (0, 0, {'view_mode': 'tree', 'view_id': self.env.ref('presale.presale_item_template_tree_view').id}),
                (0, 0, {'view_mode': 'form', 'view_id': self.env.ref('presale.presale_item_template_form_view').id}),
            ]
        }
        
##########################################################

class PresaleUpdateWizard(models.TransientModel):
    _name = 'presale.update.wizard'
    _description = 'Wizard para actualizar la Orden de Venta desde la Preventa'

    presale_id = fields.Many2one('presale.order', string="Preventa", required=True)
    current_sale_order = fields.Char(string="Orden de Venta Actual", related='presale_id.presupuesto_id.name', readonly=True)
    warning_message = fields.Html(string="Advertencia", compute='_compute_warning_message')

    @api.depends('presale_id')
    def _compute_warning_message(self):
        for wizard in self:
            if wizard.presale_id and wizard.presale_id.presupuesto_id:
                wizard.warning_message = f"""
                <div class="alert alert-warning">
                    <strong>Atención:</strong> La Orden de Venta <strong>{wizard.presale_id.presupuesto_id.name}</strong> 
                    será actualizada con la información actual de la Preventa <strong>{wizard.presale_id.name}</strong>.
                    <br/><br/>
                    <strong>Cambios que se aplicarán:</strong>
                    <ul>
                        <li>Cliente: {wizard.presale_id.partner_id.name}</li>
                        <li>Referencia: {wizard.presale_id.name}</li>
                        <li>Usuario: {wizard.presale_id.user_id.name}</li>
                    </ul>
                </div>
                """
            else:
                wizard.warning_message = "<div class='alert alert-info'>No hay orden de venta asociada.</div>"

    def action_confirm_update(self):
        """Confirmar actualización"""
        return self.presale_id.with_context(update_confirmed=True).action_approve()

    def action_cancel_update(self):
        """Cancelar actualización"""
        return {'type': 'ir.actions.act_window_close'}


class EquipoVenta(models.Model):
    _name = 'equipo.venta'
    _description = 'Equipo de Venta'
    _order = 'name'

    name = fields.Char(string='Nombre del Equipo', required=True, index=True)
    descripcion = fields.Text(string='Descripción')
    activo = fields.Boolean(string='Activo', default=True, index=True)
    
    # ✅ MEJORA: Campos adicionales para equipos
    responsable_id = fields.Many2one('res.users', string='Responsable')
    miembro_ids = fields.Many2many('res.users', 'equipo_venta_user_rel', 'equipo_id', 'user_id', string='Miembros')
    
    # ✅ MEJORA: Campos estadísticos
    presale_count = fields.Integer(string='Preventas', compute='_compute_presale_count')

    @api.depends('presale_count')  # Campo placeholder para trigger manual
    def _compute_presale_count(self):
        presale_data = self.env['presale.order'].read_group(
            [('equipo_de_venta_id', 'in', self.ids)],
            ['equipo_de_venta_id'],
            ['equipo_de_venta_id']
        )
        counts = {data['equipo_de_venta_id'][0]: data['equipo_de_venta_id_count'] for data in presale_data}
        
        for equipo in self:
            equipo.presale_count = counts.get(equipo.id, 0)

    def action_view_presales(self):
        """Ver preventas del equipo"""
        return {
            'name': f'Preventas - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'presale.order',
            'view_mode': 'tree,form',
            'domain': [('equipo_de_venta_id', '=', self.id)],
            'context': {'default_equipo_de_venta_id': self.id},
        }