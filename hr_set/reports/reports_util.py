# -*- coding: utf-8 -*-
import babel
import logging
from odoo import models, fields, api, exceptions, tools, _
from datetime import datetime, timedelta, time, date
from dateutil import relativedelta
from time import strptime, strftime, mktime
from num2words import num2words

_logger = logging.getLogger(__name__)


def _current_date_formatter(self, today=None):
    locale = self.env.context.get('lang') or 'en_US'
    today = fields.Date.from_string(today) if today else date.today()
    ttyme = datetime.fromtimestamp(mktime(strptime(str(today), "%Y-%m-%d")))
    str_month = tools.ustr(
        babel.dates.format_date(
            date=ttyme, format='MMMM', locale=locale))
    to_return = _("%d de %s de %d") % (today.day, str_month, today.year)

    return to_return


def _agregar_punto_de_miles(self, numero):
    numero_con_punto = '0'
    if numero:
        numero_con_punto = '.'.join([
            str(int(numero))[::-1][i:i + 3]
            for i in range(0, len(str(int(numero))), 3)
        ])[::-1]

    return numero_con_punto


def _calcular_letras(self, numero):
    numero = int(numero)
    letras = self.monto_en_letras = num2words(numero, lang='es').upper()
    letras = 'GUARANIES ' + letras
    return letras
