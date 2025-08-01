from odoo import fields, models, api
import logging


_logger = logging.getLogger(__name__)

class MjeResultado(models.Model):
    _name = 'mje.resultado'
    _order = "id desc"

    name=fields.Char(string='Codigo')
    dMsgRes=fields.Char(string='Descripcion')
    tipo=fields.Selection(selection=[('individual','Individual'),('lote','Lote')])
    invoice_id=fields.Many2one('account.move')