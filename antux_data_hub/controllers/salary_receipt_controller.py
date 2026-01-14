from odoo import http
from odoo.http import request
import io
import zipfile
import logging
from PyPDF2 import PdfFileReader, PdfFileWriter

_logger = logging.getLogger(__name__)

class SalaryReceiptController(http.Controller):

    @http.route('/antux_datahub/salary_receipts_zip/<int:wizard_id>', type='http', auth='user')
    def download_salary_receipts_zip(self, wizard_id, **kw):
        wizard = request.env['antux.datahub.salary.receipt.wizard'].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()

        batch = wizard.batch_id
        lines = wizard.employee_ids or batch.line_ids
        
        _logger.info("Generando ZIP optimizado de recibos para %s empleados", len(lines))
        
        # 1. Generate ONE large PDF with all receipts
        report_action = request.env.ref('antux_data_hub.action_report_salary_receipt')
        pdf_content, _ = report_action._render_qweb_pdf(res_ids=[wizard.id])
        
        # 2. Split the PDF into individual pages using PyPDF2
        pdf_reader = PdfFileReader(io.BytesIO(pdf_content))
        
        if pdf_reader.getNumPages() != len(lines):
            _logger.warning("Discrepancia entre páginas del PDF (%s) y cantidad de empleados (%s)", 
                            pdf_reader.getNumPages(), len(lines))
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
            for i, line in enumerate(lines):
                if i >= pdf_reader.getNumPages():
                    break
                
                # Create a new PDF for this single page
                pdf_writer = PdfFileWriter()
                pdf_writer.addPage(pdf_reader.getPage(i))
                
                page_buffer = io.BytesIO()
                pdf_writer.write(page_buffer)
                
                filename = "%s_%s.pdf" % (line.ci_number, batch.name.replace(' ', '_'))
                zip_file.writestr(filename, page_buffer.getvalue())
                
            _logger.info("ZIP optimizado generado correctamente")

        zip_buffer.seek(0)
        zip_filename = "Recibos_%s.zip" % batch.name.replace(' ', '_')
        
        return request.make_response(
            zip_buffer.getvalue(),
            headers=[
                ('Content-Type', 'application/zip'),
                ('Content-Disposition', 'attachment; filename=%s' % zip_filename)
            ]
        )
