from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PresaleOrderItem(models.Model):
    _name = 'presale.order.item'
    _description = 'Presale Order Item'
    _order = 'sequence, id'
    
    sequence = fields.Integer('Sequence', default=10, index=True)
    name = fields.Char(string="Nombre del Ítem", store=True, index=True)
    presale_order_id = fields.Many2one('presale.order', string="Presale Order", ondelete="cascade", required=True, index=True)
    product_id = fields.Many2one('product.product', string="Producto", index=True)
    qty = fields.Float(string="Cant (Hrs/Personas)", default=0.0, digits='Product Unit of Measure')
    unit_price = fields.Float(string="Precio", digits='Product Price')
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True, digits='Product Price')
    item_detail_ids = fields.One2many('presale.order.item.detail', 'item_id', string="Detalles del Ítem")
    
    category = fields.Selection([
        ('equipo', 'Equipos'),
        ('insumo', 'Insumos y Elementos'),
        ('maquina', 'Máquinas'),
        ('epi_epc', 'EPI / EPC'),
        ('turno', 'Turnos'),
        ('otro', 'Otros'),
    ], string="Categoría", index=True)
    
    # Campos computed
    show_product_fields = fields.Boolean(compute='_compute_ui_fields', store=False)
    show_details_fields = fields.Boolean(compute='_compute_ui_fields', store=False)
    selected_category = fields.Char(compute='_compute_ui_fields', store=False)
    
    # Campos Boolean como properties computed
    is_equipo = fields.Boolean(compute='_compute_category_booleans', inverse='_inverse_is_equipo', store=False)
    is_insumo = fields.Boolean(compute='_compute_category_booleans', inverse='_inverse_is_insumo', store=False)
    is_maquina = fields.Boolean(compute='_compute_category_booleans', inverse='_inverse_is_maquina', store=False)
    is_epi_epc = fields.Boolean(compute='_compute_category_booleans', inverse='_inverse_is_epi_epc', store=False)
    is_turno = fields.Boolean(compute='_compute_category_booleans', inverse='_inverse_is_turno', store=False)
    is_otro = fields.Boolean(compute='_compute_category_booleans', inverse='_inverse_is_otro', store=False)

    # SQL Constraints para mejor integridad
    _sql_constraints = [
        ('positive_qty', 'CHECK(qty >= 0)', 'La cantidad debe ser mayor o igual a cero.'),
        ('positive_price', 'CHECK(unit_price >= 0)', 'El precio debe ser mayor o igual a cero.'),
    ]

    # Compute con batch processing
    @api.depends('category')
    def _compute_ui_fields(self):
        for record in self:
            has_category = bool(record.category)
            record.show_product_fields = has_category
            record.show_details_fields = has_category
            record.selected_category = dict(self._fields['category'].selection).get(record.category, False) if record.category else False

    # Computed fields para retrocompatibilidad con Boolean fields
    @api.depends('category')
    def _compute_category_booleans(self):
        for record in self:
            record.is_equipo = record.category == 'equipo'
            record.is_insumo = record.category == 'insumo'
            record.is_maquina = record.category == 'maquina'
            record.is_epi_epc = record.category == 'epi_epc'
            record.is_turno = record.category == 'turno'
            record.is_otro = record.category == 'otro'

    # Inverse methods para mantener compatibilidad
    def _inverse_is_equipo(self):
        for record in self:
            if record.is_equipo:
                record.category = 'equipo'
            elif record.category == 'equipo':
                record.category = False

    def _inverse_is_insumo(self):
        for record in self:
            if record.is_insumo:
                record.category = 'insumo'
            elif record.category == 'insumo':
                record.category = False

    def _inverse_is_maquina(self):
        for record in self:
            if record.is_maquina:
                record.category = 'maquina'
            elif record.category == 'maquina':
                record.category = False

    def _inverse_is_epi_epc(self):
        for record in self:
            if record.is_epi_epc:
                record.category = 'epi_epc'
            elif record.category == 'epi_epc':
                record.category = False

    def _inverse_is_turno(self):
        for record in self:
            if record.is_turno:
                record.category = 'turno'
            elif record.category == 'turno':
                record.category = False

    def _inverse_is_otro(self):
        for record in self:
            if record.is_otro:
                record.category = 'otro'
            elif record.category == 'otro':
                record.category = False

    @api.depends('category')
    def _compute_name(self):
        category_names = dict(self._fields['category'].selection)
        for record in self:
            record.name = category_names.get(record.category, '')

    # OnChange para limpiar datos
    @api.onchange('category')
    def _onchange_category(self):
        if self.category != 'turno':
            # Limpiar campos específicos de turnos cuando no es turno
            for line in self.item_detail_ids:
                line.update({
                    'operarios': 0,
                    'diurnas_semanales': 0,
                    'horas': 0,
                    'total_turno': 0
                })

    # Subtotal con mejor manejo de dependencias
    @api.depends('item_detail_ids.total', 'item_detail_ids.total_turno', 'category')
    def _compute_subtotal(self):
        if not self:
            return
        
        for record in self:
            subtotal = 0.0
            
            if record.category == 'turno':
                # Para turnos: sumar solo total_turno
                subtotal = sum(detail.total_turno for detail in record.item_detail_ids)
            else:
                # Para otras categorías: sumar solo total
                subtotal = sum(detail.total for detail in record.item_detail_ids)
            
            record.subtotal = subtotal

    @api.constrains('category')
    def _check_item_values(self):
        for record in self:
            if record.category and not record.item_detail_ids:
                # Solo validar que tenga al menos un detalle si tiene categoría
                pass  # Las validaciones específicas se hacen en los detalles
        # Método para copiar con mejor lógica
        def copy(self, default=None):
            default = dict(default or {})
            default.update({
                'name': f"{self.name} (Copia)",
                'sequence': self.sequence + 1,
            })
            return super().copy(default)

    # Unlink optimizado
    def unlink(self):
        # Verificar permisos y dependencias antes de eliminar
        if any(item.presale_order_id.state != 'draft' for item in self):
            raise ValidationError("No se pueden eliminar ítems de preventas confirmadas.")
        return super().unlink()
    
    ############# --------- TEMPLATE ---------##############
    create_item_template = fields.Boolean(
        string="¿Crear Plantilla?", 
        default=False, 
        tracking=True, 
        help="Marcar para crear una plantilla a partir de este ítem"
    )

    item_template_ids = fields.Many2one(
        'presale.order.item', 
        string="Plantilla Asociada", 
        domain=[('create_item_template', '=', True)],
        tracking=True, 
        help="Seleccionar una plantilla existente para aplicar"
    )

    is_template = fields.Boolean(
        string="Es Plantilla", 
        compute="_compute_is_template", 
        store=True,
        help="Indica si este ítem es una plantilla"
    )

    template_name = fields.Char(
        string="Nombre de Plantilla",
        help="Nombre descriptivo para la plantilla"
    )

    # MÉTODOS (agregar al final de la clase):

    @api.depends('create_item_template')
    def _compute_is_template(self):
        for record in self:
            record.is_template = record.create_item_template

    def action_apply_item_template(self):
        """Aplica la plantilla seleccionada al ítem actual"""
        for record in self:
            if not record.item_template_ids:
                raise ValidationError(
                    "Debe seleccionar una plantilla válida antes de aplicarla."
                )
            
            template = record.item_template_ids
            if not template.create_item_template:
                raise ValidationError(
                    "El ítem seleccionado no es una plantilla válida."
                )
            
            # Si ya tiene detalles, preguntar si sobrescribir
            if record.item_detail_ids:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmar Aplicación de Plantilla',
                    'res_model': 'presale.item.template.confirm.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_item_id': record.id,
                        'default_template_id': template.id,
                    }
                }
            else:
                # Aplicar directamente si no hay detalles
                record._apply_template_details(template)

    def _apply_template_details(self, template):
        """Aplica los detalles de la plantilla al ítem actual"""
        self.ensure_one()
        
        # Limpiar detalles existentes
        self.item_detail_ids.unlink()
        
        # Actualizar campos del ítem con los de la plantilla
        self.write({
            'category': template.category,
            'qty': template.qty,
            'unit_price': template.unit_price,
        })
        
        # Copiar detalles de la plantilla
        for template_detail in template.item_detail_ids:
            detail_vals = {
                'item_id': self.id,
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
        if self.presale_order_id:
            self.presale_order_id.message_post(
                body=f"Plantilla '{template.template_name or template.name}' aplicada al ítem '{self.name}'. "
                    f"Se crearon {len(template.item_detail_ids)} detalles.",
                message_type='notification'
            )

    def action_save_as_item_template(self):
        """Marca este ítem como plantilla"""
        for record in self:
            if not record.item_detail_ids:
                raise ValidationError(
                    "No se puede crear una plantilla sin detalles. "
                    "Agregue al menos un detalle antes de guardar como plantilla."
                )
            
            # Abrir wizard para configurar la plantilla
            return {
                'type': 'ir.actions.act_window',
                'name': 'Guardar Ítem como Plantilla',
                'res_model': 'presale.item.template.save.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_item_id': record.id,
                    'default_template_name': f"Plantilla - {record.name}",
                }
            }
            
    #####################################################################################

    def _apply_template_details_append(self, template):
        """Aplica los detalles de la plantilla sin eliminar los existentes"""
        self.ensure_one()
        
        # Obtener el siguiente número de secuencia
        max_sequence = max(self.item_detail_ids.mapped('sequence') or [0])
        
        # Copiar detalles de la plantilla
        details_created = 0
        for template_detail in template.item_detail_ids:
            max_sequence += 10
            
            detail_vals = {
                'item_id': self.id,
                'name': f"{template_detail.name} (Plantilla)",
                'product_id': template_detail.product_id.id,
                'qty': template_detail.qty,
                'unit_price': template_detail.unit_price,
                'sequence': max_sequence,
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
            details_created += 1
        
        # Mensaje de confirmación
        if self.presale_order_id:
            self.presale_order_id.message_post(
                body=f"Plantilla '{template.template_name or template.name}' aplicada al ítem '{self.name}'. "
                    f"Se agregaron {details_created} detalles nuevos a los {len(self.item_detail_ids) - details_created} existentes.",
                message_type='notification'
            )

    def select_item_template(self):
        """Permite seleccionar y aplicar una plantilla a la línea de pedido actual, copiando los detalles de la plantilla seleccionada."""
        for record in self:
            if not record.item_template_ids:
                raise ValidationError("Debe seleccionar una plantilla válida antes de aplicarla.")
            template = record.item_template_ids
            # Limpiar detalles existentes
            record.item_detail_ids.unlink()
            # Copiar detalles de la plantilla
            for template_detail in template.item_detail_ids:
                detail_vals = {
                    'item_id': record.id,
                    'name': template_detail.name,
                    'product_id': template_detail.product_id.id,
                    'qty': template_detail.qty,
                    'unit_price': template_detail.unit_price,
                    'sequence': template_detail.sequence,
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
            if record.presale_order_id:
                record.presale_order_id.message_post(
                    body=f"Plantilla '{template.template_name or template.name}' aplicada al ítem '{record.name}'. Se copiaron {len(template.item_detail_ids)} detalles.",
                    message_type='notification'
                )