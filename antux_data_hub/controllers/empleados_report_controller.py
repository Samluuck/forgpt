from odoo import http
from odoo.http import request
import io
from openpyxl import Workbook
from openpyxl.styles import Font


class AntuxDataHubEmpleadosReportController(http.Controller):

    @http.route(
        '/antux_datahub/empleados_obreros/<int:batch_id>',
        type='http',
        auth='user'
    )
    def empleados_anual(self, batch_id):
        batch = request.env['antux.datahub.batch'].browse(batch_id)
        if not batch.exists():
            return request.not_found()

        # ✅ ANUAL
        stream = batch.generate_empleados_anual_excel()

        return request.make_response(
            stream.getvalue(),
            headers=[
                (
                    'Content-Type',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ),
                (
                    'Content-Disposition',
                    'attachment; filename=empleados_anual.xlsx'
                )
            ]
        )

    @http.route(
        '/antux_datahub/empleados_obreros/mensual/<int:batch_id>',
        type='http',
        auth='user'
    )
    def empleados_mensual(self, batch_id):
        batch = request.env['antux.datahub.batch'].browse(batch_id)
        if not batch.exists():
            return request.not_found()

        # ✅ MENSUAL
        stream = batch.generate_empleados_mensual_excel()

        return request.make_response(
            stream.getvalue(),
            headers=[
                (
                    'Content-Type',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                ),
                (
                    'Content-Disposition',
                    'attachment; filename=empleados_mensual.xlsx'
                )
            ]
        )

