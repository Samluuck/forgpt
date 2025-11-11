# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import xlsxwriter
import base64
from io import BytesIO


class F500Wizard(models.TransientModel):
    _name = 'f500.wizard'
    _description = 'Wizard para generar Formulario 500 IRE Versión 2'

    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    date_from = fields.Date(string='Fecha Desde', required=True, default=lambda self: fields.Date.today().replace(month=1, day=1))
    date_to = fields.Date(string='Fecha Hasta', required=True, default=lambda self: fields.Date.today().replace(month=12, day=31))
    exercise_year = fields.Char(string='Ejercicio Fiscal', compute='_compute_exercise_year', store=True, readonly=True)

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

    # Información complementaria (Rubro 10)
    contador_ruc = fields.Char(string='RUC/CI del Contador')
    auditor_ruc = fields.Char(string='RUC del Auditor')
    total_empleados = fields.Integer(string='Total de Empleados')
    beneficio_fiscal_numero = fields.Char(string='Número disposición legal - beneficio fiscal')
    beneficio_fiscal_anio = fields.Char(string='Año disposición legal - beneficio fiscal')

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

    def _get_cell_balance(self, cell_number):
        """
        Obtiene el balance total de todas las cuentas asignadas a una casilla específica
        """
        if not cell_number:
            return 0.0

        categories = self.env['f500.category'].search([
            ('f500_cell', '=', str(cell_number)),
            ('active', '=', True)
        ])

        if not categories:
            return 0.0

        total = 0.0

        for category in categories:
            accounts = self.env['account.account'].search([
                ('f500_category_id', '=', category.id),
                ('company_id', '=', self.company_id.id)
            ])

            if not accounts:
                continue

            domain = [
                ('account_id', 'in', accounts.ids),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id),
                ('parent_state', '=', 'posted'),
            ]

            moves = self.env['account.move.line'].search(domain)
            # Para ingresos, costos y gastos, usamos debit - credit para obtener el valor absoluto correcto
            # Ingresos: normalmente créditos (balance negativo), necesitamos el valor positivo
            # Costos/Gastos: normalmente débitos (balance positivo)
            debit_total = sum(moves.mapped('debit'))
            credit_total = sum(moves.mapped('credit'))
            
            # Para ingresos, el valor está en créditos (negativo en balance)
            # Para costos/gastos, el valor está en débitos (positivo en balance)
            if category.category_type == 'income':
                # Ingresos: usar créditos (valores positivos)
                balance = credit_total
            elif category.category_type in ['cost', 'expense']:
                # Costos y gastos: usar débitos (valores positivos)
                balance = debit_total
            else:
                # Para otros tipos, usar el balance absoluto
                balance = abs(sum(moves.mapped('balance')))

            if category.operation == 'subtract':
                total -= balance
            else:
                total += balance

        return abs(total)

    def _create_excel_file(self):
        """
        Crea el archivo Excel del Formulario 500 VERSIÓN 2 según formato oficial SET
        """
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('F500')

        # === CONFIGURACIÓN DE PÁGINA ===
        worksheet.set_paper(9)  # A4
        worksheet.set_margins(left=0.5, right=0.5, top=0.5, bottom=0.5)
        worksheet.set_portrait()

        # === COLORES ===
        COLOR_BLUE = '#4472C4'
        COLOR_GRAY = '#D9D9D9'
        COLOR_GRAY_LIGHT = '#F2F2F2'
        COLOR_WHITE = '#FFFFFF'

        # === FORMATOS ===
        fmt_blue_header = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 7,
            'bold': True,
            'bg_color': COLOR_BLUE,
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        })

        fmt_logo_text = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 6,
            'bold': True,
            'align': 'center',
            'valign': 'top',
            'border': 1,
            'text_wrap': True
        })

        fmt_500 = workbook.add_format({
            'font_name': 'Arial Black',
            'font_size': 60,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        fmt_label = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 8,
            'bold': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        })

        fmt_input = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 8,
            'bg_color': COLOR_GRAY_LIGHT,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })

        fmt_checkbox = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        fmt_code = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 8,
            'bold': True,
            'bg_color': COLOR_GRAY_LIGHT,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        fmt_title = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 9,
            'bold': True,
            'bg_color': COLOR_GRAY,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        })

        fmt_desc = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 7,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        })

        fmt_number = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 8,
            'num_format': '#,##0',
            'align': 'right',
            'valign': 'vcenter',
            'border': 1
        })

        fmt_white = workbook.add_format({
            'bg_color': COLOR_WHITE,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })

        # === ANCHOS DE COLUMNAS ===
        worksheet.set_column(0, 0, 3)     # A - Logo
        worksheet.set_column(1, 1, 2)     # B - Checkbox
        worksheet.set_column(2, 2, 45)    # C - Descripciones
        worksheet.set_column(3, 3, 6)     # D - Códigos
        worksheet.set_column(4, 4, 15)    # E - Importe I
        worksheet.set_column(5, 5, 15)    # F - Total II

        # === CONSTRUCCIÓN DEL ENCABEZADO ===
        row = 0

        # FILA 1: Headers azules
        worksheet.merge_range(row, 0, row, 2, 
            'PARA LLENAR LEA EL INSTRUCTIVO DISPONIBLE EN LA WEB', 
            fmt_blue_header)
        worksheet.merge_range(row, 3, row, 5, 
            'LOS IMPORTES SE CONSIGNARÁN SIN CÉNTIMOS', 
            fmt_blue_header)
        row += 1

        # FILAS 2-8: Sección de identificación con logo 500
        start_logo = row
        
        # Texto "IMPUESTO A LA RENTA..."
        worksheet.merge_range(row, 0, row + 2, 1, 
            'IMPUESTO A LA\nRENTA\nEMPRESARIAL\nGENERAL\nVERSIÓN 2', 
            fmt_logo_text)
        
        # Número de Orden
        worksheet.merge_range(row, 2, row, 2, 'Número de Orden', fmt_label)
        worksheet.merge_range(row, 3, row, 5, '', fmt_input)
        row += 1

        # RUC
        worksheet.merge_range(row, 2, row, 3, 'RUC', fmt_label)
        ruc_parts = (self.ruc or '').split('-')
        ruc_number = ruc_parts[0] if len(ruc_parts) > 0 else ''
        ruc_dv = ruc_parts[1] if len(ruc_parts) > 1 else ''
        worksheet.write(row, 4, ruc_number, fmt_input)
        worksheet.write(row, 5, 'DV', fmt_label)
        row += 1

        worksheet.merge_range(row, 4, row, 5, ruc_dv, fmt_input)
        
        # Número 500 (grande)
        worksheet.merge_range(start_logo + 3, 0, start_logo + 6, 1, '500', fmt_500)
        row += 1

        # Razón Social
        worksheet.merge_range(row, 2, row, 3, 'Razón Social/Primer Apellido', fmt_label)
        worksheet.merge_range(row, 4, row, 5, 'Segundo Apellido', fmt_label)
        row += 1

        worksheet.merge_range(row, 2, row, 3, self.razon_social or '', fmt_input)
        worksheet.merge_range(row, 4, row, 5, '', fmt_input)
        row += 1

        # Nombres
        worksheet.write(row, 2, 'Nombres', fmt_label)
        worksheet.write(row, 3, '03', fmt_code)
        worksheet.merge_range(row, 4, row, 5, 
            'Número de Orden de Declaración que rectifica', 
            fmt_label)
        row += 1

        worksheet.write(row, 2, '', fmt_input)
        worksheet.merge_range(row, 3, row, 5, self.rectified_order or '', fmt_input)
        row += 1

        # Tipo de declaración
        worksheet.write(row, 2, '01', fmt_code)
        worksheet.write(row, 3, '☑' if self.declaration_type == '01' else '☐', fmt_checkbox)
        worksheet.write(row, 4, 'Declaración Jurada Original', fmt_input)
        worksheet.write(row, 5, '04', fmt_code)
        row += 1

        worksheet.write(row, 2, '02', fmt_code)
        worksheet.write(row, 3, '☑' if self.declaration_type == '02' else '☐', fmt_checkbox)
        worksheet.write(row, 4, 'Declaración Jurada Rectificativa', fmt_input)
        worksheet.write(row, 5, 'Periodo / Ejercicio Fiscal', fmt_label)
        row += 1

        worksheet.write(row, 2, '05', fmt_code)
        worksheet.write(row, 3, '☑' if self.declaration_type == '05' else '☐', fmt_checkbox)
        worksheet.write(row, 4, 
            'Declaración Jurada en Carácter de Cese de Actividades,\nClausura o Cierre Definitivo', 
            fmt_input)
        worksheet.write(row, 5, 'Año', fmt_label)
        row += 1

        worksheet.merge_range(row, 5, row, 5, self.exercise_year or '', fmt_input)
        row += 1

        # === TÍTULO RÉGIMEN GENERAL ===
        worksheet.merge_range(row, 0, row, 5, 
            'RÉGIMEN GENERAL PARA EMPRESAS O ENTIDADES QUE REALICEN OPERACIONES GRAVADAS Y/O EXONERADAS POR EL IMPUESTO A LA RENTA EMPRESARIAL (IRE)', 
            fmt_title)
        row += 1

        # === RUBRO 1 - ESTADO DE RESULTADOS ===
        worksheet.merge_range(row, 0, row, 5, 
            'RUBRO 1 - ESTADO DE RESULTADOS', 
            fmt_title)
        row += 1

        # Encabezados
        worksheet.merge_range(row, 0, row, 2, 'INGRESOS POR', fmt_title)
        worksheet.write(row, 3, '', fmt_title)
        worksheet.write(row, 4, 'IMPORTE\n-I-', fmt_title)
        worksheet.write(row, 5, 'TOTAL\n-II-', fmt_title)
        row += 1

        # === INGRESOS (Casillas 10-23) ===
        income_items = [
            (10, 'Enajenación de bienes provenientes de la actividad comercial (compra-venta)'),
            (11, 'Prestación de servicios, incluido el arrendamiento, uso o cesión de uso de bienes,\nderechos en general, incluidos los de imagen o similares'),
            (12, 'Enajenación de bienes provenientes de la producción industrial (fabricación propia,\nincluido el ensamblaje de bienes)'),
            (13, 'Enajenación de bienes provenientes de la producción agrícola, frutícola y hortícola'),
            (14, 'Enajenación de bienes provenientes de la producción animal (lana, cuero, leche cruda,\nentre otros) o pecuaria (vacuna, equina, porcina, ovina, caprina, bufalina, entre otros)'),
            (15, 'Enajenación de bienes provenientes de la actividad forestal, minera, pesquera y otras\nde naturaleza extractiva'),
            (16, 'Intereses, comisiones, rendimientos o ganancias de capital provenientes de títulos y\nde valores mobiliarios; así como los provenientes de financiaciones o préstamos\nefectuados a personas o entidades residentes o constituidas en el país'),
            (17, 'Operaciones con instrumentos financieros derivados en el país'),
            (18, 'Otros Ingresos en el país no comprendidos en los incisos anteriores'),
            (19, 'Intereses, comisiones, rendimientos o ganancias de capital depositados en entidades\nbancarias o financieras públicas o privadas en el exterior; así como los provenientes de\nfinanciaciones o préstamos realizados a favor de personas o entidades del exterior'),
            (20, 'Colocación de capitales (dividendos, utilidades o rendimientos que se obtengan en\ncarácter de dueño de la sucursal en el exterior, socio o accionista de sociedades del\nexterior)'),
            (21, 'Operaciones con instrumentos financieros derivados del exterior'),
            (22, 'Otros Ingresos del exterior no comprendidos en los incisos anteriores'),
            (23, 'Diferencia de cambio'),
        ]

        total_77 = 0
        for casilla, descripcion in income_items:
            worksheet.merge_range(row, 0, row, 2, descripcion, fmt_desc)
            worksheet.write(row, 3, casilla, fmt_code)
            valor = self._get_cell_balance(casilla)
            worksheet.write(row, 4, valor, fmt_number)
            worksheet.write(row, 5, '', fmt_white)
            total_77 += valor
            row += 1

        # Casilla 77: TOTAL INGRESOS BRUTOS
        worksheet.merge_range(row, 0, row, 2, 
            'TOTAL DE INGRESOS BRUTOS (Sumatoria de las casillas 10 al 23)', 
            fmt_title)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, total_77, fmt_number)
        row += 1

        # Casilla 24: Devoluciones
        val_24 = self._get_cell_balance(24)
        worksheet.merge_range(row, 0, row, 2, 
            'Menos: Devoluciones, bonificaciones, descuentos otorgados u otros conceptos\nsimilares', 
            fmt_desc)
        worksheet.write(row, 3, 24, fmt_code)
        worksheet.write(row, 4, val_24, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla 78: TOTAL INGRESOS NETOS
        total_78 = total_77 - val_24
        worksheet.merge_range(row, 0, row, 2, 
            'A- TOTAL DE INGRESOS NETOS (Diferencia entre las casillas 77 y 24)', 
            fmt_title)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, total_78, fmt_number)
        row += 1

        # === EXCLUSIONES DE INGRESOS (Casillas 25-31) ===
        exclusion_items = [
            (25, 'Menos: Ingresos por operaciones de exportación a terceros países realizadas por\nusuarios de Zonas Francas'),
            (26, 'Menos: Ingresos por operaciones de exportación a terceros países por el Régimen de\nMaquila'),
            (27, 'Menos: Ingresos de fuente extranjera no gravados'),
            (28, 'Menos: Ingresos obtenidos en operaciones internacionales alcanzadas por el Régimen\nPresunto'),
            (29, 'Menos: Ingresos obtenidos de actividades de forestación y enajenación de inmuebles\nurbanos y rurales alcanzados por el Régimen Presunto'),
            (30, 'Menos: Ingresos obtenidos de actividades de comercialización de productos\nestablecidos en el Régimen Especial'),
            (31, 'Menos: Ingresos no gravados por el IRE, exentos y exonerados'),
        ]

        total_exclusions = 0
        for casilla, descripcion in exclusion_items:
            worksheet.merge_range(row, 0, row, 2, descripcion, fmt_desc)
            worksheet.write(row, 3, casilla, fmt_code)
            valor = self._get_cell_balance(casilla)
            worksheet.write(row, 4, valor, fmt_number)
            worksheet.write(row, 5, '', fmt_white)
            total_exclusions += valor
            row += 1

        # Casilla 79: TOTAL INGRESOS NETOS GRAVADOS
        total_79 = total_78 - total_exclusions
        worksheet.merge_range(row, 0, row, 2, 
            'B- TOTAL DE INGRESOS NETOS GRAVADOS (Diferencia entre la casilla 78 y el resultado\nde la sumatoria de las casillas 25 al 31)', 
            fmt_title)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, total_79, fmt_number)
        row += 1

        # === COSTOS ===
        worksheet.merge_range(row, 0, row, 2, 'COSTOS', fmt_title)
        worksheet.write(row, 3, '', fmt_title)
        worksheet.write(row, 4, 'IMPORTE\n-I-', fmt_title)
        worksheet.write(row, 5, 'TOTAL\n-II-', fmt_title)
        row += 1

        # Casilla 80: TOTAL COSTOS
        total_80 = self._get_cell_balance(80)
        worksheet.merge_range(row, 0, row, 2, 'C- TOTAL DE COSTOS', fmt_title)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, total_80, fmt_number)
        row += 1

        # === EXCLUSIONES DE COSTOS (Casillas 32-39) ===
        cost_exclusions = [
            (32, 'Menos: Costos relacionados a los ingresos por operaciones realizadas por usuarios de\nZonas Francas'),
            (33, 'Menos: Costos relacionados a los ingresos por operaciones realizadas en el Régimen\nde Maquila'),
            (34, 'Menos: Costos relacionados a ingresos de fuente extranjera no gravados'),
            (35, 'Menos: Costos relacionados a ingresos gravados obtenidos en operaciones\ninternacionales alcanzadas por el Régimen Presunto'),
            (36, 'Menos: Costos relacionados a ingresos gravados obtenidos de actividades de\nforestación o enajenación de inmuebles urbanos y rurales alcanzados por el Régimen\nPresunto'),
            (37, 'Menos: Costos relacionados a ingresos gravados obtenidos de actividades de\ncomercialización de productos establecidos en el Régimen Especial'),
            (38, 'Menos: Costos relacionados a ingresos no gravados por el IRE, exentos y exonerados'),
            (39, 'Menos: Otros costos no deducibles del IRE'),
        ]

        total_cost_exclusions = 0
        for casilla, descripcion in cost_exclusions:
            worksheet.merge_range(row, 0, row, 2, descripcion, fmt_desc)
            worksheet.write(row, 3, casilla, fmt_code)
            valor = self._get_cell_balance(casilla)
            worksheet.write(row, 4, valor, fmt_number)
            worksheet.write(row, 5, '', fmt_white)
            total_cost_exclusions += valor
            row += 1

        # Casilla 81: TOTAL COSTOS DEDUCIBLES
        total_81 = total_80 - total_cost_exclusions
        worksheet.merge_range(row, 0, row, 2, 
            'D- TOTAL DE COSTOS DEDUCIBLES (Diferencia entre la casilla 80 y el resultado de la\nsumatoria de las casillas 32 al 39)', 
            fmt_title)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, total_81, fmt_number)
        row += 1

        # Casilla 82: RENTA BRUTA
        total_82 = total_79 - total_81
        worksheet.merge_range(row, 0, row, 2, 
            'E- RENTA BRUTA (Diferencia entre las casillas 79 y 81)', 
            fmt_title)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, total_82, fmt_number)
        row += 1

        # === GASTOS ===
        worksheet.merge_range(row, 0, row, 2, 'GASTOS', fmt_title)
        worksheet.write(row, 3, '', fmt_title)
        worksheet.write(row, 4, 'IMPORTE\n-I-', fmt_title)
        worksheet.write(row, 5, 'TOTAL\n-II-', fmt_title)
        row += 1

        # === GASTOS DEDUCIBLES (Casillas 40-65) ===
        expense_items = [
            (40, 'Remuneraciones o contribuciones pagadas al personal, por servicios prestados en\nrelación de dependencia'),
            (41, 'Aguinaldos'),
            (42, 'Cargas sociales - Aporte patronal'),
            (43, 'Beneficios otorgados a los trabajadores en relación de dependencia, conforme al art.\n93 de la Constitución Nacional'),
            (44, 'Remuneraciones por servicios personales cuando no sean prestados en relación de\ndependencia, incluidas las remuneraciones del dueño de una empresa unipersonal,\nsocio o accionista'),
            (45, 'Remuneraciones porcentuales de las utilidades líquidas por servicios de carácter\npersonal, que no se encuentran en relación de dependencia y pagadas en dinero'),
            (46, 'Arrendamiento, cesión de uso de bienes y derechos'),
            (47, 'Fletes y gastos de comercialización'),
            (48, 'Gastos de movilidad y viático'),
            (49, 'Intereses financieros'),
            (50, 'Erogaciones incurridas por la explotación de un establecimiento agropecuario, en\nfincas colindantes o cercanas al mismo'),
            (51, 'Donaciones'),
            (52, 'Depreciaciones por desgaste, obsolescencia y agotamiento'),
            (53, 'Amortización de bienes intangibles'),
            (54, 'Pérdida de inventario por mortandad del ganado'),
            (55, 'Pérdidas extraordinarias y las originadas por hechos punibles cometidos por terceros'),
            (56, 'Castigo sobre malos créditos'),
            (57, 'Pérdidas por diferencia de cambio'),
            (58, 'Gastos de constitución y organización, incluidos los preoperativos y de reorganización'),
            (59, 'Reservas matemáticas y similares. Previsiones sobre malos créditos para entidades\nbancarias y financieras regidas por la Ley N° 861/1996'),
            (60, 'Gastos generales del negocio no señalados en los incisos anteriores'),
            (61, 'IVA Gasto/Costo'),
            (62, 'Impuesto a la Renta Empresarial'),
            (63, 'Gastos y erogaciones en el exterior relacionados a Instrumentos Financieros Derivados'),
            (64, 'Otros gastos y erogaciones en el exterior'),
            (65, 'Otros gastos (No señalados expresamente en los ítems anteriores)'),
        ]

        total_83 = 0
        for casilla, descripcion in expense_items:
            worksheet.merge_range(row, 0, row, 2, descripcion, fmt_desc)
            worksheet.write(row, 3, casilla, fmt_code)
            valor = self._get_cell_balance(casilla)
            worksheet.write(row, 4, valor, fmt_number)
            worksheet.write(row, 5, '', fmt_white)
            total_83 += valor
            row += 1

        # Casilla 83: TOTAL GASTOS
        worksheet.merge_range(row, 0, row, 2, 
            'F- TOTAL DE GASTOS (antes de considerar los gastos señalados en el numeral 23 del\nArt. 15 de la Ley)', 
            fmt_title)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, total_83, fmt_number)
        row += 1

        # === EXCLUSIONES DE GASTOS (Casillas 66-74) ===
        expense_exclusions = [
            (66, 'Menos: Gastos relacionados a los ingresos por operaciones realizadas por usuarios de\nZonas Francas'),
            (67, 'Menos: Gastos relacionados a los ingresos por operaciones realizadas en el Régimen\nde Maquila'),
            (68, 'Menos: Gastos relacionados a ingresos de fuente extranjera no gravados'),
            (69, 'Menos: Gastos relacionados a ingresos gravados obtenidos en operaciones\ninternacionales alcanzadas por el Régimen Presunto'),
            (70, 'Menos: Gastos relacionados a ingresos gravados obtenidos de actividades de\nforestación o enajenación de inmuebles urbanos y rurales alcanzados por el Régimen\nPresunto'),
            (71, 'Menos: Gastos relacionados a ingresos gravados obtenidos de actividades de\ncomercialización de productos establecidos en el Régimen Especial'),
            (72, 'Menos: Impuesto a la Renta Empresarial'),
            (73, 'Menos: Gastos relacionados a ingresos no gravados por el IRE, exentos y exonerados'),
            (74, 'Menos: Otros gastos no deducibles'),
        ]

        total_expense_exclusions = 0
        for casilla, descripcion in expense_exclusions:
            worksheet.merge_range(row, 0, row, 2, descripcion, fmt_desc)
            worksheet.write(row, 3, casilla, fmt_code)
            valor = self._get_cell_balance(casilla)
            worksheet.write(row, 4, valor, fmt_number)
            worksheet.write(row, 5, '', fmt_white)
            total_expense_exclusions += valor
            row += 1

        # Casilla 84: TOTAL GASTOS DEDUCIBLES
        total_84 = total_83 - total_expense_exclusions
        worksheet.merge_range(row, 0, row, 2, 
            'G- TOTAL DE GASTOS DEDUCIBLES (Diferencia entre la casilla 83 y el resultado de la\nsumatoria de las casillas 66 al 74)', 
            fmt_title)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, total_84, fmt_number)
        row += 1

        # Casilla 85: RENTA NETA ANTES DE DEDUCCIÓN
        total_85 = total_82 - total_84
        worksheet.merge_range(row, 0, row, 2, 
            'H- RENTA NETA ANTES DE LA DEDUCCIÓN DE LOS INTERESES SEÑALADOS EN EL\nNUMERAL 23 DEL ART. 15 DE LA LEY (Diferencia entre la casilla 82 y 84)', 
            fmt_title)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, total_85, fmt_number)
        row += 1

        # Casilla 75: Total intereses entre vinculadas
        val_75 = self._get_cell_balance(75)
        worksheet.merge_range(row, 0, row, 2, 
            'Total de Intereses por préstamos, regalías y asistencia técnica cuando lo realicen el\nsocio o accionista de la empresa, la casa matriz u otras sucursales o agencias del\nexterior, o entre empresas vinculadas', 
            fmt_desc)
        worksheet.write(row, 3, 75, fmt_code)
        worksheet.write(row, 4, val_75, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla 76: Porción deducible (máximo 30% de casilla 85)
        val_76 = min(val_75, total_85 * 0.30) if total_85 > 0 else 0
        worksheet.merge_range(row, 0, row, 2, 
            'Porción deducible del monto declarado en la casilla 75, correspondiente a Intereses\npor préstamos, regalías y asistencia técnica cuando lo realicen el socio o accionista de\nla empresa, la casa matriz u otras sucursales o agencias del exterior, o entre empresas\nvinculadas (No podrá superar el 30% del valor de la casilla 85)', 
            fmt_desc)
        worksheet.write(row, 3, 76, fmt_code)
        worksheet.write(row, 4, val_76, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla 86: RENTA NETA DESPUÉS DE DEDUCCIÓN
        total_86 = total_85 - val_76
        worksheet.merge_range(row, 0, row, 2, 
            'I- RENTA NETA DESPUÉS DE LA DEDUCCIÓN DE LOS INTERESES SEÑALADOS EN EL\nNUMERAL 23 DEL ART. 15 DE LA LEY (Diferencia entre la casilla 85 y 76)', 
            fmt_title)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, total_86, fmt_number)
        row += 1

        # === RUBRO 2 - TRANSFORMACIÓN Y VALUACIÓN DE ACTIVOS ===
        row += 1
        worksheet.merge_range(row, 0, row, 5, 
            'RUBRO 2 - TRANSFORMACIÓN Y VALUACIÓN DE ACTIVOS', 
            fmt_title)
        row += 1

        # Casilla a (262): Aumento por transformación
        val_262 = self._get_cell_balance(262)
        worksheet.write(row, 0, 'a', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Aumento por transformación biológica de animales vivos y de plantas, incluido el procreo y la\nexplotación forestal, así como por la valuación de Activos Biológicos', 
            fmt_desc)
        worksheet.write(row, 3, 262, fmt_code)
        worksheet.write(row, 4, val_262, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla b (263): Disminución por transformación
        val_263 = self._get_cell_balance(263)
        worksheet.write(row, 0, 'b', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Disminución por transformación y valuación de Activos Biológicos', 
            fmt_desc)
        worksheet.write(row, 3, 263, fmt_code)
        worksheet.write(row, 4, val_263, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla c: Aumento patrimonial por revaluaciones
        val_c = self._get_cell_balance(264)
        worksheet.write(row, 0, 'c', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Aumento patrimonial por revaluaciones del valor de acciones, revaluaciones técnicas o extraordinarias\nde los bienes del activo fijo e intangibles', 
            fmt_desc)
        worksheet.write(row, 3, '', fmt_code)
        worksheet.write(row, 4, val_c, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla d: Disminución patrimonial
        val_d = self._get_cell_balance(265)
        worksheet.write(row, 0, 'd', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Disminución patrimonial del valor de acciones y de los bienes del activo fijo e intangibles', 
            fmt_desc)
        worksheet.write(row, 3, '', fmt_code)
        worksheet.write(row, 4, val_d, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # === RUBRO 3 - AJUSTES POR PRECIOS DE TRANSFERENCIA ===
        row += 1
        worksheet.merge_range(row, 0, row, 5, 
            'RUBRO 3 - AJUSTES POR PRECIOS DE TRANSFERENCIA', 
            fmt_title)
        row += 1

        # Casilla a (87): Ajustes numerales 1 al 6
        val_87_1 = self._get_cell_balance(871)
        worksheet.write(row, 0, 'a', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Renta Neta equivalente al monto total de ajuste por precios de transferencia determinados\n(Numerales 1 al 6 del Artículo 38 de la Ley N° 6380/2019)', 
            fmt_desc)
        worksheet.write(row, 3, '', fmt_code)
        worksheet.write(row, 4, val_87_1, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla b (87): Ajuste numeral 7
        val_87_2 = self._get_cell_balance(872)
        worksheet.write(row, 0, 'b', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Renta Neta equivalente al monto total de ajuste por precios de transferencia determinados (Numeral 7\ndel Artículo 38 de la Ley N° 6380/2019)', 
            fmt_desc)
        worksheet.write(row, 3, '', fmt_code)
        worksheet.write(row, 4, val_87_2, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # === RUBRO 4 - RESULTADO DEL EJERCICIO ===
        row += 1
        worksheet.merge_range(row, 0, row, 5, 
            'RUBRO 4 - RESULTADO DEL EJERCICIO', 
            fmt_title)
        row += 1

        # Encabezados
        worksheet.write(row, 0, 'INC', fmt_title)
        worksheet.merge_range(row, 1, row, 2, '', fmt_title)
        worksheet.merge_range(row, 3, row, 4, 'IMPORTE', fmt_title)
        worksheet.write(row, 5, '', fmt_title)
        row += 1

        worksheet.write(row, 0, '', fmt_title)
        worksheet.merge_range(row, 1, row, 2, '', fmt_title)
        worksheet.merge_range(row, 3, row, 4, 'PÉRDIDA\n-I-', fmt_title)
        worksheet.write(row, 5, 'UTILIDAD\n-II-', fmt_title)
        row += 1

        # Casilla a (91/93): Resultado contable
        val_91 = self._get_cell_balance(91)  # Pérdida contable
        val_93 = self._get_cell_balance(93)  # Utilidad contable
        worksheet.write(row, 0, 'a', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 'Resultado contable del ejercicio', fmt_desc)
        worksheet.write(row, 3, 91, fmt_code)
        worksheet.write(row, 4, val_91, fmt_number)
        worksheet.write(row, 5, val_93, fmt_number)
        row += 1

        # Casilla b (92/94): Resultado fiscal
        # El resultado fiscal viene del Rubro 2 y 3
        ajuste_rubro2 = val_262 - val_263 + val_c - val_d
        ajuste_rubro3 = val_87_1 + val_87_2
        resultado_fiscal = total_86 + ajuste_rubro2 + ajuste_rubro3
        
        val_92 = abs(resultado_fiscal) if resultado_fiscal < 0 else 0  # Pérdida fiscal
        val_94 = resultado_fiscal if resultado_fiscal > 0 else 0  # Utilidad fiscal
        
        worksheet.write(row, 0, 'b', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 'Resultado fiscal del ejercicio', fmt_desc)
        worksheet.write(row, 3, 92, fmt_code)
        worksheet.write(row, 4, val_92, fmt_number)
        worksheet.write(row, 5, val_94, fmt_number)
        row += 1

        # === RUBRO 5 - DETERMINACIÓN DE LA RENTA NETA Y PÉRDIDA ARRASTRABLE ===
        row += 1
        worksheet.merge_range(row, 0, row, 5, 
            'RUBRO 5 - DETERMINACIÓN DE LA RENTA NETA Y PÉRDIDA ARRASTRABLE', 
            fmt_title)
        row += 1

        # Encabezados
        worksheet.write(row, 0, 'INC', fmt_title)
        worksheet.merge_range(row, 1, row, 2, '', fmt_title)
        worksheet.merge_range(row, 3, row, 4, 'IMPORTE', fmt_title)
        worksheet.write(row, 5, '', fmt_title)
        row += 1

        worksheet.write(row, 0, '', fmt_title)
        worksheet.merge_range(row, 1, row, 2, '', fmt_title)
        worksheet.merge_range(row, 3, row, 4, 'CONTRIBUYENTE\n-I-', fmt_title)
        worksheet.write(row, 5, 'FISCO\n-II-', fmt_title)
        row += 1

        # Casilla a (102): Resultado Fiscal/Utilidad
        worksheet.write(row, 0, 'a', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Resultado Fiscal del Ejercicio/Utilidad (Proviene del Rubro 4, casilla 94)', 
            fmt_desc)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, val_94, fmt_number)
        row += 1

        # Casilla b (95): Resultado Fiscal/Pérdida
        worksheet.write(row, 0, 'b', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Resultado Fiscal del Ejercicio/Pérdida (Proviene del Rubro 4, casilla 92)', 
            fmt_desc)
        worksheet.write(row, 3, 95, fmt_code)
        worksheet.write(row, 4, val_92, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla c (96): Pérdida de ejercicios anteriores
        val_96 = self._get_cell_balance(96)
        worksheet.write(row, 0, 'c', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'PÉRDIDA DE EJERCICIOS ANTERIORES (El contribuyente deberá tener en cuenta\nque la pérdida declarada en el presente Inciso, esté dentro del plazo legal\nprevisto en la Ley)', 
            fmt_desc)
        worksheet.write(row, 3, 96, fmt_code)
        worksheet.write(row, 4, val_96, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla d (97): Pérdida total acumulada
        val_97 = val_92 + val_96
        worksheet.write(row, 0, 'd', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'PÉRDIDA TOTAL ACUMULADA (Sumatoria de las casillas 95 y 96)', 
            fmt_desc)
        worksheet.write(row, 3, 97, fmt_code)
        worksheet.write(row, 4, val_97, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla e (98): Pérdida fuera de 5 años
        val_98 = self._get_cell_balance(98)
        worksheet.write(row, 0, 'e', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Menos: Pérdida que al cierre del presente ejercicio quedó por fuera de los 5\n(cinco) años', 
            fmt_desc)
        worksheet.write(row, 3, 98, fmt_code)
        worksheet.write(row, 4, val_98, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla f (99): Saldo de pérdidas compensables
        val_99 = val_97 - val_98
        worksheet.write(row, 0, 'f', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'SALDO DE PÉRDIDAS COMPENSABLES AL CIERRE DEL PRESENTE\nEJERCICIO (Diferencia entre las casillas 97 y 98).', 
            fmt_desc)
        worksheet.write(row, 3, 99, fmt_code)
        worksheet.write(row, 4, val_99, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla g (100): Pérdida que se compensa (máximo 20% de renta neta)
        val_100 = min(val_99, val_94 * 0.20) if val_94 > 0 else 0
        worksheet.write(row, 0, 'g', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Menos: Pérdida que se compensa en el presente ejercicio fiscal (No podrá\nexceder el 20 % de la Renta Neta: casilla 102)', 
            fmt_desc)
        worksheet.write(row, 3, 100, fmt_code)
        worksheet.write(row, 4, val_100, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla h (101): Saldo de pérdida al cierre
        val_101 = val_99 - val_100
        worksheet.write(row, 0, 'h', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'SALDO DE PÉRDIDA AL CIERRE DEL PRESENTE EJERCICIO (Diferencia entre las\ncasillas 99 y 100). Monto a trasladar en la casilla 96 del presente rubro de la\nDeclaración Jurada del siguiente ejercicio fiscal', 
            fmt_desc)
        worksheet.write(row, 3, 101, fmt_code)
        worksheet.write(row, 4, val_101, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla i (103): Renta neta del ejercicio
        val_103 = val_94 - val_100
        worksheet.write(row, 0, 'i', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'RENTA NETA DEL EJERCICIO (Diferencia entre las casillas 102 y 100, cuando la\ncasilla 102 sea mayor)', 
            fmt_desc)
        worksheet.write(row, 3, 103, fmt_code)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, val_103, fmt_number)
        row += 1

        # === RUBRO 6 - DETERMINACIÓN DE LA RENTA NETA PARA BENEFICIOS ESPECIALES ===
        row += 1
        worksheet.merge_range(row, 0, row, 5, 
            'RUBRO 6 - DETERMINACIÓN DE LA RENTA NETA PARA QUIENES CUENTEN CON\nRENTAS ALCANZADAS POR BENEFICIOS ESPECIALES', 
            fmt_title)
        row += 1

        # Encabezados
        worksheet.write(row, 0, 'INC', fmt_title)
        worksheet.merge_range(row, 1, row, 2, '', fmt_title)
        worksheet.merge_range(row, 3, row, 4, 'IMPORTE', fmt_title)
        worksheet.write(row, 5, '', fmt_title)
        row += 1

        worksheet.write(row, 0, '', fmt_title)
        worksheet.merge_range(row, 1, row, 2, '', fmt_title)
        worksheet.merge_range(row, 3, row, 4, 'DEDUCCIONES\n-I-', fmt_title)
        worksheet.write(row, 5, 'FISCO\n-II-', fmt_title)
        row += 1

        # Casilla a (105): Renta Neta del Ejercicio
        worksheet.write(row, 0, 'a', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Renta Neta del Ejercicio (Proviene de la casilla 103 del Rubro 5)', 
            fmt_desc)
        worksheet.write(row, 3, '', fmt_white)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, val_103, fmt_number)
        row += 1

        # Casilla b (104): Renta alcanzada por beneficios especiales
        val_104 = self._get_cell_balance(104)
        worksheet.write(row, 0, 'b', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Renta Neta alcanzada por beneficios especiales vigentes', 
            fmt_desc)
        worksheet.write(row, 3, 104, fmt_code)
        worksheet.write(row, 4, val_104, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla c (106): Renta neta imponible
        val_106 = val_103 - val_104
        worksheet.write(row, 0, 'c', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'RENTA NETA IMPONIBLE (Diferencia entre las casillas 105 y 104, cuando la\ncasilla 105 sea mayor)', 
            fmt_desc)
        worksheet.write(row, 3, 106, fmt_code)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, val_106, fmt_number)
        row += 1

        # === RUBRO 7 - DETERMINACIÓN DE LA RENTA PRESUNTA ===
        row += 1
        worksheet.merge_range(row, 0, row, 5, 
            'RUBRO 7 - DETERMINACIÓN DE LA RENTA PRESUNTA PARA CONTRIBUYENTES QUE OPTEN LIQUIDAR EL IMPUESTO\nCONFORME AL ARTÍCULO 19 DE LA LEY', 
            fmt_title)
        row += 1

        # Casilla a (107): Ingresos gravados forestación/inmuebles
        val_107 = self._get_cell_balance(107)
        worksheet.write(row, 0, 'a', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Ingresos gravados obtenidos de actividades de forestación o enajenación de inmuebles urbanos y\nrurales que formen parte del activo fijo', 
            fmt_desc)
        worksheet.write(row, 3, 107, fmt_code)
        worksheet.write(row, 4, val_107, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla b (108): Renta neta presunta (30%)
        val_108 = val_107 * 0.30
        worksheet.write(row, 0, 'b', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'RENTA NETA PRESUNTA (30% de la casilla 107)', 
            fmt_desc)
        worksheet.write(row, 3, 108, fmt_code)
        worksheet.write(row, 4, val_108, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # === RUBRO 8 - DETERMINACIÓN DEL IMPUESTO Y LIQUIDACIÓN FINAL ===
        row += 1
        worksheet.merge_range(row, 0, row, 5, 
            'RUBRO 8 - DETERMINACIÓN DEL IMPUESTO Y LIQUIDACIÓN FINAL', 
            fmt_title)
        row += 1

        # Encabezados
        worksheet.write(row, 0, 'INC', fmt_title)
        worksheet.merge_range(row, 1, row, 2, '', fmt_title)
        worksheet.merge_range(row, 3, row, 4, 'IMPORTE', fmt_title)
        worksheet.write(row, 5, '', fmt_title)
        row += 1

        worksheet.write(row, 0, '', fmt_title)
        worksheet.merge_range(row, 1, row, 2, '', fmt_title)
        worksheet.merge_range(row, 3, row, 4, 'CONTRIBUYENTE\n-I-', fmt_title)
        worksheet.write(row, 5, 'FISCO\n-II-', fmt_title)
        row += 1

        # Casilla a (116): Impuesto sobre renta neta imponible (10%)
        val_116 = (val_106 + val_108) * 0.10
        worksheet.write(row, 0, 'a', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Impuesto determinado sobre la Renta Neta Imponible y la Renta Neta Presunta\n(10% sobre la sumatoria de las casillas 106 y 108)', 
            fmt_desc)
        worksheet.write(row, 3, 116, fmt_code)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, val_116, fmt_number)
        row += 1

        # Casilla b (117): Impuesto sobre beneficios especiales
        tasa_beneficio = 0.05  # Ejemplo: 5%, debe venir de configuración
        val_117 = val_104 * tasa_beneficio
        worksheet.write(row, 0, 'b', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Impuesto determinado aplicable sobre la renta neta alcanzadas por beneficios\nespeciales (%s sobre el monto de la casilla 104 del Rubro 6)' % (tasa_beneficio * 100), 
            fmt_desc)
        worksheet.write(row, 3, 117, fmt_code)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, val_117, fmt_number)
        row += 1

        # Casilla c (118): Subtotal impuestos
        val_118 = val_116 + val_117
        worksheet.write(row, 0, 'c', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'SUBTOTAL (Sumatoria de las casillas 116 y 117)', 
            fmt_desc)
        worksheet.write(row, 3, 118, fmt_code)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, val_118, fmt_number)
        row += 1

        # Casilla d (109): Impuesto pagado en el exterior
        val_109 = self._get_cell_balance(109)
        worksheet.write(row, 0, 'd', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Impuesto a la Renta pagado en el exterior aplicado al IRE, para evitar la doble\nimposición', 
            fmt_desc)
        worksheet.write(row, 3, 109, fmt_code)
        worksheet.write(row, 4, val_109, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla e (120): Total impuesto determinado
        val_120 = val_118 - val_109
        worksheet.write(row, 0, 'e', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'TOTAL IMPUESTO DETERMINADO (Casillas 118 - 109)', 
            fmt_desc)
        worksheet.write(row, 3, 120, fmt_code)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, val_120, fmt_number)
        row += 1

        # Casilla f (110): Saldo a favor ejercicio anterior
        val_110 = self._get_cell_balance(110)
        worksheet.write(row, 0, 'f', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Saldo a favor del contribuyente del ejercicio anterior (Proviene de la casilla 115\ndel presente Rubro de la Declaración Jurada del ejercicio fiscal anterior)', 
            fmt_desc)
        worksheet.write(row, 3, 110, fmt_code)
        worksheet.write(row, 4, val_110, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla g (111): Retenciones
        val_111 = self._get_cell_balance(111)
        worksheet.write(row, 0, 'g', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Retenciones computables a favor del Contribuyente', 
            fmt_desc)
        worksheet.write(row, 3, 111, fmt_code)
        worksheet.write(row, 4, val_111, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla h (112): Percepciones
        val_112 = self._get_cell_balance(112)
        worksheet.write(row, 0, 'h', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Percepciones computables a favor del Contribuyente', 
            fmt_desc)
        worksheet.write(row, 3, 112, fmt_code)
        worksheet.write(row, 4, val_112, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla i (113): Anticipos ingresados
        val_113 = self._get_cell_balance(113)
        worksheet.write(row, 0, 'i', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Anticipos ingresados', 
            fmt_desc)
        worksheet.write(row, 3, 113, fmt_code)
        worksheet.write(row, 4, val_113, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla j (121): Multa
        val_121 = self._get_cell_balance(121)
        worksheet.write(row, 0, 'j', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Multa por presentar la Declaración Jurada con posterioridad al vencimiento', 
            fmt_desc)
        worksheet.write(row, 3, 121, fmt_code)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, val_121, fmt_number)
        row += 1

        # Casilla k (114/122): Subtotal
        val_114 = val_110 + val_111 + val_112 + val_113
        val_122 = val_120 + val_121
        worksheet.write(row, 0, 'k', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'SUBTOTAL (Columna I: Sumatoria de las casillas 110 al 113); (Columna II:\nSumatoria de las casillas 120 y 121)', 
            fmt_desc)
        worksheet.write(row, 3, 114, fmt_code)
        worksheet.write(row, 4, val_114, fmt_number)
        worksheet.write(row, 5, val_122, fmt_number)
        row += 1

        # Casilla l (115): Saldo a favor del contribuyente
        val_115 = max(val_114 - val_122, 0)
        worksheet.write(row, 0, 'l', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'SALDO A FAVOR DEL CONTRIBUYENTE (Monto a trasladar al siguiente ejercicio\nfiscal en la casilla 110 del presente Rubro). Diferencia entre las casillas 114 y\n122, cuando la casilla 114 sea mayor', 
            fmt_desc)
        worksheet.write(row, 3, 115, fmt_code)
        worksheet.write(row, 4, val_115, fmt_number)
        worksheet.write(row, 5, '', fmt_white)
        row += 1

        # Casilla m (123): Saldo a ingresar a favor del fisco
        val_123 = max(val_122 - val_114, 0)
        worksheet.write(row, 0, 'm', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'SALDO A INGRESAR A FAVOR DEL FISCO (Diferencia entre las casillas 122 y 114,\ncuando la casilla 122 sea mayor)', 
            fmt_desc)
        worksheet.write(row, 3, 123, fmt_code)
        worksheet.write(row, 4, '', fmt_white)
        worksheet.write(row, 5, val_123, fmt_number)
        row += 1

        # === RUBRO 9 - DETERMINACIÓN DE ANTICIPOS ===
        row += 1
        worksheet.merge_range(row, 0, row, 5, 
            'RUBRO 9 - DETERMINACIÓN DE ANTICIPOS PARA EL SIGUIENTE EJERCICIO FISCAL', 
            fmt_title)
        row += 1

        worksheet.write(row, 0, 'INC', fmt_title)
        worksheet.merge_range(row, 1, row, 2, '', fmt_title)
        worksheet.merge_range(row, 3, row, 5, 'IMPORTE', fmt_title)
        row += 1

        # Casilla a (124): Impuesto liquidado
        worksheet.write(row, 0, 'a', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Impuesto liquidado del ejercicio (Proviene de la casilla 120 del Rubro 8)', 
            fmt_desc)
        worksheet.write(row, 3, 124, fmt_code)
        worksheet.merge_range(row, 4, row, 5, val_120, fmt_number)
        row += 1

        # Casilla b (125): Retenciones y Percepciones
        val_125 = val_111 + val_112
        worksheet.write(row, 0, 'b', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Retenciones y Percepciones computables (Proviene de la sumatoria de las casillas 111 y 112)', 
            fmt_desc)
        worksheet.write(row, 3, 125, fmt_code)
        worksheet.merge_range(row, 4, row, 5, val_125, fmt_number)
        row += 1

        # Casilla c (126): Anticipos a ingresar
        val_126 = max(val_120 - val_125, 0)
        worksheet.write(row, 0, 'c', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Anticipos a ingresar para el siguiente ejercicio (Diferencia entre las casillas 124 y 125, cuando el monto\nde la casilla 124 sea mayor)', 
            fmt_desc)
        worksheet.write(row, 3, 126, fmt_code)
        worksheet.merge_range(row, 4, row, 5, val_126, fmt_number)
        row += 1

        # Casilla d (127): Saldo a favor a considerar
        val_127 = min(val_115, val_126)
        worksheet.write(row, 0, 'd', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Saldo a favor del contribuyente del ejercicio que se liquida (Proviene de la casilla 115. Consignar hasta\nel monto de la casilla 126)', 
            fmt_desc)
        worksheet.write(row, 3, 127, fmt_code)
        worksheet.merge_range(row, 4, row, 5, val_127, fmt_number)
        row += 1

        # Casilla e (128): Cuotas de anticipos
        val_128 = (val_126 - val_127) * 0.25
        worksheet.write(row, 0, 'e', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Cuotas de anticipos a ingresar. (Casilla 126 - casilla 127) x 25%', 
            fmt_desc)
        worksheet.write(row, 3, 128, fmt_code)
        worksheet.merge_range(row, 4, row, 5, val_128, fmt_number)
        row += 1

        # === RUBRO 10 - INFORMACIÓN COMPLEMENTARIA ===
        row += 1
        worksheet.merge_range(row, 0, row, 5, 
            'RUBRO 10 - INFORMACIÓN COMPLEMENTARIA', 
            fmt_title)
        row += 1

        worksheet.write(row, 0, 'INC', fmt_title)
        worksheet.merge_range(row, 1, row, 5, '', fmt_title)
        row += 1

        # Casilla a (129): RUC/CI del Contador
        worksheet.write(row, 0, 'a', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'RUC o Cédula de Identidad Civil del Contador, sin incluir el dígito verificador', 
            fmt_desc)
        worksheet.write(row, 3, 129, fmt_code)
        worksheet.merge_range(row, 4, row, 5, self.contador_ruc or '', fmt_input)
        row += 1

        # Casilla b (130): RUC del Auditor
        worksheet.write(row, 0, 'b', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'RUC del Auditor o de la Empresa Auditora, sin incluir el dígito verificador', 
            fmt_desc)
        worksheet.write(row, 3, 130, fmt_code)
        worksheet.merge_range(row, 4, row, 5, self.auditor_ruc or '', fmt_input)
        row += 1

        # Casilla c (131): Cantidad de personal
        worksheet.write(row, 0, 'c', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Cantidad total de personal ocupado en relación de dependencia al cierre del ejercicio', 
            fmt_desc)
        worksheet.write(row, 3, 131, fmt_code)
        worksheet.merge_range(row, 4, row, 5, self.total_empleados or 0, fmt_input)
        row += 1

        # Casilla d (132): Número disposición legal beneficio
        worksheet.write(row, 0, 'd', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Número de la disposición legal que respalda el beneficio fiscal declarado en el Rubro 6, casilla 104', 
            fmt_desc)
        worksheet.write(row, 3, 132, fmt_code)
        worksheet.merge_range(row, 4, row, 5, self.beneficio_fiscal_numero or '', fmt_input)
        row += 1

        # Casilla e (133): Año disposición legal
        worksheet.write(row, 0, 'e', fmt_label)
        worksheet.merge_range(row, 1, row, 2, 
            'Año de la disposición legal que se referencia en la casilla 132.', 
            fmt_desc)
        worksheet.write(row, 3, 133, fmt_code)
        worksheet.merge_range(row, 4, row, 5, self.beneficio_fiscal_anio or '', fmt_input)
        row += 1

        # === NOTA FINAL ===
        row += 1
        worksheet.merge_range(row, 0, row, 5, 
            'Estimado Contribuyente: Le recordamos que los pagos que efectúe emergentes de esta declaración, serán imputados en su cuenta\ncorriente conforme a lo señalado en la Ley N° 125/1991, Art. 162', 
            fmt_desc)

        # Cerrar y retornar
        workbook.close()
        output.seek(0)
        return output.read()

    def action_generate_f500(self):
        """
        Genera el archivo Excel del Formulario 500
        """
        self.ensure_one()
        
        # Validaciones
        if not self.company_id:
            raise UserError(_('Debe seleccionar una compañía.'))
        
        if not self.date_from or not self.date_to:
            raise UserError(_('Debe seleccionar un período fiscal válido.'))
        
        if self.date_from > self.date_to:
            raise UserError(_('La fecha de inicio no puede ser mayor a la fecha de fin.'))
        
        # Verificar que hay cuentas configuradas
        accounts_configured = self.env['account.account'].search_count([
            ('company_id', '=', self.company_id.id),
            ('f500_category_id', '!=', False)
        ])

        if accounts_configured == 0:
            raise UserError(_(
                'No hay cuentas configuradas para el Formulario 500.\n'
                'Por favor, asigne categorías F500 a sus cuentas contables en:\n'
                'Contabilidad → Configuración → Plan contable'
            ))
        
        # Generar archivo Excel
        excel_data = self._create_excel_file()
        
        # Generar nombre del archivo
        file_name = 'F500_IRE_{}_{}.xlsx'.format(
            self.ruc.replace('-', '_') if self.ruc else 'SIN_RUC',
            self.exercise_year or fields.Date.today().year
        )
        
        # Guardar archivo y actualizar estado
        self.write({
            'file_data': base64.b64encode(excel_data),
            'file_name': file_name,
            'state': 'done'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
        }

    def action_download_file(self):
        """
        Descarga el archivo generado
        """
        self.ensure_one()
        
        if not self.file_data:
            raise UserError(_('No hay archivo generado para descargar.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=%s&id=%s&filename_field=file_name&field=file_data&download=true' % (
                self._name, self.id
            ),
            'target': 'self',
        }