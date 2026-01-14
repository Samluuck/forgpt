from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class AntuxDataHubResumenReportController(http.Controller):

    @http.route(
        '/antux_datahub/resumen_general/<int:batch_id>/<string:report_format>',
        type='http',
        auth='user'
    )
    def resumen_general(self, batch_id, report_format):
        _logger.info(f"Generando reporte Resumen General para batch_id={batch_id}, format={report_format}")
        
        batch = request.env['antux.datahub.batch'].browse(batch_id)
        if not batch.exists():
            _logger.warning(f"Batch {batch_id} no encontrado")
            return request.not_found()

        try:
            stream = batch.generate_resumen_general_excel(report_format)
            
            filename = f'Resumen_General_{report_format}_{batch.name}.xlsx'
            
            return request.make_response(
                stream.getvalue(),
                headers=[
                    (
                        'Content-Type',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    ),
                    (
                        'Content-Disposition',
                        f'attachment; filename={filename}'
                    )
                ]
            )
        except Exception as e:
            _logger.error(f"Error generando reporte Resumen General: {str(e)}", exc_info=True)
            return request.not_found()
