# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO
from datetime import datetime

_logger = logging.getLogger(__name__)

# Importar xlsxwriter con manejo de errores
try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
    _logger.info("xlsxwriter importado correctamente")
except ImportError as e:
    XLSXWRITER_AVAILABLE = False
    _logger.error("xlsxwriter no disponible: %s", str(e))


class InformeRendimientoWizard(models.TransientModel):
    _name = 'informe.rendimiento.wizard'
    _description = 'Asistente para Informe de Rendimiento'

    fecha_desde = fields.Date(
        string='Fecha Desde',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    fecha_hasta = fields.Date(
        string='Fecha Hasta',
        required=True,
        default=fields.Date.today()
    )
    user_ids = fields.Many2many(
        'res.users',
        string='Usuarios',
        help='Dejar vacío para incluir todos los usuarios con horas'
    )
    todos_empleados = fields.Boolean(
        string='Todos los Usuarios',
        default=True
    )
    project_ids = fields.Many2many(
        'project.project',
        string='Proyectos',
        help='Dejar vacío para incluir todos los proyectos'
    )
    solo_proyectos_con_horas = fields.Boolean(
        string='Solo Proyectos con Horas Cargadas',
        default=True
    )
    excel_file = fields.Binary(
        string='Archivo Excel'
    )
    excel_filename = fields.Char(
        string='Nombre del Archivo'
    )
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('generado', 'Generado')
    ], default='borrador')

    @api.onchange('todos_empleados')
    def _onchange_todos_empleados(self):
        if self.todos_empleados:
            self.user_ids = [(5, 0, 0)]

    def generar_reporte(self):
        """Genera el reporte de rendimiento en formato Excel"""
        _logger.info("=== INICIO generar_reporte ===")
        _logger.info("Wizard ID: %s", self.id)
        _logger.info("Context: %s", self.env.context)
        
        try:
            self.ensure_one()
            _logger.info("ensure_one() ejecutado correctamente")

            # Validar fechas
            if self.fecha_desde > self.fecha_hasta:
                raise UserError(_('La fecha desde no puede ser mayor a la fecha hasta'))
            _logger.info("Validación de fechas OK")

            # Preparar el archivo Excel
            _logger.info("Iniciando creación del archivo Excel")
            if not XLSXWRITER_AVAILABLE:
                raise UserError(_('La librería xlsxwriter no está disponible. Por favor, instálela con: pip install xlsxwriter'))
            
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('RENDIMIENTO X HORA')
            _logger.info("Workbook creado correctamente")

            # Formatos
            formato_encabezado = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            formato_celda = workbook.add_format({
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            formato_numero = workbook.add_format({
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'num_format': '#,##0.00'
            })
            formato_total = workbook.add_format({
                'bold': True,
                'bg_color': '#FFFF00',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'num_format': '#,##0.00'
            })
            formato_proyecto = workbook.add_format({
                'border': 1,
                'align': 'left',
                'valign': 'vcenter'
            })
            formato_horas_utilizado = workbook.add_format({
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'italic': True
            })

            # Obtener datos
            usuarios = self._get_usuarios()
            proyectos = self._get_proyectos()
            datos_horas = self._get_datos_horas_por_usuario(usuarios, proyectos)

            if not usuarios:
                raise UserError(_('No se encontraron usuarios con los filtros seleccionados'))

            # Crear estructura básica del reporte
            worksheet.write(0, 0, 'Proyecto', formato_encabezado)
            col = 1
            for usuario in usuarios:
                worksheet.write(0, col, usuario.name, formato_encabezado)
                col += 1
            # Columnas adicionales
            worksheet.write(0, col, 'Total Horas', formato_encabezado)
            worksheet.write(0, col + 1, 'Honorario', formato_encabezado)
            worksheet.write(0, col + 2, 'Costos', formato_encabezado)
            worksheet.write(0, col + 3, 'Diferencia', formato_encabezado)

            # Segunda fila: Costo x hora por empleado
            worksheet.write(1, 0, 'COSTO X HORA', formato_encabezado)
            for idx, usuario in enumerate(usuarios):
                costo = getattr(getattr(usuario, 'employee_id', False), 'timesheet_cost', 0.0) or 0.0
                worksheet.write(1, idx + 1, costo, formato_numero)

            # Tercera fila: Total horas por empleado (se completará después de cargar filas)
            worksheet.write(2, 0, 'TOTAL HORA EMPLEADO', formato_encabezado)

            # Escribir datos de proyectos
            fila = 3
            for proyecto in proyectos:
                worksheet.write(fila, 0, proyecto.name, formato_proyecto)
                total_horas_proyecto = 0
                costo_total_proyecto = 0
                
                for idx, usuario in enumerate(usuarios):
                    horas = datos_horas.get((proyecto.id, usuario.id), 0.0)
                    worksheet.write(fila, idx + 1, horas, formato_numero)
                    total_horas_proyecto += horas
                    costo_empleado = getattr(getattr(usuario, 'employee_id', False), 'timesheet_cost', 0.0) or 0.0
                    costo_total_proyecto += horas * costo_empleado
                
                # Totales y columnas financieras
                worksheet.write(fila, col, total_horas_proyecto, formato_numero)
                # Honorario (dejar en blanco para completar manualmente)
                worksheet.write(fila, col + 1, None, formato_numero)
                # Costos calculados
                worksheet.write(fila, col + 2, costo_total_proyecto, formato_total)
                # Diferencia = Honorario - Costos (formula)
                honorario_cell = xlsxwriter.utility.xl_rowcol_to_cell(fila, col + 1)
                costos_cell = xlsxwriter.utility.xl_rowcol_to_cell(fila, col + 2)
                worksheet.write_formula(fila, col + 3, f"={honorario_cell}-{costos_cell}", formato_total)
                fila += 1

            # Completar totales por empleado (fila 2)
            for idx, _usuario in enumerate(usuarios):
                col_letra_inicio = xlsxwriter.utility.xl_rowcol_to_cell(3, idx + 1)
                col_letra_fin = xlsxwriter.utility.xl_rowcol_to_cell(fila - 1, idx + 1)
                worksheet.write_formula(2, idx + 1, f"=SUM({col_letra_inicio}:{col_letra_fin})", formato_total)
            # Total general de horas por proyecto (columna 'Total Horas') ya cargado por fila

            # Cerrar el archivo
            workbook.close()
            output.seek(0)
            _logger.info("Archivo Excel generado correctamente")

            # Guardar el archivo en el wizard
            filename = 'Informe_Rendimiento_%s_%s.xlsx' % (
                self.fecha_desde.strftime('%Y%m%d'),
                self.fecha_hasta.strftime('%Y%m%d')
            )

            # Preparar datos para guardar
            _logger.info("Preparando datos para guardar")
            excel_data = base64.b64encode(output.read())
            _logger.info("Datos Excel codificados, tamaño: %s bytes", len(excel_data))
            
            # Actualizar los campos usando el ORM con sudo() para evitar restricciones
            _logger.info("Actualizando campos del wizard usando ORM")
            self.sudo().write({
                'excel_file': excel_data,
                'excel_filename': filename,
                'estado': 'generado'
            })
            _logger.info("Campos actualizados correctamente")

            # Retornar acción para descargar el archivo directamente
            _logger.info("Preparando acción de retorno")
            action = {
                'type': 'ir.actions.act_url',
                'url': '/web/content?model=informe.rendimiento.wizard&id=%s&field=excel_file&filename_field=excel_filename&download=true' % self.id,
                'target': 'self',
            }
            _logger.info("=== FIN generar_reporte EXITOSO ===")
            return action
            
        except Exception as e:
            _logger.error("=== ERROR en generar_reporte ===")
            _logger.error("Tipo de error: %s", type(e).__name__)
            _logger.error("Mensaje de error: %s", str(e))
            _logger.error("Traceback completo:", exc_info=True)
            raise

    def generar_reporte_simple(self):
        """Versión simplificada que evita problemas con create()"""
        _logger.info("=== INICIO generar_reporte_simple ===")
        
        try:
            if not XLSXWRITER_AVAILABLE:
                raise UserError(_('La librería xlsxwriter no está disponible. Por favor, instálela con: pip install xlsxwriter'))
            
            # Generar el archivo Excel
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('RENDIMIENTO X HORA')
            
            # Escribir datos básicos
            worksheet.write(0, 0, 'Informe de Rendimiento')
            worksheet.write(1, 0, f'Fecha desde: {self.fecha_desde}')
            worksheet.write(2, 0, f'Fecha hasta: {self.fecha_hasta}')
            
            workbook.close()
            output.seek(0)
            
            # Crear el archivo de respuesta directamente
            filename = f'Informe_Rendimiento_{self.fecha_desde.strftime("%Y%m%d")}_{self.fecha_hasta.strftime("%Y%m%d")}.xlsx'
            
            # Retornar acción de descarga directa sin tocar la base de datos
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content?model=informe.rendimiento.wizard&id={self.id}&field=excel_file&filename_field=excel_filename&download=true',
                'target': 'self',
            }
            
        except Exception as e:
            _logger.error("Error en generar_reporte_simple: %s", str(e))
            raise UserError(f'Error al generar el reporte: {str(e)}')

    def test_basic(self):
        """Método de prueba básico sin Excel"""
        _logger.info("=== INICIO test_basic ===")
        
        try:
            # Validar fechas
            if self.fecha_desde > self.fecha_hasta:
                raise UserError(_('La fecha desde no puede ser mayor a la fecha hasta'))
            
            # Obtener datos básicos
            empleados = self._get_empleados()
            proyectos = self._get_proyectos()
            
            if not empleados:
                raise UserError(_('No se encontraron empleados con los filtros seleccionados'))
            
            # Crear un archivo de texto simple
            content = f"""INFORME DE RENDIMIENTO
Fecha desde: {self.fecha_desde}
Fecha hasta: {self.fecha_hasta}

EMPLEADOS ENCONTRADOS: {len(empleados)}
PROYECTOS ENCONTRADOS: {len(proyectos)}

Lista de empleados:
"""
            for emp in empleados:
                content += f"- {emp.name}\n"
            
            content += "\nLista de proyectos:\n"
            for proj in proyectos:
                content += f"- {proj.name}\n"
            
            # Convertir a bytes
            output = BytesIO()
            output.write(content.encode('utf-8'))
            output.seek(0)
            
            # Guardar como archivo de texto
            filename = f'Informe_Rendimiento_{self.fecha_desde.strftime("%Y%m%d")}_{self.fecha_hasta.strftime("%Y%m%d")}.txt'
            
            # Usar ORM para guardar
            excel_data = base64.b64encode(output.read())
            self.sudo().write({
                'excel_file': excel_data,
                'excel_filename': filename,
                'estado': 'generado'
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content?model=informe.rendimiento.wizard&id={self.id}&field=excel_file&filename_field=excel_filename&download=true',
                'target': 'self',
            }
            
        except Exception as e:
            _logger.error("Error en test_basic: %s", str(e))
            raise UserError(f'Error al generar el reporte: {str(e)}')

    def generar_reporte_directo(self):
        """Método que genera el reporte sin usar TransientModel"""
        _logger.info("=== INICIO generar_reporte_directo ===")
        
        try:
            # Obtener datos
            empleados = self._get_empleados()
            proyectos = self._get_proyectos()
            datos_horas = self._get_datos_horas(empleados, proyectos)

            if not empleados:
                raise UserError(_('No se encontraron empleados con los filtros seleccionados'))

            # Generar el archivo Excel
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('RENDIMIENTO X HORA')

            # Formatos básicos
            formato_encabezado = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1,
                'align': 'center'
            })
            formato_numero = workbook.add_format({
                'border': 1,
                'align': 'center',
                'num_format': '#,##0.00'
            })

            # Escribir encabezados
            worksheet.write(0, 0, 'Proyecto', formato_encabezado)
            col = 1
            for empleado in empleados:
                worksheet.write(0, col, empleado.name, formato_encabezado)
                col += 1
            worksheet.write(0, col, 'Total Horas', formato_encabezado)

            # Escribir datos
            fila = 1
            for proyecto in proyectos:
                worksheet.write(fila, 0, proyecto.name)
                total_horas_proyecto = 0
                
                for idx, empleado in enumerate(empleados):
                    horas = datos_horas.get((proyecto.id, empleado.id), 0.0)
                    worksheet.write(fila, idx + 1, horas, formato_numero)
                    total_horas_proyecto += horas
                
                worksheet.write(fila, col, total_horas_proyecto, formato_numero)
                fila += 1

            workbook.close()
            output.seek(0)

            # Crear respuesta HTTP directa
            filename = f'Informe_Rendimiento_{self.fecha_desde.strftime("%Y%m%d")}_{self.fecha_hasta.strftime("%Y%m%d")}.xlsx'
            
            # Retornar acción que descarga directamente el contenido
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content?model=informe.rendimiento.wizard&id={self.id}&field=excel_file&filename_field=excel_filename&download=true',
                'target': 'self',
            }
            
        except Exception as e:
            _logger.error("Error en generar_reporte_directo: %s", str(e))
            raise UserError(f'Error al generar el reporte: {str(e)}')

    def _get_usuarios(self):
        """Obtiene los usuarios según los filtros"""
        _logger.info("Obteniendo usuarios...")
        if self.todos_empleados or not self.user_ids:
            domain = [
                ('date', '>=', self.fecha_desde),
                ('date', '<=', self.fecha_hasta),
                ('project_id', '!=', False),
            ]
            # Si el usuario filtró proyectos, respetarlos
            proyectos_filtrados = False
            if self.project_ids:
                domain.append(('project_id', 'in', self.project_ids.ids))
                proyectos_filtrados = True
            elif self.solo_proyectos_con_horas:
                # Restringir a proyectos con horas en el rango
                timesheets_proj = self.env['account.analytic.line'].sudo().read_group(
                    [
                        ('date', '>=', self.fecha_desde),
                        ('date', '<=', self.fecha_hasta),
                        ('project_id', '!=', False),
                    ],
                    ['project_id'], ['project_id']
                )
                project_ids = [r['project_id'][0] for r in timesheets_proj if r.get('project_id')]
                if project_ids:
                    domain.append(('project_id', 'in', project_ids))
                    proyectos_filtrados = True

            _logger.info("Dominio usuarios: %s", domain)

            AAL = self.env['account.analytic.line'].sudo()
            # 1) usuarios desde user_id
            rows_user = AAL.read_group(domain + [('user_id','!=',False)], ['user_id'], ['user_id'])
            user_ids = {r['user_id'][0] for r in rows_user if r.get('user_id')}
            # 2) empleados con employee_id y su user_id relacionado
            rows_emp = AAL.read_group(domain + [('employee_id','!=',False)], ['employee_id'], ['employee_id'])
            emp_ids = [r['employee_id'][0] for r in rows_emp if r.get('employee_id')]
            if emp_ids:
                emp_recs = self.env['hr.employee'].sudo().browse(emp_ids)
                mapped_user_ids = {e.user_id.id for e in emp_recs if e.user_id}
                user_ids |= {uid for uid in mapped_user_ids if uid}
            user_ids = sorted(user_ids)
            _logger.info("Usuarios encontrados (todos) count=%s ids(sample)=%s", len(user_ids), user_ids[:20])
            usuarios = self.env['res.users'].sudo().browse(user_ids).sorted(key=lambda u: u.name)
            return usuarios
        else:
            _logger.info("Usuarios seleccionados: %s", len(self.user_ids))
            return self.env['res.users'].sudo().browse(self.user_ids.ids).sorted(key=lambda u: u.name)

    def _get_proyectos(self):
        """Obtiene los proyectos según los filtros"""
        _logger.info("Obteniendo proyectos...")
        domain = []

        if self.solo_proyectos_con_horas:
            # Solo proyectos con horas en el rango de fechas
            # Usar sudo() para evitar restricciones de multi-compañía
            timesheets = self.env['account.analytic.line'].sudo().search([
                ('date', '>=', self.fecha_desde),
                ('date', '<=', self.fecha_hasta),
                ('project_id', '!=', False)
            ])
            project_ids = timesheets.mapped('project_id').ids
            domain.append(('id', 'in', project_ids))
            _logger.info("Proyectos con horas cargadas: %s", len(project_ids))

        if self.project_ids:
            if domain:
                domain = ['&'] + domain + [('id', 'in', self.project_ids.ids)]
            else:
                domain.append(('id', 'in', self.project_ids.ids))
            _logger.info("Proyectos seleccionados: %s", len(self.project_ids))

        # Usar sudo() para leer proyectos sin restricciones de compañía
        proyectos = self.env['project.project'].sudo().search(domain).sorted(key=lambda p: p.name)
        _logger.info("Total proyectos encontrados: %s", len(proyectos))
        return proyectos

    def _get_datos_horas_por_usuario(self, usuarios, proyectos):
        """Obtiene las horas trabajadas por cada usuario en cada proyecto"""
        _logger.info("Obteniendo datos de horas...")
        datos = {}

        AAL = self.env['account.analytic.line'].sudo()

        # Construir mapa empleado->usuario para sumar líneas con employee_id
        emp_to_user = {}
        if usuarios:
            emp_with_users = self.env['hr.employee'].sudo().search([('user_id','in', usuarios.ids)])
            emp_to_user = {e.id: e.user_id.id for e in emp_with_users if e.user_id}
        user_ids = usuarios.ids or []

        # 1) líneas con user_id en el conjunto
        ts_user = AAL.search([
            ('date', '>=', self.fecha_desde),
            ('date', '<=', self.fecha_hasta),
            ('project_id', 'in', proyectos.ids),
            ('user_id', 'in', user_ids),
        ])
        _logger.info("Timesheets con user_id: %s", len(ts_user))
        for t in ts_user:
            key = (t.project_id.id, t.user_id.id)
            datos[key] = datos.get(key, 0.0) + t.unit_amount

        # 2) líneas sin user_id pero con employee_id mapeable a usuario del conjunto
        emp_ids = list(emp_to_user.keys()) or []
        if emp_ids:
            ts_emp = AAL.search([
                ('date', '>=', self.fecha_desde),
                ('date', '<=', self.fecha_hasta),
                ('project_id', 'in', proyectos.ids),
                ('user_id', '=', False),
                ('employee_id', 'in', emp_ids),
            ])
            _logger.info("Timesheets con employee_id (sin user_id) mapeados: %s", len(ts_emp))
            for t in ts_emp:
                uid = emp_to_user.get(t.employee_id.id)
                if not uid:
                    continue
                key = (t.project_id.id, uid)
                datos[key] = datos.get(key, 0.0) + t.unit_amount

        _logger.info("Datos de horas procesados para %s combinaciones de proyecto/usuario", len(datos))
        return datos
