from odoo import models, fields, api, _


class Aduana(models.Model):
    _name = 'despachos.aduana'
    _description = 'despachos.aduana'

    codigo = fields.Char(_('Código'))
    name = fields.Char(_('Nombre'), required=True)
    despachos = fields.One2many(
        'despachos.despacho', 'aduana', 'Despachos')

    _sql_constraints = [
        ('codigo_unique', 'unique(codigo)', 'EL codigo de aduan que desea agregar ya ha sido utilizado'),
        ('name_unique', 'unique(name)', 'El nombre de la aduana que desea agregar ya ha sido utilizado')
    ]


class TipoContenedor(models.Model):
    _name = 'despachos.tipo_contenedor'
    _description = 'despachos.tipo_contenedor'

    name = fields.Char(_('Nombre'))
    tipo = fields.Char(_('Tipo'))


class TipoDocumento(models.Model):
    _name = 'despachos.tipo_documento'
    _description = 'despachos.tipo_documento'

    name = fields.Char(_('Tipo Documento'))
    description = fields.Char(_('Descripción'))
    regimen = fields.Many2many('despachos.regimen', string="Regimen", auto_join=True)


class TipoDocumentoPrevio(models.Model):
    _name = 'despachos.tipo_documento_previo'
    _description = 'despachos.tipo_documento_previo'
    _order = "orden asc"

    name = fields.Char(_('Tipo Documento'))
    description = fields.Char(_('Descripción'))
    regimen = fields.Many2many('despachos.regimen', string="Regimen")
    orden = fields.Integer('Orden', default=1000)


class TipoDocumentoOficializacion(models.Model):
    _name = 'despachos.tipo_documento_oficializacion'
    _description = 'despachos.tipo_documento_oficializacion'

    name = fields.Char(_('Name'))
    description = fields.Char(_('Descripción'))
    regimen = fields.Many2many('despachos.regimen', string="Regimen")



class TipoDocumentoCliente(models.Model):
    _name = 'despachos.tipo_documento_cliente'
    _description = 'Tipo de documento del cliente'

    name = fields.Char('Tipo de documento')
    description = fields.Char(_('Descripción'))
    tiempo_gestion = fields.Integer('Tiempo de gestion (días)')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tipo de documento ya existe')
    ]


class Moneda(models.Model):
    _name = 'despachos.moneda'
    _description = 'despachos.moneda'

    codigo = fields.Char(_('Código'))
    name = fields.Char(_('Nombre'))


class Incoterms(models.Model):
    _name = 'despachos.incoterms'
    _description = 'despachos.incoterms'

    name = fields.Char(_('Código'))
    description = fields.Char(_('Descripción'))


class Regimen(models.Model):
    _name = 'despachos.regimen'
    _description = 'despachos.regimen'

    name = fields.Char(_('Código'), required=True)
    description = fields.Char(_('Descripción'))
    categoria = fields.Char(_('Categoría'))


class Embalaje(models.Model):
    _name = 'despachos.embalaje'
    _description = 'despachos.embalaje'

    name = fields.Char(_('Name'))
