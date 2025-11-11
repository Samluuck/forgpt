# -*- coding: utf-8 -*-

from odoo import models, fields, api

class F500Category(models.Model):
    _name = 'f500.category'
    _description = 'Categoría Formulario 500'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    code = fields.Char(string='Código', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    description = fields.Text(string='Descripción')
    parent_id = fields.Many2one('f500.category', string='Categoría Padre', ondelete='cascade')
    child_ids = fields.One2many('f500.category', 'parent_id', string='Sub-categorías')
    
    # Tipo de categoría
    category_type = fields.Selection([
        ('income', 'Ingreso'),
        ('cost', 'Costo'),
        ('expense', 'Gasto'),
        ('income_exclusion', 'Menos Ingreso No Gravado'),
        ('cost_exclusion', 'Menos Costo No Deducible'),
        ('expense_exclusion', 'Menos Gasto No Deducible'),
        ('adjustment', 'Ajuste'),
        ('other', 'Otro'),
    ], string='Tipo', required=True, default='other')
    
    # Operación matemática
    operation = fields.Selection([
        ('sum', 'Sumar (+)'),
        ('subtract', 'Restar (-)'),
    ], string='Operación', default='sum', required=True)
    
    # Casilla del F500
    f500_cell = fields.Char(
        string='Casilla F500',
        help='Número de casilla del Formulario 500 donde se reporta esta categoría'
    )
    
    # Rubro
    f500_section = fields.Selection([
        ('1', 'Rubro 1 - Estado de Resultados'),
        ('2', 'Rubro 2 - Transformación y Valuación de Activos'),
        ('3', 'Rubro 3 - Ajustes por Precios de Transferencia'),
        ('4', 'Rubro 4 - Resultado del Ejercicio'),
        ('5', 'Rubro 5 - Determinación de la Renta Neta y Pérdida Arrastrable'),
        ('6', 'Rubro 6 - Determinación de la Renta Neta para Beneficios Especiales'),
        ('7', 'Rubro 7 - Determinación de la Renta Presunta'),
        ('8', 'Rubro 8 - Determinación del Impuesto y Liquidación Final'),
        ('9', 'Rubro 9 - Determinación de Anticipos'),
        ('10', 'Rubro 10 - Información Complementaria'),
    ], string='Rubro F500')
    
    active = fields.Boolean(string='Activo', default=True)
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'El código de categoría debe ser único!'),
    ]

    def name_get(self):
        result = []
        for rec in self:
            if rec.f500_cell:
                name = f"[{rec.f500_cell}] {rec.name}"
            else:
                name = rec.name
            result.append((rec.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('f500_cell', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)