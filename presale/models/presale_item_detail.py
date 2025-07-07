from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

class PresaleOrderItemDetail(models.Model):
    _name = 'presale.order.item.detail'
    _description = 'Presale Order Item Detail'
    _order = 'item_id, sequence, id'

    # Campos básicos
    sequence = fields.Integer('Sequence', default=10, index=True)
    name = fields.Char(string="Nombre del Detalle", required=True, index=True, default="Nuevo detalle")
    item_id = fields.Many2one('presale.order.item', string="Item", ondelete="cascade", required=True, index=True)
    product_id = fields.Many2one('product.product', string="Producto", index=True)
    qty = fields.Float(string="Cantidad", default=1.0, digits='Product Unit of Measure')
    unit_price = fields.Float(string="Precio", digits='Product Price')
    total = fields.Float(string="Precio por uso", compute="_compute_total", store=True, digits='Product Price')
    
    # CAMPOS MANUALES PARA TURNOS
    operarios = fields.Integer(string="N° Operarios", default=1, help="Número total de operarios para el turno")
    desde = fields.Char(string="Desde", help="Hora de inicio (ej: 06:00, 15:30)")
    hasta = fields.Char(string="Hasta", help="Hora de fin (ej: 14:00, 23:30)")
    dias_semanales = fields.Float(string="Días a la semana", digits='Product Unit of Measure')
    horas_break_desde = fields.Char(string="Break desde", help="Hora de inicio del break (ej: 12:00, 18:30)")
    horas_break_hasta = fields.Char(string="Break hasta", help="Hora de fin del break (ej: 13:00, 19:00)")
    
    # CAMPOS CALCULADOS PARA TURNOS
    horas = fields.Float(
        string="Horas Totales Mensuales", 
        compute="_compute_horas_totales_mes", 
        store=True, 
        digits='Product Unit of Measure',
        help="Suma total de horas diurnas + nocturnas por mes"
    )
    
    horas_diurnas = fields.Float(
        string="Horas Diurnas Totales", 
        compute="_compute_horas_por_operarios", 
        store=True, 
        digits='Product Unit of Measure',
        help="Operarios diurnos × horas diurnas mensuales"
    )

    horas_nocturnas = fields.Float(
        string="Horas Nocturnas Totales", 
        compute="_compute_horas_por_operarios", 
        store=True, 
        digits='Product Unit of Measure',
        help="Operarios nocturnos × horas nocturnas mensuales"
    )
            
    total_turno_diurno = fields.Float(string="Total Turno Diurno", compute="_compute_totales_turno", store=True, digits='Product Price')
    total_turno_nocturno = fields.Float(string="Total Turno Nocturno", compute="_compute_totales_turno", store=True, digits='Product Price')
    total_turno = fields.Float(string="Total", compute="_compute_totales_turno", store=True, digits='Product Price')
    
    # CAMPOS DIURNOS (06:00 - 20:00)
    diurnas_semanales = fields.Float(string="Horas Diurnas Semanales", compute="_compute_horas_diurnas", store=True, digits='Product Unit of Measure')
    diurnas_mensuales = fields.Float(string="Horas Diurnas Mensuales", compute="_compute_horas_diurnas", store=True, digits='Product Unit of Measure')
    operarios_diurnos = fields.Integer(string="Operarios Diurnos", compute="_compute_operarios_por_turno", store=True)
    
    # CAMPOS NOCTURNOS (20:00 - 06:00)
    nocturnos_semanales = fields.Float(string="Horas Nocturnas Semanales", compute="_compute_horas_nocturnas", store=True, digits='Product Unit of Measure')
    nocturnas_mensuales = fields.Float(string="Horas Nocturnas Mensuales", compute="_compute_horas_nocturnas", store=True, digits='Product Price')
    operarios_nocturnos = fields.Integer(string="Operarios Nocturnos", compute="_compute_operarios_por_turno", store=True)
    
    # CAMPO PRECIO ESPECÍFICO PARA TURNOS
    precio_uso_turno = fields.Float(string="Precio por uso", digits='Product Price')
    
    # Campos computed
    show_turno_fields = fields.Boolean(compute='_compute_show_turno_fields', store=False)
    item_category = fields.Selection(related='item_id.category', store=True, readonly=True, index=True)

    @api.constrains('item_category', 'qty', 'unit_price', 'dias_semanales', 'operarios', 'desde', 'hasta')
    def _check_detail_values_by_category(self):
        for record in self:
            if record.item_category == 'turno':
                # Validaciones específicas para TURNOS
                if record.dias_semanales is not None and (record.dias_semanales <= 0 or record.dias_semanales > 7):
                    raise ValidationError(f"Los días semanales deben estar entre 1 y 7 en {record.name or 'el detalle'}")
                
                # Validar solo cuando se intenta confirmar/aprobar, no al crear
                if record.item_id and record.item_id.presale_order_id.state != 'draft':
                    if record.operarios is None or record.operarios <= 0:
                        raise ValidationError(f"Debe especificar al menos un operario en {record.name or 'el detalle'}")
                    if not record.dias_semanales or record.dias_semanales <= 0:
                        raise ValidationError(f"Debe especificar días semanales mayor que cero en {record.name or 'el detalle'}")
                    if not record.desde or not record.hasta:
                        raise ValidationError(f"Debe especificar horario desde-hasta en {record.name or 'el detalle'}")
            
            else:
                # Validaciones específicas para OTRAS CATEGORÍAS (no turno)
                if record.qty is not None and record.qty <= 0:
                    raise ValidationError(f"La cantidad debe ser mayor que cero en {record.name or 'el detalle'}")
                if record.unit_price is not None and record.unit_price < 0:
                    raise ValidationError(f"El precio debe ser mayor o igual a cero en {record.name or 'el detalle'}")
                
                # Validar solo cuando se intenta confirmar/aprobar, no al crear
                if record.item_id and record.item_id.presale_order_id.state != 'draft':
                    if not record.qty or record.qty <= 0:
                        raise ValidationError(f"La cantidad de usos debe ser mayor que cero en {record.name or 'el detalle'}")

    @api.depends('diurnas_mensuales', 'nocturnas_mensuales')
    def _compute_horas_totales_mes(self):
        """Calcula el total de horas mensuales (diurnas + nocturnas)"""
        for record in self:
            if record.item_category == 'turno':
                record.horas = (record.diurnas_mensuales or 0.0) + (record.nocturnas_mensuales or 0.0)
            else:
                record.horas = 0.0
    
    # Calculo de horas totales diurnas y nocturnas            
    @api.depends('operarios_diurnos', 'operarios_nocturnos', 'diurnas_mensuales', 'nocturnas_mensuales')
    def _compute_horas_por_operarios(self):
        """Calcula el total de horas por tipo multiplicando operarios × horas mensuales"""
        for record in self:
            if record.item_category == 'turno':
                record.horas_diurnas = (record.operarios_diurnos or 0) * (record.diurnas_mensuales or 0)
                record.horas_nocturnas = (record.operarios_nocturnos or 0) * (record.nocturnas_mensuales or 0)
            else:
                record.horas_diurnas = 0.0
                record.horas_nocturnas = 0.0

    def _parse_time(self, time_str):
        """Convierte string de tiempo (HH:MM) a horas decimales"""
        if not time_str:
            return 0.0
        
        # Limpiar string y validar formato
        time_str = time_str.strip()
        pattern = r'^(\d{1,2}):(\d{2})$'
        match = re.match(pattern, time_str)
        
        if not match:
            return 0.0
            
        hours = int(match.group(1))
        minutes = int(match.group(2))
        
        # Validar rangos
        if hours > 23 or minutes > 59:
            return 0.0
            
        return hours + (minutes / 60.0)
    
    @api.depends('operarios', 'desde', 'hasta')
    def _compute_operarios_por_turno(self):
        for record in self:
            if record.item_category != 'turno':
                record.operarios_diurnos = 0
                record.operarios_nocturnos = 0
                continue
                
            desde_decimal = record._parse_time(record.desde)
            hasta_decimal = record._parse_time(record.hasta)
            
            if desde_decimal == 0 and hasta_decimal == 0:
                record.operarios_diurnos = 0
                record.operarios_nocturnos = 0
                continue
                
            horas_diurnas, horas_nocturnas = record._calcular_distribucion_horas(desde_decimal, hasta_decimal)
            
            # Si el turno cruza ambas franjas, asignar operarios a ambos
            if horas_diurnas > 0 and horas_nocturnas > 0:
                record.operarios_diurnos = record.operarios or 0
                record.operarios_nocturnos = record.operarios or 0
            elif horas_diurnas > 0:
                record.operarios_diurnos = record.operarios or 0
                record.operarios_nocturnos = 0
            elif horas_nocturnas > 0:
                record.operarios_diurnos = 0
                record.operarios_nocturnos = record.operarios or 0
            else:
                record.operarios_diurnos = 0
                record.operarios_nocturnos = 0

    def _calcular_horas_efectivas(self, desde_decimal, hasta_decimal, break_decimal):
        """Calcula las horas efectivas de trabajo descontando el break"""
        if hasta_decimal <= desde_decimal:
            # Turno que cruza medianoche (ej: 22:00 a 06:00)
            horas_totales = (24 - desde_decimal) + hasta_decimal
        else:
            # Turno normal (ej: 06:00 a 14:00)
            horas_totales = hasta_decimal - desde_decimal
            
        return max(0, horas_totales - break_decimal)

    def _calcular_distribucion_horas(self, desde_decimal, hasta_decimal):
        """Calcula cuántas horas caen en horario diurno (6-20) y nocturno (20-6)"""
        diurno_inicio = 6.0   # 06:00
        diurno_fin = 20.0     # 20:00
        
        # Calcular total de horas del turno
        if desde_decimal <= hasta_decimal:
            # Turno normal (ej: 8:00 a 16:00)
            if desde_decimal == hasta_decimal:
                return 0.0, 0.0  # No hay horas si son iguales
            horas_totales = hasta_decimal - desde_decimal
            
            # Calcular intersección con horario diurno
            inicio_diurno = max(desde_decimal, diurno_inicio)
            fin_diurno = min(hasta_decimal, diurno_fin)
            horas_diurnas = max(0, fin_diurno - inicio_diurno)
            
            # El resto son nocturnas
            horas_nocturnas = horas_totales - horas_diurnas
            
        else:
            # Turno que cruza medianoche (ej: 18:00 a 02:00)
            horas_totales = hasta_decimal + 24 - desde_decimal
            
            # Primera parte: desde -> 24:00
            horas_parte1 = 24 - desde_decimal
            diurnas_parte1 = max(0, min(horas_parte1, diurno_fin - desde_decimal)) if desde_decimal < diurno_fin else 0
            nocturnas_parte1 = horas_parte1 - diurnas_parte1
            
            # Segunda parte: 00:00 -> hasta
            horas_parte2 = hasta_decimal
            if hasta_decimal <= diurno_inicio:
                # Todo nocturno
                diurnas_parte2 = 0
                nocturnas_parte2 = horas_parte2
            elif hasta_decimal <= diurno_fin:
                # Nocturno hasta las 6, luego diurno
                nocturnas_parte2 = diurno_inicio
                diurnas_parte2 = hasta_decimal - diurno_inicio
            else:
                # Nocturno hasta las 6, diurno hasta las 20, nocturno después
                nocturnas_parte2 = diurno_inicio + (hasta_decimal - diurno_fin)
                diurnas_parte2 = diurno_fin - diurno_inicio
            
            horas_diurnas = diurnas_parte1 + diurnas_parte2
            horas_nocturnas = nocturnas_parte1 + nocturnas_parte2
        
        return horas_diurnas, horas_nocturnas

    # Compute para mostrar campos de turno
    @api.depends('item_category')
    def _compute_show_turno_fields(self):
        for record in self:
            record.show_turno_fields = record.item_category == 'turno'

    # CÁLCULO DE HORAS DIURNAS
    @api.depends('desde', 'hasta', 'horas_break_desde', 'horas_break_hasta', 'dias_semanales')
    def _compute_horas_diurnas(self):
        for record in self:
            if record.item_category != 'turno':
                record.diurnas_semanales = 0.0
                record.diurnas_mensuales = 0.0
                continue
                
            desde_decimal = record._parse_time(record.desde)
            hasta_decimal = record._parse_time(record.hasta)
            break_desde_decimal = record._parse_time(record.horas_break_desde)
            break_hasta_decimal = record._parse_time(record.horas_break_hasta)
            
            if desde_decimal == 0 and hasta_decimal == 0:
                record.diurnas_semanales = 0.0
                record.diurnas_mensuales = 0.0
                continue
                
            horas_diurnas, _ = record._calcular_distribucion_horas(desde_decimal, hasta_decimal)
            
            # Descontar break específico del horario diurno
            if break_desde_decimal and break_hasta_decimal:
                break_diurno = record._calcular_break_en_franja(
                    break_desde_decimal, break_hasta_decimal, 6.0, 20.0
                )
                horas_diurnas = max(0, horas_diurnas - break_diurno)
            
            record.diurnas_semanales = horas_diurnas * (record.dias_semanales or 0)
            record.diurnas_mensuales = record.diurnas_semanales * 4.2

    # CÁLCULO DE HORAS NOCTURNAS
    @api.depends('desde', 'hasta', 'horas_break_desde', 'horas_break_hasta', 'dias_semanales')
    def _compute_horas_nocturnas(self):
        for record in self:
            if record.item_category != 'turno':
                record.nocturnos_semanales = 0.0
                record.nocturnas_mensuales = 0.0
                continue
                
            desde_decimal = record._parse_time(record.desde)
            hasta_decimal = record._parse_time(record.hasta)
            break_desde_decimal = record._parse_time(record.horas_break_desde)
            break_hasta_decimal = record._parse_time(record.horas_break_hasta)
            
            if desde_decimal == 0 and hasta_decimal == 0:
                record.nocturnos_semanales = 0.0
                record.nocturnas_mensuales = 0.0
                continue
                
            _, horas_nocturnas = record._calcular_distribucion_horas(desde_decimal, hasta_decimal)
            
            # Descontar break específico del horario nocturno
            if break_desde_decimal and break_hasta_decimal:
                # Para nocturno: 20:00-06:00 (dividido en 20-24 y 00-06)
                break_nocturno_tarde = record._calcular_break_en_franja(
                    break_desde_decimal, break_hasta_decimal, 20.0, 24.0
                )
                break_nocturno_madrugada = record._calcular_break_en_franja(
                    break_desde_decimal, break_hasta_decimal, 0.0, 6.0
                )
                break_nocturno_total = break_nocturno_tarde + break_nocturno_madrugada
                horas_nocturnas = max(0, horas_nocturnas - break_nocturno_total)
            
            record.nocturnos_semanales = horas_nocturnas * (record.dias_semanales or 0)
            record.nocturnas_mensuales = record.nocturnos_semanales * 4.2


    # CÁLCULO DE OPERARIOS POR TURNO
    def _calcular_break_en_franja(self, break_desde, break_hasta, franja_inicio, franja_fin):
        """
        Calcula cuántas horas del break caen dentro de una franja horaria específica
        """
        if break_hasta <= break_desde:
            # Break que cruza medianoche
            if franja_inicio == 0.0 and franja_fin == 6.0:
                # Franja madrugada (00:00-06:00)
                inicio_overlap = max(0.0, min(break_hasta, franja_fin))
                return max(0, inicio_overlap - 0.0)
            elif franja_inicio == 20.0 and franja_fin == 24.0:
                # Franja noche (20:00-24:00)
                fin_overlap = min(24.0, max(break_desde, franja_inicio))
                return max(0, 24.0 - fin_overlap)
            else:
                # Franja diurna (06:00-20:00)
                if break_desde < franja_fin:
                    return max(0, min(franja_fin, 24.0) - max(break_desde, franja_inicio))
                return 0.0
        else:
            # Break normal (no cruza medianoche)
            inicio_overlap = max(break_desde, franja_inicio)
            fin_overlap = min(break_hasta, franja_fin)
            return max(0, fin_overlap - inicio_overlap)
    
    # CÁLCULO DE TOTALES DE TURNO
    @api.depends('operarios_diurnos', 'operarios_nocturnos', 'diurnas_semanales', 'nocturnos_semanales', 'precio_uso_turno')
    def _compute_totales_turno(self):
        for record in self:
            if record.item_category != 'turno':
                record.total_turno_diurno = 0.0
                record.total_turno_nocturno = 0.0
                record.total_turno = 0.0
                continue
                
            precio = record.precio_uso_turno or 0.0
            
            record.total_turno_diurno = (record.operarios_diurnos or 0) * (record.diurnas_mensuales or 0) * precio
            record.total_turno_nocturno = (record.operarios_nocturnos or 0) * (record.nocturnas_mensuales or 0) * (precio * 1.3)
            record.total_turno = record.total_turno_diurno + record.total_turno_nocturno

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Actualiza unit_price, qty y name cuando se selecciona un producto"""
        if self.product_id:
            values = {}
            template = self.product_id.product_tmpl_id
            
            # Autocompletar nombre si está vacío o es el default
            if not self.name or self.name == "Nuevo detalle":
                values['name'] = self.product_id.name
            
            # Para categoría turno: autocompletar precio_uso_turno
            if self.item_category == 'turno':
                if self.product_id.standard_price > 0 and not self.precio_uso_turno:
                    values['precio_uso_turno'] = self.product_id.standard_price
            else:
                # Para otras categorías: autocompletar unit_price y qty
                if self.product_id.standard_price > 0 and not self.unit_price:
                    values['unit_price'] = self.product_id.standard_price
                
                if hasattr(template, 'qty_per_use'):
                    template_qty = template.qty_per_use
                    if template_qty > 0 and self.qty == 1.0:
                        values['qty'] = template_qty
            
            if values:
                self.update(values)

    # Create con batch processing
    @api.model_create_multi
    def create(self, vals_list):
        """Autocompleta qty y unit_price al crear registros en batch"""
        product_ids = list(set(vals.get('product_id') for vals in vals_list if vals.get('product_id')))
        products_data = {}
        
        if product_ids:
            products = self.env['product.product'].browse(product_ids)
            for product in products:
                template = product.product_tmpl_id
                products_data[product.id] = {
                    'standard_price': product.standard_price,
                    'qty_per_use': getattr(template, 'qty_per_use', 0.0)
                }
        
        for vals in vals_list:
            if vals.get('product_id') and vals['product_id'] in products_data:
                product_data = products_data[vals['product_id']]
                
                # Obtener categoría del ítem padre
                item_category = None
                if vals.get('item_id'):
                    item = self.env['presale.order.item'].browse(vals['item_id'])
                    item_category = item.category
                
                if item_category == 'turno':
                    # Para turnos: autocompletar precio_uso_turno
                    if 'precio_uso_turno' not in vals and product_data['standard_price'] > 0:
                        vals['precio_uso_turno'] = product_data['standard_price']
                else:
                    # Para otras categorías: autocompletar qty y unit_price
                    if 'qty' not in vals and product_data['qty_per_use'] > 0:
                        vals['qty'] = product_data['qty_per_use']
                    if 'unit_price' not in vals and product_data['standard_price'] > 0:
                        vals['unit_price'] = product_data['standard_price']
        
        return super().create(vals_list)
    
    # Total con mejor lógica condicional
    @api.depends('qty', 'unit_price', 'item_category', 'product_id.mul_divi')
    def _compute_total(self):
        for record in self:
            if record.qty and record.qty != 0:
                if record.item_category == 'equipo':
                    record.total = record.unit_price / record.qty
                elif record.item_category == 'insumo':
                    record.total = record.unit_price * record.qty
                elif record.item_category == 'maquina':               
                    record.total = record.unit_price / record.qty
                elif record.item_category == 'epi_epc':
                    # Para EPI/EPC: usar configuración del producto
                    if record.product_id and record.product_id.product_tmpl_id.mul_divi:
                        if record.product_id.product_tmpl_id.mul_divi == 'multiplicar':
                            record.total = record.unit_price * record.qty
                        else:  # 'dividir'
                            record.total = record.unit_price / record.qty
                    else:
                        # Default: dividir si no está configurado
                        record.total = record.unit_price / record.qty
                elif record.item_category == 'otro':
                    record.total = record.unit_price / record.qty
                elif record.item_category == 'turno':
                    record.total = 0  # Para turnos usamos total_turno por eso ponemos 0 aca
                else:
                    record.total = 0.0
            else:
                record.total = 0.0

    @api.constrains('item_category', 'desde', 'hasta', 'horas_break_desde', 'horas_break_hasta', 'dias_semanales')
    def _check_time_format(self):
        for record in self:
            if record.item_category == 'turno':
                # Validar formato de tiempo
                time_fields = [
                    ('desde', record.desde), 
                    ('hasta', record.hasta), 
                    ('horas_break_desde', record.horas_break_desde),
                    ('horas_break_hasta', record.horas_break_hasta)
                ]
                
                for field_name, field_value in time_fields:
                    if field_value:  # Solo validar si el campo tiene valor
                        field_value = str(field_value).strip()
                        if not re.match(r'^\d{1,2}:\d{2}$', field_value):
                            raise ValidationError(f"El campo {field_name} debe tener formato HH:MM (ej: 08:30)")
                
                # Validar que desde y hasta sean obligatorios
                if not record.desde:
                    raise ValidationError("El campo 'desde' es obligatorio para turnos")
                if not record.hasta:
                    raise ValidationError("El campo 'hasta' es obligatorio para turnos")
                
                # Validar lógica del break
                if record.horas_break_desde and record.horas_break_hasta:
                    break_desde = record._parse_time(record.horas_break_desde)
                    break_hasta = record._parse_time(record.horas_break_hasta)
                    
                    if break_desde == break_hasta:
                        raise ValidationError("Las horas de break desde y hasta no pueden ser iguales")
                elif record.horas_break_desde or record.horas_break_hasta:
                    raise ValidationError("Si especifica break, debe completar tanto 'desde' como 'hasta'")
                
                # ADVERTENCIA para días semanales
                if record.dias_semanales and record.dias_semanales > 7:
                    raise ValidationError("Los días semanales no pueden ser mayor a 7")
                
    @api.onchange('dias_semanales')
    def _onchange_dias_semanales(self):
        if self.dias_semanales and self.dias_semanales > 7:
            return {
                'warning': {
                    'title': 'Advertencia',
                    'message': 'Los días semanales no pueden ser mayor a 7. Se ajustará automáticamente.'
                }
            }

    @api.onchange('horas_break_desde', 'horas_break_hasta')
    def _onchange_break_hours(self):
        if self.horas_break_desde and self.horas_break_hasta:
            desde = self._parse_time(self.horas_break_desde)
            hasta = self._parse_time(self.horas_break_hasta)
            
            if desde == hasta:
                return {
                    'warning': {
                        'title': 'Advertencia',
                        'message': 'Las horas de break desde y hasta no pueden ser iguales.'
                    }
                }

    @api.constrains('item_category', 'operarios', 'dias_semanales', 'desde', 'hasta')
    def _check_detail_values(self):
        for record in self:
            if record.item_category == 'turno':
                # Validar solo cuando se intenta confirmar/aprobar, no al crear
                if record.item_id and record.item_id.presale_order_id.state != 'draft':
                    if record.operarios is None or record.operarios <= 0:  # Cambio aquí
                        raise ValidationError(f"Debe especificar al menos un operario en {record.name or 'el detalle'}")
                    if not record.dias_semanales or record.dias_semanales <= 0:
                        raise ValidationError(f"Debe especificar días semanales mayor que cero en {record.name or 'el detalle'}")
                    if not record.desde or not record.hasta:
                        raise ValidationError(f"Debe especificar horario desde-hasta en {record.name or 'el detalle'}")
            else:
                # Para otras categorías, validar solo cuando no está en borrador
                if record.item_id and record.item_id.presale_order_id.state != 'draft':
                    if not record.qty or record.qty <= 0:
                        raise ValidationError(f"La cantidad de usos debe ser mayor que cero en {record.name or 'el detalle'}")

    # Método para calcular costo total por tipo
    def get_total_cost(self):
        """Retorna el costo total según el tipo de ítem"""
        self.ensure_one()
        if self.item_category == 'turno':
            return self.total_turno
        else:
            return self.total

    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'name': f"{self.name} (Copia)",
            'sequence': self.sequence + 1,
        })
        return super().copy(default)

    # Write para validar cambios
    def write(self, vals):
        if any(detail.item_id.presale_order_id.state != 'draft' for detail in self):
            readonly_fields = {'product_id', 'qty', 'unit_price', 'operarios', 'precio_uso_turno'}
            if readonly_fields.intersection(vals.keys()):
                raise ValidationError("No se pueden modificar datos de costos en preventas confirmadas.")
        return super().write(vals)