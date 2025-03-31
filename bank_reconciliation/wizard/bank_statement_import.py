# -*- coding: utf-8 -*-
import base64
import io
import math
import logging
import pandas as pd
import unicodedata

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

def normalize_text(text):
    """Convierte texto a minúsculas, sin acentos ni espacios extra."""
    if not text:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower().strip()

def find_column_by_possibilities(df_columns, possibilities):
    """
    Dada una lista de nombres de columnas df_columns y una lista de posibilidades,
    busca la primera coincidencia. Devuelve el nombre real de la columna si la encuentra.
    Si no, devuelve None.
    """
    normalized_poss = [normalize_text(p) for p in possibilities]
    for real_col in df_columns:
        norm_real_col = normalize_text(real_col)
        if norm_real_col in normalized_poss:
            return real_col
    return None

def parse_trf_name(s):
    """
    Función para procesar el name del account.move:
    - Si empieza con "Trf." (ignorando mayúsculas), lo elimina.
    - Luego, si encuentra un paréntesis "(",
    - Devuelve el resultado limpio, sin espacios extra.
    """
    if not s:
        return ""
    s = s.strip()
    if s.lower().startswith("trf."):
        s = s[4:].strip()  # Elimina "Trf." + espacio
    paren_index = s.find("(")
    if paren_index != -1:
        s = s[:paren_index].strip()
    return s

class BankStatementImportWizard(models.TransientModel):
    _name = 'bank.statement.import.wizard'
    _description = 'Importar Extracto Bancario'

    file_data = fields.Binary("Archivo Excel", required=True)
    file_name = fields.Char("Nombre del Archivo")

    def action_import(self):
        _logger.info("Ejecutando action_import")
        if not self.file_data:
            _logger.error("No se cargó un archivo Excel.")
            raise ValidationError("Debe cargar un archivo Excel.")

        # 1) Identificamos el bank.statement
        bank_statement = self.env['bank.statement'].browse(self.env.context.get('active_id'))
        if not bank_statement:
            raise ValidationError("No se ha definido el Extracto Bancario.")

        # 2) Borramos incondicionalmente las líneas previas importadas
        self.env['bank.statement.import.line'].search([
            ('bank_statement_id', '=', bank_statement.id)
        ]).unlink()

        try:
            file_content = base64.b64decode(self.file_data)
            df = pd.read_excel(io.BytesIO(file_content))
            df.columns = df.columns.str.strip()
            _logger.info(f"Nombres de columnas originales: {list(df.columns)}")
        except Exception as e:
            _logger.error(f"Error al leer el archivo: {str(e)}")
            raise ValidationError(f"Error al leer el archivo: {str(e)}")

        # Definición de nombres posibles
        possible_ref_names = [
            "número de operación según extracto bancario",
            "referencia y/o comprobante",
            "referencia",
            "comprobante",
        ]
        possible_date_names = ["fecha"]
        possible_debit_names = [
            "debito (a)", "débito (a)", "debito", "débito", "debito a", "débito a"
        ]
        possible_credit_names = [
            "credito (b)", "crédito (b)", "credito", "crédito", "credito b", "crédito b"
        ]
        possible_balance_names = [
            "saldo a la fecha", "saldo"
        ]
        possible_description_names = [
            "tipo de transacción", "concepto y/o descripción", "concepto", "descripción"
        ]

        ref_col = find_column_by_possibilities(df.columns, possible_ref_names)
        date_col = find_column_by_possibilities(df.columns, possible_date_names)
        debit_col = find_column_by_possibilities(df.columns, possible_debit_names)
        credit_col = find_column_by_possibilities(df.columns, possible_credit_names)
        balance_col = find_column_by_possibilities(df.columns, possible_balance_names)
        desc_col = find_column_by_possibilities(df.columns, possible_description_names)

        if not ref_col:
            raise ValidationError("No se encontró ninguna columna de referencia (ej: 'Referencia' o 'Comprobante').")
        if not date_col:
            raise ValidationError("No se encontró ninguna columna de fecha (ej: 'Fecha').")

        rename_map = {
            ref_col: "ref",
            date_col: "statement_date",
        }
        if debit_col:
            rename_map[debit_col] = "debit_col"
        if credit_col:
            rename_map[credit_col] = "credit_col"
        if balance_col:
            rename_map[balance_col] = "balance_col"
        if desc_col:
            rename_map[desc_col] = "descripcion"

        df.rename(columns=rename_map, inplace=True)
        _logger.info(f"Renombradas columnas según las posibilidades: {rename_map}")
        _logger.info(f"Columnas finales: {list(df.columns)}")

        # Limpieza y conversión de columnas numéricas
        numeric_cols = ['debit_col', 'credit_col', 'balance_col']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = (
                    df[col].astype(str)
                          .str.replace('.', '', regex=False)
                          .str.replace(',', '.', regex=False)
                )
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        journal_currency = bank_statement.journal_id.currency_id
        company_currency = bank_statement.company_id.currency_id

        if journal_currency and journal_currency == company_currency:
            conversion_factor = 0.1
        else:
            conversion_factor = 1.0

        _logger.info(f"Moneda del diario: {journal_currency.name if journal_currency else 'No definida'}")
        _logger.info(f"Moneda de la compañía: {company_currency.name}")
        _logger.info(f"Factor de conversión a aplicar en Excel: {conversion_factor}")

        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col] * conversion_factor

        updated_lines = 0
        imported_lines = 0
        errors = []

        # 4) Procesamos cada fila del Excel
        for index, row in df.iterrows():
            try:
                excel_ref = str(row["ref"]).strip() if not pd.isna(row["ref"]) else ""
                if not excel_ref or excel_ref.lower() == "false":
                    _logger.info(f"Fila {index + 2} sin referencia válida ('{excel_ref}'). Se omite la línea.")
                    continue

                # Fecha
                date_to_write = False
                if "statement_date" in row and not pd.isna(row["statement_date"]):
                    date_to_write = pd.to_datetime(row["statement_date"], dayfirst=True).date()

                # Descripción
                desc_val = ""
                if "descripcion" in df.columns:
                    val = row.get("descripcion")
                    desc_val = val if not pd.isna(val) else ""

                # Valores del Excel
                debit_val = row.get("debit_col") or 0.0
                credit_val = row.get("credit_col") or 0.0
                balance_val = row.get("balance_col") or 0.0

                # =========================================================
                # LÓGICA CRUZADA:
                # Excel débito => buscar crédito en Odoo
                # Excel crédito => buscar débito en Odoo
                # =========================================================
                if debit_val != 0:
                    monto_extracto = abs(debit_val)
                    line_candidates = bank_statement.statement_lines.filtered(
                        lambda r: parse_trf_name(r.move_id.name or "") == excel_ref
                                  and (r.credit or 0.0) != 0.0
                                  and (r.debit or 0.0) == 0.0
                    )

                    total_apuntes = 0.0
                    for cand in line_candidates:
                        if cand.currency_id and cand.currency_id != cand.company_id.currency_id:
                            total_apuntes += abs(cand.amount_currency)
                        else:
                            total_apuntes += abs(cand.credit)

                    expected_side = 'credit'

                elif credit_val != 0:
                    monto_extracto = abs(credit_val)
                    line_candidates = bank_statement.statement_lines.filtered(
                        lambda r: parse_trf_name(r.move_id.name or "") == excel_ref
                                  and (r.debit or 0.0) != 0.0
                                  and (r.credit or 0.0) == 0.0
                    )

                    total_apuntes = 0.0
                    for cand in line_candidates:
                        if cand.currency_id and cand.currency_id != cand.company_id.currency_id:
                            total_apuntes += abs(cand.amount_currency)
                        else:
                            total_apuntes += abs(cand.debit)

                    expected_side = 'debit'
                else:
                    monto_extracto = 0.0
                    line_candidates = bank_statement.statement_lines.filtered(
                        lambda r: parse_trf_name(r.move_id.name or "") == excel_ref
                    )
                    total_apuntes = 0.0
                    expected_side = 'none'

                _logger.info(
                    f"Procesando fila {index + 2}: ExcelRef='{excel_ref}', "
                    f"Fecha='{date_to_write}', Desc='{desc_val}', "
                    f"monto_extracto={monto_extracto}, lado_esperado={expected_side}"
                )

                difference = abs(total_apuntes - monto_extracto)
                tolerance = 1.0

                if line_candidates:
                    if difference <= tolerance:
                        _logger.info(
                            f"Conciliación para ref '{excel_ref}': total {total_apuntes} (lado {expected_side}) "
                            f"está dentro de +/-{tolerance} respecto a {monto_extracto}."
                        )
                        line_candidates.write({
                            'statement_date': date_to_write,
                            'descripcion': desc_val,
                        })
                        updated_lines += len(line_candidates)
                    else:
                        _logger.info(
                            f"Diferencia de {difference} > {tolerance} para la ref '{excel_ref}'. "
                            "Se creará línea importada."
                        )
                        if debit_val != 0:
                            vals = {
                                'ref': excel_ref,
                                'statement_date': date_to_write,
                                'bank_statement_id': bank_statement.id,
                                'date': date_to_write,
                                'debit': 0.0,
                                'credit': debit_val,
                                'balance': balance_val,
                                'amount_currency': 0.0,
                                'descripcion': desc_val,
                            }
                        else:
                            vals = {
                                'ref': excel_ref,
                                'statement_date': date_to_write,
                                'bank_statement_id': bank_statement.id,
                                'date': date_to_write,
                                'debit': credit_val,
                                'credit': 0.0,
                                'balance': balance_val,
                                'amount_currency': 0.0,
                                'descripcion': desc_val,
                            }
                        self.env['bank.statement.import.line'].create(vals)
                        imported_lines += 1
                else:
                    _logger.info(f"No se encontraron apuntes para la ref '{excel_ref}'. Se creará línea importada.")
                    if debit_val != 0:
                        vals = {
                            'ref': excel_ref,
                            'statement_date': date_to_write,
                            'bank_statement_id': bank_statement.id,
                            'date': date_to_write,
                            'debit': 0.0,
                            'credit': debit_val,
                            'balance': balance_val,
                            'amount_currency': 0.0,
                            'descripcion': desc_val,
                        }
                    else:
                        vals = {
                            'ref': excel_ref,
                            'statement_date': date_to_write,
                            'bank_statement_id': bank_statement.id,
                            'date': date_to_write,
                            'debit': credit_val,
                            'credit': 0.0,
                            'balance': balance_val,
                            'amount_currency': 0.0,
                            'descripcion': desc_val,
                        }
                    self.env['bank.statement.import.line'].create(vals)
                    imported_lines += 1

            except Exception as e:
                _logger.error(f"Error procesando fila {index + 2}: {str(e)}")
                errors.append(f"Fila {index + 2}: Error inesperado: {str(e)}")

        # 6) Mensajes finales
        message = f"Se actualizaron {updated_lines} líneas."
        if imported_lines:
            message += f" Se importaron {imported_lines} líneas adicionales."
        if errors:
            message += "\nErrores:\n" + "\n".join(errors)
            _logger.warning(f"Errores:\n{message}")
        else:
            _logger.info("Importación completada sin errores.")

        # 7) Adjuntamos el archivo subido
        filename = self.file_name or "Conciliacion_Bancaria.xlsx"
        if not filename.lower().endswith('.xlsx'):
            filename += '.xlsx'

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': self.file_data,
            'res_model': 'bank.statement',
            'res_id': bank_statement.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        bank_statement.message_post(
            body=_("Archivo importado exitosamente"),
            attachment_ids=[attachment.id]
        )

        return {'type': 'ir.actions.act_window_close'}

class BankStatement(models.Model):
    _inherit = 'bank.statement'

    def action_open_import_wizard(self):
        _logger.info("Abriendo wizard de importación de extracto bancario.")
        return {
            'name': _('Importar Extracto Bancario'),
            'type': 'ir.actions.act_window',
            'res_model': 'bank.statement.import.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
