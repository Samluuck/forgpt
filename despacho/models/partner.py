from odoo import models, fields, api, _


class DocumentoCliente(models.Model):
    _name = 'despacho.documento_cliente'
    _description = 'Documento del Cliente'
    _order = 'vencimiento desc, id desc'

    tipo_documento = fields.Many2one(
        'despacho.tipo_documento_cliente',
        string='Tipo de Documento',
        required=True,
        help="Seleccione el tipo de documento del cliente"
    )

    archivo = fields.Binary(
        string='Archivo',
        attachment=True,
        required=True,
        help="Suba el documento digitalizado del cliente"
    )

    vencimiento = fields.Date(
        string='Fecha de Vencimiento',
        help="Fecha de vencimiento del documento si aplica"
    )

    cliente = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        ondelete='cascade',
        help="Cliente asociado a este documento"
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )

    def name_get(self):
        return [(rec.id, f"{rec.tipo_documento.name} - {rec.cliente.name}") for rec in self]


class Partner(models.Model):
    _inherit = 'res.partner'

    codigo = fields.Char(
        string='Código',
        size=20,
        help="Código único identificador del cliente",
        tracking=True
    )

    documento_cliente = fields.One2many(
        'despacho.documento_cliente',
        'cliente',
        string='Documentos del Cliente',
        help="Documentos asociados a este cliente"
    )

    _sql_constraints = [
        ('codigo_unique', 'unique(codigo, company_id)', 'El código debe ser único por compañía')
    ]


class Gasto(models.Model):
    _inherit = 'hr.expense'

    ot = fields.Many2one(
        'despacho.despacho',
        string='Orden de Trabajo Relacionada',
        tracking=True,
        help="Orden de trabajo asociada a este gasto",
        domain="[('company_id', '=', company_id)]"
    )