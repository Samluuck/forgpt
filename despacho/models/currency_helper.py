from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class CurrencyHelper(models.AbstractModel):
    """Helper para manejo correcto de conversión de monedas a texto"""
    _name = 'despacho.currency.helper'
    _description = 'Helper para conversión de monedas'
    
    def get_currency_text(self, amount, currency_code='PYG'):
        """
        Convierte un monto a texto en la moneda especificada
        """
        if not amount or amount <= 0:
            return ''
        
        try:
            # Buscar la moneda específica
            currency = self.env['res.currency'].search([
                ('name', '=', currency_code)
            ], limit=1)
            
            if not currency:
                # Fallback: crear/buscar moneda guaraní si no existe
                if currency_code == 'PYG':
                    currency = self._ensure_pyg_currency()
                elif currency_code == 'USD':
                    currency = self._ensure_usd_currency()
            
            if currency:
                # Usar el método nativo de Odoo
                return currency.amount_to_text(amount)
            else:
                return self._manual_conversion(amount, currency_code)
                
        except Exception as e:
            _logger.error(f"Error en conversión de moneda: {str(e)}")
            return self._manual_conversion(amount, currency_code)
    
    def _ensure_pyg_currency(self):
        """Asegurar que existe la moneda guaraní"""
        currency = self.env['res.currency'].search([('name', '=', 'PYG')], limit=1)
        if not currency:
            currency = self.env['res.currency'].create({
                'name': 'PYG',
                'full_name': 'Guaraní Paraguayo',
                'symbol': 'Gs.',
                'position': 'before',
                'rounding': 1.0,
                'decimal_places': 0,
            })
        return currency
    
    def _ensure_usd_currency(self):
        """Asegurar que existe la moneda dólar"""
        currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        if not currency:
            currency = self.env['res.currency'].create({
                'name': 'USD',
                'full_name': 'Dólar Estadounidense',
                'symbol': '$',
                'position': 'before',
                'rounding': 0.01,
                'decimal_places': 2,
            })
        return currency
    
    def _manual_conversion(self, amount, currency_code):
        """Conversión manual básica como fallback"""
        if currency_code == 'PYG':
            return f"{amount:,.0f} guaraníes".replace(',', '.')
        elif currency_code == 'USD':
            return f"{amount:,.2f} dólares".replace(',', '.')
        else:
            return f"{amount:,.2f} {currency_code}".replace(',', '.')


# Modificar el modelo Despacho para usar el helper
class Despacho(models.Model):
    _inherit = 'despacho.despacho'
    
    def get_amount_in_words_guaranies(self, amount):
        """Obtener monto en palabras en guaraníes"""
        helper = self.env['despacho.currency.helper']
        return helper.get_currency_text(amount, 'PYG')
    
    def get_amount_in_words_dollars(self, amount):
        """Obtener monto en palabras en dólares"""
        helper = self.env['despacho.currency.helper']
        return helper.get_currency_text(amount, 'USD')