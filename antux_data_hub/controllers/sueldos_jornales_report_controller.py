from odoo import http
from odoo.http import request


class AntuxSueldosJornalesController(http.Controller):

    @http.route(
        '/antux_datahub/sueldos_jornales/mensual/<int:batch_id>',
        type='http',
        auth='user'
    )
    def sueldos_jornales_mensual(self, batch_id):
        batch = request.env['antux.datahub.batch'].browse(batch_id)
        if not batch.exists():
            return request.not_found()

        stream, filename = request.env['antux.sueldos.jornales.report'].build_mensual_excel(batch)

        return request.make_response(
            stream.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )

    @http.route(
        '/antux_datahub/sueldos_jornales/anual/<int:company_id>/<int:year>',
        type='http',
        auth='user'
    )
    def sueldos_jornales_anual(self, company_id, year):
        company = request.env['res.company'].browse(company_id)
        if not company.exists():
            return request.not_found()

        stream, filename = request.env['antux.sueldos.jornales.report'].build_control_excel(company, year)

        return request.make_response(
            stream.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )
