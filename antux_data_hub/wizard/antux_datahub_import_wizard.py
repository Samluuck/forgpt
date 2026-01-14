import base64
import io
import openpyxl
from datetime import datetime, date
from odoo import models, fields
from odoo.exceptions import UserError

class AntuxDataHubImportWizard(models.TransientModel):
    _name = 'antux.datahub.import.wizard'
    _description = 'Importar Planilla General'

    file = fields.Binary(string='Planilla General', required=True)
    filename = fields.Char()
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    mapping_id = fields.Many2one('antux.datahub.mapping', string='Configuración de Mapeo', required=True)

    def _to_date(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(str(value), fmt).date()
            except Exception:
                pass
        return False

    def _get_value_from_mapping(self, data_row, field_name, mapping_lines):
        """
        Busca el valor en data_row usando los alias definidos en mapping_lines para field_name.
        """
        mapping_line = mapping_lines.filtered(lambda l: l.field_id.name == field_name)
        if not mapping_line:
            return None
        
        aliases = mapping_line[0].get_aliases_list()
        
        for alias in aliases:
            if alias in data_row:
                return data_row[alias]
        
        return None

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError('Debe seleccionar un archivo Excel.')

        batch_id = self.env.context.get('active_id')
        if not batch_id:
            raise UserError('No se encontró el lote activo.')

        batch = self.env['antux.datahub.batch'].browse(batch_id)
        if not batch.exists():
            raise UserError('El lote seleccionado no existe.')

        if batch.imported:
            raise UserError('Esta planilla ya fue importada. No se permite volver a cargar datos.')

        try:
            data = base64.b64decode(self.file)
            workbook = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
            sheet = workbook.active
        except Exception as e:
            raise UserError(f'Error al leer el archivo Excel: {str(e)}')

        headers = [str(cell.value).strip() if cell.value else '' for cell in sheet[1]]
        if not headers:
            raise UserError('No se pudieron leer los encabezados de la planilla.')

        mapping_lines = self.mapping_id.line_ids
        created = 0
        
        for row in sheet.iter_rows(min_row=3, values_only=True):
            data_row = dict(zip(headers, row))
            
            ci = self._get_value_from_mapping(data_row, 'ci_number', mapping_lines)
            if not ci:
                print(f"FILA DESCARTADA (sin CI): {data_row}")
                continue

            vals = {
                'batch_id': batch.id,
                'ci_number': ci,
            }

            # Campos de texto directo
            text_fields = [
                'last_name', 'first_name', 'job_title', 'patronal_number', 'insured_number',
                'payment_month_year', 'activity_code', 'sex', 'civil_status', 'nationality', 
                'domicilio', 'profession', 'exit_reason', 'work_schedule', 'state', 
                'observaciones_vacaciones'
            ]
            for f in text_fields:
                val = self._get_value_from_mapping(data_row, f, mapping_lines)
                if val is not None:
                    vals[f] = val

            # Campos Enteros
            int_fields = [
                'days_worked', 'children_under_18', 'children_with_different_abilities',
                'children_educated', 'dias_vacaciones'
            ]
            for f in int_fields:
                val = self._get_value_from_mapping(data_row, f, mapping_lines)
                if val:
                    try:
                        vals[f] = int(val)
                    except:
                        vals[f] = 0

            # Campos Float
            float_fields = ['salary_base', 'salary_total', 'remuneracion_vacaciones']
            for f in float_fields:
                val = self._get_value_from_mapping(data_row, f, mapping_lines)
                if val:
                    try:
                        vals[f] = float(val)
                    except:
                        vals[f] = 0.0

            # Campos Fecha
            date_fields = [
                'fecha_nacimiento', 'entry_date', 'exit_date', 'fecha_menor',
                'desde_vacaciones', 'hasta_vacaciones'
            ]
            for f in date_fields:
                val = self._get_value_from_mapping(data_row, f, mapping_lines)
                if val:
                    vals[f] = self._to_date(val)

            self.env['antux.datahub.line'].create(vals)
            created += 1

        if not created:
            raise UserError('No se detectaron registros válidos en la planilla usando el mapeo seleccionado.')

        batch.write({
            'state': 'processed',
            'imported': True,
            'import_date': fields.Datetime.now(),
        })

        return {'type': 'ir.actions.act_window_close'}
