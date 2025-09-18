# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import base64
import collections
from datetime import datetime, timedelta
import calendar
from odoo.exceptions import ValidationError
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception, content_disposition
import logging

_logger = logging.getLogger(__name__)
CANT_REGISTROS_HECHAUKA = 15000

MESES = [
    ('01', 'Enero'),
    ('02', 'Febrero'),
    ('03', 'Marzo'),
    ('04', 'Abril'),
    ('05', 'Mayo'),
    ('06', 'Junio'),
    ('07', 'Julio'),
    ('08', 'Agosto'),
    ('09', 'Septiembre'),
    ('10', 'Octubre'),
    ('11', 'Noviembre'),
    ('12', 'Diciembre'), ]


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


class hechauka_generados(models.Model):
    _name = 'set.hechauka.archivo'

    name = fields.Char(string="Name")
    archivo = fields.Binary(string="Archivo")
    anio = fields.Integer(string="Año")
    mes = fields.Char(string="Mes")
    periodo = fields.Integer(string="Periodo")
    filename = fields.Char(string="Nombre archivo")


class hechauka(models.TransientModel):
    _name = 'set.hechauka'

    name = fields.Char(string="Nombre")
    tipo = fields.Selection([('221', 'Venta'), ('211', 'Compra')], string="Tipo")

    mes = fields.Selection(
        [('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'), ('04', 'Abril'), ('05', 'Mayo'), ('06', 'Junio'),
         ('07', 'Julio'), ('08', 'Agosto'), ('09', 'Setiembre'), ('10', 'Octubre'), ('11', 'Noviembre'),
         ('12', 'Diciembre')], string="Mes")
    periodo = fields.Integer(string="Periodo/Año")

    tipo_presentacion = fields.Selection([('1', 'Original'), ('2', 'Rectificativa')], string="Tipo Presentacion")

    archivo = fields.Binary(string="Archivo generado")


    def generar_informe(self):
        periodo = str(self.periodo) + str(self.mes)

        if not self.env.company.ruc:
            raise ValidationError(
                'No se encuentra RUC asignado para la compañia. Debe asignarla en los parametros de la compañia')
        elif not self.env.company.dv:
            raise ValidationError(
                'No se encuentra DV asignado para la compañia. Debe asignarla en los parametros de la compañia')
        elif not self.env.company.razon_social:
            raise ValidationError(
                'No se encuentra Razon Social asignada para la compañia. Debe asignarla en los parametros de la compañia')
        elif not self.env.company.ruc_representante:
            raise ValidationError(
                'No se encuentra Ruc del Representante Legal asignado para la compañia. Debe asignarla en los parametros de la compañia')
        elif not self.env.company.dv_representante:
            raise ValidationError(
                'No se encuentra DV del Representante Legal asignado para la compañia. Debe asignarla en los parametros de la compañia.')
        elif not self.env.company.representante_legal:
            raise ValidationError(
                'No se encuentra Representante Legal asignado para la compañia. Debe asignarla en los parametros de la compañia.')

        if self.tipo == '221':
            # archivo = self.generar_ventas()
            return {
                'type': 'ir.actions.act_url',
                'url': '/getHechauka/txt/' + str(self.id),
                'target': 'current'
            }
            # self.archivo = archivo
        elif self.tipo == '211':
            # archivo = self.generar_compras()
            return {
                'type': 'ir.actions.act_url',
                'url': '/getHechauka/txt/' + str(self.id),
                'target': 'current'
            }
            # self.archivo = archivo
            # raise ValidationError ('aaa %s' % self.archivo)


    def generar_compras(self):

        periodo = str(self.periodo) + str(self.mes)
        cr = self.env.cr
        query = """select 2 as tipo_registro,
	                case when rp.parent_id is null then rp.ruc else (select re.ruc from res_partner re where re.id=rp.parent_id) end as ruc,
	                case when rp.parent_id is null then rp.dv else (select re.dv from res_partner re where re.id=rp.parent_id) end as dv,
                    case when rp.parent_id is null then rp.name else (select re.name from res_partner re where re.id=rp.parent_id) end as nombre,
	                ai.timbrado as timbrado,
	                (select rtd.codigo_hechauka from ruc_tipo_documento rtd where rtd.id = ai.tipo_comprobante) as tipo_comprobante,
	                coalesce(ai.nro_factura, ai.sec || '-' || ai.suc|| '-'||ai.nro) as nros_factura,
	                coalesce (to_char(ai.date_invoice, 'DD-MM-YYYY'),'') as fecha,
	                round(sum(case when t.name like '%10%' then (case when rc.id !=""" + str(
            self.env.company.currency_id.id) + """ then (ail.price_total/1.1) *  (select cast (set_venta as numeric) from res_currency_rate where currency_id=rc.id and name=ai.date_invoice and company_id = ai.company_id) else  ail.price_total/1.1 end)  else '0' end ),0) as gravada_10,

	                round(sum(case when t.name like '%10%' then (case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 11) *  (select cast (set_venta as numeric) from res_currency_rate where currency_id=rc.id and name=ai.date_invoice and company_id = ai.company_id),0) else (ail.price_total/11) end)  else '0' end ),0) as impuesto_10,

                    round(sum(case when t.name like '%5%' then (case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then (ail.price_total/1.05) *  (select cast (set_venta as numeric) from res_currency_rate where currency_id=rc.id and name=ai.date_invoice and company_id = ai.company_id) else ( ail.price_total/1.05) end)  else '0' end ),0) as gravada_5,
                    round(sum(case when t.name like '%5%' then (case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then (ail.price_total / 21) *  (select cast (set_venta as numeric) from res_currency_rate where currency_id=rc.id and name=ai.date_invoice and company_id = ai.company_id) else round(ail.price_total /21) end)  else '0' end ),0 ) as iva_5,
                    sum(case when t.name like '%Exen%' then (case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_unit*ail.quantity) *  (select cast (set_venta as numeric) from res_currency_rate where currency_id=rc.id and name=ai.date_invoice and company_id = ai.company_id),0) else round( ail.price_subtotal) end)  else '0' end ) as exentas,

            case when compa.exportador is null then cast ('0' as text ) else (case when ai.tipo_compra = 'exportacion' then cast('7' as text) else (case when ai.tipo_compra = 'directo' then cast('8' as text) else (case when ai.tipo_compra = 'indirecto' then cast('10' as text) else (case when ai.codigo_hechauka = 3 then cast('9' as text) else cast('0' as text) end) end ) end ) end) end as exportador,
            cast (coalesce(ai.tipo_factura,1) as text) as tipo_factura,	
            case when ai.tipo_factura = 2 then 1 else 0 end as cantidad_cuotas

            from
              account_invoice as ai
              INNER JOIN
              account_invoice_line as ail on ai.id = ail.invoice_id
                INNER JOIN account_invoice_line_tax as at on ail.id = at.invoice_line_id
                INNER JOIN account_tax as t on at.tax_id = t.id 
            INNER JOIN res_partner as rp on  (Case when ai.partner_no_despachante is not null then rp.id=ai.partner_no_despachante else rp.id=ai.partner_id end)

                inner join res_currency as rc on ai.currency_id=rc.id
                inner join res_company as compa on ai.company_id = compa.id

              where ai.type in ( 'in_invoice','out_refund') and ai.state not in ('cancel','draft')  and extract(month from ai.date_invoice)  = """ + str(
            self.mes) + """ and extract(year from ai.date_invoice) =   """ + str(self.periodo) + """
                and ai.company_id=""" + str(self.env.company.id) + """
                GROUP BY  tipo_registro,rp.ruc,rp.dv,nombre,ai.timbrado,tipo_comprobante,ai.state,rp.parent_id,rc.id,ai.amount_total,nros_factura,fecha,tipo_factura,cantidad_cuotas,ai.date_invoice,ai.company_id,compa.exportador,ai.tipo_compra,ai.codigo_hechauka
            order by fecha, nros_factura asc"""
        # raise ValidationError( ' s %s' % query)
        cr.execute(query)

        compras = cr.fetchall()
        nombre_mes = self.mes

        for m in MESES:
            if m[0] == self.mes:
                nombre_mes = m[1]
        texto = []
        aa = list()

        lista_archivos = []
        cant_archivos = list(chunks(compras, CANT_REGISTROS_HECHAUKA))
        try:
            unicode('')
        except NameError:
            unicode = str
        archivo = None
        for ii, compras in enumerate(cant_archivos):
            # los datos como cantidad de registros y monto total se cargan despues de los detalles
            # quedan vacios temporalmente hasta calcular los datos
            texto = []
            texto.append(u'')
            monto_total = 0
            for c in compras:
                # monto_total += int(c[8]) + int(c[9]) + int(c[10]) + int(c[11])
                # texto.append("\t".join([unicode(x) for x in c]))
                print(c)
                monto_total += int(c[8]) + int(c[10]) + int(c[12])  # controlar que este sumando en la columna correcta
                aa = list()
                # texto.append("\t")
                for i, x in enumerate(c):
                    if i > 7 and i < 13:
                        aa.append("".join(unicode(int(x))))
                    else:
                        aa.append("".join(unicode(x)))

                texto.append("\t".join([unicode(x) for x in aa]))

            # pdb.set_trace()
            # for i,obj in enumerate(texto):
            # 	texto[1].encode('utf-8')

            encabezado = [
                '1',
                periodo,
                self.tipo_presentacion,
                '911',
                '211',
                self.env.company.ruc,
                self.env.company.dv,
                self.env.company.razon_social,
                self.env.company.ruc_representante,  # RUC REPRESENTANTE LEGAL
                self.env.company.dv_representante,  # DV REPRESENTANTE LEGAL
                self.env.company.representante_legal,  # REPRESENTANTE LEGAL
                str(len(compras)),  # cantidad registros
                str(monto_total),  # monto total
                'SI' if self.env.company.exportador else 'NO',  # EXPORTADOR
                # 'NO',  # EXPORTADOR
                '2'
            ]

            texto[0] = ("\t".join(encabezado))
            contenido = ("\n".join(texto)).encode('utf-8')

            archivo = base64.b64encode(contenido)
            filename = 'compras_' + str(nombre_mes) + '_' + str(self.periodo) + '_' + str(ii + 1) + '.txt'
            self.name = filename
            archi = self.env['set.hechauka.archivo']
            aviejo = archi.search([('filename', '=', filename)])
            for a in aviejo:
                a.unlink()
            datos = {
                'archivo': base64.b64encode(contenido),
                'name': str(self.periodo) + str(self.mes),
                'nombre': filename,
                'mes': nombre_mes,
                'anio': self.periodo,
                'filename': filename,
            }
            # lista_archivos.append([0, False, datos])

            # new_line = archi.new(datos)
            archi.create(datos)
            # archi += new_line
            # self.archivo = archivo
        if not archivo:
            raise ValidationError(
                'No se han encontrado registros. Verifique que las Facturas de Compra o Notas de Credito correspondiente al mes seleccionado se encuentren en estado Validado o Pagado')
        return archivo


    def generar_ventas(self):
        periodo = str(self.periodo) + str(self.mes)
        cr = self.env.cr
        query = """ select 2 as tipo_registro,
                    case when rp.parent_id is null then rp.ruc else (select re.ruc from res_partner re where re.id=rp.parent_id) end as ruc,
                    case when rp.parent_id is null then rp.dv else (select re.dv from res_partner re where re.id=rp.parent_id) end as dv,
                    case when rp.parent_id is null then rp.name else (select re.name from res_partner re where re.id=rp.parent_id) end as nombre,
                    rtc.codigo_hechauka as tipo_comprobante,
                    coalesce(ai.nro_factura, ai.sec || '-' || ai.suc || '-' || ai.nro) as nros_factura,
                    coalesce(to_char(ai.date_invoice, 'DD-MM-YYYY'), '') as fecha,
                    round(sum(case when t.name like '%10%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """
                    then(ail.price_total) * (select cast (set_venta as numeric)
                    from res_currency_rate where
                    currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else ail.price_total end) / 1.1 else 0 end ), 0)  as gravada_10,
                    round(sum(case when t.name like '%10%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else (ail.price_total) end) / 11 else '0' end ), 0) as impuesto_10,
                    round(sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else (ail.price_total) end) / 1.05 else '0' end ), 0) as gravada_5,
                    round(sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else (ail.price_total) end) / 21 else '0' end ), 0 ) as iva_5,
                    sum(case when t.name like '%Exen%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_unit * ail.quantity) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round( ail.price_subtotal) end) else '0' end ) as exentas,
                    (round(sum(case when t.name like '%10%' then (case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then (ail.price_total) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else ail.price_total end) / 1.1 else 0 end ), 0)  +

                    round(sum(case when t.name like '%10%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else (ail.price_total) end) / 11 else 0 end ), 0) +

                    round(sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else (ail.price_total) end) / 1.05 else 0 end ), 0) + 
                    round(sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total / 21) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else (ail.price_total) end) / 21 else 0 end ), 0 ) + sum(case when t.name like '%Exen%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_unit * ail.quantity) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round(ail.price_subtotal) end) else 0 end ) )as total,
                    cast(coalesce(ai.tipo_factura, 1) as text) as tipo_factura,
                    coalesce(ai.cantidad_cuotas, 0) as cantidad_cuotas,
                    ai.timbrado as timbrado 
                    from account_invoice as ai INNER JOIN account_invoice_line as ail on ai.id = ail.invoice_id
                        INNER JOIN account_invoice_line_tax as at on ail.id = at.invoice_line_id INNER JOIN account_tax as t on at.tax_id = t.id INNER JOIN res_partner as rp on ai.partner_id = rp.id
                        inner join res_currency as rc on ai.currency_id = rc.id
                        inner join ruc_tipo_documento as rtc on ai.tipo_comprobante = rtc.id 
                    where ai.type in ('out_invoice', 'in_refund') and ai.state not in ('cancel', 'draft') and extract(month from ai.date_invoice)  = """ + str(
            self.mes) + """ and extract(year from ai.date_invoice) = """ + str(
            self.periodo) + """ and ai.company_id =""" + str(self.env.company.id) + """ and (rp.ruc not in ('44444401-7', '77777701-0') or ( (case when rp.parent_id is null then rp.ruc else (select re.ruc from res_partner re where re.id=rp.parent_id) end) is not null) ) 
                    GROUP BY tipo_registro, rtc.codigo_hechauka, ruc, dv, nombre, ai.timbrado, tipo_comprobante, ai.state, rp.parent_id, rc.id, ai.amount_total, nros_factura, fecha, tipo_factura, cantidad_cuotas, ai.date_invoice, ai.company_id

                    union all

                    select 2 as tipo_registro,
                    '44444401'  as ruc,
                    '7'  as dv,
                    'Importes consolidados'  as nombre,
                    0 as tipo_comprobante,
                    '0' as nros_factura,
                    coalesce(to_char(max(ai.date_invoice), 'DD-MM-YYYY'), '') as fecha,
                    round(sum(case when t.name like '%10%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total / 1.1) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else ail.price_total / 1.1 end) else '0' end ), 0) as gravada_10,
                    round(sum(case when t.name like '%10%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 11) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else (ail.price_total / 11) end) else '0' end ), 0) as impuesto_10,
                    round(sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total / 1.05) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else (ail.price_total / 1.05) end) else '0' end ), 0) as gravada_5,
                    round(sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total / 21) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else round(ail.price_total / 21) end) else '0' end ), 0 ) as iva_5,
                    sum(case when t.name like '%Exen%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_unit * ail.quantity) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round(ail.price_subtotal) end) else '0' end ) as exentas,
                    (sum(case when t.name like '%10%' then (case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 1.1) * (select cast (set_venta as numeric)from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round(ail.price_total / 1.1, 0) end) else 0 end )  + sum(case when t.name like '%10%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 11) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round((ail.price_total / 11), 0) end) else 0 end ) + sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 1.05) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round(ail.price_total / 1.05) end) else 0 end ) + sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 21) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round((ail.price_total / 21), 0) end) else 0 end ) + sum(case when t.name like '%Exen%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_unit * ail.quantity) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round(ail.price_subtotal) end) else 0 end ) )as total,
                    cast(1 as text) as tipo_factura,
                    0 as cantidad_cuotas,
                    '0' as timbrado

                    from account_invoice as ai INNER JOIN account_invoice_line as ail on ai.id = ail.invoice_id 
                                              INNER JOIN account_invoice_line_tax as at on ail.id = at.invoice_line_id
                                              INNER JOIN account_tax as t on at.tax_id = t.id
                                              INNER JOIN res_partner as rp on ai.partner_id = rp.id
                                              inner join res_currency as rc on ai.currency_id = rc.id

                    where ai.type in ('out_invoice', 'in_refund') and ai.state not in ('cancel', 'draft') and extract(month from ai.date_invoice)  = """ + str(
            self.mes) + """ and extract(year from ai.date_invoice) =  """ + str(
            self.periodo) + """ and ai.company_id = """ + str(self.env.company.id) + """ and (rp.ruc = '44444401-7' or ((case when rp.parent_id is null then rp.ruc else (select re.ruc from res_partner re where re.id=rp.parent_id) end) is null))
                    GROUP BY tipo_registro, tipo_comprobante, ai.company_id

                    union all

                    select 2 as tipo_registro,
                          '77777701'  as ruc,
                          '0'  as dv,
                          'Ventas a Agentes Diplomáticos'  as nombre,
                          0 as tipo_comprobante,
                         '0' as nros_factura,
                          coalesce(to_char(max(ai.date_invoice), 'DD-MM-YYYY'), '') as fecha,
                          round(sum(case when t.name like '%10%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total / 1.1) * (select cast (set_venta as numeric) from res_currency_rate where  currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else ail.price_total / 1.1 end) else '0' end ), 0) as gravada_10,
                          round(sum(case when t.name like '%10%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 11) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else (ail.price_total / 11) end) else '0' end ), 0) as impuesto_10,
                          round(sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total / 1.05) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else (ail.price_total / 1.05) end) else '0' end ), 0) as gravada_5,
                          round(sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then(ail.price_total / 21) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id) else round(ail.price_total / 21) end) else '0' end ), 0 ) as iva_5, 
                          sum(case when t.name like '%Exen%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_unit * ail.quantity) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round(ail.price_subtotal) end) else '0' end ) as exentas,
                          (sum(case when t.name like '%10%' then (case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 1.1) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round(ail.price_total / 1.1, 0) end) else 0 end )  + sum(case when t.name like '%10%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 11) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round((ail.price_total / 11), 0) end) else 0 end ) + sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 1.05) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round(ail.price_total / 1.05) end) else 0 end ) + sum(case when t.name like '%5%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_total / 21) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round((ail.price_total / 21), 0) end) else 0 end ) + sum(case when t.name like '%Exen%' then(case when rc.id != """ + str(
            self.env.company.currency_id.id) + """ then round((ail.price_unit * ail.quantity) * (select cast (set_venta as numeric) from res_currency_rate where currency_id = rc.id and name = ai.date_invoice and company_id = ai.company_id), 0) else round(ail.price_subtotal) end) else 0 end ) )as total,
                          cast(1 as text) as tipo_factura,
                          0 as cantidad_cuotas,
                          '0' as timbrado

                    from account_invoice as ai INNER JOIN account_invoice_line as ail on ai.id = ail.invoice_id
                                              INNER JOIN account_invoice_line_tax as at on ail.id = at.invoice_line_id
                                              INNER JOIN account_tax as t on at.tax_id = t.id 
                                              INNER JOIN res_partner as rp on ai.partner_id = rp.id
                                              inner join res_currency as rc on ai.currency_id = rc.id
                    where ai.type in ('out_invoice', 'in_refund') and ai.state not in ('cancel', 'draft') and extract(month from ai.date_invoice)  =  """ + str(
            self.mes) + """ and extract(year from ai.date_invoice) =  """ + str(
            self.periodo) + """ and ai.company_id = """ + str(self.env.company.id) + """ and rp.ruc = '77777701-0'
                    GROUP BY tipo_registro, tipo_comprobante, ai.company_id
                    order by fecha, nros_factura asc """
        # raise ValidationError( ' s %s' % query)
        cr.execute(query)

        ventas = cr.fetchall()

        # print(ventas)
        # for aa in ventas:
        #     print(aa)
        #     print('eeaaa')
        #     print('----')
        #     for ii,ee in enumerate(aa):
        #
        #         print(aa[ii])
        #         if ii==7:
        #             print('!!!!!!')
        #             print(aa[ii])
        #             aa[ii]=int(ee)
        #             print('!!!!!!')
        #         print(ee)
        #         print('---')

        lista_archivos = []
        cant_archivos = list(chunks(ventas, CANT_REGISTROS_HECHAUKA))
        try:
            unicode('')
        except NameError:
            unicode = str
        archivo = None
        nombre_mes = self.mes
        for m in MESES:
            if m[0] == self.mes:
                nombre_mes = m[1]
        texto = []
        aa = list()

        for ii, ventas in enumerate(cant_archivos):
            # print(ventas)
            # los datos como cantidad de registros y monto total se cargan despues de los detalles
            # quedan vacios temporalmente hasta calcular los datos
            texto = [[]]
            monto_total = 0
            for v in ventas:
                # print(monto_total)

                # v[ii][7]=int(v[7])
                # v[ii][8]=int(v[8])
                # v[ii][9]=int(v[9])
                # v[ii][10]=int(v[10])
                # v[ii][11]=int(v[11])
                # v[ii][12]=int(v[12])
                aa = list()
                monto_total += int(v[12])  # controlar que este sumando en la columna correcta
                # texto.append("\t")
                for i, x in enumerate(v):
                    if i > 6 and i < 13:
                        aa.append("".join(unicode(int(x))))
                    else:
                        aa.append("".join(unicode(x)))

                texto.append("\t".join([unicode(x) for x in aa]))

            encabezado = "\t".join(['1',
                                    periodo,
                                    self.tipo_presentacion,
                                    '921',
                                    '221',
                                    self.env.company.ruc,
                                    self.env.company.dv,
                                    self.env.company.razon_social,
                                    self.env.company.ruc_representante,  # RUC REPRESENTANTE LEGAL
                                    self.env.company.dv_representante,  # DV REPRESENTANTE LEGAL
                                    self.env.company.representante_legal,
                                    str(len(ventas)),  # cantidad registros
                                    str(monto_total),  # monto total
                                    '2',  # VERSION DEL FORMULARIO

                                    ])

            texto[0] = encabezado
            contenido = ("\n".join(texto)).encode('utf-8')

            archivo = base64.b64encode(contenido)
            filename = 'ventas_' + str(nombre_mes) + '_' + str(self.periodo) + '_' + str(ii + 1) + '.txt'
            self.name = filename
            archi = self.env['set.hechauka.archivo']
            aviejo = archi.search([('filename', '=', filename)])
            for a in aviejo:
                a.unlink()

            datos = {
                'archivo': base64.b64encode(contenido),
                'name': str(self.periodo) + str(self.mes),
                'nombre': filename,
                'mes': nombre_mes,
                'anio': self.periodo,
                'filename': filename,
            }
            # lista_archivos.append([0, False, datos])

            # new_line = archi.new(datos)
            archi.create(datos)
            # archi += new_line
            # self.archivo = archivo
        if not archivo:
            raise ValidationError(
                'No se han encontrado registros. Verifique que las Facturas de Venta o Notas de Credito correspondiente al mes seleccionado se encuentren en estado Validado o Pagado')
        return archivo


class DownloadPDF(http.Controller):

    @http.route('/getHechauka/txt/<int:id>', auth='public')
    def generarTXT(self, id=None, **kw):
        record = request.env['set.hechauka'].browse(id)

        iva10 = record.env.ref('l10n_py.grupo_10')
        iva5 = record.env.ref('l10n_py.grupo_5')
        exentas = record.env.ref('l10n_py.grupo_exenta')

        company_id = record.env.user.company_id

        dias = calendar.monthrange(record.periodo, int(record.mes))
        # fecha_inicio=str(record.periodo)+'-'+str(record.mes)+'-'+str(dias[0])
        fecha_inicio = str(record.periodo) + '-' + str(record.mes) + '-01'
        # fecha_fin=str(record.periodo)+'-'+str(record.mes)+'-'+str(dias[1])
        fecha_fin = str(record.periodo) + '-' + str(record.mes) + '-' + str(dias[1])
        _logger.info('dias')
        _logger.info(dias)

        # Variables,  Listas y Diccionario a ser utilizados
        lista_totales = []
        impuestos = []
        monto_iva10 = 0.0
        monto_gravada10 = 0.0
        monto_iva5 = 0.0
        monto_gravada5 = 0.0
        monto_exentas = 0.0
        total_iva10 = total_iva5 = total_grav10 = total_grav5 = total_exentas = 0.0
        diccionario_facturas = collections.OrderedDict()
        tipo = 0

        # FILTROS
        domain = []
        # domain += [('company_id', '=', company_id.id), ('date_invoice', '>=', fecha_inicio), ('date_invoice', '<=', fecha_fin)]
        domain += [('company_id', '=', company_id.id), ('date', '>=', fecha_inicio), ('date', '<=', fecha_fin),
                   ('state', 'in', ('open', 'paid')), ('no_mostrar_libro_iva', '=', False)]

        if record.tipo == '221':
            # SI ES VENTA FACTURA CLIENTE CON NOTA DE CREDITO PROVEEDOR
            domain += [('type', 'in', ('out_invoice', 'in_refund'))]
        else:
            # SI ES COMPRA FACTURA PROVEEDOR CON NOTA DE CREDITO CLIENTE
            domain += [('type', 'in', ('in_invoice', 'out_refund'))]

        # AQUI SE APLICA LA MISMA LOGICA DEL LIBRO IVA
        facturas = record.env['account.invoice'].search(domain, order='nro_factura')
        for f in facturas:
            m = f.move_id
            for linea in m.line_ids:

                if linea.tax_line_id:
                    if linea.tax_line_id.tax_group_id.id == iva10.id:
                        monto_iva10 += abs(round(linea.balance, 0))
                        # if f.type in ('out_invoice', 'in_invoice'):
                        total_iva10 += abs(round(linea.balance, 0))
                        # else:
                        #     nc_total_iva10 += abs(round(linea.balance, 0))
                    if linea.tax_line_id.tax_group_id.id == iva5.id:
                        monto_iva5 += abs(round(linea.balance, 0))
                        # if f.type in ('out_invoice', 'in_invoice'):
                        total_iva5 += abs(round(linea.balance, 0))
                        # else:
                        #     nc_total_iva5 += abs(round(linea.balance, 0))

                else:
                    if len(linea.tax_ids) == 1:
                        linea_tax = linea.tax_ids
                        # Si la factura posee iva 10%
                        if linea_tax.tax_group_id.id == iva10.id:
                            monto_gravada10 += round(linea.balance, 0)
                            # if f.type in ('out_invoice', 'in_invoice'):
                            total_grav10 += round(linea.balance, 0)
                            # else:

                            # nc_total_grav10 += round(linea.balance, 0)
                            # print(nc_total_grav10)
                        # Si la factura posee iva 5%
                        if linea_tax.tax_group_id.id == iva5.id:
                            monto_gravada5 += round(linea.balance, 0)
                            # if f.type in ('out_invoice', 'in_invoice'):
                            total_grav5 += round(linea.balance, 0)
                            # else:
                            #     nc_total_grav5 += round(linea.balance, 0)
                        # Si la factura posee exentas%
                        if linea_tax.tax_group_id.id == exentas.id:
                            monto_exentas += round(linea.balance, 0)
                            # if f.type in ('out_invoice', 'in_invoice'):
                            total_exentas += round(linea.balance, 0)
                            # else:
                            #     nc_total_exentas += round(linea.balance, 0)

            monto_gravada10 = abs(monto_gravada10)
            # total_grav10 = abs(total_grav10)
            # nc_total_grav10 = abs(nc_total_grav10)
            monto_gravada5 = abs(monto_gravada5)
            # total_grav5 = abs(total_grav5)
            # nc_total_grav5= abs(nc_total_grav5)
            monto_exentas = abs(monto_exentas)

            if monto_gravada10 > 0:
                monto_10 = monto_iva10 + monto_gravada10
                monto_nuevo_iva10 = round(monto_10 / 11)
                monto_nuevo_gravada_10 = round(monto_10 / 1.1)
            else:
                monto_nuevo_iva10 = monto_iva10
                monto_nuevo_gravada_10 = monto_gravada10
            if monto_gravada5 > 0:
                monto_5 = monto_iva5 + monto_gravada5
                monto_nuevo_iva5 = round(monto_5 / 21)
                monto_nuevo_gravada_5 = round(monto_5 / 1.05)

            else:
                monto_nuevo_iva5 = monto_iva5
                monto_nuevo_gravada_5 = monto_gravada5
            impuestos.append(monto_nuevo_gravada_10)
            impuestos.append(monto_nuevo_iva10)
            impuestos.append(monto_nuevo_gravada_5)
            impuestos.append(monto_nuevo_iva5)
            impuestos.append(monto_exentas)
            # impuestos.append(monto_gravada10)
            # impuestos.append(monto_iva10)
            # impuestos.append(monto_gravada5)
            # impuestos.append(monto_iva5)
            # impuestos.append(monto_exentas)

            # Diccionario donde el key es la Factura anidadas a sus impuestos
            diccionario_facturas.setdefault(f, impuestos)

            # Se resetea los valores para la siguiente Factura
            impuestos = []
            monto_iva10 = monto_iva5 = monto_exentas = monto_gravada5 = monto_gravada10 = 0.0

        # Lista de totales de las facturas
        lista_totales.append(total_grav10)
        lista_totales.append(total_iva10)
        lista_totales.append(total_grav5)
        lista_totales.append(total_iva5)
        lista_totales.append(total_exentas)

        fac = diccionario_facturas.items()
        # -->FIN DE LA LOGICA DEL LIBRO IVA <--#

        # DATOS Y VARIABLES PARA EL TXT
        periodo = str(record.periodo) + str(record.mes)
        cantidad = len(facturas)
        resta_cantidad_ruc4 = resta_cantidad_ruc6 = resta_cantidad_ruc7 = resta_cantidad_ruc8 =0
        nombre_mes = record.mes
        monto_total = 0
        # Lista donde estara los datos
        txt = []
        txt.append('LINEA A SER REEMPLAZADA POR EL ENCABEZADO AL FINAL')
        txt.append("\n")
        nombre = False
        gravada_10_ruc4 =gravada_10_ruc6 =gravada_10_ruc7 =gravada_10_ruc8 = 0
        iva_10_ruc4 = iva_10_ruc6 = iva_10_ruc7 = iva_10_ruc8 = 0
        gravada_5_ruc4 = gravada_5_ruc6 = gravada_5_ruc7 = gravada_5_ruc8 = 0
        iva_5_ruc4 = iva_5_ruc6 = iva_5_ruc7 = iva_5_ruc8 =  0
        iva_exento_ruc4 = iva_exento_ruc6 = iva_exento_ruc7 = iva_exento_ruc8 = 0
        for f in fac:

            # ---> VARIABLES QUE SE SETEAN EN BASE A SU CONDICION <-- #
            ruc = f[0].ruc_factura[:f[0].ruc_factura.find('-')]
            dv = f[0].ruc_factura[f[0].ruc_factura.find('-') + 1:]
            if f[0].partner_id.parent_id:
                nombre = f[0].partner_id.parent_id.name
            else:
                nombre = f[0].partner_id.name
            if f[0].tipo_comprobante.codigo_hechauka == 8:
                if f[0].partner_no_despachante:
                    nombre = f[0].partner_no_despachante.name
            if f[0].tipo_comprobante:
                if f[0].tipo_comprobante.codigo_hechauka == 4:
                    nombre = 'Proveedores del Exterior'
                    ruc = '99999901'
                    dv = '0'
                if f[0].tipo_comprobante.codigo_hechauka in [1, 2, 3, 5]:
                    numero_timbrado = str(f[0].timbrado)
                else:
                    numero_timbrado = '0'
                tipo_documento = str(f[0].tipo_comprobante.codigo_hechauka)
            if ruc == '44444401':
                nombre = 'Importes consolidados'
            elif ruc == '66666601':
                if record.env.user.company_id.exportador:
                    nombre = 'Clientes de Exportación'
                else:
                    nombre = 'Clientes del Exterior'
                    ruc = '88888801'
                    dv = '5'
            elif f[0].fiscal_position_id:
                if f[0].fiscal_position_id.tax_ids[0].tax_dest_id.tax_group_id.id == exentas.id:
                    nombre = 'Clientes del Exterior'
                    ruc = '77777701'
                    dv = '0'

            if f[0].nro_factura:
                numero_documento = f[0].nro_factura
            else:
                numero_documento = None
            fecha_documento = f[0].date
            fecha_documento = datetime.strptime(str(fecha_documento), '%Y-%m-%d').strftime("%d-%m-%Y")
            if f[0].tipo_comprobante.codigo_hechauka == 4:
                gravada_10 = f[1][1] * 10
                total_despacho = gravada_10 + f[1][1] + f[1][2] + f[1][3] + f[1][4]
                m_iva_10 = f[1][1]
                gravada_5 = f[1][2]
                m_iva_5 = f[1][3]
                m_iva_exento = f[1][4]
                total_linea = total_despacho
                if record.tipo == '221':
                    # total_linea=sum([l.credit for l in f[0].move_id.line_ids])
                    total_linea = gravada_5 + gravada_10 + m_iva_exento + m_iva_10 + m_iva_5
                else:
                    total_linea = gravada_5 + gravada_10 + m_iva_exento
            else:
                gravada_10 = f[1][0]
                m_iva_10 = f[1][1]
                gravada_5 = f[1][2]
                m_iva_5 = f[1][3]
                m_iva_exento = f[1][4]
                if record.tipo == '221':
                    # total_linea=sum([l.credit for l in f[0].move_id.line_ids])
                    total_linea = gravada_5 + gravada_10 + m_iva_exento + m_iva_10 + m_iva_5
                else:
                    total_linea = gravada_5 + gravada_10 + m_iva_exento
            monto_total += total_linea

            tipo_operacion = 0
            condicion_compra = f[0].tipo_factura
            if condicion_compra == 1:
                cantidad_cuotas = 0
            else:
                cantidad_cuotas = 1
            if not condicion_compra:
                condicion_compra = 2
            # --> FIN <--#
            # DATOS DE UNA LINEA
            #venta
            if record.tipo == '221':
                if ruc not in ('44444401','66666601','88888801','77777701'):
                    data = [
                        '2',
                        str(ruc),
                        str(dv),
                        str(nombre),
                        str(tipo_documento),
                        str(numero_documento),
                        str(fecha_documento),
                        str(int(gravada_10)),
                        str(int(m_iva_10)),
                        str(int(gravada_5)),
                        str(int(m_iva_5)),
                        str(int(m_iva_exento)),
                        str(int(total_linea)),
                        # str(tipo_operacion),
                        str(condicion_compra),
                        str(cantidad_cuotas),
                        str(numero_timbrado),
                    ]
                    # SE AGREGA TABULADOR A LA LINEA
                    fila = ("\t".join(data))
                    # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
                    txt.append(fila)
                    # SE LE AGREGA SALTO DE LINEA AL TXT
                    txt.append("\n")
                else:
                    #suma de valores de los clientes con ruc genericos
                    if ruc == '44444401':
                        gravada_10_ruc4+=int(gravada_10)
                        iva_10_ruc4+=int(m_iva_10)
                        gravada_5_ruc4+=int(gravada_5)
                        iva_5_ruc4+=int(m_iva_5)
                        iva_exento_ruc4+=int(m_iva_exento)
                        resta_cantidad_ruc4 += 1
                        nro_factura_4=numero_documento
                        fecha_4=fecha_documento
                        timbrado_4=numero_timbrado
                    elif ruc == '66666601':
                        gravada_10_ruc6 += int(gravada_10)
                        iva_10_ruc6 += int(m_iva_10)
                        gravada_5_ruc6 += int(gravada_5)
                        iva_5_ruc6 += int(m_iva_5)
                        iva_exento_ruc6 += int(m_iva_exento)
                        resta_cantidad_ruc6 += 1
                        nro_factura_6=numero_documento
                        fecha_6= fecha_documento
                        timbrado_6 = numero_timbrado
                    elif ruc == '77777701':
                        gravada_10_ruc7 += int(gravada_10)
                        iva_10_ruc7 += int(m_iva_10)
                        gravada_5_ruc7 += int(gravada_5)
                        iva_5_ruc7 += int(m_iva_5)
                        iva_exento_ruc7 += int(m_iva_exento)
                        resta_cantidad_ruc7 += 1
                        nro_factura_7=numero_documento
                        fecha_7 = fecha_documento
                        timbrado_7 = numero_timbrado
                    elif ruc == '88888801':
                        print(iva10)
                        gravada_10_ruc8 += int(gravada_10)
                        iva_10_ruc8 += int(m_iva_10)
                        gravada_5_ruc8 += int(gravada_5)
                        iva_5_ruc8 += int(m_iva_5)
                        iva_exento_ruc8 += int(m_iva_exento)
                        resta_cantidad_ruc8 += 1
                        nro_factura_8=numero_documento
                        fecha_8 = fecha_documento
                        timbrado_8 = numero_timbrado
            #compra
            else:
                data = [
                    '2',
                    str(ruc),
                    str(dv),
                    str(nombre),
                    str(numero_timbrado),
                    str(tipo_documento),
                    str(numero_documento),
                    str(fecha_documento),
                    str(int(gravada_10)),
                    str(int(m_iva_10)),
                    str(int(gravada_5)),
                    str(int(m_iva_5)),
                    str(int(m_iva_exento)),
                    # str(int(total_linea)),
                    str(tipo_operacion),
                    str(condicion_compra),
                    str(cantidad_cuotas),

                ]

                # SE AGREGA TABULADOR A LA LINEA
                fila = ("\t".join(data))
                # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
                txt.append(fila)
                # SE LE AGREGA SALTO DE LINEA AL TXT
                txt.append("\n")
        total_linea_ruc4 = gravada_5_ruc4 + gravada_10_ruc4 + iva_exento_ruc4 + iva_10_ruc4 + iva_5_ruc4
        total_linea_ruc6 = gravada_5_ruc6 + gravada_10_ruc6 + iva_exento_ruc6 + iva_10_ruc6 + iva_5_ruc6
        total_linea_ruc7 = gravada_5_ruc7 + gravada_10_ruc7 + iva_exento_ruc7 + iva_10_ruc7 + iva_5_ruc7
        total_linea_ruc8 = gravada_5_ruc8 + gravada_10_ruc8 + iva_exento_ruc8 + iva_10_ruc8 + iva_5_ruc8
        if total_linea_ruc4 >0:
            data = [
                '2',
                str('44444401'),
                str('7'),
                str('Importes consolidados'),
                str(1),
                str(nro_factura_4),
                str(fecha_4),
                str(int(gravada_10_ruc4)),
                str(int(iva_10_ruc4)),
                str(int(gravada_5_ruc4)),
                str(int(iva_5_ruc4)),
                str(int(iva_exento_ruc4)),
                str(int(total_linea_ruc4)),
                # str(tipo_operacion),
                str(1),
                str(0),
                str(timbrado_4),
            ]
            # SE AGREGA TABULADOR A LA LINEA
            fila = ("\t".join(data))
            # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
            txt.append(fila)
            # SE LE AGREGA SALTO DE LINEA AL TXT
            txt.append("\n")
        if total_linea_ruc6 > 0:
            data = [
                '2',
                str('66666601'),
                str('6'),
                str('Clientes de Exportación'),
                str(1),
                str(nro_factura_6),
                str(fecha_6),
                str(int(gravada_10_ruc6)),
                str(int(iva_10_ruc6)),
                str(int(gravada_5_ruc6)),
                str(int(iva_5_ruc6)),
                str(int(iva_exento_ruc6)),
                str(int(total_linea_ruc6)),
                # str(tipo_operacion),
                str(1),
                str(0),
                str(timbrado_6),
            ]
            # SE AGREGA TABULADOR A LA LINEA
            fila = ("\t".join(data))
            # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
            txt.append(fila)
            # SE LE AGREGA SALTO DE LINEA AL TXT
            txt.append("\n")
        if total_linea_ruc7 > 0:
            data = [
                '2',
                str('77777701'),
                str('0'),
                str('Ventas a Agentes Diplomáticos'),
                str(1),
                str(nro_factura_7),
                str(fecha_7),
                str(int(gravada_10_ruc7)),
                str(int(iva_10_ruc7)),
                str(int(gravada_5_ruc7)),
                str(int(iva_5_ruc7)),
                str(int(iva_exento_ruc7)),
                str(int(total_linea_ruc7)),
                # str(tipo_operacion),
                str(1),
                str(0),
                str(timbrado_7),
            ]
            # SE AGREGA TABULADOR A LA LINEA
            fila = ("\t".join(data))
            # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
            txt.append(fila)
            # SE LE AGREGA SALTO DE LINEA AL TXT
            txt.append("\n")

        if total_linea_ruc8 > 0:
            data = [
                '2',
                str('88888801'),
                str('5'),
                str('Clientes del Exterior'),
                str(1),
                str(nro_factura_8),
                str(fecha_8),
                str(int(gravada_10_ruc8)),
                str(int(iva_10_ruc8)),
                str(int(gravada_5_ruc8)),
                str(int(iva_5_ruc8)),
                str(int(iva_exento_ruc8)),
                str(int(total_linea_ruc8)),
                # str(tipo_operacion),
                str(1),
                str(0),
                str(timbrado_8),
            ]
            # SE AGREGA TABULADOR A LA LINEA
            fila = ("\t".join(data))
            # SE AGREGA LINEA TABULADA A LA LISTA DEL TXT
            txt.append(fila)
            # SE LE AGREGA SALTO DE LINEA AL TXT
            txt.append("\n")

        # raise ValidationError('hola')
        if record.tipo == '221':
            tipo = 'venta'
            if resta_cantidad_ruc4 >0:
                cantidad=cantidad-resta_cantidad_ruc4+1
            if resta_cantidad_ruc6 >0:
                cantidad=cantidad-resta_cantidad_ruc6+1
            if resta_cantidad_ruc7 >0:
                cantidad=cantidad-resta_cantidad_ruc7+1
            if resta_cantidad_ruc8 >0:
                cantidad=cantidad-resta_cantidad_ruc8+1
            encabezado = [
                '1',
                periodo,
                record.tipo_presentacion,
                '921',
                '221',
                record.env.user.company_id.ruc,
                record.env.user.company_id.dv,
                record.env.user.company_id.razon_social,
                record.env.user.company_id.ruc_representante,  # RUC REPRESENTANTE LEGAL
                record.env.user.company_id.dv_representante,  # DV REPRESENTANTE LEGAL
                record.env.user.company_id.representante_legal,
                str(cantidad),  # cantidad registros
                str(int(monto_total)),  # monto total
                '2',  # VERSION DEL FORMULARIO
            ]
        else:
            tipo = 'compra'
            encabezado = [
                '1',
                periodo,
                record.tipo_presentacion,
                '911',
                '211',
                record.env.user.company_id.ruc,
                record.env.user.company_id.dv,
                record.env.user.company_id.razon_social,
                record.env.user.company_id.ruc_representante,  # RUC REPRESENTANTE LEGAL
                record.env.user.company_id.dv_representante,  # DV REPRESENTANTE LEGAL
                record.env.user.company_id.representante_legal,  # REPRESENTANTE LEGAL
                str(cantidad),  # cantidad registros
                str(int(monto_total)),  # monto total
                'SI' if record.env.user.company_id.exportador else 'NO',  # EXPORTADOR
                # 'NO',  # EXPORTADOR
                '2'
            ]
        # SE AGREGA TABULADOR AL ENCABEZADO
        linea0 = ("\t".join(encabezado))
        # SE AGREGA ENCABEZADO CON TABULADOR A LA LISTA TXT
        txt[0] = linea0
        filename = str(tipo) + '_' + str(nombre_mes) + '_' + str(record.periodo) + '.txt'
        return request.make_response(
            txt,
            [('Content-Type', 'text/plain'),
             ('Content-Disposition', content_disposition(filename))])