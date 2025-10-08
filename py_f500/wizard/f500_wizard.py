# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import xlsxwriter
import base64
from io import BytesIO
from datetime import datetime


class F500Wizard(models.TransientModel):
    _name = 'f500.wizard'
    _description = 'Wizard para generar Formulario 500 IRE'

    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    date_from = fields.Date(string='Fecha Desde', required=True, default=lambda self: fields.Date.today().replace(month=1, day=1))
    date_to = fields.Date(string='Fecha Hasta', required=True, default=lambda self: fields.Date.today().replace(month=12, day=31))
    exercise_year = fields.Char(string='Ejercicio Fiscal', compute='_compute_exercise_year', store=True)

    # Tipo de declaración
    declaration_type = fields.Selection([
        ('01', 'Declaración Jurada Original'),
        ('02', 'Declaración Jurada Rectificativa'),
        ('05', 'Declaración Jurada en Carácter de Cese de Actividades, Clausura o Cierre Definitivo')
    ], string='Tipo de Declaración', default='01', required=True)

    rectified_order = fields.Char(string='Número de Orden de Declaración que rectifica')

    # Datos de identificación
    ruc = fields.Char(string='RUC', related='company_id.vat', readonly=True)
    razon_social = fields.Char(string='Razón Social', related='company_id.name', readonly=True)

    # Información complementaria
    contador_ruc = fields.Char(string='RUC/CI del Contador')
    auditor_ruc = fields.Char(string='RUC del Auditor')
    total_empleados = fields.Integer(string='Total de Empleados')

    # Archivo generado
    file_data = fields.Binary(string='Archivo Excel', readonly=True)
    file_name = fields.Char(string='Nombre del Archivo', readonly=True)
    state = fields.Selection([('draft', 'Borrador'), ('done', 'Generado')], default='draft')

    @api.depends('date_from')
    def _compute_exercise_year(self):
        for rec in self:
            if rec.date_from:
                rec.exercise_year = str(rec.date_from.year)
            else:
                rec.exercise_year = str(fields.Date.today().year)

    def _get_account_balance(self, account_codes, date_from, date_to):
        """
        Obtiene el saldo de cuentas contables por código
        """
        if not account_codes:
            return 0.0

        domain = [
            ('account_id.code', 'in', account_codes),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('company_id', '=', self.company_id.id),
            ('parent_state', '=', 'posted'),
        ]

        moves = self.env['account.move.line'].search(domain)
        return sum(moves.mapped('balance'))

    def _get_income_data(self):
        """
        Obtiene datos de ingresos para el Rubro 1
        """
        data = {}

        # Casillas 10-23: Ingresos por tipo
        data['10'] = abs(self._get_account_balance(['701', '7011', '7012'], self.date_from, self.date_to))
        data['11'] = abs(self._get_account_balance(['704', '7041', '7042'], self.date_from, self.date_to))
        data['12'] = abs(self._get_account_balance(['702', '7021'], self.date_from, self.date_to))
        data['13'] = abs(self._get_account_balance(['7031', '7032'], self.date_from, self.date_to))
        data['14'] = abs(self._get_account_balance(['7033'], self.date_from, self.date_to))
        data['15'] = abs(self._get_account_balance(['7034'], self.date_from, self.date_to))
        data['16'] = abs(self._get_account_balance(['771', '772'], self.date_from, self.date_to))
        data['17'] = abs(self._get_account_balance(['773'], self.date_from, self.date_to))
        data['18'] = abs(self._get_account_balance(['709', '751', '752'], self.date_from, self.date_to))
        data['19'] = abs(self._get_account_balance(['774'], self.date_from, self.date_to))
        data['20'] = abs(self._get_account_balance(['775'], self.date_from, self.date_to))
        data['21'] = 0
        data['22'] = 0
        data['23'] = abs(self._get_account_balance(['776'], self.date_from, self.date_to))

        # Casilla 24: Devoluciones y descuentos
        data['24'] = abs(self._get_account_balance(['708'], self.date_from, self.date_to))

        # Casillas 25-31: Menos ingresos no gravados
        data['25'] = 0  # Zonas Francas
        data['26'] = 0  # Maquila
        data['27'] = 0  # Fuente extranjera no gravados
        data['28'] = 0  # Operaciones internacionales presunto
        data['29'] = 0  # Forestación inmuebles presunto
        data['30'] = 0  # Régimen especial
        data['31'] = abs(self._get_account_balance(['7081', '7082'], self.date_from, self.date_to))  # Exentos

        return data

    def _get_costs_data(self):
        """
        Obtiene datos de costos
        """
        data = {}

        # Total de costos
        total_costs = abs(self._get_account_balance(
            ['601', '602', '603', '604', '605', '606', '607', '608', '609'],
            self.date_from, self.date_to
        ))
        data['80'] = total_costs

        # Menos: costos no deducibles
        data['32'] = 0  # Zonas Francas
        data['33'] = 0  # Maquila
        data['34'] = 0  # Fuente extranjera no gravados
        data['35'] = 0  # Operaciones internacionales presunto
        data['36'] = 0  # Forestación inmuebles presunto
        data['37'] = 0  # Régimen especial
        data['38'] = 0  # Ingresos no gravados
        data['39'] = 0  # Otros costos no deducibles

        return data

    def _get_expenses_data(self):
        """
        Obtiene datos de gastos deducibles
        """
        data = {}

        # Casillas 40-65: Gastos deducibles
        data['40'] = abs(self._get_account_balance(['621', '6211'], self.date_from, self.date_to))
        data['41'] = abs(self._get_account_balance(['6212'], self.date_from, self.date_to))
        data['42'] = abs(self._get_account_balance(['6213'], self.date_from, self.date_to))
        data['43'] = abs(self._get_account_balance(['6214'], self.date_from, self.date_to))
        data['44'] = abs(self._get_account_balance(['6221', '6222'], self.date_from, self.date_to))
        data['45'] = abs(self._get_account_balance(['6223'], self.date_from, self.date_to))
        data['46'] = abs(self._get_account_balance(['641', '6411'], self.date_from, self.date_to))
        data['47'] = abs(self._get_account_balance(['642', '6421'], self.date_from, self.date_to))
        data['48'] = abs(self._get_account_balance(['643', '6431'], self.date_from, self.date_to))
        data['49'] = abs(self._get_account_balance(['661', '6611'], self.date_from, self.date_to))
        data['50'] = 0
        data['51'] = abs(self._get_account_balance(['6511'], self.date_from, self.date_to))
        data['52'] = abs(self._get_account_balance(['6811', '6812'], self.date_from, self.date_to))
        data['53'] = abs(self._get_account_balance(['6821'], self.date_from, self.date_to))
        data['54'] = 0
        data['55'] = abs(self._get_account_balance(['6791'], self.date_from, self.date_to))
        data['56'] = abs(self._get_account_balance(['6851'], self.date_from, self.date_to))
        data['57'] = abs(self._get_account_balance(['676'], self.date_from, self.date_to))
        data['58'] = 0
        data['59'] = 0
        data['60'] = abs(self._get_account_balance(['631', '632', '633', '644', '645', '646'], self.date_from, self.date_to))
        data['61'] = 0
        data['62'] = 0
        data['63'] = 0
        data['64'] = 0
        data['65'] = abs(self._get_account_balance(['671', '672', '673'], self.date_from, self.date_to))

        # Casillas 66-74: Menos gastos no deducibles
        data['66'] = 0  # Zonas Francas
        data['67'] = 0  # Maquila
        data['68'] = 0  # Fuente extranjera no gravados
        data['69'] = 0  # Operaciones internacionales presunto
        data['70'] = 0  # Forestación inmuebles presunto
        data['71'] = 0  # Régimen especial
        data['72'] = 0  # IRE
        data['73'] = 0  # Ingresos no gravados
        data['74'] = 0  # Otros gastos no deducibles

        # Casilla 75: Intereses, regalías entre vinculadas
        data['75'] = abs(self._get_account_balance(['6612'], self.date_from, self.date_to))

        return data

    def _create_excel_file(self, data_income, data_costs, data_expenses):
        """
        Crea el archivo Excel COMPLETO del Formulario 500 oficial
        """
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Formulario 500')

        # === CONFIGURACIÓN GENERAL DE HOJA ===
        worksheet.set_paper(9)  # A4
        worksheet.set_margins(left=0.4, right=0.4, top=0.5, bottom=0.5)
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 0)
        worksheet.set_default_row(18)

        # === PALETA DE COLORES ===
        color_primary = '#28969A'
        color_primary_light = '#CCE8E9'
        color_border = '#28969A'
        color_note = '#F4F8F9'

        base_font = {
            'font_name': 'Arial',
            'font_size': 9,
        }

        fmt_header = workbook.add_format({
            **base_font,
            'bg_color': color_primary,
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1,
            'border_color': color_border,
        })

        fmt_cell = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True,
        })

        fmt_label = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 8,
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True,
        })

        fmt_code = workbook.add_format({
            **base_font,
            'bg_color': color_primary,
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': color_border,
        })

        fmt_col_header = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 8,
            'align': 'center',
            'valign': 'vcenter',
            'bold': True,
            'bg_color': color_primary_light,
            'text_wrap': True,
        })

        fmt_number = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 9,
            'num_format': '#,##0',
            'align': 'right',
            'valign': 'vcenter',
        })

        fmt_section = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 9,
            'bold': True,
            'bg_color': color_primary,
            'font_color': 'white',
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True,
        })

        fmt_subsection = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 9,
            'bold': True,
            'bg_color': color_primary_light,
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True,
        })

        fmt_total = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 9,
            'bold': True,
            'bg_color': color_primary_light,
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True,
        })

        fmt_number_total = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 9,
            'bold': True,
            'bg_color': color_primary_light,
            'num_format': '#,##0',
            'align': 'right',
            'valign': 'vcenter',
        })

        fmt_blank = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 9,
            'bg_color': 'white',
        })

        fmt_note = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 8,
            'align': 'left',
            'valign': 'top',
            'text_wrap': True,
            'bg_color': color_note,
        })

        fmt_center = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 8,
            'align': 'center',
            'valign': 'vcenter',
        })

        fmt_center_bold = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 9,
            'align': 'center',
            'valign': 'vcenter',
            'bold': True,
            'bg_color': color_primary_light,
            'text_wrap': True,
        })

        fmt_field_label = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'align': 'left',
            'valign': 'vcenter',
            'bold': True,
        })

        fmt_field_label_center = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'align': 'center',
            'valign': 'vcenter',
            'bold': True,
        })

        fmt_white_center = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': 'white',
        })

        fmt_logo_text = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'font_size': 11,
            'bold': True,
        })

        fmt_logo_number = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'font_size': 28,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
        })

        fmt_checkbox = workbook.add_format({
            **base_font,
            'border': 1,
            'border_color': color_border,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': 'white',
        })

                                # Definición de columnas principales
        worksheet.set_column('A:A', 18)
        worksheet.set_column('B:B', 6)
        worksheet.set_column('C:C', 5)
        worksheet.set_column('D:D', 18)
        worksheet.set_column('E:E', 18)
        worksheet.set_column('F:F', 18)
        worksheet.set_column('G:G', 18)
        worksheet.set_column('H:I', 7)
        worksheet.set_column('J:K', 7)

        for idx, height in {
            0: 24,
            1: 20,
            2: 24,
            3: 20,
            4: 24,
            5: 20,
            6: 22,
            7: 24,
            8: 24,
            9: 24,
            10: 22,
            11: 22,
            12: 22,
        }.items():
            worksheet.set_row(idx, height)

        col_code = 1
        col_check = 2
        col_desc_start = 3
        col_desc_end = 6
        col_desc = col_desc_start
        col_amount_start = 7
        col_amount_end = 8
        col_total_start = 9
        col_total_end = 10

        col_amount = col_amount_start
        col_total = col_total_end

        def blank_code_area(r, fmt=fmt_blank):
            worksheet.write_blank(r, col_code, None, fmt)
            worksheet.write_blank(r, col_check, None, fmt)

        def write_code_cell(r, code):
            worksheet.write(r, col_code, str(code), fmt_code)
            worksheet.write_blank(r, col_check, None, fmt_checkbox)

        def write_desc_cell(r, text, fmt=fmt_label):
            worksheet.merge_range(r, col_desc_start, r, col_desc_end, text, fmt)

        def blank_desc_cell(r, fmt=fmt_blank):
            write_desc_cell(r, '', fmt)

        def write_amount_cell(r, value, fmt=fmt_number):
            worksheet.merge_range(r, col_amount_start, r, col_amount_end, value, fmt)

        def write_total_cell(r, value, fmt=fmt_number):
            worksheet.merge_range(r, col_total_start, r, col_total_end, value, fmt)

        def blank_amount_cell(r, fmt=fmt_blank):
            worksheet.merge_range(r, col_amount_start, r, col_amount_end, '', fmt)

        def blank_total_cell(r, fmt=fmt_blank):
            worksheet.merge_range(r, col_total_start, r, col_total_end, '', fmt)

        # === ENCABEZADO ===
        row = 0
        worksheet.merge_range(row, col_code, row, col_desc_end, 'PARA LLENAR LEA EL INSTRUCTIVO DISPONIBLE EN LA WEB', fmt_header)
        worksheet.merge_range(row, col_amount_start, row, col_total_end, 'LOS IMPORTES SE CONSIGNARÁN SIN CÉNTIMOS', fmt_header)
        row += 1

        worksheet.merge_range(row, col_code, row, col_desc_end, 'Número de Orden', fmt_field_label)
        worksheet.merge_range(row, col_amount_start, row, col_amount_end, 'RUC', fmt_field_label_center)
        worksheet.merge_range(row, col_total_start, row, col_total_end, 'DV', fmt_field_label_center)
        row += 1

        blank_desc_cell(row)
        worksheet.merge_range(row, col_amount_start, row, col_amount_end, '', fmt_white_center)
        worksheet.merge_range(row, col_total_start, row, col_total_end, '', fmt_white_center)
        row += 1

        worksheet.merge_range(row, col_code, row, col_desc_end, 'Razón Social/Primer Apellido', fmt_field_label)
        worksheet.merge_range(row, col_amount_start, row, col_total_end, 'Segundo Apellido', fmt_field_label_center)
        row += 1

        blank_desc_cell(row)
        blank_amount_cell(row)
        blank_total_cell(row)
        row += 1

        worksheet.merge_range(row, col_code, row, col_desc_end, 'Nombres', fmt_field_label)
        worksheet.merge_range(row, col_amount_start, row + 1, col_amount_start, '03', fmt_code)
        worksheet.merge_range(row, col_amount_end, row, col_total_end, 'Número de Orden de Declaración que rectifica', fmt_field_label)
        row += 1

        blank_desc_cell(row)
        worksheet.merge_range(row, col_amount_end, row, col_total_end, self.rectified_order or '', fmt_white_center)
        row += 1

        option_rows = [
            ('01', 'Declaración Jurada Original'),
            ('02', 'Declaración Jurada Rectificativa'),
            ('05', 'Declaración Jurada en Carácter de Cese de Actividades, Clausura o Cierre Definitivo'),
        ]
        option_start = row
        for code, label in option_rows:
            write_code_cell(row, code)
            write_desc_cell(row, label)
            row += 1
        option_end = row - 1

        worksheet.merge_range(option_start, col_amount_start, option_end, col_amount_start, '04', fmt_code)
        worksheet.merge_range(option_start, col_amount_end, option_start, col_total_end, 'Periodo / Ejercicio Fiscal', fmt_field_label_center)
        worksheet.merge_range(option_start + 1, col_amount_end, option_start + 1, col_total_end, 'Año', fmt_field_label_center)

        digits_row = option_start + 2
        exercise_digits = (self.exercise_year or '').strip()
        exercise_digits = exercise_digits[-4:] if exercise_digits else ''
        exercise_digits = exercise_digits.rjust(4, ' ')
        for idx, col in enumerate(range(col_amount_end, col_total_end + 1)):
            char = exercise_digits[idx] if idx < len(exercise_digits) else ''
            worksheet.write(digits_row, col, '' if char == ' ' else char, fmt_white_center)

        row = option_end + 1

        # === RUBRO 1 - ESTADO DE RESULTADOS ===
# === RUBRO 1 - ESTADO DE RESULTADOS ===
        # Ingresos (10-23)
        income_items = [
            (10, 'Enajenación de bienes provenientes de la actividad comercial (compra-venta)'),
            (11, 'Prestación de servicios, incluido el arrendamiento, uso o cesión de uso de bienes, derechos en general, incluidos los de imagen o similares'),
            (12, 'Enajenación de bienes provenientes de la producción industrial (fabricación propia, incluido el ensamblaje de bienes)'),
            (13, 'Enajenación de bienes provenientes de la producción agrícola, frutícola y hortícola'),
            (14, 'Enajenación de bienes provenientes de la producción animal (lana, cuero, leche cruda, entre otros) o pecuaria (vacuna, equina, porcina, ovina, caprina, bufalina, entre otros)'),
            (15, 'Enajenación de bienes provenientes de la actividad forestal, minera, pesquera y otras de naturaleza extractiva'),
            (16, 'Intereses, comisiones, rendimientos o ganancias de capital provenientes de títulos y de valores mobiliarios; así como los provenientes de financiaciones o préstamos efectuados a personas o entidades residentes o constituidas en el país'),
            (17, 'Operaciones con instrumentos financieros derivados en el país'),
            (18, 'Otros Ingresos en el país no comprendidos en los incisos anteriores'),
            (19, 'Intereses, comisiones, rendimientos o ganancias de capital depositados en entidades bancarias o financieras públicas o privadas en el exterior; así como los provenientes de financiaciones o préstamos realizados a favor de personas o entidades del exterior'),
            (20, 'Colocación de capitales (dividendos, utilidades o rendimientos que se obtengan en carácter de dueño de la sucursal en el exterior, socio o accionista de sociedades del exterior)'),
            (21, 'Operaciones con instrumentos financieros derivados del exterior'),
            (22, 'Otros Ingresos del exterior no comprendidos en los incisos anteriores'),
            (23, 'Diferencia de cambio'),
        ]

        total_77 = 0
        for casilla, descripcion in income_items:
            write_code_cell(row, casilla)
            
            write_desc_cell(row, descripcion, fmt_label)
            valor = data_income.get(str(casilla), 0)
            write_amount_cell(row, valor, fmt_number)
            blank_total_cell(row)
            total_77 += valor
            row += 1

        # Casilla 77
        write_desc_cell(row, 'TOTAL DE INGRESOS BRUTOS (Sumatoria de las casillas 10 al 23)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, total_77, fmt_number_total)
        row += 1

        # Casilla 24
        write_desc_cell(row, 'Menos: Devoluciones, bonificaciones, descuentos otorgados u otros conceptos similares', fmt_label)
        write_code_cell(row, 24)
        
        val_24 = data_income.get('24', 0)
        write_amount_cell(row, val_24, fmt_number)
        blank_total_cell(row)
        row += 1

        # Casilla 78: A- TOTAL DE INGRESOS NETOS
        total_78 = total_77 - val_24
        write_desc_cell(row, 'A- TOTAL DE INGRESOS NETOS (Diferencia entre las casillas 77 y 24)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, total_78, fmt_number_total)
        row += 1

        # Casillas 25-31
        exclusion_items = [
            (25, 'Menos: Ingresos por operaciones de exportación a terceros países realizadas por usuarios de Zonas Francas'),
            (26, 'Menos: Ingresos por operaciones de exportación a terceros países por el Régimen de Maquila'),
            (27, 'Menos: Ingresos de fuente extranjera no gravados'),
            (28, 'Menos: Ingresos obtenidos en operaciones internacionales alcanzadas por el Régimen Presunto'),
            (29, 'Menos: Ingresos obtenidos de actividades de forestación y enajenación de inmuebles urbanos y rurales alcanzados por el Régimen Presunto'),
            (30, 'Menos: Ingresos obtenidos de actividades de comercialización de productos establecidos en el Régimen Especial'),
            (31, 'Menos: Ingresos no gravados por el IRE, exentos y exonerados'),
        ]

        total_exclusions = 0
        for casilla, descripcion in exclusion_items:
            write_code_cell(row, casilla)
            
            write_desc_cell(row, descripcion, fmt_label)
            valor = data_income.get(str(casilla), 0)
            write_amount_cell(row, valor, fmt_number)
            blank_total_cell(row)
            total_exclusions += valor
            row += 1

        # Casilla 79: B- TOTAL DE INGRESOS NETOS GRAVADOS
        total_79 = total_78 - total_exclusions
        write_desc_cell(row, 'B- TOTAL DE INGRESOS NETOS GRAVADOS (Diferencia entre la casilla 78 y el resultado de la sumatoria de las casillas 25 al 31)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, total_79, fmt_number_total)
        row += 1

        # === COSTOS ===
        write_desc_cell(row, 'COSTOS', fmt_col_header)
        blank_code_area(row, fmt_col_header)
        
        write_amount_cell(row, 'IMPORTE\n-I-', fmt_col_header)
        write_total_cell(row, 'TOTAL\n-II-', fmt_col_header)
        row += 1

        # Casilla 80: C- TOTAL DE COSTOS
        total_80 = data_costs.get('80', 0)
        write_desc_cell(row, 'C- TOTAL DE COSTOS', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, total_80, fmt_number_total)
        row += 1

        # Casillas 32-39: Menos costos no deducibles
        cost_exclusions = [
            (32, 'Menos: Costos relacionados a los ingresos por operaciones realizadas por usuarios de Zonas Francas'),
            (33, 'Menos: Costos relacionados a los ingresos por operaciones realizadas en el Régimen de Maquila'),
            (34, 'Menos: Costos relacionados a ingresos de fuente extranjera no gravados'),
            (35, 'Menos: Costos relacionados a ingresos gravados obtenidos en operaciones internacionales alcanzadas por el Régimen Presunto'),
            (36, 'Menos: Costos relacionados a ingresos gravados obtenidos de actividades de forestación o enajenación de inmuebles urbanos y rurales alcanzados por el Régimen Presunto'),
            (37, 'Menos: Costos relacionados a ingresos gravados obtenidos de actividades de comercialización de productos establecidos en el Régimen Especial'),
            (38, 'Menos: Costos relacionados a ingresos no gravados por el IRE, exentos y exonerados'),
            (39, 'Menos: Otros costos no deducibles del IRE'),
        ]

        total_cost_exclusions = 0
        for casilla, descripcion in cost_exclusions:
            write_code_cell(row, casilla)
            
            write_desc_cell(row, descripcion, fmt_label)
            valor = data_costs.get(str(casilla), 0)
            write_amount_cell(row, valor, fmt_number)
            blank_total_cell(row)
            total_cost_exclusions += valor
            row += 1

        # Casilla 81: D- TOTAL DE COSTOS DEDUCIBLES
        total_81 = total_80 - total_cost_exclusions
        write_desc_cell(row, 'D- TOTAL DE COSTOS DEDUCIBLES (Diferencia entre la casilla 80 y el resultado de la sumatoria de las casillas 32 al 39)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, total_81, fmt_number_total)
        row += 1

        # Casilla 82: E- RENTA BRUTA
        total_82 = total_79 - total_81
        write_desc_cell(row, 'E- RENTA BRUTA (Diferencia entre las casillas 79 y 81)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, total_82, fmt_number_total)
        row += 1

        # === GASTOS ===
        write_desc_cell(row, 'GASTOS', fmt_col_header)
        blank_code_area(row, fmt_col_header)
        
        write_amount_cell(row, 'IMPORTE\n-I-', fmt_col_header)
        write_total_cell(row, 'TOTAL\n-II-', fmt_col_header)
        row += 1

        # Casillas 40-65: Gastos deducibles
        expense_items = [
            (40, 'Remuneraciones o contribuciones pagadas al personal, por servicios prestados en relación de dependencia'),
            (41, 'Aguinaldos'),
            (42, 'Cargas sociales - Aporte patronal'),
            (43, 'Beneficios otorgados a los trabajadores en relación de dependencia, conforme al art. 93 de la Constitución Nacional'),
            (44, 'Remuneraciones por servicios personales cuando no sean prestados en relación de dependencia, incluidas las remuneraciones del dueño de una empresa unipersonal, socio o accionista'),
            (45, 'Remuneraciones porcentuales de las utilidades líquidas por servicios de carácter personal, que no se encuentran en relación de dependencia y pagadas en dinero'),
            (46, 'Arrendamiento, cesión de uso de bienes y derechos'),
            (47, 'Fletes y gastos de comercialización'),
            (48, 'Gastos de movilidad y viático'),
            (49, 'Intereses financieros'),
            (50, 'Erogaciones incurridas por la explotación de un establecimiento agropecuario, en fincas colindantes o cercanas al mismo'),
            (51, 'Donaciones'),
            (52, 'Depreciaciones por desgaste, obsolescencia y agotamiento'),
            (53, 'Amortización de bienes intangibles'),
            (54, 'Pérdida de inventario por mortandad del ganado'),
            (55, 'Pérdidas extraordinarias y las originadas por hechos punibles cometidos por terceros'),
            (56, 'Castigo sobre malos créditos'),
            (57, 'Pérdidas por diferencia de cambio'),
            (58, 'Gastos de constitución y organización, incluidos los preoperativos y de reorganización'),
            (59, 'Reservas matemáticas y similares. Previsiones sobre malos créditos para entidades bancarias y financieras regidas por la Ley N° 861/1996'),
            (60, 'Gastos generales del negocio no señalados en los incisos anteriores'),
            (61, 'IVA Gasto/Costo'),
            (62, 'Impuesto a la Renta Empresarial'),
            (63, 'Gastos y erogaciones en el exterior relacionados a Instrumentos Financieros Derivados'),
            (64, 'Otros gastos y erogaciones en el exterior'),
            (65, 'Otros gastos (No señalados expresamente en los ítems anteriores)'),
        ]

        total_83_base = 0
        for casilla, descripcion in expense_items:
            write_code_cell(row, casilla)
            
            write_desc_cell(row, descripcion, fmt_label)
            valor = data_expenses.get(str(casilla), 0)
            write_amount_cell(row, valor, fmt_number)
            blank_total_cell(row)
            total_83_base += valor
            row += 1

        # Casilla 83: F- TOTAL DE GASTOS
        write_desc_cell(row, 'F- TOTAL DE GASTOS (antes de considerar los gastos señalados en el numeral 23 del Art. 15 de la Ley)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, total_83_base, fmt_number_total)
        row += 1

        # Casillas 66-74: Menos gastos no deducibles
        expense_exclusions = [
            (66, 'Menos: Gastos relacionados a los ingresos por operaciones realizadas por usuarios de Zonas Francas'),
            (67, 'Menos: Gastos relacionados a los ingresos por operaciones realizadas en el Régimen de Maquila'),
            (68, 'Menos: Gastos relacionados a ingresos de fuente extranjera no gravados'),
            (69, 'Menos: Gastos relacionados a ingresos gravados obtenidos en operaciones internacionales alcanzadas por el Régimen Presunto'),
            (70, 'Menos: Gastos relacionados a ingresos gravados obtenidos de actividades de forestación o enajenación de inmuebles urbanos y rurales alcanzados por el Régimen Presunto'),
            (71, 'Menos: Gastos relacionados a ingresos gravados obtenidos de actividades de comercialización de productos establecidos en el Régimen Especial'),
            (72, 'Menos: Impuesto a la Renta Empresarial'),
            (73, 'Menos: Gastos relacionados a ingresos no gravados por el IRE, exentos y exonerados'),
            (74, 'Menos: Otros gastos no deducibles'),
        ]

        total_expense_exclusions = 0
        for casilla, descripcion in expense_exclusions:
            write_code_cell(row, casilla)
            
            write_desc_cell(row, descripcion, fmt_label)
            valor = data_expenses.get(str(casilla), 0)
            write_amount_cell(row, valor, fmt_number)
            blank_total_cell(row)
            total_expense_exclusions += valor
            row += 1

        # Casilla 84: G- TOTAL DE GASTOS DEDUCIBLES
        total_84 = total_83_base - total_expense_exclusions
        write_desc_cell(row, 'G- TOTAL DE GASTOS DEDUCIBLES (Diferencia entre la casilla 83 y el resultado de la sumatoria de las casillas 66 al 74)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, total_84, fmt_number_total)
        row += 1

        # Casilla 85: H- RENTA NETA ANTES DE LA DEDUCCIÓN
        total_85 = total_82 - total_84
        write_desc_cell(row, 'H- RENTA NETA ANTES DE LA DEDUCCIÓN DE LOS INTERESES SEÑALADOS EN EL NUMERAL 23 DEL ART. 15 DE LA LEY (Diferencia entre la casilla 82 y 84)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, total_85, fmt_number_total)
        row += 1

        # Casilla 75: Intereses vinculadas
        write_desc_cell(row, 'Total de Intereses por préstamos, regalías y asistencia técnica cuando lo realicen el socio o accionista de la empresa, la casa matriz u otras sucursales o agencias del exterior, o entre empresas vinculadas', fmt_label)
        write_code_cell(row, 75)
        
        val_75 = data_expenses.get('75', 0)
        write_amount_cell(row, val_75, fmt_number)
        blank_total_cell(row)
        row += 1

        # Casilla 76: Porción deducible (máximo 30% de casilla 85)
        val_76 = min(val_75, total_85 * 0.30)
        write_desc_cell(row, 'Porción deducible del monto declarado en la casilla 75, correspondiente a Intereses por préstamos, regalías y asistencia técnica cuando lo realicen el socio o accionista de la empresa, la casa matriz u otras sucursales o agencias del exterior, o entre empresas vinculadas (No podrá superar el 30% del valor de la casilla 85)', fmt_label)
        write_code_cell(row, 76)
        
        write_amount_cell(row, val_76, fmt_number)
        blank_total_cell(row)
        row += 1

        # Casilla 86: I- RENTA NETA DESPUÉS DE LA DEDUCCIÓN
        total_86 = total_85 - val_76
        write_desc_cell(row, 'I- RENTA NETA DESPUÉS DE LA DEDUCCIÓN DE LOS INTERESES SEÑALADOS EN EL NUMERAL 23 DEL ART. 15 DE LA LEY (Diferencia entre la casilla 85 y 76)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, total_86, fmt_number_total)
        row += 1

        # === RUBRO 2 - TRANSFORMACIÓN Y VALUACIÓN DE ACTIVOS ===
        row += 1
        worksheet.merge_range(row, col_code, row, col_total_end, 'RUBRO 2 - TRANSFORMACIÓN Y VALUACIÓN DE ACTIVOS', fmt_section)
        row += 1

        rubro2_items = [
            ('a', 87, 'Aumento por transformación biológica de animales vivos y de plantas, incluido el procreo y la explotación forestal, así como por la valuación de Activos Biológicos'),
            ('b', 88, 'Disminución por transformación y valuación de Activos Biológicos'),
            ('c', 89, 'Aumento patrimonial por revaluaciones del valor de acciones, revaluaciones técnicas o extraordinarias de los bienes del activo fijo e intangibles'),
            ('d', 90, 'Disminución patrimonial del valor de acciones y de los bienes del activo fijo e intangibles'),
        ]

        total_87_89 = 0
        total_88_90 = 0
        for inc, casilla, descripcion in rubro2_items:
            write_code_cell(row, casilla)
            
            write_desc_cell(row, descripcion, fmt_label)
            write_amount_cell(row, 0, fmt_number)
            blank_total_cell(row)
            if casilla in [87, 89]:
                total_87_89 += 0
            else:
                total_88_90 += 0
            row += 1

        # === RUBRO 3 - AJUSTES POR PRECIOS DE TRANSFERENCIA ===
        row += 1
        worksheet.merge_range(row, col_code, row, col_total_end, 'RUBRO 3 - AJUSTES POR PRECIOS DE TRANSFERENCIA', fmt_section)
        row += 1

        write_desc_cell(row, 'Renta Neta equivalente al monto total de ajuste por precios de transferencia determinados (Numerales 1 al 6 del Artículo 38 de la Ley N° 6380/2019)', fmt_label)
        write_code_cell(row, 262)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        row += 1

        write_desc_cell(row, 'Renta Neta equivalente al monto total de ajuste por precios de transferencia determinados (Numeral 7 del Artículo 38 de la Ley N° 6380/2019)', fmt_label)
        write_code_cell(row, 263)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        row += 1

        # === RUBRO 4 - RESULTADO DEL EJERCICIO ===
        row += 1
        worksheet.merge_range(row, col_code, row, 10, 'RUBRO 4 - RESULTADO DEL EJERCICIO', fmt_section)
        worksheet.merge_range(row, col_amount, row, col_total, 'IMPORTE', fmt_col_header)
        row += 1

        blank_desc_cell(row)
        blank_code_area(row)
        
        write_amount_cell(row, 'PÉRDIDA\n-I-', fmt_col_header)
        write_total_cell(row, 'UTILIDAD\n-II-', fmt_col_header)
        row += 1

        # Resultado contable (casilla 91/93)
        write_desc_cell(row, 'Resultado contable del ejercicio', fmt_label)
        write_code_cell(row, '91/93')
        
        resultado_contable = total_86 + total_87_89 - total_88_90
        if resultado_contable < 0:
            write_amount_cell(row, abs(resultado_contable), fmt_number)
            blank_total_cell(row)
        else:
            blank_amount_cell(row)
            write_total_cell(row, resultado_contable, fmt_number)
        row += 1

        # Resultado fiscal (casilla 92/94)
        write_desc_cell(row, 'Resultado fiscal del ejercicio', fmt_label)
        write_code_cell(row, '92/94')
        
        resultado_fiscal = total_86
        if resultado_fiscal < 0:
            write_amount_cell(row, abs(resultado_fiscal), fmt_number)
            blank_total_cell(row)
            val_92 = abs(resultado_fiscal)
            val_94 = 0
        else:
            blank_amount_cell(row)
            write_total_cell(row, resultado_fiscal, fmt_number)
            val_92 = 0
            val_94 = resultado_fiscal
        row += 1

        # === RUBRO 5 - DETERMINACIÓN DE LA RENTA NETA Y PÉRDIDA ARRASTRABLE ===
        row += 1
        worksheet.merge_range(row, col_code, row, 10, 'RUBRO 5 - DETERMINACIÓN DE LA RENTA NETA Y PÉRDIDA ARRASTRABLE', fmt_section)
        worksheet.merge_range(row, col_amount, row, col_total, 'IMPORTE', fmt_col_header)
        row += 1

        blank_desc_cell(row)
        blank_code_area(row)
        
        write_amount_cell(row, 'CONTRIBUYENTE\n-I-', fmt_col_header)
        write_total_cell(row, 'FISCO\n-II-', fmt_col_header)
        row += 1

        # Casilla 102: Utilidad
        write_desc_cell(row, 'Resultado Fiscal del Ejercicio/Utilidad (Proviene del Rubro 4, casilla 94)', fmt_label)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_94, fmt_number)
        val_102 = val_94
        row += 1

        # Casilla 95: Pérdida
        write_desc_cell(row, 'Resultado Fiscal del Ejercicio/Pérdida (Proviene del Rubro 4, casilla 92)', fmt_label)
        write_code_cell(row, 95)
        
        write_amount_cell(row, val_92, fmt_number)
        blank_total_cell(row)
        row += 1

        # Pérdidas de ejercicios anteriores
        write_desc_cell(row, 'PÉRDIDA DE EJERCICIOS ANTERIORES (El contribuyente deberá tener en cuenta que la pérdida declarada en el presente Inciso, esté dentro del plazo legal previsto en la Ley)', fmt_label)
        write_code_cell(row, 96)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        val_96 = 0
        row += 1

        # Casilla 97: Pérdida total acumulada
        val_97 = val_92 + val_96
        write_desc_cell(row, 'PÉRDIDA TOTAL ACUMULADA (Sumatoria de las casillas 95 y 96)', fmt_label)
        write_code_cell(row, 97)
        
        write_amount_cell(row, val_97, fmt_number)
        blank_total_cell(row)
        row += 1

        # Casilla 98: Pérdida fuera de plazo
        write_desc_cell(row, 'Menos: Pérdida que al cierre del presente ejercicio quedó por fuera de los 5 (cinco) años', fmt_label)
        write_code_cell(row, 98)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        val_98 = 0
        row += 1

        # Casilla 99: Saldo pérdidas compensables
        val_99 = val_97 - val_98
        write_desc_cell(row, 'SALDO DE PÉRDIDAS COMPENSABLES AL CIERRE DEL PRESENTE EJERCICIO (Diferencia entre las casillas 97 y 98)', fmt_label)
        write_code_cell(row, 99)
        
        write_amount_cell(row, val_99, fmt_number)
        blank_total_cell(row)
        row += 1

        # Casilla 100: Pérdida que se compensa
        val_100 = min(val_99, val_102 * 0.20) if val_102 > 0 else 0
        write_desc_cell(row, 'Menos: Pérdida que se compensa en el presente ejercicio fiscal (No podrá exceder el 20 % de la Renta Neta: casilla 102)', fmt_label)
        write_code_cell(row, 100)
        
        write_amount_cell(row, val_100, fmt_number)
        blank_total_cell(row)
        row += 1

        # Casilla 101: Saldo pérdida al cierre
        val_101 = val_99 - val_100
        write_desc_cell(row, 'SALDO DE PÉRDIDA AL CIERRE DEL PRESENTE EJERCICIO (Diferencia entre las casillas 99 y 100). Monto a trasladar en la casilla 96 del presente rubro de la Declaración Jurada del siguiente ejercicio fiscal', fmt_label)
        write_code_cell(row, 101)
        
        write_amount_cell(row, val_101, fmt_number)
        blank_total_cell(row)
        row += 1

        # Casilla 103: Renta neta del ejercicio
        val_103 = max(val_102 - val_100, 0)
        write_desc_cell(row, 'RENTA NETA DEL EJERCICIO (Diferencia entre las casillas 102 y 100, cuando la casilla 102 sea mayor)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_103, fmt_number_total)
        row += 1

        # === RUBRO 6 - DETERMINACIÓN DE LA RENTA NETA PARA QUIENES CUENTEN CON RENTAS ALCANZADAS POR BENEFICIOS ESPECIALES ===
        row += 1
        worksheet.merge_range(row, col_code, row, 10, 'RUBRO 6 - DETERMINACIÓN DE LA RENTA NETA PARA QUIENES CUENTEN CON RENTAS ALCANZADAS POR BENEFICIOS ESPECIALES', fmt_section)
        worksheet.merge_range(row, col_amount, row, col_total, 'IMPORTE', fmt_col_header)
        row += 1

        blank_desc_cell(row)
        blank_code_area(row)
        
        write_amount_cell(row, 'DEDUCCIONES\n-I-', fmt_col_header)
        write_total_cell(row, 'FISCO\n-II-', fmt_col_header)
        row += 1

        # Casilla 105: Renta Neta del Ejercicio
        write_desc_cell(row, 'Renta Neta del Ejercicio (Proviene de la casilla 103 del Rubro 5)', fmt_label)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_103, fmt_number)
        row += 1

        # Casilla 104: Renta alcanzada por beneficios especiales
        write_desc_cell(row, 'Renta Neta alcanzada por beneficios especiales vigentes', fmt_label)
        write_code_cell(row, 104)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        val_104 = 0
        row += 1

        # Casilla 106: Renta neta imponible
        val_106 = val_103 - val_104
        write_desc_cell(row, 'RENTA NETA IMPONIBLE (Diferencia entre las casillas 105 y 104, cuando la casilla 105 sea mayor)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_106, fmt_number_total)
        row += 1

        # === RUBRO 7 - DETERMINACIÓN DE LA RENTA PRESUNTA ===
        row += 1
        worksheet.merge_range(row, col_code, row, col_total_end, 'RUBRO 7 - DETERMINACIÓN DE LA RENTA PRESUNTA PARA CONTRIBUYENTES QUE OPTEN LIQUIDAR EL IMPUESTO CONFORME AL ARTÍCULO 19 DE LA LEY', fmt_section)
        row += 1

        # Casilla 107: Ingresos forestación/inmuebles
        write_desc_cell(row, 'Ingresos gravados obtenidos de actividades de forestación o enajenación de inmuebles urbanos y rurales que formen parte del activo fijo', fmt_label)
        write_code_cell(row, 107)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        val_107 = 0
        row += 1

        # Casilla 108: Renta neta presunta (30% de 107)
        val_108 = val_107 * 0.30
        write_desc_cell(row, 'RENTA NETA PRESUNTA (30% de la casilla 107)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_108, fmt_number_total)
        row += 1

        # === RUBRO 8 - DETERMINACIÓN DEL IMPUESTO Y LIQUIDACIÓN FINAL ===
        row += 1
        worksheet.merge_range(row, col_code, row, 10, 'RUBRO 8 - DETERMINACIÓN DEL IMPUESTO Y LIQUIDACIÓN FINAL', fmt_section)
        worksheet.merge_range(row, col_amount, row, col_total, 'IMPORTE', fmt_col_header)
        row += 1

        blank_desc_cell(row)
        blank_code_area(row)
        
        write_amount_cell(row, 'CONTRIBUYENTE\n-I-', fmt_col_header)
        write_total_cell(row, 'FISCO\n-II-', fmt_col_header)
        row += 1

        # Tasa del IRE: 10%
        tasa_ire = 10

        # Casilla 116: Impuesto sobre renta neta imponible y presunta
        val_116 = (val_106 + val_108) * (tasa_ire / 100)
        write_desc_cell(row, f'Impuesto determinado sobre la Renta Neta Imponible y la Renta Neta Presunta ({tasa_ire}% sobre la sumatoria de las casillas 106 y 108)', fmt_label)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_116, fmt_number)
        row += 1

        # Casilla 117: Impuesto sobre beneficios especiales
        val_117 = 0  # Varía según beneficio
        write_desc_cell(row, f'Impuesto determinado aplicable sobre la renta neta alcanzadas por beneficios especiales (.........% sobre el monto de la casilla 104 del Rubro 6)', fmt_label)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_117, fmt_number)
        row += 1

        # Casilla 118: Subtotal
        val_118 = val_116 + val_117
        write_desc_cell(row, 'SUBTOTAL (Sumatoria de las casillas 116 y 117)', fmt_label)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_118, fmt_number)
        row += 1

        # Casilla 109: Impuesto pagado exterior
        write_desc_cell(row, 'Impuesto a la Renta pagado en el exterior aplicado al IRE, para evitar la doble imposición', fmt_label)
        write_code_cell(row, 109)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        val_109 = 0
        row += 1

        # Casilla 120: Total impuesto determinado
        val_120 = val_118 - val_109
        write_desc_cell(row, 'TOTAL IMPUESTO DETERMINADO (Casillas 118 - 109)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_120, fmt_number_total)
        row += 1

        # Casilla 110: Saldo a favor ejercicio anterior
        write_desc_cell(row, 'Saldo a favor del contribuyente del ejercicio anterior (Proviene de la casilla 115 del presente Rubro de la Declaración Jurada del ejercicio fiscal anterior)', fmt_label)
        write_code_cell(row, 110)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        val_110 = 0
        row += 1

        # Casilla 111: Retenciones
        write_desc_cell(row, 'Retenciones computables a favor del Contribuyente', fmt_label)
        write_code_cell(row, 111)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        val_111 = 0
        row += 1

        # Casilla 112: Percepciones
        write_desc_cell(row, 'Percepciones computables a favor del Contribuyente', fmt_label)
        write_code_cell(row, 112)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        val_112 = 0
        row += 1

        # Casilla 113: Anticipos
        write_desc_cell(row, 'Anticipos ingresados', fmt_label)
        write_code_cell(row, 113)
        
        write_amount_cell(row, 0, fmt_number)
        blank_total_cell(row)
        val_113 = 0
        row += 1

        # Casilla 121: Multa
        write_desc_cell(row, 'Multa por presentar la Declaración Jurada con posterioridad al vencimiento', fmt_label)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, 0, fmt_number)
        val_121 = 0
        row += 1

        # Casilla 114/122: Subtotal
        val_114 = val_110 + val_111 + val_112 + val_113
        val_122 = val_120 + val_121
        write_desc_cell(row, 'SUBTOTAL (Columna I: Sumatoria de las casillas 110 al 113); (Columna II: Sumatoria de las casillas 120 y 121)', fmt_label)
        blank_code_area(row)
        
        write_amount_cell(row, val_114, fmt_number)
        write_total_cell(row, val_122, fmt_number)
        row += 1

        # Casilla 115: Saldo a favor contribuyente
        val_115 = max(val_114 - val_122, 0)
        write_desc_cell(row, 'SALDO A FAVOR DEL CONTRIBUYENTE (Monto a trasladar al siguiente ejercicio fiscal en la casilla 110 del presente Rubro). Diferencia entre las casillas 114 y 122, cuando la casilla 114 sea mayor', fmt_total)
        blank_code_area(row)
        
        write_amount_cell(row, val_115, fmt_number_total)
        blank_total_cell(row)
        row += 1

        # Casilla 123: Saldo a ingresar a favor del fisco
        val_123 = max(val_122 - val_114, 0)
        write_desc_cell(row, 'SALDO A INGRESAR A FAVOR DEL FISCO (Diferencia entre las casillas 122 y 114, cuando la casilla 122 sea mayor)', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_123, fmt_number_total)
        row += 1

        # === RUBRO 9 - DETERMINACIÓN DE ANTICIPOS PARA EL SIGUIENTE EJERCICIO FISCAL ===
        row += 1
        worksheet.merge_range(row, col_code, row, col_total_end, 'RUBRO 9 - DETERMINACIÓN DE ANTICIPOS PARA EL SIGUIENTE EJERCICIO FISCAL', fmt_section)
        worksheet.merge_range(row, 3, row, 3, 'IMPORTE', fmt_col_header)
        row += 1

        # Casilla 124: Impuesto liquidado
        write_desc_cell(row, 'Impuesto liquidado del ejercicio (Proviene de la casilla 120 del Rubro 8)', fmt_label)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_120, fmt_number)
        row += 1

        # Casilla 125: Retenciones y Percepciones
        val_125 = val_111 + val_112
        write_desc_cell(row, 'Retenciones y Percepciones computables (Proviene de la sumatoria de las casillas 111 y 112)', fmt_label)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_125, fmt_number)
        row += 1

        # Casilla 126: Anticipos a ingresar
        val_126 = max(val_120 - val_125, 0)
        write_desc_cell(row, 'Anticipos a ingresar para el siguiente ejercicio (Diferencia entre las casillas 124 y 125, cuando el monto de la casilla 124 sea mayor)', fmt_label)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_126, fmt_number)
        row += 1

        # Casilla 127: Saldo a favor
        val_127 = min(val_115, val_126)
        write_desc_cell(row, 'Saldo a favor del contribuyente del ejercicio que se liquida (Proviene de la casilla 115. Consignar hasta el monto de la casilla 126)', fmt_label)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_127, fmt_number)
        row += 1

        # Casilla 128: Cuotas de anticipos
        val_128 = max((val_126 - val_127) * 0.25, 0)
        write_desc_cell(row, 'Cuotas de anticipos a ingresar. (Casilla 126 - casilla 127) x 25%', fmt_total)
        blank_code_area(row)
        
        blank_amount_cell(row)
        write_total_cell(row, val_128, fmt_number_total)
        row += 1

        # === RUBRO 10 - INFORMACIÓN COMPLEMENTARIA ===
        row += 1
        worksheet.merge_range(row, col_code, row, col_total_end, 'RUBRO 10 - INFORMACIÓN COMPLEMENTARIA', fmt_section)
        worksheet.merge_range(row, 3, row, 3, '', fmt_section)
        row += 1

        # Casilla 129: RUC Contador
        write_desc_cell(row, 'RUC o Cédula de Identidad Civil del Contador, sin incluir el dígito verificador', fmt_label)
        write_code_cell(row, 129)
        
        worksheet.merge_range(row, col_amount, row, col_total, self.contador_ruc or '', fmt_cell)
        row += 1

        # Casilla 130: RUC Auditor
        write_desc_cell(row, 'RUC del Auditor o de la Empresa Auditora, sin incluir el dígito verificador', fmt_label)
        write_code_cell(row, 130)
        
        worksheet.merge_range(row, col_amount, row, col_total, self.auditor_ruc or '', fmt_cell)
        row += 1

        # Casilla 131: Total empleados
        write_desc_cell(row, 'Cantidad total de personal ocupado en relación de dependencia al cierre del ejercicio', fmt_label)
        write_code_cell(row, 131)
        
        worksheet.merge_range(row, col_amount, row, col_total, self.total_empleados or 0, fmt_cell)
        row += 1

        # Casilla 132: Número disposición beneficio
        write_desc_cell(row, 'Número de la disposición legal que respalda el beneficio fiscal declarado en el Rubro 6, casilla 104', fmt_label)
        write_code_cell(row, 132)
        
        worksheet.merge_range(row, col_amount, row, col_total, '', fmt_cell)
        row += 1

        # Casilla 133: Año disposición
        write_desc_cell(row, 'Año de la disposición legal que se referencia en la casilla 132.', fmt_label)
        write_code_cell(row, 133)
        
        worksheet.merge_range(row, col_amount, row, col_total, '', fmt_cell)
        row += 1

        # Nota final
        row += 1
        worksheet.merge_range(row, col_code, row, col_total_end,
            'Estimado Contribuyente: Le recordamos que los pagos que efectúe emergentes de esta declaración, serán imputados en su cuenta corriente conforme a lo señalado en la Ley N° 125/1991, Art. 162',
            fmt_note)

        # === HOJA ANEXO ===
        annex = workbook.add_worksheet('Anexo')
        annex.set_paper(9)
        annex.set_margins(left=0.4, right=0.4, top=0.5, bottom=0.5)
        annex.fit_to_pages(1, 0)
        annex.set_landscape()
        annex.set_default_row(18)

        annex.set_column('A:A', 5)
        annex.set_column('B:B', 38)
        annex.set_column('C:C', 5)
        annex.set_column('D:D', 16)
        annex.set_column('E:E', 5)
        annex.set_column('F:F', 16)
        annex.set_column('G:G', 5)
        annex.set_column('H:H', 16)
        annex.set_column('I:I', 5)
        annex.set_column('J:J', 16)

        annex_row = 0
        annex.merge_range(annex_row, 0, annex_row, 9, 'ANEXO', fmt_section)
        annex_row += 1
        annex.merge_range(annex_row, 0, annex_row, 9, 'PARA CONTRIBUYENTES QUE REALICEN ACTIVIDAD AGROPECUARIA', fmt_subsection)
        annex_row += 2

        def write_annex_table(title, categories, rows):
            nonlocal annex_row
            annex.merge_range(annex_row, 0, annex_row, 9, title, fmt_subsection)
            annex_row += 1
            annex.write(annex_row, 0, 'INC.', fmt_col_header)
            annex.write(annex_row, 1, 'MOVIMIENTOS', fmt_col_header)
            for idx, category in enumerate(categories):
                start_col = 2 + idx * 2
                annex.merge_range(annex_row, start_col, annex_row, start_col + 1, category, fmt_col_header)
            annex_row += 1

            for inc, label, codes in rows:
                if codes is None:
                    annex.merge_range(annex_row, 0, annex_row, 9, label, fmt_center_bold)
                    annex_row += 1
                    continue

                annex.write(annex_row, 0, inc, fmt_code)
                annex.write(annex_row, 1, label, fmt_label)
                for idx, code in enumerate(codes):
                    code_col = 2 + idx * 2
                    value_col = code_col + 1
                    annex.write(annex_row, code_col, code, fmt_code)
                    annex.write_blank(annex_row, value_col, None, fmt_blank)
                annex_row += 1

            annex_row += 2

        cuadro1_rows = [
            ('a', 'Existencia Anterior', [134, 148, 162, 176]),
            ('b', 'Nacimientos', [135, 149, 163, 177]),
            ('c', 'Reclasificación Entrada', [136, 150, 164, 178]),
            ('d', 'Compra', [137, 151, 165, 179]),
            ('e', 'Aparcería y Otros Ingresos', [138, 152, 166, 180]),
            ('f', 'Total Entrada', [139, 153, 167, 181]),
            ('g', 'Mortandad', [140, 154, 168, 182]),
            ('h', 'Reclasificación Salida', [141, 155, 169, 183]),
            ('i', 'Consumo', [142, 156, 170, 184]),
            ('j', 'Venta', [143, 157, 171, 185]),
            ('k', 'Extravío y Otros Egresos', [144, 158, 172, 186]),
            ('l', 'Total Salida', [145, 159, 173, 187]),
            ('m', 'Existencia Final', [146, 160, 174, 188]),
            ('n', 'Valor del Ganado', [147, 161, 175, 189]),
        ]

        cuadro2_rows = [
            ('a', 'Existencia Anterior', [190, 204, 218, 232]),
            ('b', 'Nacimientos', [191, 205, 219, 233]),
            ('c', 'Reclasificación Entrada', [192, 206, 220, 234]),
            ('d', 'Compra', [193, 207, 221, 235]),
            ('e', 'Aparcería y Otros Ingresos', [194, 208, 222, 236]),
            ('f', 'Total Entrada', [195, 209, 223, 237]),
            ('g', 'Mortandad', [196, 210, 224, 238]),
            ('h', 'Reclasificación Salida', [197, 211, 225, 239]),
            ('i', 'Consumo', [198, 212, 226, 240]),
            ('j', 'Venta', [199, 213, 227, 241]),
            ('k', 'Extravío y Otros Egresos', [200, 214, 228, 242]),
            ('l', 'Total Salida', [201, 215, 229, 243]),
            ('m', 'Existencia Final', [202, 216, 230, 244]),
            ('n', 'Valor del Ganado', [203, 217, 231, 245]),
        ]

        cuadro3_rows = [
            (None, 'EN DEPÓSITO PROPIO', None),
            ('a', 'Kilogramos', [246, 248, 250, 252]),
            ('b', 'Valor total', [247, 249, 251, 253]),
            (None, 'EN DEPÓSITO DE TERCEROS', None),
            ('c', 'Kilogramos', [254, 256, 258, 260]),
            ('d', 'Valor total', [255, 257, 259, 261]),
        ]

        write_annex_table('CUADRO 1 - INVENTARIO DE LA EXISTENCIA DEL GANADO',
                          ['TERNEROS', 'DESMAMANTES', 'VAQUILLAS', 'VACAS'],
                          cuadro1_rows)

        write_annex_table('CUADRO 2 - INVENTARIO DE LA EXISTENCIA DEL GANADO',
                          ['TOROS', 'NOVILLOS', 'HACIENDA EQUINA', 'OTROS'],
                          cuadro2_rows)

        write_annex_table('CUADRO 3 - INFORMACIÓN DE PRODUCTOS AGRÍCOLAS EN EXISTENCIA',
                          ['MAÍZ', 'SOJA', 'TRIGO', 'OTROS'],
                          cuadro3_rows)

        workbook.close()
        output.seek(0)
        return output.read()

    def action_generate_f500(self):
        """
        Genera el archivo Excel del Formulario 500
        """
        self.ensure_one()

        if not self.company_id:
            raise UserError(_('Debe seleccionar una compañía'))

        if not self.date_from or not self.date_to:
            raise UserError(_('Debe seleccionar el período fiscal'))

        if self.date_from > self.date_to:
            raise UserError(_('La fecha desde no puede ser mayor a la fecha hasta'))

        # Obtener datos contables
        data_income = self._get_income_data()
        data_costs = self._get_costs_data()
        data_expenses = self._get_expenses_data()

        # Generar archivo Excel
        excel_data = self._create_excel_file(data_income, data_costs, data_expenses)

        # Nombre del archivo
        file_name = f'Formulario_500_IRE_{self.exercise_year}_{self.company_id.vat or "SIN_RUC"}.xlsx'

        self.write({
            'file_data': base64.b64encode(excel_data),
            'file_name': file_name,
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'f500.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_download_file(self):
        """
        Descarga el archivo generado
        """
        self.ensure_one()

        if not self.file_data:
            raise UserError(_('No hay archivo generado. Por favor, genere primero el formulario.'))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=f500.wizard&id={self.id}&field=file_data&download=true&filename={self.file_name}',
            'target': 'self',
        }
