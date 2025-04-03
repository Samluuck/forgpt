from odoo import models, fields, api, _


class DocumentoCliente(models.Model):
    _name = 'despachos.documento_cliente'
    _description = 'Documento del cliente'

    tipo_documento = fields.Many2one('despachos.tipo_documento_cliente', 'Tipo de documento')
    archivo = fields.Binary('Archivo', attachment=True)
    vencimiento = fields.Date('Fecha de vencimiento')

    cliente = fields.Many2one('res.partner', 'Cliente')


class Partner(models.Model):
    _inherit = 'res.partner'

    codigo = fields.Char(_('Código'))
    documento_cliente = fields.One2many('despachos.documento_cliente', 'cliente', 'Documentos de cliente')


class Gasto(models.Model):
    _inherit = 'hr.expense'

    ot = fields.Many2one('despachos.despacho', string="Orden de trabajo relacionada")
