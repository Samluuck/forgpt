from odoo import models, fields, api

class PresaleOrderItem(models.Model):
    _name = 'presale.order.item'
    _description = 'Presale Order Item'
        
    name = fields.Char(string="Nombre del Ítem", store=True)
    presale_order_id = fields.Many2one('presale.order', string="Presale Order", ondelete="cascade")
    product_id = fields.Many2one('product.product', string="Producto")
    qty = fields.Float(string="Cant (Hrs/Personas)", default=0.0)
    unit_price = fields.Float(string="Precio")
    subtotal = fields.Float(string="Subtotal", compute="_calcular_subtotal", store=True)
    item_detail_ids = fields.One2many('presale.order.item.detail', 'item_id', string="Detalles del Ítem")
    
    # Campos booleanos por categoría
    is_equipo = fields.Boolean(string="Equipos")
    is_insumo = fields.Boolean(string="Insumos y Elementos")
    is_maquina = fields.Boolean(string="Máquinas")
    is_epi_epc = fields.Boolean(string="EPI / EPC")
    is_turno = fields.Boolean(string="Turnos")
    is_otro = fields.Boolean(string="Otros")

    # Añade force_save=True a los campos computados que se usan en la vista
    show_product_fields = fields.Boolean(compute='_compute_show_fields', store=False, force_save=True)
    show_details_fields = fields.Boolean(compute='_compute_show_fields', store=False, force_save=True)
    selected_category = fields.Char(compute='_compute_selected_category', store=False, force_save=True)

    # Asigna valor al campo name de acuerdo al check marcado (ahora mismo es deshabilitado)
    @api.depends('is_equipo', 'is_insumo', 'is_maquina', 'is_epi_epc', 'is_turno', 'is_otro')
    def _compute_name(self):
        for record in self:
            if record.is_turno:
                record.name = "Turno"
            elif record.is_equipo:
                record.name = "Equipos"
            elif record.is_insumo:
                record.name = "Insumos y Elementos"
            elif record.is_maquina:
                record.name = "Máquinas"
            elif record.is_epi_epc:
                record.name = "EPI / EPC"
            elif record.is_otro:
                record.name = "Otros"
            else:
                record.name = False

    @api.onchange('is_turno')
    def _onchange_is_turno(self):
        for record in self:
            if not record.is_turno:
                # Limpiar campos específicos de turnos cuando se deselecciona
                for line in record.item_detail_ids:
                    line.update({
                        'operarios': 0,
                        'diurnas_semanales': 0,
                        'horas': 0,
                        'total_turno': 0
                    })

    @api.depends('item_detail_ids.total')
    def _calcular_subtotal(self):
        for detalle in self:
            detalle.subtotal = sum(line.total for line in detalle.item_detail_ids)

    @api.depends('is_equipo', 'is_insumo', 'is_maquina', 'is_epi_epc', 'is_turno', 'is_otro')
    @api.onchange('is_equipo', 'is_insumo', 'is_maquina', 'is_epi_epc', 'is_turno', 'is_otro')
    def _compute_show_fields(self):
        for record in self:
            any_selected = any([
                record.is_equipo,
                record.is_insumo,
                record.is_maquina,
                record.is_epi_epc,
                record.is_turno,
                record.is_otro
            ])
            record.show_product_fields = any_selected
            record.show_details_fields = any_selected

    @api.depends('is_equipo', 'is_insumo', 'is_maquina', 'is_epi_epc', 'is_turno', 'is_otro')
    def _compute_selected_category(self):
        for record in self:
            if record.is_equipo:
                record.selected_category = "Equipos"
            elif record.is_insumo:
                record.selected_category = "Insumos y Elementos"
            elif record.is_maquina:
                record.selected_category = "Máquinas"
            elif record.is_epi_epc:
                record.selected_category = "EPI / EPC"
            elif record.is_turno:
                record.selected_category = "Turnos"
            elif record.is_otro:
                record.selected_category = "Otros"
            else:
                record.selected_category = False
                
    @api.onchange('is_equipo', 'is_insumo', 'is_maquina', 'is_epi_epc', 'is_turno', 'is_otro')
    def _onchange_categoria(self):
        for record in self:
            # Exclusividad: solo uno puede estar en True
            campos = [
                ('is_equipo', record.is_equipo),
                ('is_insumo', record.is_insumo),
                ('is_maquina', record.is_maquina),
                ('is_epi_epc', record.is_epi_epc),
                ('is_turno', record.is_turno),
                ('is_otro', record.is_otro),
            ]
            seleccionados = [k for k, v in campos if v]
            if seleccionados:
                seleccionado = seleccionados[0]
                for campo, _ in campos:
                    setattr(record, campo, campo == seleccionado)
                # Mostrar secciones al seleccionar categoría
                record.show_product_fields = True
                record.show_details_fields = True
            else:
                # Ocultar todo si no hay categoría
                record.show_product_fields = False
                record.show_details_fields = False

    @api.depends('operarios', 'diurnas_semanales', 'horas', 'unit_price')
    def _compute_total_turno(self):
        for record in self:
            if record.is_turno:
                record.total_turno = (record.operarios or 0) * (record.diurnas_semanales or 0) * (record.horas or 0) * (record.unit_price or 0)
            else:
                record.total_turno = 0.0