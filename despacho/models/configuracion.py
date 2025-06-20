from odoo import models, fields, api, _

class Aduana(models.Model):
    _name = 'despacho.aduana'
    _description = 'Aduana'
    _order = 'name asc'

    codigo = fields.Char('Código', required=True)
    name = fields.Char('Nombre', required=True)
    despachos = fields.One2many('despacho.despacho', 'aduana', 'Despachos')

    _sql_constraints = [
        ('codigo_unique', 'unique(codigo)', 'El código de aduana ya existe'),
        ('name_unique', 'unique(name)', 'El nombre de aduana ya existe')
    ]

    def name_get(self):
        return [(rec.id, f"{rec.codigo} - {rec.name}") for rec in self]

class TipoContenedor(models.Model):
    _name = 'despacho.tipo_contenedor'
    _description = 'Tipo de Contenedor'
    _order = 'name asc'

    name = fields.Char('Nombre', required=True)
    tipo = fields.Char('Tipo', required=True)

    def name_get(self):
        return [(rec.id, f"{rec.name} ({rec.tipo})") for rec in self]

class TipoDocumento(models.Model):
    _name = 'despacho.tipo_documento'
    _description = 'Tipo de Documento'
    _order = 'name asc'

    name = fields.Char('Tipo Documento', required=True)
    description = fields.Char('Descripción')
    regimen = fields.Many2many(
        'despacho.regimen',
        string="Régimen",
        help="Régimen al que aplica este tipo de documento"
    )

    def name_get(self):
        return [(rec.id, f"{rec.name} - {rec.description}") if rec.description else (rec.id, rec.name)
                for rec in self]

class TipoDocumentoPrevio(models.Model):
    _name = 'despacho.tipo_documento_previo'
    _description = 'Tipo de Documento Previo'
    _order = "orden asc, name asc"

    name = fields.Char('Tipo Documento', required=True)
    description = fields.Char('Descripción')
    regimen = fields.Many2many(
        'despacho.regimen',
        string="Régimen",
        help="Régimen al que aplica este tipo de documento previo"
    )
    orden = fields.Integer('Orden', default=1000)

    def name_get(self):
        return [(rec.id, f"{rec.name} - {rec.description}") if rec.description else (rec.id, rec.name)
                for rec in self]

class TipoDocumentoOficializacion(models.Model):
    _name = 'despacho.tipo_documento_oficializacion'
    _description = 'Tipo de Documento de Oficialización'
    _order = 'name asc'

    name = fields.Char('Nombre', required=True)
    description = fields.Char('Descripción')
    regimen = fields.Many2many(
        'despacho.regimen',
        string="Régimen",
        help="Régimen al que aplica este tipo de documento de oficialización"
    )

    def name_get(self):
        return [(rec.id, f"{rec.name} - {rec.description}") if rec.description else (rec.id, rec.name)
                for rec in self]

class TipoDocumentoCliente(models.Model):
    _name = 'despacho.tipo_documento_cliente'
    _description = 'Tipo de Documento del Cliente'
    _order = 'name asc'

    name = fields.Char('Tipo de documento', required=True)
    description = fields.Char('Descripción')
    tiempo_gestion = fields.Integer(
        'Tiempo de gestión (días)',
        help="Tiempo estimado de gestión en días"
    )

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Este tipo de documento ya existe')
    ]

    def name_get(self):
        return [(rec.id, f"{rec.name} - {rec.description}") if rec.description else (rec.id, rec.name)
                for rec in self]

class Moneda(models.Model):
    _name = 'despacho.moneda'
    _description = 'Moneda'
    _order = 'name asc'

    codigo = fields.Char('Código', required=True, size=3)
    name = fields.Char('Nombre', required=True)

    _sql_constraints = [
        ('codigo_unique', 'unique(codigo)', 'El código de moneda ya existe'),
        ('name_unique', 'unique(name)', 'El nombre de moneda ya existe')
    ]

    def name_get(self):
        return [(rec.id, f"{rec.codigo} - {rec.name}") for rec in self]

class Incoterms(models.Model):
    _name = 'despacho.incoterms'
    _description = 'Incoterms'
    _order = 'name asc'

    name = fields.Char('Código', required=True, size=4)
    description = fields.Char('Descripción', required=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Este incoterm ya existe'),
        ('description_unique', 'unique(description)', 'Esta descripción de incoterm ya existe')
    ]

    def name_get(self):
        return [(rec.id, f"{rec.name} - {rec.description}") for rec in self]

class Regimen(models.Model):
    _name = 'despacho.regimen'
    _description = 'Régimen Aduanero'
    _order = 'name asc'

    name = fields.Char('Código', required=True, size=4)
    description = fields.Char('Descripción', required=True)
    categoria = fields.Char('Categoría')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Este código de régimen ya existe')
    ]

    def name_get(self):
        return [(rec.id, f"{rec.name} - {rec.description}") for rec in self]

class Embalaje(models.Model):
    _name = 'despacho.embalaje'
    _description = 'Tipo de Embalaje'
    _order = 'name asc'

    name = fields.Char('Nombre', required=True)

    def name_get(self):
        return [(rec.id, rec.name) for rec in self]