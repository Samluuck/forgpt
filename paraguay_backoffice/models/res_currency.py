from odoo import fields, models, exceptions, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError,UserError
import logging
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit='res.currency'



    @api.model
    def _get_query_currency_table_invoice_based(self):
        ''' Construye la tabla de moneda basada en la moneda y fecha de la factura.'''

        user_company = self.env.company
        user_currency = user_company.currency_id

        query = f"""
        SELECT 
            line.company_id,
            COALESCE(res_currency_rate.rate, 1) AS rate,
            {user_currency.decimal_places} AS precision
        FROM account_move_line AS line
        JOIN account_move AS move ON line.move_id = move.id
        LEFT JOIN res_currency_rate ON line.currency_id = res_currency_rate.currency_id AND move.date = res_currency_rate.name
        WHERE (res_currency_rate.company_id IS NULL OR res_currency_rate.company_id = line.company_id)
        """

        return query








