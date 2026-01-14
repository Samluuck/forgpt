from odoo import fields, models, api

class AntuxDataHubMapping(models.Model):
    _name = 'antux.datahub.mapping'
    _description = 'Configuración de Mapeo de Importación'

    name = fields.Char(string='Nombre', required=True)
    line_ids = fields.One2many(
        'antux.datahub.mapping.line',
        'mapping_id',
        string='Líneas de Mapeo'
    )
    active = fields.Boolean(default=True)

class AntuxDataHubMappingLine(models.Model):
    _name = 'antux.datahub.mapping.line'
    _description = 'Línea de Mapeo de Columna'

    mapping_id = fields.Many2one(
        'antux.datahub.mapping',
        string='Mapeo',
        required=True,
        ondelete='cascade'
    )
    
    field_id = fields.Many2one(
        'ir.model.fields',
        string='Campo en Odoo',
        required=True,
        domain="[('model', '=', 'antux.datahub.line')]",
        ondelete='cascade'
    )
    
    excel_header_aliases = fields.Text(
        string='Encabezados Excel (Alias)',
        help="Ingrese los posibles nombres de columna en el Excel separados por coma. Ej: C.I., Cedula, Documento"
    )

    def get_aliases_list(self):
        """Retorna una lista limpia de alias"""
        self.ensure_one()
        if not self.excel_header_aliases:
            return []
        # Separar por coma o salto de línea y limpiar espacios
        raw_list = self.excel_header_aliases.replace('\n', ',').split(',')
        return [x.strip() for x in raw_list if x.strip()]
