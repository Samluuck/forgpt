from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PresaleItemTemplateConfirmWizard(models.TransientModel):
    _name = 'presale.item.template.confirm.wizard'
    _description = 'Confirmar Aplicación de Plantilla de Ítem'

    item_id = fields.Many2one('presale.order.item', string="Ítem", required=True)
    template_id = fields.Many2one('presale.order.item', string="Plantilla", required=True)
    
    template_name = fields.Char(related='template_id.template_name', readonly=True)
    current_details_count = fields.Integer(
        string="Detalles Actuales", 
        compute='_compute_current_details_count'
    )
    template_details_count = fields.Integer(
        string="Detalles en Plantilla", 
        compute='_compute_template_details_count'
    )
    
    overwrite_existing = fields.Boolean(
        string="Sobrescribir detalles existentes", 
        default=True,
        help="Si está marcado, se eliminarán todos los detalles actuales y se aplicará la plantilla"
    )

    @api.depends('item_id')
    def _compute_current_details_count(self):
        for record in self:
            record.current_details_count = len(record.item_id.item_detail_ids)

    @api.depends('template_id')
    def _compute_template_details_count(self):
        for record in self:
            record.template_details_count = len(record.template_id.item_detail_ids)

    def action_confirm_apply(self):
        """Confirma y aplica la plantilla"""
        self.ensure_one()
        
        if self.overwrite_existing:
            self.item_id._apply_template_details(self.template_id)
        else:
            # Aplicar sin eliminar detalles existentes
            self.item_id._apply_template_details_append(self.template_id)
        
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Cancela la operación"""
        return {'type': 'ir.actions.act_window_close'}


class PresaleItemTemplateSaveWizard(models.TransientModel):
    _name = 'presale.item.template.save.wizard'
    _description = 'Guardar Ítem como Plantilla'

    item_id = fields.Many2one('presale.order.item', string="Ítem", required=True)
    template_name = fields.Char(string="Nombre de la Plantilla", required=True)
    template_description = fields.Text(string="Descripción")
    
    create_copy = fields.Boolean(
        string="Crear copia como plantilla", 
        default=True,
        help="Si está marcado, se creará una copia como plantilla. "
             "Si no, se marcará el ítem actual como plantilla."
    )

    details_count = fields.Integer(
        string="Detalles a incluir", 
        compute='_compute_details_count'
    )

    @api.depends('item_id')
    def _compute_details_count(self):
        for record in self:
            record.details_count = len(record.item_id.item_detail_ids)

    def action_save_template(self):
        """Guarda la plantilla"""
        self.ensure_one()
        
        if self.create_copy:
            # Crear una copia como plantilla
            template_vals = {
                'name': self.template_name,
                'template_name': self.template_name,
                'create_item_template': True,
                'presale_order_id': False,  # Las plantillas no pertenecen a una preventa específica
                'category': self.item_id.category,
            }
            
            template = self.item_id.copy(template_vals)
            
            message = f"Plantilla de ítem '{self.template_name}' creada exitosamente como copia."
            
        else:
            # Marcar el ítem actual como plantilla
            self.item_id.write({
                'create_item_template': True,
                'template_name': self.template_name,
            })
            
            message = f"Ítem marcado como plantilla: '{self.template_name}'"
        
        # Mensaje de confirmación
        if self.item_id.presale_order_id:
            self.item_id.presale_order_id.message_post(
                body=message,
                message_type='notification'
            )
        
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Cancela la operación"""
        return {'type': 'ir.actions.act_window_close'}


class PresaleItemFromTemplateWizard(models.TransientModel):
    _name = 'presale.item.from.template.wizard'
    _description = 'Crear Ítem desde Plantilla'

    presale_order_id = fields.Many2one('presale.order', string="Preventa", required=True)
    template_id = fields.Many2one(
        'presale.order.item', 
        string="Seleccionar Plantilla", 
        domain=[('create_item_template', '=', True)],
        required=True
    )
    
    item_name = fields.Char(
        string="Nombre del Ítem", 
        required=True,
        help="Nombre para el nuevo ítem"
    )
    
    template_name = fields.Char(related='template_id.template_name', readonly=True)
    template_category = fields.Selection(related='template_id.category', readonly=True)
    template_details_count = fields.Integer(
        string="Detalles en Plantilla", 
        compute='_compute_template_details_count'
    )

    @api.depends('template_id')
    def _compute_template_details_count(self):
        for record in self:
            record.template_details_count = len(record.template_id.item_detail_ids)

    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Auto-completar nombre basado en la plantilla"""
        if self.template_id:
            self.item_name = self.template_id.template_name or self.template_id.name

    def action_create_item(self):
        """Crear nuevo ítem desde plantilla"""
        self.ensure_one()
        
        if not self.template_id.create_item_template:
            raise ValidationError("El ítem seleccionado no es una plantilla válida.")
        
        # Crear nuevo ítem basado en la plantilla
        new_item_vals = {
            'presale_order_id': self.presale_order_id.id,
            'name': self.item_name,
            'category': self.template_id.category,
            'qty': self.template_id.qty,
            'unit_price': self.template_id.unit_price,
            'sequence': self._get_next_sequence(),
        }
        
        new_item = self.env['presale.order.item'].create(new_item_vals)
        
        # Copiar detalles de la plantilla
        for template_detail in self.template_id.item_detail_ids:
            detail_vals = {
                'item_id': new_item.id,
                'name': template_detail.name,
                'product_id': template_detail.product_id.id,
                'qty': template_detail.qty,
                'unit_price': template_detail.unit_price,
                'sequence': template_detail.sequence,
                # Copiar campos específicos de turnos si aplica
                'operarios': template_detail.operarios,
                'desde': template_detail.desde,
                'hasta': template_detail.hasta,
                'dias_semanales': template_detail.dias_semanales,
                'horas_break_desde': template_detail.horas_break_desde,
                'horas_break_hasta': template_detail.horas_break_hasta,
                'precio_uso_turno': template_detail.precio_uso_turno,
            }
            
            self.env['presale.order.item.detail'].create(detail_vals)
        
        # Mensaje de confirmación
        self.presale_order_id.message_post(
            body=f"Ítem '{self.item_name}' creado desde plantilla '{self.template_id.template_name or self.template_id.name}'. "
                 f"Se agregaron {len(self.template_id.item_detail_ids)} detalles.",
            message_type='notification'
        )
        
        # Retornar a la vista del nuevo ítem
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ítem Creado',
            'res_model': 'presale.order.item',
            'view_mode': 'form',
            'res_id': new_item.id,
            'target': 'current',
        }

    def _get_next_sequence(self):
        """Obtener la siguiente secuencia para el nuevo ítem"""
        max_sequence = max(self.presale_order_id.order_item_ids.mapped('sequence') or [0])
        return max_sequence + 10

    def action_cancel(self):
        """Cancela la operación"""
        return {'type': 'ir.actions.act_window_close'}