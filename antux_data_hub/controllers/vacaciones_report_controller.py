from odoo import http
from odoo.http import request

class AntuxVacacionesController(http.Controller):

    @http.route('/antux_datahub/vacaciones/mensual/<int:batch_id>', type='http', auth='user')
    def vacaciones_mensual(self, batch_id):
        batch = request.env['antux.datahub.batch'].browse(batch_id)
        if not batch.exists():
            return request.not_found()

        stream, filename = batch.generate_vacaciones_mensual_excel()

        return request.make_response(
            stream.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )

    @http.route('/antux_datahub/vacaciones/anual/<int:batch_id>', type='http', auth='user')
    def vacaciones_anual(self, batch_id):
        batch = request.env['antux.datahub.batch'].browse(batch_id)
        if not batch.exists():
            return request.not_found()

        stream, filename = batch.generate_vacaciones_anual_excel()

        return request.make_response(
            stream.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )
