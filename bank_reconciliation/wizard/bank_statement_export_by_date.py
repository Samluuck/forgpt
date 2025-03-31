from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import io
import pandas as pd
import base64

class BankStatementExportByDate(models.TransientModel):
    _name = 'bank.statement.export.by.date'
    _description = 'Exportar Extractos Bancarios por Fechas'

    date_from = fields.Date(string='Desde')
    date_to = fields.Date(string='Hasta')
    file_data = fields.Binary('Archivo Excel')
    file_name = fields.Char('Nombre de Archivo')

    def generate_excel(self):
        if not self.date_from or not self.date_to:
            raise UserError("Debes definir ambas fechas: Desde y Hasta")

        statements = self.env['bank.statement'].search([
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to)
        ])

        if not statements:
            raise UserError("No se encontraron extractos bancarios en ese rango.")

        data = []
        for st in statements:
            journal = st.journal_id
            bank_name = journal.name or ""
            bank_account = journal.bank_account_id.acc_number if journal.bank_account_id else ""
            currency_name = journal.currency_id.name if journal.currency_id else "PYG"

            for line in st.statement_lines:
                fecha_linea = line.statement_date or ""
                tipo_transaccion = line.descripcion or ""
                data.append({
                    "Banco o Entidad del Sistema Financiero": bank_name,
                    "Número de cuenta": bank_account,
                    "Fecha": fecha_linea,
                    "País Cuenta SO": st.company_id.country_id.name or "",
                    "Moneda": currency_name,
                    "N° Operación": line.ref,
                    "Tipo Transacción": tipo_transaccion,
                    "Débito": line.debito,
                    "Crédito": line.credito,
                    "Saldo": line.saldo,
                })

        if not data:
            data = [{"Mensaje": "No hay líneas para exportar."}]

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Conciliación Bancaria")
            workbook = writer.book
            worksheet = writer.sheets["Conciliación Bancaria"]

            header_format = workbook.add_format({
                'bold': True, 'text_wrap': True, 'valign': 'middle',
                'align': 'center', 'fg_color': '#1F4E78', 'font_color': '#FFFFFF'
            })
            wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            for col_num, col_name in enumerate(df.columns):
                worksheet.write(0, col_num, col_name, header_format)
                worksheet.set_column(col_num, col_num, 30, wrap_format)
            worksheet.freeze_panes(1, 0)

        output.seek(0)
        self.file_data = base64.b64encode(output.read())
        self.file_name = f"Extractos_{self.date_from}_{self.date_to}.xlsx".replace("-", "_")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bank.statement.export.by.date',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
