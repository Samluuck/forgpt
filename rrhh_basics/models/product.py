from odoo import models, fields, api
from datetime import datetime


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'


    # print_format_1 = fields.Selection(selection_add=[('2x8xprice', '2 x 8 with price')],ondelete={'2x8xprice': 'set default', '2x7xprice':'set default'})
    # print_format = fields.Selection(selection_add=[('4x7xprice', 'Diseño1')],ondelete={'4x7xprice': 'set default', '4x7xprice':'set default'})
    formato_impresion= fields.Selection(selection = [('diseno_1', 'Diseño 1 (Nombre , Foto y Precio)',),('diseno_2', 'Diseño 2 (Nombre , Código de Barra  y Precio)',),('diseno_3', 'Diseño 3 (Logo y Datos de la empresa)',),('diseno_4', 'Diseño 4 (Imagen del Producto, código y Precio )',)])

    @api.onchange('formato_impresion')
    def _compute_extra(self):
        for wizard in self:
            wizard.extra_html=wizard.formato_impresion

    @api.depends('formato_impresion')
    def _compute_dimensions(self):
        for wizard in self:
            wizard.extra_html=wizard.formato_impresion
            if 'diseno_1' or 'diseno_2' or 'diseno_3' or 'diseno_4' in wizard.formato_impresion:
                columns=2
                rows = 8
                wizard.columns = int(columns)
                wizard.rows = int(rows)
            else:
                wizard.columns, wizard.rows = 1, 1





    # @api.depends('formato_impresion')
    # def _compute_dimensions(self):
    #     for wizard in self:
    #         if 'x' in wizard.print_format:
    #             columns, rows = wizard.print_format.split('x')[:2]
    #             wizard.columns = int(columns)
    #             wizard.rows = int(rows)
    #         else:
    #             wizard.columns, wizard.rows = 1, 1